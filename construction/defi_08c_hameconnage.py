"""Défi C du mardi 10/11 (correction) : un hameçonnage est un problème d'accès, au moins P2.

Constaté le 05/11 : « J'ai cliqué sur le lien d'un mail suspect et j'ai saisi mon mot de passe » était classé
reseau · P3 par le modèle. Le dataset (cas C10) attend acces · P2.

Le défi, sur une copie de l'étape 8 (construction/atelier/mon_helpdesk.py) :
    - une fonction est_hameconnage(ticket) : des mots, sans LLM, donc explicable et testable ;
    - une fonction regles_metier(ticket, categorie, priorite) qui applique le plancher d'urgence ET la nouvelle règle ;
    - l'appeler dans trier ET dans la tâche de --evaluer : sinon on mesure autre chose que ce qu'on livre.

Lancer :
    uv run --project infrastructure python construction/defi_08c_hameconnage.py --thread t-phish "J'ai cliqué sur le lien d'un mail suspect et j'ai saisi mon mot de passe"
    uv run --project infrastructure python construction/defi_08c_hameconnage.py --thread t-mdp "J'ai oublié mon mot de passe"
    uv run --project infrastructure python construction/defi_08c_hameconnage.py --evaluer

Réussi si : le premier ticket sort en acces · P2, le second n'est PAS touché par la règle, et dans l'experiment
le cas C10 passe à categorie_juste = 1 et priorite_juste = 1.
"""
import argparse
from datetime import datetime
import asyncio
import json
import logging
from pathlib import Path
from typing import Literal

import httpx
import openai
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langfuse import observe, propagate_attributes
from langfuse.experiment import Evaluation
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import NodeError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, RetryPolicy, TimeoutPolicy, interrupt
from pydantic import BaseModel, Field

from helpdesk_ops import kb
from helpdesk_ops.config import basculer_vllm, creer_llm
from helpdesk_ops.donnees import INVENTAIRE
from helpdesk_ops.evaluation import creer_juge, ev_moyennes, ev_qualification, noter, resume, synchroniser_dataset
from helpdesk_ops.jalons.j1 import REFUS
from helpdesk_ops.jalons.j3 import CONSIGNE_ACCES, DESCRIPTION_ACCES, etat_compte
from helpdesk_ops.mcp_inventaire import filtrer_outils, transport_stdio
from helpdesk_ops.multi_agents import CONSIGNES, DESCRIPTIONS, PROMPT_COORDINATEUR
from helpdesk_ops.observabilite import init_observabilite
from helpdesk_ops.reseau import RESEAU, ping_serveur
from helpdesk_ops.securite import creer_garde_fou
from helpdesk_ops.texte import normaliser

parser = argparse.ArgumentParser(description="HelpDesk-Ops, étape 8 : évaluation et sécurité")
parser.add_argument("message", nargs="?", default="Outlook plante dès que j'ouvre une pièce jointe")
parser.add_argument("--thread", default="conv-demo", help="identifiant de la conversation")
parser.add_argument("--oublier", action="store_true", help="effacer la conversation (RGPD)")
parser.add_argument("--approuver", metavar="NOM", help="valider le ticket P1 en attente")
parser.add_argument("--refuser", metavar="NOM", help="refuser le ticket P1 en attente")
parser.add_argument("--motif", default="", help="motif du refus")
parser.add_argument("--panne", type=int, default=0, help="nombre d'échecs de la supervision avant succès")
parser.add_argument("--indexer", action="store_true", help="(ré)indexer data/kb dans Qdrant, puis quitter")
parser.add_argument("--juger", action="store_true", help="noter la fidélité de la réponse avec le juge LLM")
parser.add_argument("--evaluer", action="store_true", help="lancer l'experiment sur le dataset, puis quitter")
args = parser.parse_args()

