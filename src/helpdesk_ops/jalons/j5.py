"""Jalon J5 : HelpDesk-Ops prêt pour la production (corrigé de l'exercice 5.1 inclus).

    START → garde_fou (règles + LLM) ─SUPPORT─→ coordinateur ─→ controle_sortie → END
                                     └─sinon──→ refus_poli ───┘
    coordinateur (J3) + middlewares : PII · plafonds d'appels · liste blanche des délégations + journal d'audit
    spécialiste KB : documents nettoyés et encadrés (injection indirecte)
    contrôle de sortie : commande sensible sans source → réponse remplacée ; 1ʳᵉ réponse précédée de l'information
                         « vous échangez avec une IA » (AI Act art. 50) ; chaque réponse marquée (métadonnées)

À distribuer après le débriefing de J5 : ce module contient le corrigé de l'exercice 5.1 (liste blanche + audit).
"""
import asyncio
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langfuse import get_client
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from helpdesk_ops import securite as sec
from helpdesk_ops.conformite import MESSAGE_IA, marquer
from helpdesk_ops.jalons.j1 import REFUS, REPLI
from helpdesk_ops.jalons.j3 import DESCRIPTION_ACCES, construire_specialistes_j3
from helpdesk_ops.multi_agents import Recherche, construire_coordinateur, recherche_qdrant
from helpdesk_ops.ticketing import TICKETING, Ticketing

VERSION = "helpdesk-ops-j5"


class EtatJ5(MessagesState):
    decision: str
    bloquees: list[str]
    references_retirees: list[str]


def derniere_demande(state: EtatJ5) -> str:
    return next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")


def premier_tour(state: EtatJ5) -> bool:
    """Aucune réponse avant la dernière demande : c'est le premier échange de la conversation."""
    messages = state["messages"]
    dernier_humain = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
    return not any(isinstance(m, AIMessage) for m in messages[:dernier_humain])


def _signaler_injection(lignes: list[str]) -> None:
    """Une consigne cachée retirée d'un document : on le voit dans Langfuse (WARNING), on ne le subit pas."""
    with get_client().start_as_current_observation(name="document-nettoye", as_type="guardrail",
                                                   output={"lignes_retirees": len(lignes)}) as obs:
        obs.update(level="WARNING", status_message="consigne cachée retirée d'un document de la KB")


