"""Normalisation de texte français : le piège n°1 des règles par mots-clés."""
import unicodedata


def sans_accents(texte: str) -> str:
    """'Accès Réseau' -> 'Acces Reseau' : décompose les lettres accentuées puis retire les accents."""
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def normaliser(texte: str) -> str:
    """Forme de comparaison : sans accents, en minuscules, sans espaces superflus."""
    return " ".join(sans_accents(texte).lower().split())
