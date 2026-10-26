# Programme — « Orchestration d'agents & Monitoring : LangGraph + Langfuse (stack 100 % locale) »

> **Architect's take :** on repart de zéro. Pendant 5 jours, on part d'un agent seul pour arriver à un **système multi-agents gouverné, observé et évalué**, sans aucune clé d'API. **Langfuse est branché dès le premier jour** : le monitoring n'est pas un module de fin, il accompagne toute la semaine.

- **Version :** v0.9 (23 octobre 2026) : J5 complet : notebook J5-02 (lab red-team, `notebooks/J5_02_red_team.ipynb`, taux mesurés avec `granite4.1:3b` sur CPU : injection discrète 3/3 → 0/3 avec le contrôle de sortie reproduite, ASI08 démontré avec un modèle simulé qui insiste) ; `guide_formateur/GUIDE_FORMATEUR.md`. v0.8 (22 octobre 2026) : J5 en cours : modules `securite`, `conformite`, `redteam`, jalon `helpdesk_ops.jalons.j5`, gate de CI (`ci/`), `langgraph.json`, interface Streamlit (`app/`), notebooks J5-01, J5-03, J5-04, Ex5.1, QCM et grille (`guide_formateur/evaluation/`) ; notebook J5-02 (lab red-team) **à rédiger par le formateur** ; flux sortants coupés (analytique du CLI LangGraph, vérification PyPI, statistiques Streamlit) ; conformité revérifiée le 22/10 (corrections ci-dessous). v0.7 (21 octobre 2026) : J4 complet (5 notebooks, Ex4.1, corrigé, dataset d'évaluation de 20 cas `data/eval/`, modules `evaluation` et `tableau_bord`, purge RGPD des traces, deck) ; constats de préparation : routeur de J3 à 20 % (consigne), juge incohérent (note calculée en code), `OLLAMA_MAX_LOADED_MODELS=1` sur un poste de 32 Go. v0.6 : J3 complet (5 notebooks, Ex3.1, corrigé, KB de 20 articles, RAG hybride Qdrant, serveur MCP, jalon `helpdesk_ops.jalons.j3`, deck) ; ajout de `fastembed` et `deepagents` 0.7.19 au lock, sans changer les versions gelées. v0.5 : J2 complet. v0.4 (20/10) : revérification des versions et de la conformité (§0), J1 complet. v0.3 (28/09) : Qdrant remplace Chroma, uv remplace pip/venv
- **Salle :** postes **Ubuntu Linux, GPU NVIDIA, ≥ 32 Go de RAM**, avec **un Langfuse par poste**
- **Préparation (formateur) :** Docker, 47 Go de RAM, **sans GPU** : même `docker compose`, Ollama en mode CPU
- **Durée :** 5 jours × 8 h de présence (hypothèse : 08h30–16h30, 1 h de pause midi et 2 pauses de 15 min, soit **≈ 6h30 de contenu par jour, ≈ 33 h au total**), répartition **30 % théorie / 70 % pratique**
- **Public :** développeurs juniors à intermédiaires, **bases LangChain acquises** (LCEL, PromptTemplate, Ollama, RAG simple)
- **Contrainte :** 100 % local. Ollama pour les LLM, HuggingFace pour les embeddings, **Qdrant** pour les vecteurs, Langfuse **auto-hébergé**, **uv** pour l'environnement Python. Aucune donnée ne sort de la machine.
- **Angle transverse :** sécurité (OWASP Agentic Top 10), RGPD, NIS2, AI Act

---

## 0. Stack de référence, vérifiée le 28/09/2026

> **Revérification du 20/10/2026 : lock volontairement gelé.** Sont sortis depuis : `langchain` 1.4.6 (HITL `interrupt_mode="per_call"`), `langgraph` 1.2.16, `langfuse` **5.0.x** (majeure, bloquée par `<5`), Ollama 0.40.6, Qdrant 1.19.2, uv 0.13.3. On garde `uv.lock` du 28/09 tant que la salle n'a pas validé une mise à jour (`uv lock --upgrade` + `smoke_test.py` + exécution de tous les notebooks). Les notebooks J1 ont été exécutés de bout en bout avec ce lock le 20/10/2026.

> **Revérification du 23/10/2026 : lock toujours gelé.** Sorties depuis le 20/10 : `langchain` 1.4.7, `langchain-core` **1.7.0** (⚠️ streaming des tool-calls en `tool-call-delta` : à tester avant toute montée), `langgraph` 1.2.16, `langgraph-checkpoint-sqlite` 3.1.2, `langfuse` 5.0.4 (la branche 4.x continue : 4.18.0, accepté par `<5`), serveur Langfuse v4.68, Ollama 0.40.9, Qdrant 1.20.0 (serveur et client), uv 0.13.5, `deepagents` 0.7.30, `streamlit` 1.66.1. **Images figées** : Langfuse 4.46.0 (version de préparation, `LANGFUSE_VERSION`), Ollama 0.34.4, Qdrant v1.19.1. **Failles sur les versions gelées :** aucune sur `langchain`, `langgraph`, `langfuse`, Ollama, Streamlit. GHSA-6hmw-9432-67qq (`langgraph-checkpoint-sqlite` < 3.1.2) ne vise que `SqliteStore`, non utilisé (vérifié dans le dépôt). GHSA-frc7-44gm-99qq (Qdrant < 1.20, critique) ne vise que le mode cluster, non utilisé. GHSA-47w2-rfrr-wvq8 (`deepagents` < 0.7.25) : contournement des règles de permissions sur les fichiers, donc n'en pas configurer dans la démo J3. Doc LangGraph : elle affiche `recursion_limit` = 1000, le code de la 1.2 dit 10 007.

Versions relevées sur PyPI et GitHub, et imports testés dans un environnement propre (voir §6).

| Composant | Version actuelle | Épinglage proposé | Remarque |
|---|---|---|---|
| `langchain` | **1.4.2** (18/09/2026) | `>=1.4,<2` | 1.4 : intégration **MCP** en bêta (`langchain.mcp`, extra `mcp`, qui installe `fastmcp`) |
| `langchain-core` | 1.6.5 | `>=1.6,<2` | |
| `langgraph` | **1.2.12** (21/09/2026) | `>=1.2,<2` | 1.1 : `invoke`/`stream` typés (v2). 1.2 : **timeouts par nœud**, **gestionnaires d'erreur par nœud**, arrêt propre (drain) |
| `langgraph-checkpoint-sqlite` | 3.1.1 | `>=3.1,<4` | persistance locale |
| `langfuse` (SDK Python) | **4.15.6** (24/09/2026) | `>=4.15,<5` | ⚠️ **v4, pas v3** : voir encadré ci-dessous |
| Serveur Langfuse (self-hosted) | **v4** | image `langfuse/langfuse:4` + worker | Postgres, ClickHouse, Redis, MinIO. **4 cœurs / 16 Go recommandés** |
| `langchain-ollama` | 1.1.0 | `>=1.1,<2` | |
| `langchain-huggingface` / `sentence-transformers` | 1.2.2 / 6.1.0 | | |
| `langchain-qdrant` / `qdrant-client` | 1.1.0 / **1.19.1** (16/09/2026) | `>=1.1,<2` / `>=1.19,<2` | `QdrantVectorStore` s'appuie sur `query_points` ; `search()` est déprécié côté serveur |
| Serveur Qdrant | **v1.19.1** | image `qdrant/qdrant:v1.19.1` | clé API obligatoire, télémétrie coupée, dashboard `:6333/dashboard` |
| **uv** | **0.12.19** (25/09/2026) | `required-version >=0.12` | `pyproject.toml` + **un seul `uv.lock` universel** (Linux salle + Windows préparation) |
| `pydantic` | 2.13.5 | `>=2.13,<3` | |
| `streamlit` | 1.64.0 | | interface de démonstration |
| `deepagents` | 0.7.19 | `>=0.7.19,<0.7.20` *(démo J3)* | harnais haut niveau ; ⚠️ GHSA-47w2-rfrr-wvq8 (< 0.7.25) : pas de règles de permissions fichiers dans la démo ; la 0.7.29 tirerait `langchain` 1.4.6 (lock gelé). ⚠️ sans `model=`, modèle cloud par défaut ; `write_todos` optionnel depuis 0.7.0 |
| Ollama | **0.34.4** (23/09/2026) | | |
| `langgraph-supervisor` | 0.0.31 (**figé depuis nov. 2025, dépôt archivé le 20/09/2026**) | **❌ retiré** | le README recommande désormais le **supervisor via tools** |

**🔴 Trois points de l'audit de juin sont déjà obsolètes :**

1. **Langfuse SDK v4** (et non v3). Les changements qui nous concernent :
   - `CallbackHandler` ne prend plus `update_trace`. Session, user, tags et metadata se posent via `with propagate_attributes(session_id=…, user_id=…, tags=[…]):`
   - `start_as_current_span` / `start_as_current_generation` deviennent `start_as_current_observation(as_type=…)`
   - Datasets : `item.run()` est supprimé et remplacé par `dataset.run_experiment(name=…, task=…)`
   - Metadata : `dict[str, str]`, 200 caractères maximum par valeur
   - Le serveur self-hosted doit être en **v4** pour les API `observations` / `metrics`
   - **v5** (oct. 2026) : serveur ≥ 4.59, `run_experiment` via OpenTelemetry, metadata JSON. Non utilisée ici (`langfuse<5`), mais à signaler en J4
2. **`langgraph-supervisor`** n'est plus la voie recommandée. La doc multi-agents actuelle présente 5 patterns : *Subagents (as tools), Handoffs, Skills, Router, Custom workflow*.
3. **Modèles locaux** : `gemma3` / `qwen2.5` sont dépassés pour les agents (voir tableau suivant).

### Modèles Ollama pour les agents (tool-calling)

| Rôle | Modèle proposé | Taille | Pourquoi |
|---|---|---|---|
| `MODEL_AGENT` (salle GPU, défaut) | **`granite4.1:8b`** | 5,3 Go | tool-calling natif, 128K de contexte, **Apache 2.0** (argument gouvernance AI Act), reste utilisable en CPU pour la préparation |
| `MODEL_AGENT_ALT` (comparaison J4) | `gemma4:12b` | ≈ 7,7 à 8 Go selon la quantification | tool-calling natif, raisonnement configurable, 256K de contexte. Confortable avec un GPU ≥ 12 Go de VRAM |
| `MODEL_SMALL` (démo des limites) | `granite4.1:3b` | 2,1 Go | plus d'erreurs de tool-calling, **à montrer dans Langfuse** |
| `MODEL_JUDGE` (LLM-as-judge) | `gemma4:12b` | | juge ≠ modèle évalué (biais d'auto-évaluation) |

> **Préparation sans GPU (47 Go) :** l'inférence CPU d'un 8B donne un ordre de grandeur de quelques tokens/s. C'est suffisant pour écrire et tester les notebooks. Pour itérer vite, `.env` permet de basculer `MODEL_AGENT=granite4.1:3b`. **La VRAM des GPU de la salle reste à confirmer** : c'est elle qui décide si `gemma4:12b` est jouable en classe.
| Embeddings | `sentence-transformers` multilingue (HF) | | inchangé par rapport au prérequis |

> ⚠️ **4ᵉ élément obsolète trouvé en préparant l'infra :** la variable `LANGFUSE_HOST` est **dépréciée** dans le SDK v4. On utilise **`LANGFUSE_BASE_URL`**.

---

## 1. Fil rouge : « HelpDesk-Ops », l'assistant support multi-agents de *NordTech SA* (entreprise fictive)

Chaque jour ajoute une couche au même projet :

```
J1  Agent unique en StateGraph + tools locaux          → tracé dans Langfuse
J2  + mémoire (SQLite), HITL, sortie structurée,        → sessions Langfuse
      robustesse (retry/timeout/error handler)
J3  + système multi-agents : router → [KB-RAG | Ticketing | Diagnostic]
      + serveur MCP local (outils « inventaire »)       → arbre de traces multi-agents
J4  + prompts versionnés, scores, datasets, experiments → tableau de bord qualité
J5  + middlewares de sécurité, red-team OWASP, CI d'éval, conformité → livraison
```

---

## 2. Déroulé détaillé

Légende : 📘 théorie · 🛠️ pratique · 🧪 exercice (corrigé fourni) · 🔒 sécurité/conformité

### JOUR 1 — Du chain au graphe : LangGraph fondamentaux + tracing dès le départ

| Créneau | Contenu |
|---|---|
| 08h30–09h15 | 📘 Accueil, objectifs, tour d'horizon « de LCEL aux agents » : pourquoi une chaîne ne suffit plus (boucles, décisions, état). *Analogie : la recette de cuisine (chaîne) vs le chef qui goûte et ajuste (agent).* |
| 09h15–10h30 | 🛠️ **Lab 0 : infra et premier tracing** (notebook `J1_01`). `uv sync` (Python 3.12 + dépendances figées par `uv.lock`), `uv run generate_env.py`, `docker compose up` (Ollama + Qdrant + Langfuse v4), `ollama pull`, clés Langfuse et Qdrant pré-provisionnées, `uv run smoke_test.py`. 🔒 Secrets hors du code, `.env` dans `.gitignore`, Qdrant refuse toute requête sans clé. Client Langfuse avec masquage PII, `CallbackHandler`, sessions, `@observe`. |
| 10h45–12h00 | 📘🛠️ **Rappel express agents** (notebook `J1_02`) : `@tool`, `bind_tools`, boucle ReAct **codée à la main** (le « avant » pédagogique), puis `create_agent`, tracés dans Langfuse : *« voici ce que votre boucle fait réellement »*. |
| 13h00–14h30 | 📘🛠️ **StateGraph from scratch** (notebook `J1_03`) : `State` (`TypedDict`, `MessagesState`), **reducers** (`add_messages`, `operator.add`), nœuds, arêtes, **arêtes conditionnelles**, `START`/`END`, `ToolNode` + `tools_condition`. Visualisation `draw_mermaid()`. |
| 14h45–16h00 | 🧪 **Ex1.1** (`Ex1_1_stategraph_support`) : reconstruire l'agent support en graphe explicite. **Ex1.2** (`Ex1_2_garde_fou`) : ajouter un nœud `garde_fou` qui rejette les demandes hors périmètre avant l'agent. |
| 16h00–16h30 | 📘 Debrief dans Langfuse : lire une trace (trace → observations → generations), latence par nœud, tokens. Quiz de fin de journée. |

### JOUR 2 — Agents stateful, contrôlés et robustes

| Créneau | Contenu |
|---|---|
| 08h30–10h00 | 📘🛠️ **Persistance** (notebook `J2_01`) : `InMemorySaver` → `SqliteSaver`, `thread_id` = conversation, `get_state`, **time travel** (rejouer depuis un checkpoint). *Analogie : les sauvegardes d'un jeu vidéo.* 🔒 RGPD : ce que contient un checkpoint (données personnelles !), durée de conservation, droit à l'effacement d'un thread (`delete_thread`), purge planifiée (`purger_threads`). ⚠️ `prune()` est documenté mais non implémenté par `SqliteSaver` 3.1. |
| 10h15–12h00 | 📘🛠️ **Human-in-the-loop** (notebook `J2_02`) : `interrupt()`, reprise avec `Command(resume=…)`, validation humaine avant `creer_ticket`, piège du rejeu et idempotence, `HumanInTheLoopMiddleware`. 🧪 **Ex2.1** (`Ex2_1_validation_p1`) : un ticket P1 exige une approbation humaine. |
| 13h00–14h15 | 📘🛠️ **Sortie structurée & logique métier** (notebook `J2_03`) : modèle Pydantic (`TicketDecision`), `with_structured_output` (méthode `json_schema` retenue : `function_calling` peut renvoyer `None` sans erreur), `response_format=ToolStrategy(…)`, routage par `Command(goto=…)`. |
| 14h30–16h00 | 📘🛠️ **Robustesse (nouveautés LangGraph 1.2)** (notebook `J2_04`) : `RetryPolicy`, **`TimeoutPolicy` par nœud** (LLM local lent ; ⚠️ réservé aux nœuds `async`, refusé à la compilation sur un nœud synchrone), **gestionnaire d'erreur par nœud** (paramètre typé `NodeError`) qui renvoie un `Command` de repli (⚠️ avec `goto`, sinon le graphe s'arrête). **Sous-graphes.** 🧪 **Ex2.2** (`Ex2_2_reseau_instable`) : un tool « réseau » instable ; rendre le graphe tolérant aux pannes, puis vérifier dans Langfuse. |
| 16h00–16h30 | 📘 **Bilan** (notebook `J2_05`) : le jalon J2 sur une conversation complète, sessions Langfuse avec `propagate_attributes(session_id, user_id)`, utilisateur pseudonymisé. Quiz. |

### JOUR 3 — Orchestration multi-agents & MCP

| Créneau | Contenu |
|---|---|
| 08h30–09h45 | 📘 **Les 5 patterns** (notebook `J3_01`) : sous-agents, handoffs, skills, routeur, workflow sur mesure ; démonstration routeur (et ses erreurs de routage) et handoff. Quand le multi-agents est justifié, et quand c'est de la sur-ingénierie (latence mesurée). *Analogie : help-desk N1 qui dispatche vers les experts N2.* |
| 10h00–12h00 | 🛠️ **RAG hybride et sous-agents** (notebook `J3_02`) : KB de 20 articles (`data/kb/`) indexée dans Qdrant (dense HF + BM25 français, `Modifier.IDF`, ids stables), comparaison dense / BM25 / hybride, filtres de payload (visibilité N1/N2, catégorie) ; spécialistes KB-RAG, Diagnostic, Ticketing exposés **comme outils** d'un coordinateur, isolation du contexte. 🧪 **Ex3.1** (`Ex3_1_quatrieme_specialiste`) : un spécialiste Accès, routage vérifié dans Langfuse. |
| 13h00–14h15 | 📘🛠️ **Parallélisme** (notebook `J3_03`) : `Send` (map-reduce) sur 3 sources, reducer, `max_concurrency` ; gain mesuré : ×3 sur des sources qui attendent, ×1,5 sur des appels au même Ollama. |
| 14h30–15h45 | 📘🛠️ **MCP** (notebook `J3_04`) : serveur FastMCP « inventaire parc » avec annotations, consommé via `langchain.mcp` (**bêta**) en processus, stdio (journal `log_file`) ou HTTP local ; liste blanche côté client. 🔒 **Supply chain** (OWASP ASI04) : check-list, `FASTMCP_CHECK_FOR_UPDATES=off`. |
| 15h45–16h30 | 📘 **Deep Agents et bilan** (notebook `J3_05`) : `create_deep_agent` mesuré sur modèle local (~20 min sur CPU) ; jalon J3 (garde-fou + coordinateur + 4 spécialistes + MCP). Quiz. |

### JOUR 4 — Monitoring & évaluation avec Langfuse v4 (le cœur)

| Créneau | Contenu |
|---|---|
| 08h30–09h30 | 📘 **Observabilité LLM ≠ logs classiques** (notebook `J4_01`) : non-déterminisme, qualité, latence, coût. Modèle Langfuse v4 : traces, **observations typées** (span, generation, tool, agent…), **fondé sur OpenTelemetry**. Les trois premiers jours relus par l'API metrics (`helpdesk_ops.tableau_bord`) ; ⚠️ serveur en mode *events_only* : `/api/public/traces` répond 404, on passe par l'API v2 des observations et l'API metrics. |
| 09h30–10h45 | 🛠️ **Instrumentation fine** (notebook `J4_02`) : `@observe`, `start_as_current_observation(as_type=…)`, niveaux `WARNING`, `propagate_attributes` (tags, metadata, version). 🔒 **RGPD** : minimisation (`capture_input=False`), masquage *avant* envoi (fonction `mask` du client), **effacement** d'une personne et **purge planifiée** par l'API (`purger_traces`, simulation par défaut ; ⚠️ la *data retention* automatique est une fonction Enterprise), qui a accès à l'UI. |
| 11h00–12h00 | 🛠️ **Prompt management** (notebook `J4_03`) : externaliser le prompt de tri dans Langfuse, le versionner, labels `production`/`staging`, lien prompt ↔ génération, mesure v1/v2 (50 % → 100 % sur six tickets en préparation), promotion, retour arrière, **repli** si Langfuse est injoignable, gouvernance. |
| 13h00–14h15 | 📘🛠️ **Scores** (notebook `J4_04`) : feedback utilisateur (👍/👎 + motif), **LLM-as-judge local** (`MODEL_JUDGE`, `reasoning=False`) sur la fidélité aux sources, calibré sur des réponses réelles de J3 ; biais de longueur et injection dans le texte jugé (ASI01) ; note **calculée** à partir des constats du juge (`noter`). |
| 14h30–16h00 | 🛠️ **Datasets & Experiments** (notebook `J4_05`) : dataset de 20 cas support versionné dans Git (`data/eval/helpdesk_eval.json`, issus des défauts constatés de J1 à J3), `dataset.run_experiment(task=…, max_concurrency=1)`, consigne de routage v1 (J3) contre v2, comparaison **`granite4.1:3b` vs `granite4.1:8b` vs `gemma4:12b`** sur la justesse du routage, le taux de tool-calls valides et la latence. 🧪 **Ex4.1** : produire le tableau comparatif et recommander un modèle, chiffres à l'appui. |
| 16h00–16h30 | 📘 Dashboards (fin de `J4_05`) : six questions d'un responsable Ops, six widgets, les mêmes chiffres par l'API metrics. Quiz. |

### JOUR 5 — Production, sécurité & conformité + projet final

| Créneau | Contenu |
|---|---|
| 08h30–10h00 | 📘🛠️ **Middleware LangChain 1.x** : hooks (`before_model`, `wrap_model_call`, `wrap_tool_call`, `after_model`…) et middlewares fournis, vérifiés dans la 1.4.2 : `PIIMiddleware`, `HumanInTheLoopMiddleware`, `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware`, `ModelRetryMiddleware` / `ToolRetryMiddleware`, `ModelFallbackMiddleware`, `SummarizationMiddleware`, `ContextEditingMiddleware` (nouveaux : `ToolErrorMiddleware`, `LLMToolSelectorMiddleware`). Notebook `J5_01` : ordre d'exécution observé, `PIIMiddleware` (protège le modèle, pas la trace), repli de modèle, piège synchrone/asynchrone. 🧪 **Ex5.1** (`Ex5_1_liste_blanche_audit`) : sous-classe d'`AgentMiddleware` (`wrap_tool_call` **et** `awrap_tool_call`) en liste blanche + journal d'audit. |
| 10h15–11h45 | 🔒 **Lab red-team OWASP Top 10 for Agentic Applications 2026** : injection indirecte via un document de la KB (ASI01 *Goal Hijack*), détournement d'outil (ASI02), exécution de code (ASI05, le classique `eval()`), empoisonnement mémoire (ASI06), défaillances en cascade (ASI08). Chaque attaque doit être **visible dans Langfuse**, puis corrigée. Briques prêtes dans `helpdesk_ops.redteam` (agents vulnérable / protégé, détecteurs, taux sur plusieurs essais) ; notebook `J5_02_red_team` (taux sur 3 essais, alertes retrouvées par `chronologie_incident`). Mesuré en préparation : une injection rédigée comme une procédure passe la protection d'entrée, le contrôle de sortie l'arrête. |
| 12h45–13h45 | 📘🔒 **Conformité appliquée** : **AI Act art. 50** (obligation d'informer l'utilisateur qu'il parle à une IA, **en vigueur depuis le 02/08/2026** ; marquage machine-lisible art. 50(2) : délai au 02/12/2026 pour les systèmes mis sur le marché **avant** le 02/08/2026), classification de risque (un assistant support n'est pas « haut risque » ; échéances haut risque reportées par l'Omnibus, Règl. (UE) 2026/1744, JO du 24/07/2026 : **annexe III au 02/12/2027**, **annexe I au 02/08/2028** ; ⚠️ un rectificatif de la version allemande est annoncé, date non confirmée, à vérifier au JO), art. 4 culture IA (selon une source secondaire, l'obligation directe devient un devoir de soutien de la Commission et des États membres : à vérifier). Notebook `J5_03` : faits datés avec leur statut de vérification, information IA et marquage, registre, purge planifiée, chronologie d'incident. **NIS2** : traçabilité des incidents, rôle des traces Langfuse dans la notification ; en Belgique, loi d'avril 2024, CyFun/ISO 27001 et échéances CCB du 18/04/2026 et du 18/04/2027 (à revérifier sur ccb.belgium.be avant la session : site inaccessible lors de la vérification du 22/10). **RGPD** : minimisation, rétention des checkpoints et des traces. |
| 13h45–14h30 | 🛠️ **DevOps** : **gate d'évaluation en CI** (GitHub Actions : exécuter l'experiment Langfuse, faire échouer le build si le score régresse), packaging du backend (`langgraph-cli` en local), interface Streamlit branchée sur le graphe. Notebook `J5_04` : `ci/eval_gate.py` (garde-fou + experiments + seuils, code de sortie), `ci/eval-gate.yml` (runner auto-hébergé pour la gate), `langgraph dev` via `infrastructure/serveur_langgraph.*` (sans analytique ni vérification PyPI), `app/helpdesk_app.py` ; énoncé du projet final. |
| 14h30–16h00 | 🧪 **Projet final** (binômes) : étendre HelpDesk-Ops avec une fonctionnalité imposée, instrumentée, évaluée et sécurisée. Démo de 5 min par binôme. |
| 16h00–16h30 | Évaluation (QCM de 40 questions Build/Test/Deploy/Monitor + grille projet, voir §8 et `guide_formateur/evaluation/` ; correction humaine uniquement), feuille de route « et après », clôture. |