RACINE = next(p for p in Path(__file__).resolve().parents if (p / "infrastructure").is_dir())   # la racine du cours
SORTIE = Path(__file__).resolve().parent / "sortie"
BASE = RACINE / "data" / "checkpoints" / "construction.sqlite"
TICKETS = RACINE / "data" / "checkpoints" / "construction_tickets.json"

llm = creer_llm("agent")                         # le modèle désigné par infrastructure/.env
langfuse, handler = init_observabilite()         # client Langfuse avec masque PII + CallbackHandler

if args.indexer:
    print(f"📚 {kb.indexer(recreer=True)} morceaux indexés dans la collection {kb.nom_collection()}")
    raise SystemExit(0)


class TicketDecision(BaseModel):
    """Qualification d'une demande de support."""
    categorie: Literal["reseau", "materiel", "logiciel", "acces", "autre"]
    priorite: Literal["P1", "P2", "P3", "P4"] = Field(
        description="P1 : production arrêtée ou nombreux utilisateurs bloqués ; P4 : simple demande")
    resume: str = Field(description="résumé du problème en une phrase, sans donnée personnelle")


# --------------------------------------------------------------------------- la chaîne de tri (LCEL)
PROMPT_TRI = ChatPromptTemplate.from_messages([
    ("system",
     "Tu es l'agent de tri N1 du help-desk de NordTech SA. Qualifie le ticket. "
     "Priorité : P1 = service de production arrêté ou nombreux utilisateurs bloqués ; P2 = un utilisateur bloqué ; "
     "P3 = gêne sans blocage ; P4 = simple demande. Le résumé ne contient aucune donnée personnelle."),
    ("human", "Ticket : {ticket}"),
])
tri = PROMPT_TRI | llm.with_structured_output(TicketDecision, method="json_schema")


# --------------------------------------------------------------------------- les règles métier (sans LLM)
def estimer_priorite(ticket: str) -> str:
    """P1 si un mot d'urgence apparaît, sinon P3 : simple, donc explicable."""
    texte = normaliser(ticket)
    return "P1" if any(m in texte for m in ("bloque", "urgent", "production", "tous les utilisateurs")) else "P3"


# ═══ NOUVEAU (défi C) : une règle de sécurité, écrite en Python, appliquée APRÈS le modèle ═══
def est_hameconnage(ticket: str) -> bool:
    """Un lien ou un mail suspect ET un mot de passe saisi : le compte est peut-être compromis."""
    texte = normaliser(ticket)
    return "mot de passe" in texte and any(m in texte for m in ("lien", "mail suspect", "phishing", "hameconnage"))


def regles_metier(ticket: str, categorie: str, priorite: str) -> tuple[str, str]:
    """Les règles s'appliquent dans le graphe ET dans l'experiment : on mesure ce qu'on livre."""
    if estimer_priorite(ticket) == "P1":
        priorite = "P1"                                                 # le plancher d'urgence (étape 6)
    if est_hameconnage(ticket):
        categorie, priorite = "acces", min(priorite, "P2")             # au moins P2 : « P1 » < « P2 » < « P3 »
    return categorie, priorite


def file_attente(categorie: str) -> str:
    return "N2-infra" if categorie in ("reseau", "materiel") else "N1"


decider = creer_garde_fou(llm)        # renvoie SUPPORT, HORS_PERIMETRE ou INJECTION ; en cas de doute : HORS_PERIMETRE

