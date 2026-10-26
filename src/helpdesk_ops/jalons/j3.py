"""Jalon J3 : HelpDesk-Ops multi-agents complet (corrigé de l'exercice 3.1 inclus).

    garde_fou (J1) ─SUPPORT─→ coordinateur ─┬─ demander_kb
                                             ├─ demander_diagnostic (+ outils MCP inventaire filtrés)
                                             ├─ demander_ticketing
                                             └─ demander_acces   ← 4ᵉ spécialiste (Ex3.1)

À distribuer après le débriefing de J3 : ce module contient le corrigé de l'exercice 3.1.
"""
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from helpdesk_ops.jalons.j1 import REFUS, decider_par_regles
from helpdesk_ops.multi_agents import (Recherche, construire_coordinateur, construire_specialistes, outils_kb,
                                       recherche_qdrant)
from helpdesk_ops.ticketing import TICKETING, Ticketing

# Annuaire simulé (comptes pseudonymisés)
COMPTES = {
    "collab-3fa91c": "actif",
    "collab-8b20d4": "verrouillé (3 échecs de connexion, déverrouillage automatique dans 15 min)",
    "collab-71e0aa": "mot de passe expiré",
    "collab-c45f12": "désactivé (départ le 2026-09-30)",
}


@tool(parse_docstring=True)
def etat_compte(identifiant: str) -> str:
    """État du compte NordTech d'un collaborateur dans l'annuaire (actif, verrouillé, expiré, désactivé).

    Args:
        identifiant: identifiant pseudonymisé du collaborateur, par exemple 'collab-8b20d4'
    """
    return COMPTES.get(identifiant.strip().lower(), f"compte inconnu : {identifiant}")


CONSIGNE_ACCES = ("Tu es le spécialiste Accès du help-desk NordTech. Vérifie l'état du compte avec etat_compte, puis indique "
                  "la procédure à suivre (KB) en citant [KB-xxx]. Tu ne réinitialises jamais un mot de passe toi-même.")
DESCRIPTION_ACCES = "Vérifie l'état du compte d'un collaborateur (verrouillé, expiré, désactivé) et donne la procédure d'accès."


def specialiste_acces(llm: BaseChatModel, recherche: Recherche = recherche_qdrant) -> CompiledStateGraph:
    """4ᵉ spécialiste : annuaire + procédures de la seule catégorie « acces » (filtre de payload)."""
    recherche_acces = lambda question: recherche(question, categorie="acces")   # noqa: E731
    return create_agent(llm, [etat_compte, *outils_kb(recherche_acces)], system_prompt=CONSIGNE_ACCES,
                        name="specialiste_acces")


def construire_specialistes_j3(llm: BaseChatModel, *, recherche: Recherche = recherche_qdrant,
                               outils_mcp: list[BaseTool] = (), ticketing: Ticketing = TICKETING) -> dict[str, CompiledStateGraph]:
    specialistes = construire_specialistes(llm, recherche=recherche, outils_mcp=outils_mcp, ticketing=ticketing)
    specialistes["acces"] = specialiste_acces(llm, recherche)
    return specialistes


def construire_helpdesk_j3(llm: BaseChatModel, *, llm_specialistes: BaseChatModel | None = None,
                           recherche: Recherche = recherche_qdrant, outils_mcp: list[BaseTool] = (),
                           ticketing: Ticketing = TICKETING, checkpointer=None) -> CompiledStateGraph:
    specialistes = construire_specialistes_j3(llm_specialistes or llm, recherche=recherche, outils_mcp=outils_mcp,
                                              ticketing=ticketing)
    coordinateur = construire_coordinateur(llm, specialistes, {"acces": DESCRIPTION_ACCES})

    class Etat(MessagesState):
        decision: str

    def garde_fou(state: Etat) -> dict:
        return {"decision": decider_par_regles(state["messages"][-1].content)}

    def refus_poli(state: Etat) -> dict:
        return {"messages": [AIMessage(REFUS[state["decision"]])]}

    b = StateGraph(Etat)
    b.add_node("garde_fou", garde_fou)
    b.add_node("refus_poli", refus_poli)
    b.add_node("coordinateur", coordinateur)
    b.add_edge(START, "garde_fou")
    b.add_conditional_edges("garde_fou", lambda s: "coordinateur" if s["decision"] == "SUPPORT" else "refus_poli",
                            ["coordinateur", "refus_poli"])
    b.add_edge("coordinateur", END)
    b.add_edge("refus_poli", END)
    return b.compile(checkpointer=checkpointer)