---

## 3. Arborescence des livrables

```
Orchestration/
├── PROGRAMME_Orchestration_Agents_Monitoring.md   ← ce document
├── infrastructure/
│   ├── docker-compose.yml          # Ollama + Qdrant + Langfuse v4 (web, worker, postgres, clickhouse, redis, minio)
│   ├── generate_env.py             # .env aléatoire : LANGFUSE_*, QDRANT_*, OLLAMA_BASE_URL, MODEL_*
│   ├── pyproject.toml / uv.lock / .python-version   # uv sync = environnement identique partout
│   ├── pull_models.sh / .ps1       # pré-téléchargement des modèles (salle sans réseau)
│   └── smoke_test.py               # vérifie Ollama + Langfuse + imports
├── notebooks/
│   ├── J1_01_infra_et_tracing.ipynb, J1_02_agents_fondamentaux.ipynb, J1_03_stategraph.ipynb … J5_04_projet_final.ipynb
│   └── _sources/                   # générateurs build_*.py des notebooks et exercices (python build_j1_02.py)
├── exercices/
│   ├── enonces/  J1_01_defi, Ex1_1_stategraph_support, Ex1_2_garde_fou … Ex5.1 (.ipynb)
│   └── corriges/ mêmes noms + _corrige (.ipynb)
├── src/                            # paquet helpdesk-ops-lib, installé en éditable par uv sync
│   ├── helpdesk_ops/               # socle (config, texte, pii, observabilite, donnees) dès J1,
│   │                               # puis outils, tri, jalons/j1 … j5 livrés en fin de journée
│   └── tests/                      # uv run pytest ../src/tests (sans réseau), base de la gate CI J5
├── data/                           # KB fictive NordTech (Markdown/PDF), dataset d'éval (JSON)
│   ├── kb/                         # 20 articles Markdown fictifs (J3), avec en-têtes de métadonnées
│   ├── eval/                       # helpdesk_eval.json : 20 cas annotés (J4) ; redteam.json : 12 cas du garde-fou (J5)
│   ├── redteam/                    # canari.txt : fichier visé par le scénario ASI05 (aucun secret réel)
│   ├── checkpoints/                # SQLite des notebooks : conversations en clair, ignoré par Git
│   └── logs/                       # journaux des serveurs MCP (stdio), ignoré par Git
├── ci/                             # eval_gate.py (gate locale ou CI), seuils.json, eval-gate.yml (GitHub Actions)
├── app/helpdesk_app.py             # interface Streamlit du jalon J5 (+ .streamlit/config.toml à la racine)
├── langgraph.json                  # graphe « helpdesk » servi par langgraph dev (infrastructure/serveur_langgraph.*)
├── supports/                       # decks BStorm par jour (.pptx) ; _sources/ : générateurs (voir son README)
└── guide_formateur/
    ├── GUIDE_FORMATEUR.md          # préparation, déroulé minuté, points de vigilance, FAQ, pannes fréquentes
    ├── evaluation/                 # QCM_final.md, QCM_final_corrige.md, grille_projet.md
    └── slides_outline.md           # (optionnel)
```