if args.evaluer:
    def tache(*, item, **kwargs) -> dict:
        question = item.input["question"]
        decision = decider(question)
        if decision != "SUPPORT":
            return {"refus": decision, "categorie": None, "priorite": None}
        q = tri.invoke({"ticket": question})
        if q is None:
            return {"refus": None, "categorie": None, "priorite": None}
        categorie, priorite = regles_metier(question, q.categorie, q.priorite)   # ═══ NOUVEAU (défi C) : les mêmes règles
        return {"refus": None, "categorie": categorie, "priorite": priorite}

    def ev_garde_fou(*, output, expected_output, **kwargs) -> Evaluation:
        return Evaluation(name="garde_fou_juste", value=float(output["refus"] == expected_output["refus"]),
                          comment=f"attendu {expected_output['refus'] or 'SUPPORT'}, obtenu {output['refus'] or 'SUPPORT'}")

    dataset = langfuse.get_dataset(synchroniser_dataset(langfuse))     # le JSON du dépôt reste la source de vérité
    resultat = dataset.run_experiment(name="construction-etape-8", run_name=f"regle-hameconnage · {getattr(llm, 'model', '?')} · {datetime.now():%d/%m %H:%M}",
                                      task=tache, evaluators=[ev_garde_fou, ev_qualification],
                                      run_evaluators=[ev_moyennes], max_concurrency=1)   # max_concurrency=1 : un GPU, un modèle
    for r in resultat.item_results:
        print(f"   {r.item.input['question'][:60]:60} → {r.output}")
    print(f"📊 {resume(resultat)}")
    langfuse.flush()
    print("🔭 Langfuse › Datasets › helpdesk-ops-eval › Experiments : cocher deux runs, Compare "
          "(ou : python construction/comparer_experiments.py)")
    raise SystemExit(0)


# --------------------------------------------------------------------------- les outils
@tool(parse_docstring=True)
def statut_serveur(nom: str) -> str:
    """Retourne le statut (en ligne, hors ligne, dégradé) d'un serveur de l'inventaire NordTech.

    Args:
        nom: nom d'hôte exact en minuscules, par exemple 'srv-vpn-01'
    """
    return INVENTAIRE.get(nom.strip().lower(), f"inconnu : '{nom}' n'est pas dans l'inventaire")


@tool(parse_docstring=True)
def rechercher_procedures(question: str) -> str:
    """Cherche les procédures du help-desk NordTech les plus pertinentes pour un problème.

    Args:
        question: le problème décrit en une phrase, par exemple 'le VPN ne se connecte pas depuis l'hôtel'
    """
    return kb.formater(kb.rechercher(question, k=3))


BOUCLE = asyncio.new_event_loop()                  # une seule boucle : le client MCP reste attaché à celle qui l'a créé
OUTILS_MCP_PROPOSES = BOUCLE.run_until_complete(MCPAdapter(transport_stdio()).list_tools())
OUTILS_MCP = filtrer_outils(OUTILS_MCP_PROPOSES, autorises={"lister_postes", "detail_poste", "historique_interventions"})

ERREURS_RESEAU_LLM = (ConnectionError, httpx.TransportError, openai.APIConnectionError, openai.InternalServerError)
REPLI = "Je n'ai pas pu traiter votre demande automatiquement : je la transmets à un technicien N1."
# Le repli rassure l'utilisateur, le journal garde la vraie cause (stderr)
logging.basicConfig(format="⚠️  %(asctime)s %(name)s · %(message)s", datefmt="%H:%M:%S")
journal = logging.getLogger("helpdesk-ops")

SPECIALISTES = {
    "kb": create_agent(llm, [rechercher_procedures], system_prompt=CONSIGNES["kb"], name="specialiste_kb"),
    "diagnostic": create_agent(llm, [statut_serveur, ping_serveur, *OUTILS_MCP], system_prompt=CONSIGNES["diagnostic"],
                               name="specialiste_diagnostic"),
    "acces": create_agent(llm, [etat_compte, rechercher_procedures], system_prompt=CONSIGNE_ACCES, name="specialiste_acces"),
}
DESCRIPTIONS_SPECIALISTES = {"kb": DESCRIPTIONS["kb"], "diagnostic": DESCRIPTIONS["diagnostic"], "acces": DESCRIPTION_ACCES}


