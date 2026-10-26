"""Jalon J2 : un agent support stateful, contrôlé et robuste (Ex2.1 + Ex2.2).

    START → garde_fou ─SUPPORT─→ agent ⇄ tools
                      │            └─(réponse)→ qualifier ─besoin_ticket=False─→ END
                      │                                  ├─P2 à P4──────────────→ creer_ticket → END
                      │                                  └─P1─→ validation_humaine ─approuver/modifier→ creer_ticket
                      │                                                             └─rejeter──────────→ ticket_refuse → END
                      └─sinon──→ refus_poli → END

- **Persistance** : checkpointer + thread_id (une conversation = un thread) ;
- **HITL** : `interrupt()` avant la création d'un ticket P1, reprise par `Command(resume=…)` ;
- **Sortie structurée** : `TicketDecision` (Pydantic), routage par `Command(goto=…)` ;
- **Robustesse** : RetryPolicy, TimeoutPolicy (nœuds async), error_handler avec `NodeError`.

Graphe asynchrone (les timeouts l'exigent) : utiliser `ainvoke` / `astream`.
À distribuer après le débriefing de J2 : ce module contient les corrigés des exercices 2.1 et 2.2.
"""
from typing import Awaitable, Callable, Literal

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import NodeError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, RetryPolicy, TimeoutPolicy, interrupt
from pydantic import BaseModel, Field

from helpdesk_ops.jalons.j1 import REFUS, REPLI, decider_par_regles
from helpdesk_ops.outils import chercher_kb, statut_serveur
from helpdesk_ops.reseau import ping_serveur
from helpdesk_ops.ticketing import TICKETING, Ticketing
from helpdesk_ops.tri import file_attente

OUTILS = [statut_serveur, chercher_kb, ping_serveur]

PROMPT_SYSTEME = SystemMessage(
    "Tu es l'agent support N1 du help-desk de NordTech SA. "
    "Réponds toujours en français, en 3 phrases maximum. "
    "Utilise statut_serveur pour l'état d'un serveur, ping_serveur pour tester sa joignabilité réseau "
    "et chercher_kb pour une procédure. N'invente jamais de procédure ni de nom de serveur. "
    "Ne promets jamais la création d'un ticket : c'est le système qui la décide après ta réponse."
)

PROMPT_QUALIFICATION = SystemMessage(
    "Tu qualifies la demande de support de la conversation ci-dessous pour l'outil de ticketing de NordTech SA. "
    "besoin_ticket=False si la réponse donnée suffit (simple question, procédure en libre-service). "
    "Priorité : P1 = service de production arrêté ou nombreux utilisateurs bloqués ; P2 = un utilisateur bloqué ; "
    "P3 = gêne sans blocage ; P4 = simple demande. Le résumé ne contient aucune donnée personnelle."
)


class TicketDecision(BaseModel):
    """Qualification d'une demande de support."""
    besoin_ticket: bool = Field(description="True si un technicien doit intervenir")
    categorie: Literal["reseau", "materiel", "logiciel", "acces", "autre"]
    priorite: Literal["P1", "P2", "P3", "P4"] = Field(
        description="P1 : production arrêtée ou nombreux utilisateurs bloqués ; P4 : simple demande")
    resume: str = Field(description="résumé du problème en une phrase, sans donnée personnelle")


class EtatJ2(MessagesState):
    decision: str                      # garde-fou : SUPPORT, HORS_PERIMETRE, INJECTION
    qualification: dict | None         # TicketDecision sérialisée (un dict se relit sans surprise depuis SQLite)
    validation: dict | None            # réponse humaine : {"action", "par", "priorite"?}
    ticket_id: str | None


Qualifieur = Callable[[list], Awaitable[TicketDecision]]


def tour_courant(messages: list) -> list:
    """Les messages du dernier tour : la dernière question humaine et tout ce qui suit."""
    indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return messages[indices[-1]:] if indices else messages


def creer_qualifieur(llm: BaseChatModel) -> Qualifieur:
    """Sortie structurée : le modèle doit renvoyer un TicketDecision valide (validé par Pydantic).

    method="json_schema" (défaut d'Ollama) : la génération est contrainte par le schéma, le format est
    garanti. Mesuré le 20/10/2026 (granite4.1:8b, CPU, appels isolés) : 11 à 26 s par décision.
    "function_calling" a la même latence mais peut renvoyer None SANS erreur si le modèle répond en
    prose au lieu d'appeler l'outil. Dans les deux cas, c'est PROMPT_QUALIFICATION (définition des
    priorités) qui rend les décisions cohérentes ; sans lui, « souris sans fil » sortait en P1.
    """
    structure = llm.with_structured_output(TicketDecision, method="json_schema")

    async def qualifier(messages: list) -> TicketDecision:
        utiles = [m for m in messages if isinstance(m, (HumanMessage, AIMessage)) and m.content]
        return await structure.ainvoke([PROMPT_QUALIFICATION, *utiles])

    return qualifier


