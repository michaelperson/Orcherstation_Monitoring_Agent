"""Outil de ticketing simulé de NordTech SA (jalon J2).

Deux règles de production, appliquées dès la formation :
- **idempotence** : créer deux fois le ticket d'une même demande (reprise après interruption,
  rejeu, double clic) renvoie le ticket existant au lieu d'en créer un second ;
- **traçabilité** : chaque ticket garde qui l'a validé (validation humaine des P1).
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Ticket:
    id: str
    categorie: str
    priorite: str
    resume: str
    file: str
    valide_par: str | None = None
    cree_le: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


class Ticketing:
    """Stockage en mémoire. En production : l'API de l'outil ITSM (avec la même clé d'idempotence)."""

    def __init__(self, prefixe: str = "NT"):
        self.prefixe = prefixe
        self._tickets: dict[str, Ticket] = {}
        self._par_cle: dict[str, str] = {}

    def creer(self, *, cle_idempotence: str, categorie: str, priorite: str, resume: str, file: str,
              valide_par: str | None = None) -> Ticket:
        if cle_idempotence in self._par_cle:   # déjà créé pour cette demande : on ne duplique pas
            return self._tickets[self._par_cle[cle_idempotence]]
        ticket = Ticket(id=f"{self.prefixe}-{len(self._tickets) + 1:04d}", categorie=categorie, priorite=priorite,
                        resume=resume, file=file, valide_par=valide_par)
        self._tickets[ticket.id] = ticket
        self._par_cle[cle_idempotence] = ticket.id
        return ticket

    def par_cle(self, cle_idempotence: str) -> Ticket | None:
        """Le ticket déjà créé pour cette clé, s'il existe."""
        identifiant = self._par_cle.get(cle_idempotence)
        return self._tickets[identifiant] if identifiant else None

    def lister(self) -> list[Ticket]:
        return list(self._tickets.values())

    def vider(self) -> None:
        self._tickets.clear()
        self._par_cle.clear()


TICKETING = Ticketing()   # instance partagée par les notebooks