def comme_outil(nom: str, specialiste, description: str) -> BaseTool:
    async def deleguer(consigne: str, config: RunnableConfig) -> str:
        resultat = await specialiste.ainvoke({"messages": [HumanMessage(consigne)]},
                                             config={**config, "run_name": f"specialiste-{nom}"})   # traces imbriquées
        return resultat["messages"][-1].content
    deleguer.__doc__ = f"""{description}

        Args:
            consigne: la tâche précise confiée au spécialiste, avec les identifiants utiles (serveur, poste, compte)
        """
    return tool(f"demander_{nom}", parse_docstring=True)(deleguer)


coordinateur = create_agent(llm, [comme_outil(n, s, DESCRIPTIONS_SPECIALISTES[n]) for n, s in SPECIALISTES.items()],
                            system_prompt=PROMPT_COORDINATEUR, name="coordinateur")


def enregistrer_ticket(cle: str, **champs) -> tuple[dict, bool]:
    """Renvoie (ticket, créé). La même clé renvoie le ticket existant : pas de doublon au rejeu."""
    tickets = json.loads(TICKETS.read_text(encoding="utf-8")) if TICKETS.exists() else {}
    if cle in tickets:
        return tickets[cle], False
    ticket = {"id": f"NT-{len(tickets) + 1:04d}", **champs}
    tickets[cle] = ticket
    TICKETS.write_text(json.dumps(tickets, ensure_ascii=False, indent=2), encoding="utf-8")
    return ticket, True


# --------------------------------------------------------------------------- l'état et les nœuds
class EtatTicket(MessagesState):
    ticket: str
    categorie: str
    priorite: str
    file: str
    valide_par: str
    resume: str
    decision: str


def garde_fou(state: EtatTicket) -> dict:
    return {"decision": decider(state["ticket"])}


def apres_garde_fou(state: EtatTicket) -> Literal["trier", "refus_poli"]:
    return "trier" if state["decision"] == "SUPPORT" else "refus_poli"


def refus_poli(state: EtatTicket) -> dict:
    return {"messages": [HumanMessage(state["ticket"]), AIMessage(REFUS[state["decision"]])]}


async def trier(state: EtatTicket) -> dict:
    decision = await tri.ainvoke({"ticket": state["ticket"]})
    if decision is None:                                                # sortie inexploitable : repli prudent
        decision = TicketDecision(categorie="autre", priorite="P3", resume=state["ticket"][:120])
    categorie, priorite = regles_metier(state["ticket"], decision.categorie, decision.priorite)   # ═══ NOUVEAU (défi C)
    return {"categorie": categorie, "priorite": priorite, "file": file_attente(categorie), "valide_par": "",
            "resume": decision.resume,
            "messages": [HumanMessage(f"[{categorie} · {priorite}] {state['ticket']}")]}


async def coordonner(state: EtatTicket) -> dict:
    resultat = await coordinateur.ainvoke({"messages": state["messages"]})
    return {"messages": resultat["messages"][len(state["messages"]):]}   # seulement les messages nouveaux


def apres_coordinateur(state: EtatTicket) -> Literal["valider", "creer_ticket"]:
    return "valider" if state["priorite"] == "P1" else "creer_ticket"


def agent_en_echec(state: EtatTicket, error: NodeError) -> Command[Literal["__end__"]]:
    journal.error("nœud %s en échec, repli envoyé à l'utilisateur : %r", error.node, error.error)
    return Command(update={"messages": [AIMessage(REPLI)]}, goto=END)   # pas de ticket sur une analyse incomplète


def valider(state: EtatTicket) -> Command[Literal["creer_ticket", "__end__"]]:
    decision = interrupt({"question": "Créer ce ticket P1 ?", "ticket": state["ticket"],
                          "categorie": state["categorie"], "file": state["file"]})
    if decision["action"] == "approuver":
        return Command(goto="creer_ticket", update={"valide_par": decision["par"]})
    refus = AIMessage(f"Ticket P1 refusé par {decision['par']}" + (f" : {decision['motif']}" if decision["motif"] else "."))
    return Command(goto=END, update={"messages": [refus]})


