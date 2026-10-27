# Programme — « Orchestration d'agents & Monitoring : LangGraph + Langfuse (stack 100 % locale) »

> **En bref :** en 4 jours, on part de zéro (aucune connaissance de LangChain n'est supposée) pour arriver à un **système multi-agents gouverné, observé et évalué**, sans aucune clé d'API. **LangChain d'abord, Langfuse aussitôt après** : dès la fin de la première matinée, tout ce que vous écrivez est tracé, et le monitoring accompagne toute la formation.

- **Version :** **v1.0 (27 octobre 2026) : format 4 jours** (validé avec le coordinateur), socle LangChain intégré au J1 (« LangChain express ») et au J3 (« RAG en 3 briques »), moteur **vLLM** sur le GPU de la salle, évaluation par **mini-projet** (pas de QCM). *Historique :* v0.9 (23/10) J5 complet (lab red-team) ; v0.8 (22/10) J5 en cours ; v0.7 (21/10) J4 complet ; v0.6 J3 ; v0.5 J2 ; v0.4 (20/10) J1 et revérification ; v0.3 (28/09) Qdrant et uv.
- **Salle :** postes **Ubuntu Linux, GPU NVIDIA RTX PRO 4000 Blackwell (24 Go)**, ≥ 32 Go de RAM, avec **un Langfuse par poste** ; modèles servis par **vLLM**
- **Préparation (formateur) :** Docker, 47 Go de RAM, **sans GPU** : même `docker compose`, **Ollama** en mode CPU (moteur de repli)
- **Durée :** **4 jours** × 8 h de présence (08h30–16h30, 1 h de pause midi et 2 pauses de 15 min, soit **≈ 6h30 de contenu par jour, ≈ 26 h au total**), répartition **30 % théorie / 70 % pratique**
- **Public :** développeurs juniors à intermédiaires
- **Prérequis :** Python (fonctions, classes, dictionnaires, `pip`/environnements virtuels), notions de HTTP et JSON, usage du terminal ; Docker est un plus. **Aucune connaissance de LangChain, de LangGraph ni du RAG n'est requise** : les bases sont enseignées le J1 et le J3.
- **Contrainte :** 100 % local. **vLLM** pour les LLM en salle (Ollama en repli sur un poste sans GPU), HuggingFace pour les embeddings, **Qdrant** pour les vecteurs, Langfuse **auto-hébergé**, **uv** pour l'environnement Python. Aucune donnée ne sort de la machine.
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
| `langchain-openai` | 1.6.6 | `>=1.6.6,<1.7` | client de **vLLM** (API compatible OpenAI) ; la 1.7 exigerait `langchain-core` 1.7 (lock gelé) |
| `langchain-ollama` | 1.1.0 | `>=1.1,<2` | repli : poste sans GPU, plan B |
| `langchain-huggingface` / `sentence-transformers` | 1.2.2 / 6.1.0 | | |
| `langchain-qdrant` / `qdrant-client` | 1.1.0 / **1.19.1** (16/09/2026) | `>=1.1,<2` / `>=1.19,<2` | `QdrantVectorStore` s'appuie sur `query_points` ; `search()` est déprécié côté serveur |
| Serveur Qdrant | **v1.19.1** | image `qdrant/qdrant:v1.19.1` | clé API obligatoire, télémétrie coupée, dashboard `:6333/dashboard` |
| **uv** | **0.12.19** (25/09/2026) | `required-version >=0.12` | `pyproject.toml` + **un seul `uv.lock` universel** (Linux salle + Windows préparation) |
| `pydantic` | 2.13.5 | `>=2.13,<3` | |
| `streamlit` | 1.64.0 | | interface de démonstration |
| `deepagents` | 0.7.19 | `>=0.7.19,<0.7.20` *(démo J3)* | harnais haut niveau ; ⚠️ GHSA-47w2-rfrr-wvq8 (< 0.7.25) : pas de règles de permissions fichiers dans la démo ; la 0.7.29 tirerait `langchain` 1.4.6 (lock gelé). ⚠️ sans `model=`, modèle cloud par défaut ; `write_todos` optionnel depuis 0.7.0 |
| **vLLM** (serveur, salle) | **v0.32.0** (18/10/2026) | image `vllm/vllm-openai:v0.32.0` (CUDA 13, pilote ≥ 580) | un serveur par modèle, clé API, hors ligne, télémétrie coupée |
| Ollama (repli) | **0.34.4** (23/09/2026) | | préparation sans GPU |
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

### Modèles pour les agents (tool-calling)

> **Moteur (27/10/2026) : vLLM v0.32.0 en salle**, un serveur par modèle (poids Hugging Face : `ibm-granite/granite-4.1-8b-fp8`, `granite-4.1-3b-fp8`, `google/gemma-4-12B-it-qat-w4a16-ct`, licences Apache 2.0). Ollama reste le moteur de la préparation sans GPU et le plan B. Les noms ci-dessous sont identiques sur les deux moteurs.

| Rôle | Modèle proposé | Taille | Pourquoi |
|---|---|---|---|
| `MODEL_AGENT` (salle GPU, défaut) | **`granite4.1:8b`** | 9,6 Go (vLLM, FP8) · 5,3 Go (Ollama) | tool-calling natif, 128K de contexte, **Apache 2.0** (argument gouvernance AI Act), reste utilisable en CPU pour la préparation |
| `MODEL_AGENT_ALT` (comparaison J4) | `gemma4:12b` | 10,3 Go (vLLM, 4 bits QAT) · ≈ 8 Go (Ollama) | tool-calling natif, raisonnement configurable, 256K de contexte ; sur vLLM, servi seul (mode juge, J4) |
| `MODEL_SMALL` (démo des limites) | `granite4.1:3b` | 4,2 Go (vLLM, FP8) · 2,1 Go (Ollama) | plus d'erreurs de tool-calling, **à montrer dans Langfuse** |
| `MODEL_JUDGE` (LLM-as-judge) | `gemma4:12b` | | juge ≠ modèle évalué (biais d'auto-évaluation) |
| Embeddings | `sentence-transformers` multilingue (HF) | ≈ 0,5 Go | sur CPU, pour laisser la VRAM à vLLM |

> **Préparation sans GPU (47 Go) :** l'inférence CPU d'un 8B donne un ordre de grandeur de quelques tokens/s. C'est suffisant pour écrire et tester les notebooks. Pour itérer vite, `.env` permet de basculer `MODEL_AGENT=granite4.1:3b`. **GPU de la salle (confirmé le 27/10) : RTX PRO 4000 Blackwell, 24 Go**, servi par **vLLM** : `granite4.1:8b` + `granite4.1:3b` en continu (≈ 21 Go réservés), `gemma4:12b` seul en J4 (mode juge).

> ⚠️ **4ᵉ élément obsolète trouvé en préparant l'infra :** la variable `LANGFUSE_HOST` est **dépréciée** dans le SDK v4. On utilise **`LANGFUSE_BASE_URL`**.

---

## 1. Fil rouge : « HelpDesk-Ops », l'assistant support multi-agents de *NordTech SA* (entreprise fictive)

Chaque jour ajoute une couche au même projet :

```
J1  LangChain express (modèle, messages, prompt, chaîne)
      → agent unique en StateGraph + tools locaux        → tracé dans Langfuse
J2  + mémoire (SQLite), HITL, sortie structurée,         → sessions Langfuse
      robustesse (retry/timeout/error handler)
J3  + RAG (3 briques, puis hybride Qdrant)
      + système multi-agents : coordinateur → [KB-RAG | Ticketing | Diagnostic | Accès]
      + serveur MCP local (outils « inventaire »)        → arbre de traces multi-agents
J4  + scores, juge LLM, datasets, experiments            → qualité mesurée
      + red-team OWASP, conformité, mini-projet          → une fonctionnalité livrée
```

---

## 2. Déroulé détaillé

Légende : 📘 théorie · 🛠️ pratique · 🧪 exercice (corrigé fourni) · 🎬 démonstration du formateur · 🔒 sécurité/conformité

### JOUR 1 — De LangChain au graphe, tracé dès la première chaîne

| Créneau | Contenu |
|---|---|
| 08h30–09h00 | 📘 Accueil, objectifs, fil rouge *HelpDesk-Ops* ; lancement de l'installation des postes (`bash infrastructure/installer_reseau.sh`). |
| 09h00–10h00 | 📘 **Lab 0 expliqué** pendant les téléchargements : uv, **vLLM** (un serveur par modèle, VRAM réservée), Qdrant, Langfuse v4, `smoke_test.py`. 🔒 Secrets hors du code, clés API obligatoires (Qdrant, vLLM). Premiers concepts de **LangChain** : modèle de chat, messages, prompt, chaîne. |
| 10h15–11h00 | 🛠️ **LangChain express** (notebook `J1_01`, §1–4) : `invoke` / `stream` / `batch`, `SystemMessage` / `HumanMessage` / `AIMessage` (le LLM n'a pas de mémoire), `ChatPromptTemplate`, chaîne **LCEL** `prompt \| llm \| StrOutputParser()` : le classifieur de tickets. |
| 11h00–12h00 | 🛠️ **Premier tracing** (notebook `J1_01`, §5–11) : client Langfuse avec **masquage PII**, `CallbackHandler` sur la chaîne écrite le matin, sessions (`propagate_attributes`), `@observe`. 🔒 RGPD des traces. Mini-défi en autonomie. |
| 13h00–14h00 | 📘🛠️ **Fondamentaux des agents** (notebook `J1_02`) : `@tool`, `bind_tools`, boucle ReAct **codée à la main**, puis `create_agent`, tracés dans Langfuse ; 🎬 petit modèle contre grand modèle. |
| 14h00–15h15 | 📘🛠️ **StateGraph pas à pas** (notebook `J1_03`) : `State` (`TypedDict`, `MessagesState`), **reducers** (`add_messages`, `operator.add`), nœuds, arêtes, **arêtes conditionnelles**, `ToolNode` + `tools_condition`, `recursion_limit`. |
| 15h30–16h15 | 🧪 **Ex1.1** (`Ex1_1_stategraph_support`) : reconstruire l'agent support en graphe explicite. |
| 16h15–16h30 | 📘 Débrief dans Langfuse (lire une trace) ; 🎬 **Ex1.2** (garde-fou avant l'agent, OWASP ASI01) commenté ; quiz. |

### JOUR 2 — Agents stateful, contrôlés et robustes

| Créneau | Contenu |
|---|---|
| 08h30–09h45 | 📘🛠️ **Persistance** (notebook `J2_01`) : `InMemorySaver` → `SqliteSaver`, `thread_id` = conversation, `get_state`, **time travel**. *Analogie : les sauvegardes d'un jeu vidéo.* 🔒 RGPD : un checkpoint contient des données personnelles ; conservation, effacement d'un thread, purge planifiée. |
| 10h00–12h00 | 📘🛠️ **Human-in-the-loop** (notebook `J2_02`) : `interrupt()`, reprise avec `Command(resume=…)`, piège du rejeu et idempotence, `HumanInTheLoopMiddleware`. 🧪 **Ex2.1** (`Ex2_1_validation_p1`) : un ticket P1 exige une approbation humaine. |
| 13h00–14h00 | 📘🛠️ **Sortie structurée** (notebook `J2_03`) : modèle Pydantic (`TicketDecision`), `with_structured_output` (méthode `json_schema`), routage par `Command(goto=…)`. |
| 14h00–15h30 | 📘🛠️ **Robustesse (LangGraph 1.2)** (notebook `J2_04`) : `RetryPolicy`, `TimeoutPolicy` par nœud, gestionnaire d'erreur par nœud, sous-graphes ; 🎬 **Ex2.2** (outil réseau instable) commenté. |
| 15h45–16h30 | 🎬 **Bilan** (notebook `J2_05`) : le jalon J2 sur une conversation complète, sessions Langfuse, utilisateur pseudonymisé ; quiz oral. |

### JOUR 3 — RAG, orchestration multi-agents & MCP, puis observabilité

| Créneau | Contenu |
|---|---|
| 08h30–09h45 | 📘 **Les 5 patterns multi-agents** (notebook `J3_01`) : sous-agents, handoffs, skills, routeur, workflow sur mesure ; quand le multi-agents est justifié, et quand c'est de la sur-ingénierie (latence mesurée). |
| 10h00–12h00 | 📘🛠️ **RAG en 3 briques** (embeddings, vector store, retriever, chaîne RAG minimale), puis **RAG hybride sur Qdrant** (notebook `J3_02`) : dense + BM25 français, filtres de payload ; spécialistes exposés **comme outils** d'un coordinateur. 🧪 **Ex3.1** (`Ex3_1_quatrieme_specialiste`) : un spécialiste Accès. |
| 13h00–13h20 | 🎬 **Parallélisme** (notebook `J3_03`) : `Send` et map-reduce, gain mesuré. |
| 13h20–14h35 | 📘🛠️ **MCP** (notebook `J3_04`) : serveur FastMCP « inventaire parc », consommé via `langchain.mcp` (bêta), liste blanche côté client. 🔒 **Supply chain** (OWASP ASI04). |
| 14h50–15h05 | 🎬 **Deep Agents et bilan** (notebook `J3_05`) : trace commentée d'un `create_deep_agent` ; jalon J3. |
| 15h05–16h30 | 📘🛠️ **Observabilité LLM ≠ logs classiques** (notebook `J4_01`) : non-déterminisme, qualité, latence, coût ; modèle Langfuse v4 (observations typées, OpenTelemetry) ; les trois jours relus par l'API metrics, percentiles plutôt que moyennes. |

### JOUR 4 — Évaluer, attaquer, livrer

| Créneau | Contenu |
|---|---|
| 08h30–09h15 | 🛠️ **Instrumentation fine** (notebook `J4_02`) : `@observe`, observations typées, niveaux `WARNING`. 🔒 **RGPD** : minimisation, masquage avant envoi, effacement d'une personne, purge planifiée. |
| 09h15–09h30 | 🎬 **Prompts versionnés** (notebook `J4_03`) : labels `production` / `staging`, lien prompt ↔ génération, retour arrière. |
| 09h30–10h30 | 📘🛠️ **Scores et juge LLM local** (notebook `J4_04`) : retours utilisateurs, juge de fidélité aux sources (`gemma4:12b`, juge ≠ modèle évalué), calibration, biais et injection ; note calculée en code. |
| 10h45–12h00 | 🛠️ **Datasets & experiments** (notebook `J4_05`) : dataset de 20 cas versionné, `run_experiment(max_concurrency=1)`, consigne v1 contre v2. 🧪 **Ex4.1** : comparer les modèles, chiffres et incertitude à l'appui. |
| 13h00–14h00 | 🔒 **Middleware en 10 minutes, puis red-team OWASP Agentic 2026** (notebook `J5_02`) : injection indirecte par un document (ASI01), détournement d'outil (ASI02), empoisonnement de la mémoire (ASI06) ; chaque attaque mesurée en **taux**, vue dans Langfuse, corrigée, remesurée. ASI05 et ASI08 en autonomie. |
| 14h00–14h20 | 📘🔒 **Conformité express** : **AI Act art. 50** (informer l'utilisateur, en vigueur depuis le 02/08/2026), pourquoi un assistant support n'est pas « haut risque » et ce qui le ferait basculer (annexe III), **NIS2** : des traces à la notification d'incident. |
| 14h30–15h55 | 🧪 **Mini-projet en binômes : « HelpDesk-Ops parle néerlandais »** (`MiniProjet_J4_neerlandais`) : garde-fou bilingue, réponse dans la langue du ticket, mini-dataset évalué avant / après, traces, un contrôle de sécurité prouvé par un cas de test. Gel du code à 15h45. |
| 15h55–16h30 | Démos de 3 min par binôme, retour du formateur (une réussite, une limite, une piste), feuille de route « et après », clôture. |

### Pour aller plus loin (notebooks fournis, hors du déroulé de la session)

Le contenu du format 5 jours reste disponible dans le dépôt, à suivre en autonomie : middlewares LangChain 1.x en détail (`J5_01`, 🧪 Ex5.1 liste blanche + journal d'audit), conformité complète (`J5_03` : faits datés, marquage, registre, chronologie d'incident), DevOps (`J5_04` : **gate d'évaluation en CI**, `langgraph dev`, interface Streamlit).

---

## 3. Arborescence des livrables

```
Orchestration/
├── PROGRAMME_Orchestration_Agents_Monitoring.md   ← ce document
├── infrastructure/
│   ├── docker-compose.yml          # Ollama + Qdrant + Langfuse v4 (web, worker, postgres, clickhouse, redis, minio)
│   ├── docker-compose.vllm.yml     # salle : 3 serveurs vLLM (agent, small, juge), Ollama désactivé
│   ├── vllm_mode.sh                # bascule agents ↔ juge (24 Go ne tiennent pas les 3 modèles)
│   ├── generate_env.py             # .env aléatoire : LANGFUSE_*, QDRANT_*, LLM_BACKEND, VLLM_*, OLLAMA_BASE_URL, MODEL_*
│   ├── installer_reseau.sh         # installation en salle par le réseau, en deux temps (J1 matin, puis --fond)
│   ├── pyproject.toml / uv.lock / .python-version   # uv sync = environnement identique partout
│   ├── pull_models.sh / .ps1       # pré-téléchargement des modèles Ollama (poste sans GPU)
│   └── smoke_test.py               # vérifie le moteur LLM (vLLM ou Ollama) + Qdrant + Langfuse + imports
├── notebooks/
│   ├── J1_01_infra_et_tracing.ipynb, J1_02_agents_fondamentaux.ipynb, J1_03_stategraph.ipynb … J5_04_projet_final.ipynb
│   └── _sources/                   # générateurs build_*.py des notebooks et exercices (python build_j1_02.py)
├── exercices/
│   ├── enonces/  J1_01_defi, Ex1_1_stategraph_support, Ex1_2_garde_fou … Ex4_1, MiniProjet_J4_neerlandais (.ipynb)
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
    ├── evaluation/                 # grille_mini_projet_j4.md (format 4 jours) ; QCM et grille du format 5 jours
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
**Pas encore testé :** la fiabilité réelle du tool-calling des modèles cités, et **tout le chemin vLLM** (jamais exécuté sur GPU au 27/10). À benchmarker sur le matériel de la salle avant la session (le notebook J4 servira aussi à ça).

## 7. Décisions (validées le 28/09/2026)

1. **Matériel :** **un Langfuse par poste** (Ubuntu, GPU, ≥ 32 Go). Infra : un seul `docker-compose.yml`, plus `docker-compose.vllm.yml` activé dans la salle (`docker-compose.gpu.yml` pour le plan B Ollama). Les clés Langfuse sont **pré-provisionnées** (initialisation automatique au démarrage), donc aucun clic manuel dans l'UI le jour J.
2. **Horaires :** 08h30–16h30 confirmés.
3. **Évaluation :** pas de référentiel imposé, **alignement sur la demande du marché** (§8).
4. **Format 4 jours** (26/10/2026, programme validé par le coordinateur le 27/10) : 04, 06, 09 et 10/11/2026 ; aucun prérequis LangChain.
5. **Moteur vLLM** (27/10/2026) sur le GPU de la salle ; Ollama conservé en repli.

## 8. Alignement sur la demande du marché

Les deux signaux les plus concrets (vérifiés le 23/10/2026) :

- **LangChain Certified Agent Engineer** (l'examen de l'éditeur) : 4 domaines à poids égal, **Build / Test / Deploy / Monitor**. 40 QCM, 28 bonnes réponses pour réussir, 120 min, semi open-book avec une organisation LangSmith fournie. L'examen s'appuie sur LangSmith (SaaS), donc la formation **ne prépare pas à l'examen**, mais couvre les mêmes compétences sur une stack souveraine.
- **State of Agent Engineering (LangChain, publié le 12/06/2026, enquête de nov.–déc. 2025, 1 340 répondants) :** 57 % des organisations ont des agents en production. Premier frein : la **qualité** (32 %), puis la latence (20 %). La **sécurité** est citée par 24,9 % des grandes entreprises (≥ 2 000 salariés ; son rang parmi les freins reste à confirmer). **89 %** ont de l'observabilité, mais seulement **52 %** font de l'éval offline. Premier cas d'usage : le **support client** (26,5 %), ce qui valide le choix du fil rouge.

**Conséquence sur l'évaluation :** pas de QCM dans le format 4 jours. Un **mini-projet en binômes** (J4 après-midi), avec une grille de retour sur quatre domaines, remplie par le formateur (jamais par un LLM) :

| Domaine | Couvert par | Preuve attendue dans le mini-projet |
|---|---|---|
| **Build** | J1–J3 | la fonctionnalité dans le graphe (garde-fou bilingue, réponse dans la langue du ticket) |
| **Test** | J4 | un mini-dataset, une experiment avant / après, des scores lus |
| **Monitor** | J1→J4 | une trace de démonstration : session, utilisateur pseudonyme, scores |
| **Sécurité** | J1, J3, J4 | une injection refusée, prouvée par un cas de test |

Le domaine **Deploy** de la certification (gate d'évaluation en CI, packaging, interface) est couvert par les notebooks fournis en autonomie (§2, « Pour aller plus loin »).

La sécurité et la conformité (OWASP Agentic, RGPD, NIS2, AI Act) sont transverses : sur un CV, c'est ce qui différencie le profil.

---

## Sources

- PyPI : [langchain](https://pypi.org/project/langchain/) · [langgraph](https://pypi.org/project/langgraph/) · [langfuse](https://pypi.org/project/langfuse/)
- [LangChain / LangGraph changelog](https://docs.langchain.com/oss/python/releases/changelog) · [Multi-agent patterns](https://docs.langchain.com/oss/python/langchain/multi-agent) · [langgraph-supervisor README](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Langfuse Python SDK v3 → v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4) · [Langfuse self-hosting Docker Compose](https://langfuse.com/self-hosting/deployment/docker-compose)
- [vLLM releases](https://github.com/vllm-project/vllm/releases) · [Ollama releases](https://github.com/ollama/ollama/releases) · [granite4.1](https://ollama.com/library/granite4.1) · [gemma4](https://ollama.com/library/gemma4) · [Best Ollama models 2026 (Morph)](https://www.morphllm.com/best-ollama-models)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [Synthèse Cycode](https://cycode.com/blog/owasp-top-10-agentic-applications/)
- Marché : [LangChain Certified Agent Engineer](https://kb.langchain.com/articles/5297173898-what-is-the-langchain-certified-agent-engineer-exam) · [State of Agent Engineering 2026](https://www.langchain.com/state-of-agent-engineering)
- [Langfuse docker-compose.yml officiel](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml)
- AI Act Omnibus : [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/) · [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/) · [Goodwin, art. 50](https://www.goodwinlaw.com/en/insights/publications/2026/08/alerts-technology-dpc-eu-ai-act-transparency-obligations-now-in-force)
