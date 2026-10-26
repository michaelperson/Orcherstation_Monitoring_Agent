"""Orchestration multi-agents du help-desk (cours du jour 3) : spécialistes, sous-agents comme outils, routeur.

    coordinateur (create_agent)
      ├─ demander_kb          → spécialiste KB-RAG     : rechercher_procedures (Qdrant hybride, public seulement)
      ├─ demander_diagnostic  → spécialiste Diagnostic : statut_serveur, ping_serveur (+ outils MCP inventaire)
      └─ demander_ticketing   → spécialiste Ticketing  : tickets_ouverts, ouvrir_ticket (P1 refusé : validation J2)

**Isolation du contexte** : un spécialiste ne reçoit que la consigne du coordinateur, jamais toute la
conversation ; il rend un texte court. Chaque spécialiste a ses propres outils : un outil n'est exposé
qu'à l'agent qui en a besoin (OWASP ASI02).
"""
import hashlib
from typing import Callable, Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import Field, create_model

from helpdesk_ops.outils import statut_serveur, tickets_ouverts
from helpdesk_ops.reseau import ping_serveur
from helpdesk_ops.ticketing import TICKETING, Ticketing
from helpdesk_ops.tri import file_attente

Recherche = Callable[..., str]


def recherche_qdrant(question: str, categorie: str | None = None) -> str:
    """Recherche hybride dans la KB (public seulement), formatée avec les références [KB-xxx]."""
    from helpdesk_ops import kb
    return kb.formater(kb.rechercher(question, k=3, categorie=categorie))


# --------------------------------------------------------------------------- outils des spécialistes
def outils_kb(recherche: Recherche) -> list[BaseTool]:
    @tool(parse_docstring=True)
    def rechercher_procedures(question: str) -> str:
        """Cherche les procédures du help-desk NordTech les plus pertinentes pour un problème.

        Args:
            question: le problème décrit en une phrase, par exemple 'le VPN ne se connecte pas depuis l'hôtel'
        """
        return recherche(question)
    return [rechercher_procedures]


def outils_ticketing(ticketing: Ticketing) -> list[BaseTool]:
    @tool(parse_docstring=True)
    def ouvrir_ticket(resume: str, categorie: str, priorite: str) -> str:
        """Ouvre un ticket dans l'outil de ticketing NordTech (P2 à P4 uniquement).

        Args:
            resume: une phrase, sans donnée personnelle
            categorie: 'reseau', 'materiel', 'logiciel', 'acces' ou 'autre'
            priorite: 'P2' (un utilisateur bloqué), 'P3' (gêne) ou 'P4' (demande)
        """
        if priorite == "P1":   # le P1 suit le circuit de validation humaine du jalon J2
            return "P1 refusé : un ticket P1 exige la validation du responsable N2 (circuit de validation)."
        if priorite not in ("P2", "P3", "P4") or categorie not in ("reseau", "materiel", "logiciel", "acces", "autre"):
            return "valeurs invalides : categorie parmi reseau, materiel, logiciel, acces, autre ; priorite parmi P2, P3, P4"
        cle = hashlib.sha256(f"{categorie}|{resume.strip().lower()}".encode()).hexdigest()   # idempotence
        t = ticketing.creer(cle_idempotence=cle, categorie=categorie, priorite=priorite, resume=resume,
                            file=file_attente(categorie))
        return f"ticket {t.id} ouvert ({t.priorite}, file {t.file})"
    return [tickets_ouverts, ouvrir_ticket]


# --------------------------------------------------------------------------- spécialistes
CONSIGNES = {
    "kb": "Tu es le spécialiste Procédures du help-desk NordTech. Utilise rechercher_procedures, puis réponds en "
          "3 phrases maximum EN CITANT les références [KB-xxx] utilisées. Si aucun extrait ne répond, dis-le : n'invente rien.",
    "diagnostic": "Tu es le spécialiste Diagnostic du help-desk NordTech. Utilise tes outils pour établir les FAITS "
                  "(état, joignabilité, historique). Tu n'agis jamais sur un serveur ou un poste. Réponds en 3 phrases maximum.",
    "ticketing": "Tu es le spécialiste Ticketing du help-desk NordTech. Tu consultes les files et ouvres des tickets "
                 "P2 à P4. Un P1 suit un circuit de validation humaine : ne le contourne pas. Réponds en 2 phrases.",
}

DESCRIPTIONS = {
    "kb": "Trouve la procédure du help-desk pour un problème (VPN, Outlook, imprimante, Wi-Fi, Teams…) et la résume avec ses références KB.",
    "diagnostic": "Établit les faits techniques sur un serveur (statut, ping) ou un poste de travail (fiche, historique d'interventions).",
    "ticketing": "Consulte les files de tickets ou ouvre un ticket P2 à P4 (jamais P1).",
}