Format de chaque notebook, identique au kit précédent : **[Markdown] théorie + analogie + « Tips du formateur »**, puis **[Code] fil rouge commenté + « ce que vous devez observer »**.

---

## 4. Propositions d'enrichissement (concepts actuels, en plus de l'audit)

1. **MCP natif LangChain 1.4**, incontournable fin 2026 et porte d'entrée de la sécurité supply chain.
2. **OWASP Top 10 for Agentic Applications 2026** comme fil conducteur de la sécurité, plus parlant pour des devs que l'OWASP LLM Top 10 générique.
3. **CI d'évaluation** (*evals as tests*) : la bonne pratique DevOps qui manque dans la plupart des formations LLM.
4. **LangGraph 1.2** : timeouts et gestionnaires d'erreur par nœud, directement utiles avec des modèles locaux lents.
5. **Transparence AI Act art. 50** appliquée au code : message d'information systématique + marquage des réponses générées.

## 5. Ce que j'ai volontairement écarté

- `langgraph-supervisor` / `langgraph-swarm` : plus recommandés, remplacés par les patterns « as tools » et « handoffs » faits main.
- `AgentExecutor`, `langchain-classic` : hors sujet pour ce public.
- LangSmith : SaaS, contraire à la promesse « 100 % local » (cité une fois, en comparaison).