def messages_outils_de_repli(state: EtatJ2, motif: str) -> list[ToolMessage]:
    """Une réponse d'erreur par appel d'outil en attente : sans elles, le modèle reçoit un historique invalide."""
    dernier = state["messages"][-1]
    return [ToolMessage(content=f"outil indisponible ({motif}) : ne pas réessayer, le signaler à l'utilisateur",
                        tool_call_id=appel["id"], name=appel["name"], status="error")
            for appel in getattr(dernier, "tool_calls", [])]


def construire_support_j2(
    llm: BaseChatModel,
    *,
    qualifieur: Qualifieur | None = None,
    decider: Callable[[str], str] = decider_par_regles,
    checkpointer=None,
    ticketing: Ticketing = TICKETING,
    timeout_llm_s: float = 120.0,      # poste CPU ; en salle GPU, 30 s suffisent
    timeout_outil_s: float = 10.0,
    tentatives: int = 3,
) -> CompiledStateGraph:
    llm_outils = llm.bind_tools(OUTILS)
    qualifieur = qualifieur or creer_qualifieur(llm)

    # ------------------------------------------------------------------ garde-fou (J1)
    def garde_fou(state: EtatJ2) -> dict:
        return {"decision": decider(state["messages"][-1].content), "qualification": None,
                "validation": None, "ticket_id": None}

    def router_garde_fou(state: EtatJ2) -> Literal["agent", "refus_poli"]:
        return "agent" if state["decision"] == "SUPPORT" else "refus_poli"

    def refus_poli(state: EtatJ2) -> dict:
        return {"messages": [AIMessage(REFUS[state["decision"]])]}

    # ------------------------------------------------------------------ agent + outils, robustes
    async def agent(state: EtatJ2) -> dict:
        return {"messages": [await llm_outils.ainvoke([PROMPT_SYSTEME, *state["messages"]])]}

    def agent_en_echec(state: EtatJ2, error: NodeError) -> Command:
        # Retries épuisés ou timeout : réponse polie, et surtout pas de ticket créé sur une analyse incomplète
        return Command(update={"messages": [AIMessage(REPLI)]}, goto=END)

    def qualification_en_echec(state: EtatJ2, error: NodeError) -> Command:
        return Command(update={"qualification": None,
                               "messages": [AIMessage("Votre demande est transmise au help-desk N1 pour qualification.")]},
                       goto=END)

    def outils_en_echec(state: EtatJ2, error: NodeError) -> Command[Literal["agent"]]:
        # ⚠️ Après un error_handler, les arêtes normales du nœud ne sont PAS suivies : sans goto, le graphe s'arrête
        return Command(update={"messages": messages_outils_de_repli(state, type(error.error).__name__)}, goto="agent")

    # ------------------------------------------------------------------ qualification structurée
    async def qualifier(state: EtatJ2) -> Command[Literal["validation_humaine", "creer_ticket", "__end__"]]:
        # On qualifie la demande DU TOUR, pas toute la conversation : sinon un ancien incident
        # (« l'ERP est en panne ») serait re-qualifié à chaque nouvelle question (« et le VPN ? »)
        decision = await qualifieur(tour_courant(state["messages"]))
        if decision is None:   # sortie non structurée : on ne crée rien d'office, un humain reprendra
            return Command(update={"qualification": None,
                                   "messages": [AIMessage("Votre demande est transmise au help-desk N1 pour qualification.")]},
                           goto=END)
        maj = {"qualification": decision.model_dump()}
        if not decision.besoin_ticket:
            return Command(update=maj, goto=END)
        return Command(update=maj, goto="validation_humaine" if decision.priorite == "P1" else "creer_ticket")

    # ------------------------------------------------------------------ validation humaine (HITL)
    def validation_humaine(state: EtatJ2) -> Command[Literal["creer_ticket", "ticket_refuse"]]:
        # ⚠️ Tout ce qui précède interrupt() est REJOUÉ à la reprise : aucun effet de bord ici
        reponse = interrupt({
            "type": "validation_ticket_p1",
            "ticket_propose": state["qualification"],
            "actions": ["approuver", "modifier", "rejeter"],
        })
        if reponse.get("action") == "rejeter":
            return Command(update={"validation": reponse}, goto="ticket_refuse")
        maj = {"validation": reponse}
        if reponse.get("action") == "modifier" and reponse.get("priorite"):
            maj["qualification"] = {**state["qualification"], "priorite": reponse["priorite"]}
        return Command(update=maj, goto="creer_ticket")

    def creer_ticket(state: EtatJ2, config: RunnableConfig) -> dict:
        q = state["qualification"]
        cle = config.get("configurable", {}).get("thread_id", "sans-thread")   # idempotence : 1 ticket par conversation
        deja = ticketing.par_cle(cle)
        if deja is not None:   # relance ou rejeu : on n'annonce pas une création qui n'a pas eu lieu
            return {"ticket_id": deja.id,
                    "messages": [AIMessage(f"Votre demande est déjà suivie sous le ticket {deja.id} ({deja.priorite}).")]}
        ticket = ticketing.creer(cle_idempotence=cle, categorie=q["categorie"], priorite=q["priorite"],
                                 resume=q["resume"], file=file_attente(q["categorie"]),
                                 valide_par=(state.get("validation") or {}).get("par"))
        suffixe = f", validé par {ticket.valide_par}" if ticket.valide_par else ""
        return {"ticket_id": ticket.id,
                "messages": [AIMessage(f"Ticket {ticket.id} enregistré ({ticket.priorite}, file {ticket.file}{suffixe}).")]}

    def ticket_refuse(state: EtatJ2) -> dict:
        motif = (state.get("validation") or {}).get("motif", "non précisé")
        return {"messages": [AIMessage(f"La création du ticket P1 a été refusée par le responsable (motif : {motif}).")]}

    # ------------------------------------------------------------------ câblage
    b = StateGraph(EtatJ2)
    b.add_node("garde_fou", garde_fou)
    b.add_node("refus_poli", refus_poli)
    b.add_node("agent", agent,
               # Réseau : on réessaie (le client Ollama lève ConnectionError, httpx ses TransportError).
               # Timeout : PAS de nouvel essai (sur CPU, 3 × 2 min) → repli direct via agent_en_echec.
               retry_policy=RetryPolicy(max_attempts=tentatives, retry_on=(ConnectionError, httpx.TransportError)),
               timeout=TimeoutPolicy(run_timeout=timeout_llm_s), error_handler=agent_en_echec)
    b.add_node("tools", ToolNode(OUTILS),
               retry_policy=RetryPolicy(max_attempts=tentatives, initial_interval=0.2, retry_on=ConnectionError),
               timeout=TimeoutPolicy(run_timeout=timeout_outil_s), error_handler=outils_en_echec)
    b.add_node("qualifier", qualifier,
               retry_policy=RetryPolicy(max_attempts=tentatives, retry_on=(ConnectionError, httpx.TransportError)),
               timeout=TimeoutPolicy(run_timeout=timeout_llm_s), error_handler=qualification_en_echec)
    b.add_node("validation_humaine", validation_humaine)
    b.add_node("creer_ticket", creer_ticket)
    b.add_node("ticket_refuse", ticket_refuse)
    b.add_edge(START, "garde_fou")
    b.add_conditional_edges("garde_fou", router_garde_fou)
    b.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "qualifier"})
    b.add_edge("tools", "agent")
    b.add_edge("creer_ticket", END)
    b.add_edge("ticket_refuse", END)
    b.add_edge("refus_poli", END)
    return b.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------- façade conversationnelle
