"""Checkpoints LangGraph et RGPD (jalon J2).

Un checkpoint contient TOUT l'état du graphe, donc toute la conversation : noms, e-mails,
numéros… en clair. Le masquage Langfuse (J1) ne s'applique pas ici. Il faut donc :
- une **durée de conservation** appliquée par une purge planifiée (art. 5.1.e) ;
- un **droit à l'effacement** par conversation (art. 17) : `delete_thread` ;
- un fichier SQLite protégé (droits, chiffrement du disque) et hors de Git (`*.sqlite` dans .gitignore).
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver

from helpdesk_ops.config import trouver_env


def chemin_checkpoints(nom: str = "checkpoints.sqlite") -> Path:
    """Fichier SQLite des checkpoints, dans Orchestration/data/checkpoints/ (créé au besoin, ignoré par Git)."""
    dossier = trouver_env().parent.parent / "data" / "checkpoints"
    dossier.mkdir(parents=True, exist_ok=True)
    ignore = dossier / ".gitignore"
    if not ignore.exists():   # ce dossier contient des conversations en clair : jamais versionné
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")
    return dossier / nom


def _derniere_activite(saver: BaseCheckpointSaver) -> dict[str, datetime]:
    """thread_id -> horodatage du checkpoint le plus récent."""
    activite: dict[str, datetime] = {}
    for cp in saver.list(None):
        thread_id = cp.config["configurable"]["thread_id"]
        ts = datetime.fromisoformat(cp.checkpoint["ts"])
        activite[thread_id] = max(ts, activite.get(thread_id, ts))
    return activite


def purger_threads(saver: BaseCheckpointSaver, conservation: timedelta, *,
                   maintenant: datetime | None = None, simulation: bool = False) -> list[str]:
    """Supprime les conversations inactives depuis plus de `conservation`. Renvoie les thread_id concernés.

    `simulation=True` : liste sans supprimer (à journaliser avant la première vraie purge).
    À planifier (cron, tâche planifiée) avec une durée documentée dans le registre des traitements.
    """
    limite = (maintenant or datetime.now(timezone.utc)) - conservation
    perimes = sorted(t for t, ts in _derniere_activite(saver).items() if ts < limite)
    if not simulation:
        for thread_id in perimes:
            saver.delete_thread(thread_id)
    return perimes