def construire_specialistes(llm: BaseChatModel, *, recherche: Recherche = recherche_qdrant,
                            outils_mcp: list[BaseTool] = (), ticketing: Ticketing = TICKETING) -> dict[str, CompiledStateGraph]:
    """Les trois spécialistes du cours : KB-RAG, Diagnostic, Ticketing (chacun un create_agent avec SES outils)."""
    return {
        "kb": create_agent(llm, outils_kb(recherche), system_prompt=CONSIGNES["kb"], name="specialiste_kb"),
        "diagnostic": create_agent(llm, [statut_serveur, ping_serveur, *outils_mcp], system_prompt=CONSIGNES["diagnostic"],
                                   name="specialiste_diagnostic"),
        "ticketing": create_agent(llm, outils_ticketing(ticketing), system_prompt=CONSIGNES["ticketing"],
                                  name="specialiste_ticketing"),
    }


def comme_outil(nom: str, agent: CompiledStateGraph, description: str | None = None) -> BaseTool:
    """Un spécialiste exposé au coordinateur comme un outil : il ne reçoit QUE la consigne (isolation du contexte)."""
    async def deleguer(consigne: str, config: RunnableConfig) -> str:
        resultat = await agent.ainvoke({"messages": [HumanMessage(consigne)]},
                                       config={**config, "run_name": f"specialiste-{nom}"})   # traces imbriquées
        return resultat["messages"][-1].content

    deleguer.__doc__ = f"""{description or DESCRIPTIONS[nom]}

        Args:
            consigne: la tâche précise confiée au spécialiste, avec les identifiants utiles (serveur, poste, compte)
        """
    return tool(f"demander_{nom}", parse_docstring=True)(deleguer)


# « Conserve les numéros de ticket » a suffi, pendant la préparation (20/10/2026), pour que le modèle
# INVENTE « Ticket : TKT-2025-0012 » alors qu'aucun ticket n'existait : on interdit explicitement.
PROMPT_COORDINATEUR = (
    "Tu es le coordinateur du help-desk N1 de NordTech SA. Tu ne réponds jamais de mémoire : tu délègues à tes "
    "spécialistes (un appel par sujet, avec une consigne précise), puis tu rédiges une réponse finale en français, "
    "en 4 phrases maximum. Reprends telles quelles les références [KB-xxx] citées par les spécialistes. "
    "Ne mentionne un numéro de ticket QUE s'il figure mot pour mot dans la réponse d'un spécialiste : n'en invente jamais."
)


def construire_coordinateur(llm: BaseChatModel, specialistes: dict[str, CompiledStateGraph],
                            descriptions: dict[str, str] | None = None, *, middleware=()) -> CompiledStateGraph:
    """`middleware` : ajouté en J5 (PII, plafonds d'appels, liste blanche + audit)."""
    descriptions = {**DESCRIPTIONS, **(descriptions or {})}
    return create_agent(llm, [comme_outil(nom, agent, descriptions[nom]) for nom, agent in specialistes.items()],
                        system_prompt=PROMPT_COORDINATEUR, name="coordinateur", middleware=list(middleware))


# --------------------------------------------------------------------------- variante : routeur (un seul spécialiste)
def construire_routeur(llm: BaseChatModel, specialistes: dict[str, CompiledStateGraph],
                       descriptions: dict[str, str] | None = None) -> CompiledStateGraph:
    """Une décision structurée, puis UN spécialiste : moins cher, mais incapable de traiter une demande à plusieurs sujets."""
    descriptions = {**DESCRIPTIONS, **(descriptions or {})}
    destinations = tuple(specialistes)
    # Schéma construit à la volée : les valeurs permises sont exactement les spécialistes présents
    Aiguillage = create_model("Aiguillage", specialiste=(Literal[destinations], Field(
        description=" ; ".join(f"{n} : {descriptions[n]}" for n in destinations))))
    choix = llm.with_structured_output(Aiguillage, method="json_schema")

    async def router(state: MessagesState) -> Command:
        decision = await choix.ainvoke([("system", "Choisis le spécialiste du help-desk NordTech qui doit traiter la demande."),
                                        state["messages"][-1]])
        cible = decision.specialiste if decision is not None else destinations[0]   # repli prudent
        return Command(goto=cible)

    b = StateGraph(MessagesState)
    b.add_node("router", router, destinations=destinations)
    for nom, agent in specialistes.items():
        b.add_node(nom, agent)
        b.add_edge(nom, END)
    b.add_edge(START, "router")
    return b.compile()