def construire_helpdesk_j5(llm: BaseChatModel, *, llm_garde_fou: BaseChatModel | None = None,
                           llm_specialistes: BaseChatModel | None = None, recherche: Recherche = recherche_qdrant,
                           outils_mcp: list[BaseTool] = (), ticketing: Ticketing = TICKETING,
                           journal: sec.JournalAudit | None = None, modele: str = "", checkpointer=None) -> CompiledStateGraph:
    decider = sec.creer_garde_fou(llm_garde_fou or llm)
    recherche_sure = sec.recherche_protegee(recherche, signaler=_signaler_injection)
    specialistes = construire_specialistes_j3(llm_specialistes or llm, recherche=recherche_sure,
                                              outils_mcp=outils_mcp, ticketing=ticketing)
    delegations = {f"demander_{nom}" for nom in specialistes}
    coordinateur = construire_coordinateur(
        llm, specialistes, {"acces": DESCRIPTION_ACCES},
        middleware=[*sec.middlewares_pii(), *sec.middlewares_limites(), sec.liste_blanche(delegations, journal)])
    modele = modele or getattr(llm, "model", "") or type(llm).__name__

    def garde_fou(state: EtatJ5) -> dict:
        demande = derniere_demande(state)
        with get_client().start_as_current_observation(name="garde-fou", as_type="guardrail", input=demande,
                                                       metadata={"strategie": "hybride"}) as obs:
            decision = decider(demande)
            obs.update(output=decision)
        return {"decision": decision, "bloquees": [], "references_retirees": []}

    def refus_poli(state: EtatJ5) -> dict:
        return {"messages": [AIMessage(REFUS[state["decision"]])]}

    def controle_sortie(state: EtatJ5) -> dict:
        derniere = state["messages"][-1]
        texte = derniere.content if isinstance(derniere.content, str) else str(derniere.content)
        retirees: list[str] = []
        if texte.startswith("Model call limits exceeded"):   # message anglais du ModelCallLimitMiddleware
            texte, bloquees = REPLI, []
        else:
            texte, retirees = sec.retirer_references_inexistantes(texte)
            if retirees:
                with get_client().start_as_current_observation(name="references-inexistantes", as_type="guardrail",
                                                               output={"retirees": retirees}) as obs:
                    obs.update(level="WARNING", status_message="référence KB inventée retirée de la réponse")
            texte, bloquees = sec.controler_sortie(texte)
        if bloquees:
            with get_client().start_as_current_observation(name="controle-sortie", as_type="guardrail",
                                                           output={"commandes_bloquees": bloquees}) as obs:
                obs.update(level="WARNING", status_message="commande sensible sans source : réponse remplacée")
        if premier_tour(state):   # AI Act art. 50 : informer dès le premier échange (placé ici, pas avant l'agent)
            texte = f"{MESSAGE_IA}\n\n{texte}"
        reponse = marquer(AIMessage(texte, id=derniere.id), version=VERSION, modele=modele)
        return {"messages": [reponse], "bloquees": bloquees, "references_retirees": retirees}

    b = StateGraph(EtatJ5)
    for nom, noeud in (("garde_fou", garde_fou), ("refus_poli", refus_poli), ("coordinateur", coordinateur),
                       ("controle_sortie", controle_sortie)):
        b.add_node(nom, noeud)
    b.add_edge(START, "garde_fou")
    b.add_conditional_edges("garde_fou", lambda s: "coordinateur" if s["decision"] == "SUPPORT" else "refus_poli",
                            ["coordinateur", "refus_poli"])
    b.add_edge("coordinateur", "controle_sortie")
    b.add_edge("refus_poli", "controle_sortie")
    b.add_edge("controle_sortie", END)
    return b.compile(checkpointer=checkpointer)


async def arepondre_j5(graphe: CompiledStateGraph, question: str, *, thread_id: str, user_id: str = "anonyme",
                       callbacks=None) -> AIMessage:
    """Une question dans une conversation ; renvoie le dernier message (marqué), jamais une exception brute."""
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}, "callbacks": callbacks or [],
              "run_name": VERSION, "recursion_limit": 40}
    try:
        etat = await graphe.ainvoke({"messages": [HumanMessage(question)]}, config=config)
        return etat["messages"][-1]
    except Exception:   # noqa: BLE001  l'utilisateur reçoit le repli ; l'erreur est dans la trace
        return AIMessage(REPLI)


@lru_cache(maxsize=1)
def _graphe_serveur() -> CompiledStateGraph:
    from helpdesk_ops.config import creer_llm
    return construire_helpdesk_j5(creer_llm("agent"))


async def graphe(config=None) -> CompiledStateGraph:
    """Point d'entrée de `langgraph.json` (serveur LangGraph local) ; le serveur fournit lui-même la persistance.

    Constaté le 22/10/2026 : le serveur appelle cette fabrique à CHAQUE exécution, dans sa boucle asynchrone, et
    `langgraph dev` refuse les appels bloquants (lecture du .env, création du journal) : « BlockingError ».
    D'où une construction unique (cache), faite dans un thread.
    """
    return await asyncio.to_thread(_graphe_serveur)


def repondre_avec_trace(graphe: CompiledStateGraph, question: str, *, thread_id: str, user_id: str,
                        langfuse, handler) -> tuple[AIMessage, str]:
    """Version synchrone pour une interface (Streamlit) : une trace par échange, rattachée à la session et à
    l'utilisateur (pseudonyme) ; renvoie aussi l'identifiant de trace, pour y attacher le 👍/👎."""
    from langfuse import propagate_attributes
    with propagate_attributes(session_id=thread_id, user_id=user_id, version=VERSION, tags=["helpdesk-ops", "j5"]):
        with langfuse.start_as_current_observation(name=VERSION, as_type="agent", input=question) as racine:
            message = asyncio.run(arepondre_j5(graphe, question, thread_id=thread_id, user_id=user_id, callbacks=[handler]))
            racine.update(output=message.content)
            return message, langfuse.get_current_trace_id()
