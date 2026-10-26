import asyncio
from pathlib import Path

import pytest

from conftest import FauxModeleOutils
from helpdesk_ops import kb
from helpdesk_ops.jalons.j1 import decider_par_regles
from helpdesk_ops.jalons.j3 import construire_helpdesk_j3, construire_specialistes_j3
from helpdesk_ops.multi_agents import construire_coordinateur, construire_specialistes, outils_ticketing
from helpdesk_ops.ticketing import Ticketing


def recherche_factice(question, categorie=None):
    return f"[KB-001] procédure VPN (catégorie demandée : {categorie})"


# --------------------------------------------------------------------------- KB : lecture et découpage (sans Qdrant)
def test_articles_et_metadonnees():
    articles = kb.charger_articles(Path(__file__).resolve().parents[2] / "data" / "kb")
    assert len(articles) == 20
    assert {a.metadata["visibilite"] for a in articles} == {"public", "interne"}
    morceaux = kb.decouper(articles)
    assert all(m.page_content.startswith(m.metadata["titre"]) for m in morceaux)   # le titre reste indexé


def test_filtre_public_par_defaut():
    f = kb.filtre()
    assert f.must[0].key == "metadata.visibilite" and f.must[0].match.value == "public"
    assert kb.filtre(public_seulement=False) is None
    assert len(kb.filtre(categorie="acces").must) == 2


# --------------------------------------------------------------------------- garde-fou élargi pour J3
@pytest.mark.parametrize("demande", ["Le PC-0203 est très lent", "Combien de tickets en N2-infra ?", "Mon code MFA ne marche plus"])
def test_garde_fou_accepte_les_demandes_j3(demande):
    assert decider_par_regles(demande) == "SUPPORT"


# --------------------------------------------------------------------------- sous-agents comme outils
def test_coordinateur_delegue_et_isole_le_contexte():
    coord = FauxModeleOutils(outil="demander_diagnostic", args={"consigne": "statut de srv-erp-02"})
    spec = FauxModeleOutils()   # appelle statut_serveur(srv-erp-02)
    specialistes = construire_specialistes(spec, recherche=recherche_factice, ticketing=Ticketing())
    graphe = construire_coordinateur(coord, specialistes)
    etat = asyncio.run(graphe.ainvoke({"messages": [("user", "Bonjour, je suis Julie, srv-erp-02 répond-il ?")]}))
    assert etat["messages"][-1].content == "Réponse : Réponse : hors ligne"
    # Isolation : le spécialiste n'a vu que la consigne, jamais le message (ni le nom) de l'utilisateur
    assert all("Julie" not in " ".join(appel) for appel in spec.vus)
    assert any("statut de srv-erp-02" in " ".join(appel) for appel in spec.vus)


def test_specialiste_acces_filtre_la_categorie():
    spec = FauxModeleOutils(outil="rechercher_procedures", args={"question": "compte verrouillé"})
    specialistes = construire_specialistes_j3(spec, recherche=recherche_factice, ticketing=Ticketing())
    etat = asyncio.run(specialistes["acces"].ainvoke({"messages": [("user", "compte verrouillé")]}))
    assert "catégorie demandée : acces" in etat["messages"][-1].content


def test_jalon_refuse_hors_perimetre_sans_appeler_le_modele():
    coord = FauxModeleOutils()
    g = construire_helpdesk_j3(coord, recherche=recherche_factice, ticketing=Ticketing())
    etat = asyncio.run(g.ainvoke({"messages": [("user", "Écris-moi un poème")]}))
    assert coord.appels == 0 and "informatique" in etat["messages"][-1].content


# --------------------------------------------------------------------------- ticketing
def test_ouvrir_ticket_refuse_p1_et_reste_idempotent():
    t = Ticketing()
    _, ouvrir = outils_ticketing(t)
    assert "P1 refusé" in ouvrir.invoke({"resume": "ERP arrêté", "categorie": "logiciel", "priorite": "P1"})
    for _ in range(2):
        ouvrir.invoke({"resume": "Écran qui clignote", "categorie": "materiel", "priorite": "P3"})
    assert len(t.lister()) == 1
    assert "invalides" in ouvrir.invoke({"resume": "x", "categorie": "urgent", "priorite": "P2"})


# --------------------------------------------------------------------------- MCP : liste blanche côté client
def test_mcp_liste_blanche():
    from langchain.mcp import MCPAdapter
    from helpdesk_ops.mcp_inventaire import filtrer_outils, mcp
    outils = asyncio.run(MCPAdapter(mcp).list_tools())
    noms = {o.name for o in outils}
    assert noms == {"lister_postes", "detail_poste", "historique_interventions", "reinitialiser_poste"}
    assert {o.name for o in filtrer_outils(outils)} == noms - {"reinitialiser_poste"}
    assert [o.name for o in filtrer_outils(outils, autorises={"detail_poste"})] == ["detail_poste"]
