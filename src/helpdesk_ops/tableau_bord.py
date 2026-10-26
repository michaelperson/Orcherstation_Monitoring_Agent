"""Indicateurs pour un responsable Ops, via l'API metrics de Langfuse v4 (jour 4).

Vérifié le 21/10/2026 sur le serveur de la formation (mode « events_only ») :
- vues disponibles : `observations`, `scores-numeric`, `scores-categorical`, `scores-boolean`
  (la vue `traces` est refusée : on agrège les observations, par `traceName`) ;
- une dimension à forte cardinalité (`sessionId`, `userId`) exige `config.row_limit` et un `orderBy` décroissant.
"""
import json
from datetime import datetime, timedelta, timezone

from langfuse import Langfuse


def requete(langfuse: Langfuse, *, vue: str = "observations", mesures: list[tuple[str, str]],
            dimensions: list[str] = (), filtres: list[dict] = (), depuis: timedelta = timedelta(days=7),
            granularite: str | None = None, limite: int | None = None) -> list[dict]:
    """Une requête metrics : mesures = [(measure, aggregation)], ex. [("latency", "p95"), ("count", "count")]."""
    maintenant = datetime.now(timezone.utc)
    corps = {
        "view": vue,
        "metrics": [{"measure": m, "aggregation": a} for m, a in mesures],
        "dimensions": [{"field": d} for d in dimensions],
        "filters": list(filtres),
        "fromTimestamp": (maintenant - depuis).isoformat(),
        "toTimestamp": maintenant.isoformat(),
    }
    if granularite:
        corps["timeDimension"] = {"granularity": granularite}
    if limite:   # obligatoire pour les dimensions à forte cardinalité
        m, a = mesures[0]
        corps["config"] = {"row_limit": limite}
        corps["orderBy"] = [{"field": f"{a}_{m}", "direction": "desc"}]
    return langfuse.api.metrics.metrics(query=json.dumps(corps)).data


GENERATIONS = [{"column": "type", "operator": "=", "value": "GENERATION", "type": "string"}]


def latence_par_trace(langfuse: Langfuse, **kw) -> list[dict]:
    """p50 / p95 (ms) et volume par nom de trace : où le temps passe-t-il ?"""
    return requete(langfuse, mesures=[("latency", "p50"), ("latency", "p95"), ("count", "count")],
                   dimensions=["traceName"], **kw)


def generations_par_modele(langfuse: Langfuse, **kw) -> list[dict]:
    """Appels LLM, latence p95 et tokens par modèle : le coût d'un modèle local, c'est du temps GPU."""
    return requete(langfuse, mesures=[("count", "count"), ("latency", "p95"), ("totalTokens", "sum")],
                   dimensions=["providedModelName"], filtres=GENERATIONS, **kw)


def erreurs_par_niveau(langfuse: Langfuse, **kw) -> list[dict]:
    return requete(langfuse, mesures=[("count", "count")], dimensions=["level"], **kw)


def volume_par_jour(langfuse: Langfuse, **kw) -> list[dict]:
    return requete(langfuse, mesures=[("count", "count")], granularite="day", **kw)


def scores_moyens(langfuse: Langfuse, **kw) -> list[dict]:
    return requete(langfuse, vue="scores-numeric", mesures=[("value", "avg"), ("count", "count")], dimensions=["name"], **kw)


def sessions_les_plus_actives(langfuse: Langfuse, n: int = 10, **kw) -> list[dict]:
    return requete(langfuse, mesures=[("count", "count")], dimensions=["sessionId"], limite=n, **kw)
