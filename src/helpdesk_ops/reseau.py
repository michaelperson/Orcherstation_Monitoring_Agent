"""Supervision réseau simulée et INSTABLE (jalon J2, exercice 2.2).

Un vrai outil réseau échoue (timeout, connexion refusée) ou répond lentement. On simule ces
pannes de façon **reproductible** : un même scénario donne toujours la même séquence, ce qui
permet de tester la tolérance aux pannes (RetryPolicy, TimeoutPolicy, error_handler).
"""
import asyncio
import random
from dataclasses import dataclass, field

from langchain_core.tools import tool

from helpdesk_ops.donnees import INVENTAIRE


@dataclass
class SimulateurReseau:
    """`echecs_avant_succes` premiers appels en ConnectionError, puis `taux_echec` aléatoire (graine fixe).

    `latence_s` : durée de chaque appel ; au-delà du timeout du nœud, c'est un NodeTimeoutError.
    """
    echecs_avant_succes: int = 0
    taux_echec: float = 0.0
    latence_s: float = 0.0
    graine: int = 42
    appels: int = 0
    _alea: random.Random = field(init=False, repr=False)

    def __post_init__(self):
        self._alea = random.Random(self.graine)

    def configurer(self, *, echecs_avant_succes: int = 0, taux_echec: float = 0.0, latence_s: float = 0.0,
                   graine: int = 42) -> "SimulateurReseau":
        """Réinitialise le scénario (compteur d'appels et graine compris)."""
        self.echecs_avant_succes, self.taux_echec, self.latence_s, self.graine = (
            echecs_avant_succes, taux_echec, latence_s, graine)
        self.appels = 0
        self._alea = random.Random(graine)
        return self

    async def ping(self, hote: str) -> str:
        self.appels += 1
        await asyncio.sleep(self.latence_s)
        if self.appels <= self.echecs_avant_succes or self._alea.random() < self.taux_echec:
            raise ConnectionError(f"supervision injoignable (appel n°{self.appels})")
        statut = INVENTAIRE.get(hote.strip().lower())
        if statut is None:
            return f"inconnu : '{hote}' n'est pas dans l'inventaire"
        if statut == "hors ligne":
            return f"{hote} : aucune réponse au ping (100 % de perte)"
        return f"{hote} : répond au ping en 3 ms"


RESEAU = SimulateurReseau()   # instance partagée, reconfigurée par les notebooks


@tool(parse_docstring=True)
async def ping_serveur(hote: str) -> str:
    """Teste la joignabilité réseau d'un serveur NordTech (ping depuis la supervision).

    Args:
        hote: nom d'hôte exact en minuscules, par exemple 'srv-erp-02'
    """
    return await RESEAU.ping(hote)