def creer_ticket(state: EtatTicket, config: RunnableConfig) -> dict:
    cle = f"{config['configurable']['thread_id']}:{normaliser(state['ticket'])}"
    ticket, cree = enregistrer_ticket(cle, categorie=state["categorie"], priorite=state["priorite"],
                                      file=state["file"], resume=state["resume"],
                                      valide_par=state["valide_par"] or None)
    texte = f"Ticket {ticket['id']} {'créé' if cree else 'déjà existant'} dans la file {ticket['file']}"
    return {"messages": [AIMessage(texte + (f", validé par {ticket['valide_par']}." if ticket["valide_par"] else "."))]}


builder = StateGraph(EtatTicket)
builder.add_node("garde_fou", garde_fou)
builder.add_node("refus_poli", refus_poli)
builder.add_node("trier", trier, retry_policy=RetryPolicy(max_attempts=3, retry_on=ERREURS_RESEAU_LLM),
                 timeout=TimeoutPolicy(run_timeout=120))
builder.add_node("coordinateur", coordonner, retry_policy=RetryPolicy(max_attempts=2, retry_on=ERREURS_RESEAU_LLM),
                 timeout=TimeoutPolicy(run_timeout=600), error_handler=agent_en_echec)   # CPU : jusqu'à 6 min mesurées le 07/11
builder.add_node("valider", valider)
builder.add_node("creer_ticket", creer_ticket)
builder.add_edge(START, "garde_fou")
builder.add_conditional_edges("garde_fou", apres_garde_fou)
builder.add_edge("refus_poli", END)
builder.add_edge("trier", "coordinateur")
builder.add_conditional_edges("coordinateur", apres_coordinateur)
builder.add_edge("creer_ticket", END)


def dessiner(graphe, nom: str) -> None:
    SORTIE.mkdir(exist_ok=True)
    (SORTIE / f"{nom}.md").write_text(f"```mermaid\n{graphe.get_graph().draw_mermaid()}\n```\n", encoding="utf-8")
    try:
        print(graphe.get_graph().draw_ascii())
    except ImportError:
        print("(dessin ASCII indisponible : grandalf absent)")
    print(f"🗺️  Schéma Mermaid : {(SORTIE / (nom + '.md')).relative_to(RACINE)}\n")


async def en_attente(graphe, config) -> list[dict]:
    return [i.value for t in (await graphe.aget_state(config)).tasks for i in t.interrupts]


@observe(name="helpdesk-ops", capture_input=False)
async def traiter(graphe, entree, config) -> tuple[dict, str]:
    etat = await graphe.ainvoke(entree, config=config)
    return etat, langfuse.get_current_trace_id()


def poser_scores(trace_id: str, decision: str, reponse: str) -> None:
    langfuse.create_score(trace_id=trace_id, name="garde_fou", value=decision, data_type="CATEGORICAL")
    if decision != "SUPPORT" or not reponse:
        return
    cite = "[KB-" in reponse
    langfuse.create_score(trace_id=trace_id, name="sources_citees", value=float(cite), data_type="BOOLEAN")
    print(f"   ⭐ score sources_citees : {'oui' if cite else 'non'}")
    if args.juger:
        basculer_vllm("juge")                                       # vLLM : 24 Go ne tiennent pas agent + juge
        juger = creer_juge(creer_llm("judge", reasoning=False))     # juge ≠ modèle évalué
        j = juger(reponse, kb.formater(kb.rechercher(args.message, k=3)))
        basculer_vllm("agents")
        if j is not None:
            langfuse.create_score(trace_id=trace_id, name="fidelite", value=noter(j), data_type="NUMERIC",
                                  comment=f"sans source : {j.affirmations_sans_source[:3]}")
            print(f"   ⚖️  fidélité (note calculée) : {noter(j)} · sans source : {j.affirmations_sans_source[:3]}")


