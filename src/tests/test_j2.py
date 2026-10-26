import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from helpdesk_ops.jalons.j1 import REPLI
from helpdesk_ops.jalons.j2 import TicketDecision, arepondre, areprendre, construire_support_j2
from helpdesk_ops.persistance import purger_threads
from helpdesk_ops.reseau import RESEAU
from helpdesk_ops.ticketing import Ticketing


def qualifieur_fixe(**champs):
    """Remplace le LLM de qualification : renvoie toujours la même décision."""
    decision = TicketDecision(**{"besoin_ticket": True, "categorie": "reseau", "priorite": "P3",
                                 "resume": "problème réseau", **champs})

    async def qualifier(messages):
        return decision
    return qualifier


@pytest.fixture
def ticketing():
    return Ticketing()


def graphe(modele, ticketing, **options):
    options.setdefault("qualifieur", qualifieur_fixe())
    return construire_support_j2(modele, checkpointer=InMemorySaver(), ticketing=ticketing, **options)


def tour(g, question, thread_id="t1"):
    return asyncio.run(arepondre(g, question, thread_id=thread_id))


# --------------------------------------------------------------------------- sortie structurée et routage
def test_p3_cree_un_ticket_sans_validation(faux_modele, ticketing):
    r = tour(graphe(faux_modele, ticketing), "srv-erp-02 ne répond plus")
    assert r["interruption"] is None and r["ticket_id"] == "NT-0001"
    assert ticketing.lister()[0].file == "N2-infra" and ticketing.lister()[0].valide_par is None


def test_pas_de_ticket_si_inutile(faux_modele, ticketing):
    r = tour(graphe(faux_modele, ticketing, qualifieur=qualifieur_fixe(besoin_ticket=False)), "srv-erp-02 ?")
    assert r["ticket_id"] is None and ticketing.lister() == []
    assert r["reponse"] == "Réponse : hors ligne"


def test_qualification_illisible_pas_de_ticket(faux_modele, ticketing):
    async def illisible(messages):
        return None   # ce que renvoie with_structured_output(method="function_calling") si le modèle répond en prose
    r = tour(graphe(faux_modele, ticketing, qualifieur=illisible), "srv-erp-02 ne répond plus")
    assert ticketing.lister() == [] and "transmise au help-desk N1" in r["reponse"]


def test_qualification_en_panne_pas_de_ticket(faux_modele, ticketing):
    async def en_panne(messages):
        raise ConnectionError("ollama injoignable")
    r = tour(graphe(faux_modele, ticketing, qualifieur=en_panne, tentatives=2), "srv-erp-02 ne répond plus")
    assert ticketing.lister() == [] and "transmise au help-desk N1" in r["reponse"]


def test_decision_invalide_refusee_par_pydantic():
    with pytest.raises(ValueError):
        TicketDecision(besoin_ticket=True, categorie="reseau", priorite="P0", resume="x")


# --------------------------------------------------------------------------- validation humaine (HITL)
def test_p1_attend_une_validation_puis_cree(faux_modele, ticketing):
    g = graphe(faux_modele, ticketing, qualifieur=qualifieur_fixe(priorite="P1"))
    r = tour(g, "srv-erp-02 en panne, toute la compta est bloquée")
    assert r["interruption"]["type"] == "validation_ticket_p1" and ticketing.lister() == []
    r = asyncio.run(areprendre(g, {"action": "approuver", "par": "resp-n2"}, thread_id="t1"))
    assert r["ticket_id"] == "NT-0001" and ticketing.lister()[0].valide_par == "resp-n2"


def test_p1_modifie_en_p2(faux_modele, ticketing):
    g = graphe(faux_modele, ticketing, qualifieur=qualifieur_fixe(priorite="P1"))
    tour(g, "srv-erp-02 en panne")
    asyncio.run(areprendre(g, {"action": "modifier", "priorite": "P2", "par": "resp-n2"}, thread_id="t1"))
    assert ticketing.lister()[0].priorite == "P2"


