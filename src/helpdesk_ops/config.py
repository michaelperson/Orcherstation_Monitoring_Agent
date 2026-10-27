"""Configuration du poste : une seule source de vérité, `infrastructure/.env` (généré par generate_env.py)."""
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

# Rôle fonctionnel -> (variable du modèle, variable de l'URL vLLM) : le code parle de rôles, le .env choisit
# les modèles. vLLM sert UN modèle par serveur, d'où une URL par rôle (alt et judge partagent le serveur gemma).
ROLES_MODELES = {
    "agent": ("MODEL_AGENT", "VLLM_URL_AGENT"),
    "alt": ("MODEL_AGENT_ALT", "VLLM_URL_ALT"),
    "small": ("MODEL_SMALL", "VLLM_URL_SMALL"),
    "judge": ("MODEL_JUDGE", "VLLM_URL_JUDGE"),
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


def moteur() -> str:
    """'vllm' (salle, GPU) ou 'ollama' (préparation sans GPU, plan B). Un .env sans LLM_BACKEND = Ollama."""
    return os.environ.get("LLM_BACKEND", "ollama").strip().lower()


def basculer_vllm(mode: str) -> None:
    """vLLM : 'agents' (granite 8b + 3b) ou 'juge' (gemma4 seul) ; 24 Go ne tiennent pas les trois ensemble.

    Appelle infrastructure/vllm_mode.sh (1 à 3 min si le mode change, immédiat sinon). Sans effet sous Ollama,
    qui charge les modèles à la demande.
    """
    if mode not in ("agents", "juge"):
        raise ValueError(f"mode inconnu : {mode!r}. Modes valides : agents, juge")
    if "LLM_BACKEND" not in os.environ:
        charger_env()
    if moteur() != "vllm":
        return
    subprocess.run(["bash", str(trouver_env().parent / "vllm_mode.sh"), mode], check=True)


def creer_llm(role: str = "agent", *, temperature: float = 0, num_ctx: int = 16384,
              reasoning: bool | None = None, **kwargs) -> BaseChatModel:
    """Modèle de chat pour un rôle ('agent', 'alt', 'small', 'judge'), sur le moteur choisi par LLM_BACKEND.

    temperature=0 : décisions reproductibles (choix d'outil, routage).
    num_ctx=16384 : Ollama seulement. vLLM fixe le contexte au démarrage du serveur (--max-model-len) et
        REFUSE un prompt trop long (erreur 400), là où Ollama le tronque en silence.
    reasoning=False : coupe le raisonnement de gemma4 (juge). Ollama : paramètre `reasoning` ;
        vLLM : `chat_template_kwargs={"enable_thinking": False}`.
    """
    if role not in ROLES_MODELES:
        raise ValueError(f"rôle inconnu : {role!r}. Rôles valides : {', '.join(ROLES_MODELES)}")
    var_modele, var_url = ROLES_MODELES[role]
    if var_modele not in os.environ:
        charger_env()

    if moteur() == "ollama":
        from langchain_ollama import ChatOllama
        if reasoning is not None:
            kwargs["reasoning"] = reasoning
        return ChatOllama(
            model=os.environ[var_modele],
            base_url=os.environ["OLLAMA_BASE_URL"],
            temperature=temperature,
            num_ctx=num_ctx,
            **kwargs,
        )

    from langchain_openai import ChatOpenAI
    if reasoning is not None:
        corps = kwargs.setdefault("extra_body", {})
        corps.setdefault("chat_template_kwargs", {})["enable_thinking"] = reasoning
    # max_retries=0 : le client OpenAI réessaie 2 fois par défaut, en silence. Les nouveaux essais sont
    # l'affaire du graphe (RetryPolicy, J2-04), pas du client.
    kwargs.setdefault("max_retries", 0)
    return ChatOpenAI(
        model=os.environ[var_modele],
        base_url=os.environ[var_url],
        api_key=os.environ["VLLM_API_KEY"],
        temperature=temperature,
        **kwargs,
    )
