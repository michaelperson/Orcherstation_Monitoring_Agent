"""Conformité appliquée au help-desk (cours du jour 5) : AI Act art. 50, RGPD (conservation), NIS2 (traçabilité).

Ce module traduit des obligations en code ; il ne remplace ni le DPO ni le juriste. Les durées de
conservation ci-dessous sont des PROPOSITIONS pédagogiques, à fixer dans le registre des traitements.
Les références réglementaires et leurs échéances sont détaillées (avec leur statut de vérification)
dans le notebook J5-03.
"""
from datetime import datetime, timedelta, timezone

from langchain_core.messages import AIMessage
from langfuse import Langfuse
from langgraph.checkpoint.base import BaseCheckpointSaver

from helpdesk_ops.observabilite import purger_traces
from helpdesk_ops.persistance import purger_threads

SYSTEME = "HelpDesk-Ops"

# AI Act art. 50(1) : la personne est informée qu'elle interagit avec un système d'IA, dès le début.
MESSAGE_IA = ("Vous échangez avec HelpDesk-Ops, un assistant d'intelligence artificielle du help-desk NordTech. "
              "Ses réponses peuvent contenir des erreurs : aucune action sensible n'est faite sans un technicien. "
              "Vos échanges sont journalisés pour la qualité du service et conservés 30 jours.")


def marquer(message: AIMessage, *, version: str, modele: str) -> AIMessage:
    """Marquage machine-lisible d'une réponse générée (métadonnées), en plus de l'information visible.

    Les métadonnées voyagent avec le message (API, Streamlit, traces) : un système aval peut détecter qu'un
    contenu est généré par une IA, par quel système et quelle version. Format à aligner sur les standards
    retenus par l'entreprise (à vérifier : lignes directrices et codes de pratique de la Commission sur l'art. 50).
    """
    marque = {"genere_par_ia": True, "systeme": SYSTEME, "version": version, "modele": modele,
              "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    return message.model_copy(update={"response_metadata": {**message.response_metadata, "ia_act_art50": marque}})


def est_marque(message: AIMessage) -> bool:
    return bool(message.response_metadata.get("ia_act_art50", {}).get("genere_par_ia"))


# --------------------------------------------------------------------------- RGPD : conservation (art. 5.1.e)
CONSERVATION = {   # proposition, à valider et à inscrire au registre des traitements
    "checkpoints": timedelta(days=30),    # conversations en clair (J2)
    "traces": timedelta(days=30),         # Langfuse, données masquées mais pas anonymes (J4)
}


def purge_planifiee(langfuse: Langfuse, saver: BaseCheckpointSaver, *, maintenant: datetime | None = None,
                    simulation: bool = True) -> dict[str, list[str]]:
    """La purge à planifier chaque nuit (cron, tâche planifiée) : checkpoints ET traces, une seule politique."""
    maintenant = maintenant or datetime.now(timezone.utc)
    return {
        "checkpoints": purger_threads(saver, CONSERVATION["checkpoints"], maintenant=maintenant, simulation=simulation),
        "traces": purger_traces(langfuse, avant=maintenant - CONSERVATION["traces"], simulation=simulation),
    }


# --------------------------------------------------------------------------- NIS2 : chronologie d'un incident
def chronologie_incident(langfuse: Langfuse, *, debut: datetime, fin: datetime | None = None,
                         niveaux: tuple[str, ...] = ("ERROR", "WARNING"), limite: int = 200) -> list[dict]:
    """Observations en erreur ou en alerte sur une période, dans l'ordre : la matière première d'une notification.

    Les traces disent QUAND, QUOI (nœud, outil, modèle) et avec quel message ; le rapport d'incident reste
    rédigé par un humain. Mode events_only : API v2 des observations (champs « core,basic »).
    """
    lignes = []
    for niveau in niveaux:
        page = langfuse.api.observations.get_many(fields="core,basic", limit=limite, level=niveau,
                                                  from_start_time=debut, to_start_time=fin)
        lignes += [{"debut": o.start_time, "niveau": o.level, "nom": o.name, "type": o.type,
                    "message": (o.status_message or "")[:200], "trace_id": o.trace_id, "session_id": o.session_id}
                   for o in page.data]
    return sorted(lignes, key=lambda l: l["debut"])