## 6. Vérifications faites

Environnement propre `langchain 1.4.2` / `langgraph 1.2.12` / `langfuse 4.15.6`. Imports validés : `create_agent`, tous les middlewares cités, `StateGraph`, `interrupt`, `Command`, `Send`, `RetryPolicy`, `TimeoutPolicy`, `ToolNode`, `InMemorySaver`, `SqliteSaver`, `langfuse.get_client`, `observe`, `propagate_attributes`, `langfuse.langchain.CallbackHandler`. `langchain.mcp` nécessite l'extra `mcp` (`langchain[mcp]`, qui installe `fastmcp`).
**Pas encore testé :** la fiabilité réelle du tool-calling des modèles Ollama cités. À benchmarker sur le matériel de la salle avant la session (le notebook J4 servira aussi à ça).

## 7. Décisions (validées le 28/09/2026)

1. **Matériel :** **un Langfuse par poste** (Ubuntu, GPU, ≥ 32 Go). Infra : un seul `docker-compose.yml`, plus un fichier `docker-compose.gpu.yml` activé dans la salle. Les clés Langfuse sont **pré-provisionnées** (initialisation automatique au démarrage), donc aucun clic manuel dans l'UI le jour J.
2. **Horaires :** 08h30–16h30 confirmés.
3. **Évaluation :** pas de référentiel imposé, **alignement sur la demande du marché** (§8).

