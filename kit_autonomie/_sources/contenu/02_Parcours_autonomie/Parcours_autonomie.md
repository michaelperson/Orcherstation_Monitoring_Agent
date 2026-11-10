# Votre parcours d'autonomie

La formation s'arrête, votre apprentissage non. Ce parcours vous dit **quoi faire, dans quel ordre, et avec quel
support**, pour maîtriser seul tout ce qui a été vu, vite ou pas du tout (MCP notamment), puis pour construire
votre propre projet.

Comptez **6 semaines à raison de 4 à 6 heures par semaine**. Le rythme importe moins que la régularité.

---

## Le kit en un coup d'œil

Le kit est dans le dépôt du cours, dossier `kit_autonomie/` (page d'accueil : `kit_autonomie/00_COMMENCEZ_ICI.html`).
Le code, lui, est à la racine du dépôt.

| Où | Quand l'ouvrir |
|---|---|
| `kit_autonomie/01_Installation` | en premier : remettre la stack en route chez vous |
| `kit_autonomie/02_Parcours_autonomie` | ce document : votre feuille de route |
| `kit_autonomie/03_Support_consolide` | **le cours complet** en un seul document (HTML et PDF), 7 chapitres, avec fiches mémo et auto-évaluations |
| `comprendre/` | avant chaque notion difficile : les mécanismes en animation pas à pas |
| `notebooks/`, `exercices/`, `construction/` | le code : notebooks exécutés, exercices et corrigés, construction étape par étape |
| `kit_autonomie/04_Guide_interactif_projet` | semaines 5 et 6 : construire **votre** projet de A à Z |
| `kit_autonomie/05_Guide_Claude` | dès que vous codez votre projet : travailler avec Claude sans perdre la main |
| `kit_autonomie/06_Ressources` | pour aller plus loin : les meilleurs tutoriels et cours, vérifiés |
| `kit_autonomie/07_Slides_formation` | les slides projetées en séance et leurs annexes (fiches 🔎) ; dans le zip distribué seulement |

---

## La méthode, pour chaque notion

1. **Voir** : l'animation de `comprendre/` (5 minutes, flèches ← →, essayez les deux branches).
2. **Lire** : la section du support consolidé (l'idée, le code, ce qu'on observe, les pièges).
3. **Exécuter** : le notebook, cellule par cellule, puis l'étape de construction correspondante.
4. **Refaire** : l'exercice **sans** ouvrir le corrigé (`exercices/enonces/`). Bloqué plus de 20 minutes : la
   fiche 🔎 de l'annexe des slides, puis seulement le corrigé (`exercices/corriges/`).
5. **Comparer** les étapes de construction : dans VS Code, clic droit sur l'étape 3 › *Select for Compare*, puis sur
   l'étape 4 › *Compare with Selected*. Les ajouts sont marqués `# ═══ NOUVEAU (étape N)`.
6. **Observer** : la trace dans Langfuse à chaque lancement. Le dessin, l'exécution et la trace racontent la
   même histoire.
7. **Vérifier** : l'auto-évaluation en fin de chapitre. Moins de 5 sur 6 : relisez la section concernée.

---

## Semaine 0 · Remettre la stack en route (1 à 2 h)

- [ ] `01_Installation/Guide_installation` jusqu'au smoke test vert
- [ ] `uv run --project infrastructure pytest construction/test_etapes.py -q` : tout est câblé
- [ ] Lancer l'étape 0 et retrouver sa trace dans Langfuse
- [ ] Support, **chapitre 1** (la stack locale). Facultatif : le notebook `J0_01` qui reconstruit la stack

## Semaine 1 · Les fondations (consolidation)

| Notion | Animation | Support | Pratique |
|---|---|---|---|
| Chaîne LCEL, traçage Langfuse | | ch. 2 | `J1_01`, étapes 0 et 1, défi J1-01 |
| Agent et outils, boucle ReAct | `boucle_react.html` | ch. 2 | `J1_02`, étape 2 |
| StateGraph, état, reducers, routage | `stategraph_reducers.html` | ch. 2 | `J1_03`, étape 3, **Ex1.1**, défi 3 |

- [ ] Ex1.1 refait sans corrigé · [ ] Ex1.2 (garde-fou) · [ ] auto-évaluation du chapitre 2

## Semaine 2 · Des agents qui se souviennent et qui demandent

| Notion | Animation | Support | Pratique |
|---|---|---|---|
| Persistance, `thread_id`, voyage dans le temps, effacement | `persistance_time_travel.html` | ch. 3 | `J2_01`, étape 4 |
| `interrupt()`, `Command(resume=…)`, idempotence | `interrupt_reprise.html` | ch. 3 | `J2_02`, étape 5, défi 5, **Ex2.1** |
| Sortie structurée, plancher d'urgence | | ch. 3 | `J2_03`, étape 6a |
| `RetryPolicy`, `TimeoutPolicy`, `error_handler` | `robustesse_retry_timeout.html` | ch. 3 | `J2_04`, étape 6 (`--panne 2`, `--panne 5`), **Ex2.2** |

- [ ] `J2_05_bilan_sessions` · [ ] auto-évaluation du chapitre 3

## Semaine 3 · Plusieurs agents, des connaissances, et MCP

C'est la semaine la plus importante si vous n'avez pas vu MCP en séance : le **chapitre 5** est écrit comme un
cours complet, avec un TP guidé.

| Notion | Animation | Support | Pratique |
|---|---|---|---|
| Les 5 patterns multi-agents | `coordinateur_specialistes.html` | ch. 4 | `J3_01` |
| RAG hybride sur Qdrant | `rag_hybride.html` | ch. 4 | `J3_02`, étape 7 (`--indexer` d'abord) |
| Spécialistes comme outils | `coordinateur_specialistes.html` | ch. 4 | étape 7, **Ex3.1**, défi 8a |
| Parallélisme `Send`, Deep Agents | `send_map_reduce.html` | ch. 4 | `J3_03`, `J3_05` |
| **MCP** : serveur FastMCP, client, liste blanche | `mcp_client_serveur.html` | **ch. 5** | `J3_04`, étape 7, **TP du chapitre 5**, Ex5.1 |

- [ ] Le TP « Créez votre propre serveur MCP » terminé · [ ] auto-évaluations des chapitres 4 et 5

## Semaine 4 · Observer, mesurer, sécuriser

| Notion | Support | Pratique |
|---|---|---|
| Observabilité, API, RGPD des traces, prompts versionnés | ch. 6 | `J4_01`, `J4_02`, `J4_03` |
| Scores, juge LLM et sa calibration | ch. 6 | `J4_04`, étape 8 `--juger` |
| Datasets et experiments, comparer deux runs | ch. 6 | `J4_05`, étape 8 `--evaluer`, défis 8b et 8c, **Ex4.1** |
| Middleware, garde-fou, liste blanche et audit, red-team | ch. 7 | `J5_01`, `J5_02`, **Ex5.1** |
| Conformité, gate en CI, `langgraph dev` | ch. 7 | `J5_03`, `J5_04` |

- [ ] **Langfuse Explorer** (`langfuse-explorer`) : un Langfuse seul, sans modèle ni GPU,
  rempli de 7 jours d'activité synthétique, et 33 missions guidées pour maîtriser l'interface
  (`start.ps1` ou `start.sh`, puis `guide/index.html`)
- [ ] **Examen blanc** : le mini-projet « HelpDesk-Ops parle néerlandais »
  (`exercices/enonces/MiniProjet_J4_neerlandais.ipynb`). Il combine garde-fou, graphe, dataset et sécurité. Le
  corrigé existe : ne l'ouvrez qu'à la fin.

## Semaines 5 et 6 · Votre projet, de A à Z

- [ ] `04_Guide_interactif_projet/Guide_projet_A_a_Z.html` : 13 étapes, de la fiche projet à la production,
  avec cases à cocher, code de départ, prompt pour l'IA, critère de fin et quiz
- [ ] `05_Guide_Claude` : configurer Claude (règles, documentation à jour par MCP, permissions) et utiliser la
  bibliothèque de prompts
- [ ] Un commit par étape terminée ; « Exporter mes notes » à la fin de chaque séance de travail

---

## Les réflexes à garder

- **Dessiner, exécuter, observer** : `draw_ascii()` avant de lancer, puis la trace Langfuse après.
- **Un format valide n'est pas une décision juste** : une règle explicable en Python garde le dernier mot.
- **Les consignes au modèle vont dans le prompt** : en `json_schema`, le modèle ne lit pas `Field(description=…)`.
- **Rien qui touche le monde extérieur avant `interrupt()`** : le nœud repart du début à la reprise.
- **Une erreur se journalise avant le repli poli** : un repli silencieux cache les pannes.
- **Un outil n'est donné qu'à qui en a besoin** ; un serveur MCP passe par une liste blanche côté client.
- **Ce qui n'est pas mesuré n'est qu'une impression** : un changement de prompt, de modèle ou de règle repasse
  par l'experiment, et on compare les runs.