def test_p1_rejete(faux_modele, ticketing):
    g = graphe(faux_modele, ticketing, qualifieur=qualifieur_fixe(priorite="P1"))
    tour(g, "srv-erp-02 en panne")
    r = asyncio.run(areprendre(g, {"action": "rejeter", "par": "resp-n2", "motif": "doublon"}, thread_id="t1"))
    assert ticketing.lister() == [] and "doublon" in r["reponse"]


def test_idempotence_un_ticket_par_conversation(faux_modele, ticketing):
    g = graphe(faux_modele, ticketing)
    tour(g, "srv-erp-02 ne répond plus")
    tour(g, "toujours rien sur srv-erp-02")
    assert len(ticketing.lister()) == 1
    tour(g, "srv-erp-02 ne répond plus", thread_id="t2")
    assert len(ticketing.lister()) == 2


# --------------------------------------------------------------------------- robustesse
def test_outil_instable_reessaye(ticketing, faux_modele):
    faux_modele.outil, faux_modele.args = "ping_serveur", {"hote": "srv-mail-01"}
    RESEAU.configurer(echecs_avant_succes=2)
    r = tour(graphe(faux_modele, ticketing, tentatives=3), "srv-mail-01 répond-il ?")
    assert RESEAU.appels == 3   # 2 échecs, puis succès au 3e essai
    assert r["ticket_id"] == "NT-0001"


def test_outil_en_panne_repli_sans_planter(ticketing, faux_modele):
    faux_modele.outil, faux_modele.args = "ping_serveur", {"hote": "srv-mail-01"}
    RESEAU.configurer(echecs_avant_succes=99)
    g = graphe(faux_modele, ticketing, tentatives=2, qualifieur=qualifieur_fixe(besoin_ticket=False))
    r = tour(g, "srv-mail-01 répond-il ?")
    assert RESEAU.appels == 2
    assert r["reponse"].startswith("Réponse : outil indisponible (ConnectionError)")


def test_agent_trop_lent_repli(ticketing, faux_modele):
    faux_modele.delai_s = 0.3
    g = graphe(faux_modele, ticketing, timeout_llm_s=0.05, tentatives=1)
    r = tour(g, "srv-erp-02 ?")
    assert r["reponse"] == REPLI and ticketing.lister() == []


# --------------------------------------------------------------------------- RGPD : purge des conversations
def test_purge_des_conversations_inactives(faux_modele, ticketing):
    saver = InMemorySaver()
    g = construire_support_j2(faux_modele, checkpointer=saver, ticketing=ticketing,
                              qualifieur=qualifieur_fixe(besoin_ticket=False))
    asyncio.run(arepondre(g, "srv-erp-02 ?", thread_id="ancien"))
    dans_un_an = datetime.now(timezone.utc) + timedelta(days=365)
    assert purger_threads(saver, timedelta(days=30), maintenant=dans_un_an, simulation=True) == ["ancien"]
    assert list(saver.list(None))   # simulation : rien supprimé
    assert purger_threads(saver, timedelta(days=30), maintenant=dans_un_an) == ["ancien"]
    assert not list(saver.list(None))


# --------------------------------------------------------------------------- régressions constatées en exécutant J2-05
def test_qualification_ne_voit_que_le_tour_courant(faux_modele, ticketing):
    vus = []

    async def espion(messages):
        vus.append([m.content for m in messages])
        return TicketDecision(besoin_ticket=False, categorie="autre", priorite="P4", resume="question")

    g = graphe(faux_modele, ticketing, qualifieur=espion)
    tour(g, "srv-erp-02 en panne, la compta est bloquée")
    tour(g, "Autre chose : comment reconfigurer le VPN ?")
    assert not any("compta" in texte for texte in vus[1])   # l'ancien incident n'est pas re-qualifié


def test_la_reponse_de_l_agent_n_est_pas_masquee_par_le_ticket(faux_modele, ticketing):
    g = graphe(faux_modele, ticketing)
    r = tour(g, "srv-erp-02 ne répond plus")
    assert "Réponse : hors ligne" in r["reponse"] and "NT-0001 enregistré" in r["reponse"]
    r = tour(g, "toujours rien sur srv-erp-02")
    assert "déjà suivie sous le ticket NT-0001" in r["reponse"] and len(ticketing.lister()) == 1