## 8. Alignement sur la demande du marché

Les deux signaux les plus concrets (vérifiés le 23/10/2026) :

- **LangChain Certified Agent Engineer** (l'examen de l'éditeur) : 4 domaines à poids égal, **Build / Test / Deploy / Monitor**. 40 QCM, 28 bonnes réponses pour réussir, 120 min, semi open-book avec une organisation LangSmith fournie. L'examen s'appuie sur LangSmith (SaaS), donc la formation **ne prépare pas à l'examen**, mais couvre les mêmes compétences sur une stack souveraine.
- **State of Agent Engineering (LangChain, publié le 12/06/2026, enquête de nov.–déc. 2025, 1 340 répondants) :** 57 % des organisations ont des agents en production. Premier frein : la **qualité** (32 %), puis la latence (20 %). La **sécurité** est citée par 24,9 % des grandes entreprises (≥ 2 000 salariés ; son rang parmi les freins reste à confirmer). **89 %** ont de l'observabilité, mais seulement **52 %** font de l'éval offline. Premier cas d'usage : le **support client** (26,5 %), ce qui valide le choix du fil rouge.

**Conséquence sur l'évaluation finale :** QCM de 40 questions et grille de projet, sur les **4 domaines de 25 % chacun** :

| Domaine | Couvert par | Preuve attendue dans le projet final |
|---|---|---|
| **Build** | J1–J3 | graphe multi-agents fonctionnel, HITL, sortie structurée |
| **Test** | J4 | dataset + experiment Langfuse, comparaison chiffrée |
| **Deploy** | J5 | gate d'éval en CI, packaging, Streamlit |
| **Monitor** | J1→J5 | traces avec sessions, scores, masquage RGPD |

