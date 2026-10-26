import pytest

from helpdesk_ops.config import ROLES_MODELES, creer_llm
from helpdesk_ops.pii import masquer_pii
from helpdesk_ops.texte import normaliser, sans_accents


def test_sans_accents():
    assert sans_accents("Accès Réseau, BLOQUÉ") == "Acces Reseau, BLOQUE"
    assert normaliser("  Écran   BLOQUÉ ") == "ecran bloque"


@pytest.mark.parametrize("entree, attendu", [
    ("écrire à a.b@c.be", "écrire à <EMAIL>"),
    ("0470 12 34 56", "<TEL>"),
    ("+32 470 12 34 56", "<TEL>"),
    ("0470/12.34.56", "<TEL>"),
    ("BE71 0961 2345 6769", "<IBAN>"),
])
def test_masquage_formats(entree, attendu):
    assert masquer_pii(data=entree) == attendu


def test_masquage_structures():
    # Le tuple est le cas qui fuyait : @observe transmet les arguments sous forme de tuple
    assert masquer_pii(data=("BE71 0961 2345 6769",)) == ("<IBAN>",)
    assert masquer_pii(data={"args": ("a@b.be",), "kwargs": {"tel": ["0470 12 34 56"]}}) == \
        {"args": ("<EMAIL>",), "kwargs": {"tel": ["<TEL>"]}}
    assert masquer_pii(data=42) == 42


def test_limites_connues_du_masquage():
    # Documente les limites : si ce test casse, le masque a été amélioré, mettre à jour les supports
    assert masquer_pii(data="Julie Martin") == "Julie Martin"
    assert masquer_pii(data="0032 470 12 34 56") == "0032 470 12 34 56"


def test_role_inconnu():
    with pytest.raises(ValueError, match="rôle inconnu"):
        creer_llm("chef")
    assert set(ROLES_MODELES) == {"agent", "alt", "small", "judge"}
