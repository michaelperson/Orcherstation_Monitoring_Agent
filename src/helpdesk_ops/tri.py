"""Tri des tickets (jalon J1) : classifieur LCEL, normalisation et règles métier."""
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from helpdesk_ops.donnees import CATEGORIES
from helpdesk_ops.texte import normaliser

PROMPT_CLASSIFIEUR = ChatPromptTemplate.from_messages([
    ("system",
     "Tu es l'agent de tri N1 du help-desk de NordTech SA. "
     "Classe le ticket dans UNE catégorie parmi : {categories}. "
     "Réponds uniquement par le nom de la catégorie, en minuscules, sans ponctuation."),
    ("human", "Ticket : {ticket}"),
])

MOTS_URGENCE = ("bloque", "urgent", "production", "tous les utilisateurs")   # comparés à un texte normalisé


def creer_classifieur(llm: BaseChatModel) -> Runnable:
    """prompt | llm | parser. Entrée : {"ticket": ..., "categories": ...} ; sortie : texte brut du modèle."""
    return PROMPT_CLASSIFIEUR | llm | StrOutputParser()


def normaliser_categorie(brute: str) -> str:
    """Garde-fou : 'Réseau.', 'Accès' ou 'catégorie : reseau' -> catégorie valide ; sinon 'autre' (repli sûr)."""
    nettoyee = normaliser(brute).rstrip(".")
    return next((c for c in CATEGORIES if c in nettoyee), "autre")


def file_attente(categorie: str) -> str:
    """Règle métier : réseau et matériel partent en N2-infra, le reste reste en N1."""
    return "N2-infra" if categorie in ("reseau", "materiel") else "N1"


def estimer_priorite(ticket: str) -> str:
    """Règle volontairement simple (donc explicable) : P1 si mot d'urgence, sinon P3."""
    texte = normaliser(ticket)
    return "P1" if any(mot in texte for mot in MOTS_URGENCE) else "P3"