Plus un **bonus transverse Sécurité & Conformité** : une attaque OWASP corrigée et la mention AI Act art. 50. Sur un CV, c'est ce qui différencie le profil.

---

## Sources

- PyPI : [langchain](https://pypi.org/project/langchain/) · [langgraph](https://pypi.org/project/langgraph/) · [langfuse](https://pypi.org/project/langfuse/)
- [LangChain / LangGraph changelog](https://docs.langchain.com/oss/python/releases/changelog) · [Multi-agent patterns](https://docs.langchain.com/oss/python/langchain/multi-agent) · [langgraph-supervisor README](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Langfuse Python SDK v3 → v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4) · [Langfuse self-hosting Docker Compose](https://langfuse.com/self-hosting/deployment/docker-compose)
- [Ollama releases](https://github.com/ollama/ollama/releases) · [granite4.1](https://ollama.com/library/granite4.1) · [gemma4](https://ollama.com/library/gemma4) · [Best Ollama models 2026 (Morph)](https://www.morphllm.com/best-ollama-models)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [Synthèse Cycode](https://cycode.com/blog/owasp-top-10-agentic-applications/)
- Marché : [LangChain Certified Agent Engineer](https://kb.langchain.com/articles/5297173898-what-is-the-langchain-certified-agent-engineer-exam) · [State of Agent Engineering 2026](https://www.langchain.com/state-of-agent-engineering)
- [Langfuse docker-compose.yml officiel](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml)
- AI Act Omnibus : [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/) · [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/) · [Goodwin, art. 50](https://www.goodwinlaw.com/en/insights/publications/2026/08/alerts-technology-dpc-eu-ai-act-transparency-obligations-now-in-force)
