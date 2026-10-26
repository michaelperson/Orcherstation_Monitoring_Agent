"""Client Langfuse (SDK v4) configuré une fois, avec masquage des données personnelles ; purge RGPD des traces."""
from datetime import datetime

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from helpdesk_ops.config import charger_env
from helpdesk_ops.pii import masquer_pii


def init_observabilite(*, mask=masquer_pii, verifier: bool = True) -> tuple[Langfuse, CallbackHandler]:
    """Renvoie (client Langfuse, CallbackHandler LangChain).

    Le SDK v4 garde un client unique par clé publique : c'est la PREMIÈRE configuration qui
    s'applique. Pour changer de fonction de masquage, redémarrer le kernel.
    Clés et URL viennent de l'environnement (LANGFUSE_PUBLIC_KEY, _SECRET_KEY, _BASE_URL).
    """
    charger_env()
    langfuse = Langfuse(mask=mask)
    if verifier and not langfuse.auth_check():
        raise RuntimeError("Langfuse refuse les clés (ou démarre encore : attendre 2-3 min)")
    return langfuse, CallbackHandler()


# --------------------------------------------------------------------------- RGPD : purge et effacement (J4)
def traces_concernees(langfuse: Langfuse, *, avant: datetime | None = None, user_id: str | None = None,
                      session_id: str | None = None) -> list[str]:
    """Identifiants des traces dont l'observation racine correspond aux critères.

    Le serveur v4 tourne en mode « events_only » : `/api/public/traces` répond 404, on passe donc par
    l'API v2 des observations (racines uniquement). Vérifié le 21/10/2026.
    """
    ids, curseur = set(), None
    while True:
        page = langfuse.api.observations.get_many(fields="core", limit=1000, cursor=curseur, is_root_observation=True,
                                                  to_start_time=avant, user_id=user_id, session_id=session_id)
        ids.update(o.trace_id for o in page.data)
        curseur = (page.meta.cursor if page.meta else None)
        if not curseur or not page.data:
            return sorted(ids)


def purger_traces(langfuse: Langfuse, *, avant: datetime | None = None, user_id: str | None = None,
                  session_id: str | None = None, simulation: bool = True) -> list[str]:
    """Supprime les traces visées (conservation limitée, droit à l'effacement). `simulation=True` : liste seulement.

    La « data retention » automatique de Langfuse est réservée à l'édition Enterprise ; en open source,
    la suppression par API fonctionne (vérifié : 1 observation avant, 0 après) et se planifie comme
    `persistance.purger_threads` pour les checkpoints.
    """
    if avant is None and user_id is None and session_id is None:
        raise ValueError("critère obligatoire : avant, user_id ou session_id (refus de tout purger par mégarde)")
    ids = traces_concernees(langfuse, avant=avant, user_id=user_id, session_id=session_id)
    if not simulation:
        for i in range(0, len(ids), 100):
            langfuse.api.trace.delete_multiple(trace_ids=ids[i:i + 100])
    return ids


def effacer_session(langfuse: Langfuse, session_id: str, *, traces_connues: list[str] = (), attente_s: float = 30,
                    intervalle_s: float = 2) -> tuple[list[str], list[str]]:
    """Effacement d'une conversation à la demande de la personne (RGPD art. 17) ; renvoie (supprimées, introuvables).

    Constaté le 22/10/2026 avec l'interface Streamlit : effacer juste après un échange supprimait 0 trace et
    annonçait pourtant un succès. L'envoi vers Langfuse est asynchrone et l'ingestion prend quelques secondes.
    On vide donc la file d'envoi, puis on attend que les traces CONNUES (identifiants gardés par l'interface)
    soient visibles avant de supprimer ; celles qui restent introuvables sont signalées, jamais passées sous silence.
    """
    import time
    langfuse.flush()
    attendues, debut = set(traces_connues), time.monotonic()
    while True:
        trouvees = set(traces_concernees(langfuse, session_id=session_id))
        if attendues <= trouvees or time.monotonic() - debut > attente_s:
            break
        time.sleep(intervalle_s)
    a_supprimer = sorted(trouvees)
    for i in range(0, len(a_supprimer), 100):
        langfuse.api.trace.delete_multiple(trace_ids=a_supprimer[i:i + 100])
    return a_supprimer, sorted(attendues - trouvees)
