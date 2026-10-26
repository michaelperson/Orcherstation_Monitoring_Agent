"""Configuration du poste : une seule source de vérité, `infrastructure/.env` (généré par generate_env.py)."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

# Rôle fonctionnel -> variable .env : le code parle de rôles, le .env choisit les modèles
ROLES_MODELES = {
    "agent": "MODEL_AGENT",
    "alt": "MODEL_AGENT_ALT",
    "small": "MODEL_SMALL",
    "judge": "MODEL_JUDGE",
}


def trouver_env(depart: Path | None = None, nom_dossier: str = "infrastructure") -> Path:
    """Remonte l'arborescence depuis `depart` (par défaut le dossier courant) jusqu'à trouver infrastructure/.env."""
    depart = depart or Path.cwd()
    for dossier in [depart, *depart.parents]:
        candidat = dossier / nom_dossier / ".env"
        if candidat.exists():
            return candidat
    raise FileNotFoundError("infrastructure/.env introuvable : lance `uv run generate_env.py`")


def charger_env(chemin: Path | None = None) -> Path:
    """Charge .env dans os.environ. override=True : modifier .env puis relancer suffit, sans redémarrer le kernel."""
    chemin = chemin or trouver_env()
    load_dotenv(chemin, override=True)
    return chemin


def creer_llm(role: str = "agent", *, temperature: float = 0, num_ctx: int = 16384, **kwargs) -> ChatOllama:
    """ChatOllama pour un rôle ('agent', 'alt', 'small', 'judge').

    temperature=0 : décisions reproductibles (choix d'outil, routage).
    num_ctx=16384 : un contexte trop petit tronque en silence le prompt système des agents.
    """
    if role not in ROLES_MODELES:
        raise ValueError(f"rôle inconnu : {role!r}. Rôles valides : {', '.join(ROLES_MODELES)}")
    if "OLLAMA_BASE_URL" not in os.environ:
        charger_env()
    return ChatOllama(
        model=os.environ[ROLES_MODELES[role]],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=temperature,
        num_ctx=num_ctx,
        **kwargs,
    )