async def main() -> None:
    BASE.parent.mkdir(parents=True, exist_ok=True)
    RESEAU.configurer(echecs_avant_succes=args.panne)
    async with AsyncSqliteSaver.from_conn_string(str(BASE)) as memoire:
        graphe = builder.compile(checkpointer=memoire)
        config = {"configurable": {"thread_id": args.thread}, "callbacks": [handler],
                  "run_name": "helpdesk", "recursion_limit": 25}

        if args.oublier:
            await memoire.adelete_thread(args.thread)
            print(f"🧹 Conversation {args.thread} effacée du fichier SQLite (les tickets créés restent : c'est l'ITSM).")
            return

        avant = len((await graphe.aget_state(config)).values.get("messages", []))
        if args.approuver or args.refuser:
            if not await en_attente(graphe, config):
                raise SystemExit(f"Rien à valider sur le thread {args.thread}.")
            entree = Command(resume={"action": "approuver" if args.approuver else "refuser",
                                     "par": args.approuver or args.refuser, "motif": args.motif})
            print(f"✍️  Décision de {args.approuver or args.refuser} : {'approuvé' if args.approuver else 'refusé'}")
        else:
            if await en_attente(graphe, config):
                raise SystemExit(f"Le thread {args.thread} attend une validation : --approuver NOM ou --refuser NOM.")
            if avant == 0:
                dessiner(graphe, "defi_08c_hameconnage_graphe")
                retenus = {o.name for o in OUTILS_MCP}
                print("🔌 MCP inventaire : " + ", ".join(f"{o.name} {'✅' if o.name in retenus else '⛔'}"
                                                         for o in OUTILS_MCP_PROPOSES))
            entree = {"ticket": args.message}
            print(f"🎫 {args.message}")

        with propagate_attributes(session_id=args.thread, user_id="agent-n1-042", tags=["construction", "defi-8c"]):
            etat, trace_id = await traiter(graphe, entree, config)

        print(f"   🛡️  garde-fou : {etat['decision']}")
        if etat["decision"] != "SUPPORT":
            print(f"   🤖 {etat['messages'][-1].content}   (ni coordinateur, ni outil, ni ticket)")
            poser_scores(trace_id, etat["decision"], "")
            return

        print(f"   📐 décision : {etat['categorie']} · {etat['priorite']} · « {etat['resume']} »")
        for appel in (a for m in etat["messages"][avant:] for a in getattr(m, "tool_calls", [])):
            print(f"   🧭 délégué à : {appel['name']}({appel['args']})")
        if RESEAU.appels:
            print(f"   📡 supervision : {RESEAU.appels} appel(s), dont {min(RESEAU.appels, args.panne)} en échec")
        attente = await en_attente(graphe, config)
        if attente:
            q = attente[0]
            print(f"   🏷️  {etat['categorie']} · {etat['priorite']} · file {etat['file']}")
            print(f"   🤖 {etat['messages'][-1].content}")
            print(f"⏸  {q['question']} Le graphe est arrêté, son état est dans le checkpoint. Pour reprendre :")
            print(f"   ... defi_08c_hameconnage.py --thread {args.thread} --approuver <nom>   (ou --refuser <nom> --motif ...)")
        else:
            reponse = next((m.content for m in reversed(etat["messages"][avant:-1])
                            if isinstance(m, AIMessage) and m.content and not m.tool_calls), "")
            if reponse:                                       # la réponse de l'agent, avant l'annonce du ticket
                print(f"   🤖 {reponse}")
            print(f"   🎫 {etat['messages'][-1].content}")
            print(f"📒 Tickets : {TICKETS.relative_to(RACINE)}")
            poser_scores(trace_id, etat["decision"], reponse)


BOUCLE.run_until_complete(main())
langfuse.flush()
print(f"🔭 Langfuse › Sessions › {args.thread}")
