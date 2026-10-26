# `src/helpdesk_ops` : le code du fil rouge HelpDesk-Ops

Le code que les notebooks construisent jour après jour, rangé dans un paquet Python importable. Les notebooks l'importent au lieu de recopier les mêmes 50 lignes de configuration.

## Installation

Rien à faire : `uv sync` dans `infrastructure/` l'installe en mode **éditable** (`[tool.uv.sources]` dans `infrastructure/pyproject.toml`). Une modification dans `src/` est prise en compte après un redémarrage du kernel.

```bash
cd infrastructure
uv sync
uv run pytest ../src/tests        # 79 tests, sans Ollama ni Langfuse (modèle simulé, tracing désactivé)
```

## Contenu

| Module | Rôle | Disponible |
|---|---|---|
| `config` | lecture de `infrastructure/.env`, `creer_llm(role)` (`agent`, `alt`, `small`, `judge`) | dès J1 |
| `texte` | `sans_accents`, `normaliser` (comparaisons en français) | dès J1 |
| `pii` | `masquer_pii`, la fonction `mask` du client Langfuse | dès J1 |
| `observabilite` | `init_observabilite()` → (client Langfuse v4 avec masquage, `CallbackHandler`) ; `traces_concernees`, `purger_traces` (effacement RGPD, purge planifiée, simulation par défaut), `effacer_session` (attend l'ingestion des traces connues, J5) | dès J1 (purge : J4) |
| `donnees` | inventaire, files de tickets et KB **fictifs** de NordTech SA | dès J1 |
| `outils` | `statut_serveur`, `tickets_ouverts`, `chercher_kb` | **fin de J1** |
| `tri` | classifieur LCEL, `normaliser_categorie`, `file_attente`, `estimer_priorite` | **fin de J1** |
| `jalons/j1` | agent support en StateGraph + garde-fou (règles ou LLM), `repondre()` | **fin de J1** |
| `ticketing` | ticketing simulé, **idempotent** (clé = `thread_id`), trace qui a validé | dès J2 |
| `reseau` | supervision simulée **instable** et reproductible (`RESEAU.configurer(...)`), outil `ping_serveur` | dès J2 |
| `persistance` | `chemin_checkpoints()` (→ `data/checkpoints/`, ignoré par Git), `purger_threads()` | dès J2 |
| `jalons/j2` | agent async : persistance, validation P1 (`interrupt`), `TicketDecision`, retries/timeouts/replis ; `arepondre`, `areprendre` | **fin de J2** |
| `kb` | KB `data/kb/` sur Qdrant : `indexer()`, `rechercher(question, public_seulement, categorie, mode)`, `precharger_modeles()` | dès J3 |
| `multi_agents` | spécialistes KB / Diagnostic / Ticketing, `comme_outil`, `construire_coordinateur`, `construire_routeur` | dès J3 |
| `mcp_inventaire` | serveur FastMCP « inventaire-parc », `transport_stdio()`, `filtrer_outils()` (liste blanche) | dès J3 |
| `jalons/j3` | garde-fou + coordinateur + 4 spécialistes (Accès = corrigé Ex3.1) : `construire_helpdesk_j3` | **fin de J3** |
| `tableau_bord` | requêtes de l'API metrics (mode *events_only*) : `latence_par_trace`, `generations_par_modele`, `erreurs_par_niveau`, `volume_par_jour`, `scores_moyens`, `sessions_les_plus_actives` | dès J4 |
| `evaluation` | dataset `data/eval/helpdesk_eval.json` (20 cas) et `synchroniser_dataset` ; tâches `tache_routage` (consignes `CONSIGNE_ROUTAGE_V1`/`V2`), `tache_outil`, `tache_qualification` ; évaluateurs ; juge LLM (`Jugement`, `creer_juge`, `noter` : note calculée) ; `resume`, `lignes_resultat` | dès J4 |
| `securite` | garde-fou hybride (`creer_garde_fou`), `middlewares_pii`, `middlewares_limites`, `ListeBlancheAudit` + `JournalAudit` (corrigé Ex5.1), nettoyage et encadrement des documents, `controler_sortie`, `retirer_references_inexistantes` | dès J5 |
| `conformite` | `MESSAGE_IA` et `marquer` (AI Act art. 50), `CONSERVATION`, `purge_planifiee`, `chronologie_incident` (NIS2) | dès J5 |
| `redteam` | scénarios du lab J5 : agents vulnérable / protégé, détecteurs, mesure d'un taux sur plusieurs essais (simulés, locaux) | dès J5 |
| `jalons/j5` | jalon J3 + garde-fou hybride, middlewares, KB protégée, contrôle de sortie, information IA et marquage ; `graphe` pour `langgraph.json`, `repondre_avec_trace` pour Streamlit | **fin de J5** |

⚠️ Les modules marqués **fin de J1** / **fin de J2** contiennent les corrigés des exercices du jour (1.1, 1.2, défi J1-01 ; 2.1, 2.2 ; 3.1 ; 5.1). Le module `evaluation` fournit les briques de l'exercice 4.1 (le tableau et la recommandation restent à écrire). Si le dossier est distribué aux apprenants dès le premier jour, retirez-les et distribuez-les après le débriefing. Chaque journée ajoutera son jalon (`jalons/j2`…).

## Utilisation dans un notebook

```python
from helpdesk_ops.config import creer_llm
from helpdesk_ops.observabilite import init_observabilite
from helpdesk_ops.jalons.j1 import construire_support, repondre

langfuse, langfuse_handler = init_observabilite()
support = construire_support(creer_llm("agent"))
print(repondre(support, "srv-erp-02 est-il en ligne ?", callbacks=[langfuse_handler]))
```

## Tests

Les tests documentent aussi les **limites assumées** (masque PII qui laisse passer les noms, garde-fou par règles contournable par reformulation). Si l'un de ces tests casse parce que le code a été amélioré, mettez à jour les supports qui citent la limite.

Ils servent de base à la gate de CI du jour 5.