def _resultat(etat) -> dict:
    """État v2 -> {'reponse', 'interruption', 'ticket_id'} : ce dont une interface a besoin.

    `reponse` réunit TOUS les messages de l'agent du tour (sa réponse ET l'annonce du ticket) :
    le dernier message seul masquerait la réponse de l'agent derrière « Ticket NT-… enregistré ».
    """
    valeurs = etat.value
    textes = [m.content for m in tour_courant(valeurs.get("messages", []))
              if isinstance(m, AIMessage) and m.content and not m.tool_calls]
    return {
        "reponse": "\n".join(textes),
        "interruption": etat.interrupts[0].value if etat.interrupts else None,
        "ticket_id": valeurs.get("ticket_id"),
    }


async def arepondre(graphe: CompiledStateGraph, question: str, *, thread_id: str, callbacks=None,
                    recursion_limit: int = 15) -> dict:
    """Un tour de conversation. Si `interruption` n'est pas None, attendre une décision puis appeler `areprendre`."""
    cfg = {"configurable": {"thread_id": thread_id}, "callbacks": callbacks or [],
           "run_name": "helpdesk-ops-j2", "recursion_limit": recursion_limit}
    return _resultat(await graphe.ainvoke({"messages": [HumanMessage(question)]}, cfg, version="v2"))


async def areprendre(graphe: CompiledStateGraph, decision: dict, *, thread_id: str, callbacks=None,
                     recursion_limit: int = 15) -> dict:
    """Reprend une conversation interrompue avec la décision humaine ({'action': 'approuver', 'par': …})."""
    cfg = {"configurable": {"thread_id": thread_id}, "callbacks": callbacks or [],
           "run_name": "helpdesk-ops-j2-reprise", "recursion_limit": recursion_limit}
    return _resultat(await graphe.ainvoke(Command(resume=decision), cfg, version="v2"))
