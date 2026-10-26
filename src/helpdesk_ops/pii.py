"""Masquage des données personnelles AVANT l'envoi vers Langfuse (RGPD art. 5.1.c et 25).

Expressions volontairement simples (pédagogiques). Elles ratent les noms propres, les adresses,
`+32 (0)470…`, `0032 470…`, les numéros fixes et les IBAN non belges. En production : une
bibliothèque dédiée (Presidio) ou le PIIMiddleware de LangChain (J5), une rétention courte et un
accès restreint. Aucune de ces mesures ne suffit seule.
"""
import re

MOTIFS_PII = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "TEL": re.compile(r"(?:\+32|0)\s?4\d{2}(?:[\s./]?\d{2}){3}"),   # mobiles belges : 04xx xx xx xx
    "IBAN": re.compile(r"\bBE\d{2}(?:\s?\d{4}){3}\b"),              # IBAN belge
}


def masquer_pii(*, data, **kwargs):
    """Fonction `mask` du client Langfuse : appelée sur chaque input/output/metadata avant l'envoi.

    Descend récursivement dans les dict, list et tuple (`@observe` transmet les arguments
    sous forme de tuple : sans ce cas, la trace racine part en clair).
    """
    if isinstance(data, str):
        for etiquette, motif in MOTIFS_PII.items():
            data = motif.sub(f"<{etiquette}>", data)
        return data
    if isinstance(data, dict):
        return {cle: masquer_pii(data=valeur) for cle, valeur in data.items()}
    if isinstance(data, (list, tuple)):
        return type(data)(masquer_pii(data=element) for element in data)
    return data
