# Infrastructure HelpDesk-Ops (stack 100 % locale)

| Service | URL | Rôle |
|---|---|---|
| Langfuse (UI + API) | http://localhost:3000 | traces, sessions, scores, prompts, datasets |
| vLLM (salle, GPU) | http://127.0.0.1:8001 · 8002 · 8003 | LLM locaux, API compatible OpenAI (clé `VLLM_API_KEY`) : granite4.1:8b · granite4.1:3b · gemma4:12b (J4) |
| Ollama (repli, sans GPU) | http://127.0.0.1:11434 | LLM locaux sur CPU : préparation, plan B |
| Qdrant (REST + dashboard) | http://localhost:6333/dashboard | base vectorielle (clé API obligatoire) |
| MinIO | http://localhost:9090 | stockage objets de Langfuse (interne) |
| Postgres, ClickHouse, Redis, Qdrant gRPC :6334 | `127.0.0.1` uniquement | stockage interne |

## Pré-requis

- Docker (Compose v2)
- **uv ≥ 0.12** : c'est le seul outil Python à installer, il gère lui-même Python 3.12.
  - Linux / macOS : `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell) : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- ~40 Go de disque libre (images, modèles, torch)

## Démarrage en 5 commandes

```bash
cd infrastructure

# 1. Environnement Python : crée .venv avec Python 3.12 et installe EXACTEMENT uv.lock
uv sync

# 2. Secrets aléatoires + clés Langfuse pré-provisionnées + clé Qdrant (une seule fois)
uv run generate_env.py

# 3 + 4. Salle (Ubuntu + GPU) : vLLM. Démarre la stack et télécharge les poids (voir « Salle de formation »)
bash installer_reseau.sh            # puis, l'après-midi du J1 : bash installer_reseau.sh --fond

# 3. Préparation SANS GPU : Ollama (generate_env.py a écrit LLM_BACKEND=ollama faute de nvidia-smi)
docker compose up -d
# 4. Télécharger les modèles Ollama (≈ 15 Go)
./pull_models.sh          # Linux
.\pull_models.ps1         # Windows (PowerShell)

# 5. Vérification de bout en bout (6 contrôles)
uv run smoke_test.py
```

Puis, depuis la racine du dossier `Orchestration` :

```bash
uv run --project infrastructure jupyter lab
```

⚠️ `--project infrastructure` est indispensable : la racine n'a pas de `pyproject.toml`, et un simple `uv run` y utilise **en silence** le Python du système (sans les dépendances du cours). Lancé depuis `infrastructure/`, Jupyter ne verrait pas les dossiers `notebooks/` et `exercices/`.

Le code du fil rouge (`src/helpdesk_ops`) est installé par `uv sync` en mode éditable : voir `src/README.md`. Tests : `uv run pytest ../src/tests` (depuis `infrastructure/`).

Langfuse met **2 à 3 minutes** à être prêt au premier démarrage (migrations ClickHouse). Identifiants de l'UI : affichés par `generate_env.py` (et présents dans `.env`).

## Pourquoi uv plutôt que pip + venv ?

| Besoin | pip + venv | uv |
|---|---|---|
| Installer Python 3.12 | à faire à la main | `uv sync` le télécharge si besoin (`.python-version`) |
| Reproductibilité | `requirements.lock` par plateforme | **un seul `uv.lock` universel** (Linux salle + Windows préparation) |
| Temps d'installation | plusieurs minutes | 10 à 100× plus rapide (cache global, résolution en Rust) |
| Dépendances de dev séparées | fichiers multiples | `[dependency-groups]` dans `pyproject.toml` |
| Lancer un script | activer le venv | `uv run script.py` (pas d'activation à oublier) |

**Mise à jour des versions (formateur) :** `uv lock --upgrade`, puis `uv sync`, puis `uv run smoke_test.py`, puis commit de `pyproject.toml` et `uv.lock`. Une mise à jour ne passe jamais en salle sans smoke test vert.

**torch :** les wheels PyPI sont en CUDA sous Linux et en CPU sous Windows. Le lock universel gère les deux sans index spécifique.

## Salle de formation (Ubuntu + GPU) : vLLM

GPU de la salle : **RTX PRO 4000 Blackwell, 24 Go**. Moteur : **vLLM v0.32.0** (`docker-compose.vllm.yml`), choisi le 27/10/2026.

1. Installer le pilote NVIDIA (**≥ 580** : l'image vLLM est en CUDA 13) et le **NVIDIA Container Toolkit**, puis vérifier : `docker run --rm --gpus all ubuntu:24.04 nvidia-smi`. `installer_reseau.sh` refuse de continuer avec un pilote plus ancien.
2. Toujours démarrer avec la surcharge : `docker compose -f docker-compose.yml -f docker-compose.vllm.yml up -d`. Ollama ne démarre pas avec ce fichier (profil `ollama`).
3. **Un serveur vLLM par modèle**, chacun avec une part **fixe** de la VRAM réservée au démarrage :

   | Service | Modèle servi | Poids Hugging Face | Disque | VRAM réservée |
   |---|---|---|---|---|
   | `vllm-agent` :8001 | `granite4.1:8b` | `ibm-granite/granite-4.1-8b-fp8` | 9,6 Go | 0,60 (≈ 14 Go) |
   | `vllm-small` :8002 | `granite4.1:3b` | `ibm-granite/granite-4.1-3b-fp8` | 4,2 Go | 0,27 (≈ 6,5 Go) |
   | `vllm-juge` :8003 (profil `juge`) | `gemma4:12b` | `google/gemma-4-12B-it-qat-w4a16-ct` | 10,3 Go | 0,60, **seul** |

   Les noms servis (`--served-model-name`) sont ceux d'Ollama : `MODEL_*` dans `.env` ne change pas d'un moteur à l'autre. Les URL sont dans `VLLM_URL_AGENT`, `_SMALL`, `_ALT`, `_JUDGE` (alt et judge = le serveur gemma).
4. **Mode « agents » (J1 → J4 matin)** : 8b + 3b. **Mode « juge » (J4-04, Ex4.1)** : gemma4 seul. Les deux ne tiennent pas ensemble sur 24 Go. Bascule : `bash vllm_mode.sh juge` / `bash vllm_mode.sh agents` (1 à 3 min) ; les notebooks J4-04 et Ex4.1 l'appellent eux-mêmes (`helpdesk_ops.config.basculer_vllm`).
5. Contrôle : `nvidia-smi` pendant une inférence ; `uv run smoke_test.py` vérifie que chaque serveur sert le modèle attendu et refuse une requête sans clé.
6. **Premier démarrage d'un serveur : jusqu'à ≈ 10 min** (chargement, compilation, capture des graphes CUDA). Le cache (volume `vllm_cache`) rend les suivants plus rapides.
7. Embeddings : sur **CPU** par défaut (`EMBEDDING_DEVICE=cpu`), pour ne pas prendre de VRAM aux serveurs vLLM.
8. Tool-calling : `--tool-call-parser=granite4` (granite) et `gemma4` (gemma, avec le gabarit `tool_chat_template_gemma4.jinja` de l'image : celui du checkpoint ignore les outils). **Non testé sur GPU** au 27/10 : si le smoke test signale « le modèle n'a PAS appelé l'outil », essayer `VLLM_TOOL_PARSER_GRANITE=hermes` dans `.env` (même format `<tool_call>`), puis `docker compose -f docker-compose.yml -f docker-compose.vllm.yml up -d`.

**Plan B en salle (vLLM ne démarre pas)** : `LLM_BACKEND=ollama` dans `.env`, puis `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` et `./pull_models.sh` (image Ollama 3,8 Go + ≈ 15 Go de modèles). Aucun code ne change : `creer_llm` lit le moteur dans `.env`. Avec Ollama sur ce GPU, `granite4.1:8b` + `gemma4:12b` tiennent ensemble (≈ 17–18 Go, `OLLAMA_MAX_LOADED_MODELS=2`).

## Poste de préparation (sans GPU) : Ollama

- vLLM exige un GPU NVIDIA : sans `nvidia-smi`, `generate_env.py` écrit `LLM_BACKEND=ollama` (forcer avec `--moteur`). Un `.env` antérieur au 27/10, sans `LLM_BACKEND`, reste sur Ollama.
- Même compose, **sans** fichier de surcharge. Docker Desktop : allouer **≥ 24 Go** à la VM WSL2 (`.wslconfig` → `memory=24GB`), car Langfuse + Qdrant + un 8B en CPU consomment beaucoup.
- **Mémoire** : avec `OLLAMA_MAX_LOADED_MODELS=2` (défaut), granite 8b (8,3 Go avec 16k de contexte) et gemma4 12b restent chargés ensemble : le conteneur Ollama a atteint 18 Go sur 23 pendant la préparation du J4, et l'exécution a été interrompue faute de mémoire. Sur un poste de préparation, ajouter `OLLAMA_MAX_LOADED_MODELS=1` au `.env` puis `docker compose up -d ollama` : un modèle à la fois, au prix d'un rechargement à chaque changement de modèle. En salle (GPU), garder 2 si la VRAM le permet.
- Pour itérer vite : `MODEL_AGENT=granite4.1:3b` dans `.env` (pas besoin de redémarrer la stack, les notebooks relisent `.env`).

## Clé USB des modèles (allège le J1 d'≈ 10 Go par poste)

La clé ne contient que des **modèles** : `granite4.1:8b` au format vLLM (`ibm-granite/granite-4.1-8b-fp8`, 9,6 Go) et les embeddings (MiniLM + BM25, 0,5 Go). Les images Docker et l'environnement Python passent toujours par le réseau.

```bash
# Formateur, la veille (réseau requis une fois) : clé de 16 Go en exFAT ou NTFS
cd infrastructure
uv run cle_modeles.py fabriquer --dest E:\helpdesk-modeles          # --tout : + 3b et gemma4 (≈ 25 Go)
uv run cle_modeles.py verifier --cle E:\helpdesk-modeles

# Poste de la salle : la clé est montée sous /media/$USER/<NOM>
bash infrastructure/installer_reseau.sh --cle /media/$USER/<NOM>/helpdesk-modeles
bash infrastructure/installer_reseau.sh --fond --cle /media/$USER/<NOM>/helpdesk-modeles   # si la clé est toujours là
```

- Les modèles de la clé sont copiés **avant** tout téléchargement ; seul ce qui manque passe par le réseau (copie sans écrasement : relance sans risque).
- Caches Hugging Face copiés **sans liens symboliques** (exFAT n'en stocke pas) ; un `MANIFESTE.json` porte la taille et l'empreinte SHA-256 de chaque fichier (`verifier`).
- La clé ne sert qu'au chemin **vLLM** pour le LLM ; sous Ollama (plan B), seuls les embeddings sont repris de la clé.
- Une seule clé pour toute la salle : elle passe de poste en poste (copie ≈ 1 à 3 min en USB 3), le poste n'en a plus besoin une fois la copie faite.

## Réseau : « TLS handshake timeout » (constaté le 27/10/2026)

Symptôme : `ollama pull` ou `docker compose pull` échoue en « net/http: TLS handshake timeout », alors que `curl` vers le même registre répond en moins d'une seconde. Cause : les programmes écrits en Go (Ollama, le démon Docker) envoient depuis Go 1.24 un message TLS plus gros (échange de clés post-quantique `X25519MLKEM768`), que certains réseaux ou pare-feu laissent tomber.

- **Ollama** : corrigé dans `docker-compose.yml` (`GODEBUG=tlsmlkem=0`, réglable par `OLLAMA_GODEBUG` dans `.env`).
- **Démon Docker (Linux, droits administrateur)** :

  ```bash
  sudo mkdir -p /etc/systemd/system/docker.service.d
  printf '[Service]
Environment="GODEBUG=tlsmlkem=0"
' | sudo tee /etc/systemd/system/docker.service.d/godebug.conf
  sudo systemctl daemon-reload && sudo systemctl restart docker
  ```

  Docker Desktop (poste de préparation) : un nouvel essai suffit en général ; `installer_reseau.sh` fait 3 essais et ne télécharge que les images absentes.

## Qdrant : points d'attention

- **Clé API obligatoire**, même en local (Zero Trust). Le smoke test vérifie qu'une requête sans clé est bien refusée (HTTP 401).
- Le client Python affiche `UserWarning: Api key is used with an insecure connection` : c'est attendu en HTTP local. En production, TLS obligatoire.
- API client : `query_points` est l'API actuelle. `search()` / `recommend()` sont dépréciés côté serveur depuis v1.19, ne pas les enseigner.
- Filtres via LangChain : le payload est rangé sous `metadata`, donc un filtre s'écrit `key="metadata.categorie"`.
- Tests unitaires et CI : `QdrantClient(":memory:")` donne la même API **sans serveur**.

## Opérations courantes

| Besoin | Commande |
|---|---|
| État des services | `docker compose ps` (projet Compose `helpdesk-ops`, volumes `helpdesk-ops_*`) |
| Logs Langfuse | `docker compose logs -f langfuse-web langfuse-worker` |
| Arrêt (données conservées) | `docker compose down` |
| **Remise à zéro complète** (traces, vecteurs, modèles) | `docker compose down -v` puis `uv run generate_env.py --force` |
| Mettre à jour les dépendances Python | `uv lock --upgrade && uv sync` |
| Lire les traces par API | `GET /api/public/v2/observations` : le serveur v4 tourne en mode *events_only*, `/api/public/traces` répond 404 |
| (Ré)indexer la KB (J3) | `uv run python -c "from helpdesk_ops.kb import indexer; print(indexer(recreer=True))"` |
| Basculer vLLM (J4) | `bash vllm_mode.sh juge` puis `bash vllm_mode.sh agents` ; `bash vllm_mode.sh` affiche l'état |
| Logs vLLM | `docker compose -f docker-compose.yml -f docker-compose.vllm.yml logs -f vllm-agent` |
| Lancer le serveur MCP en HTTP | `uv run python -m helpdesk_ops.mcp_inventaire --http 8765` (écoute sur 127.0.0.1 seulement) |
| Gate d'évaluation (J5) | `uv run python ../ci/eval_gate.py --rapide` (code de sortie 1 si un score passe sous `ci/seuils.json`) |
| Servir le jalon J5 par l'API LangGraph | `./serveur_langgraph.ps1` ou `./serveur_langgraph.sh` → `http://127.0.0.1:2024` |
| Interface Streamlit (J5) | depuis la racine du cours : `uv run --project infrastructure streamlit run app/helpdesk_app.py` |

**Zéro flux sortant (J3).** `generate_env.py` pose `FASTMCP_CHECK_FOR_UPDATES=off` (sinon FastMCP interroge PyPI à chaque démarrage de serveur), `FASTMCP_SHOW_SERVER_BANNER=false` et `HF_HUB_DISABLE_TELEMETRY=1`. Les modèles d'embeddings (HF multilingue, BM25) sont préchargés par `pull_models` : faites-le la veille, le premier téléchargement a pris 4 minutes avec des coupures pendant la préparation.

**Zéro flux sortant (J5), vérifié le 22/10/2026.** `langgraph-cli` envoie une analytique d'usage et le serveur `langgraph dev` interroge PyPI au démarrage : les scripts `serveur_langgraph.*` posent `LANGGRAPH_CLI_NO_ANALYTICS=1` et `LANGGRAPH_NO_VERSION_CHECK=true` (plus `PYTHONUTF8=1`, sans quoi le `.env` est lu en cp1252 sous Windows). `langgraph-cli` n'est pas dans `uv.lock` (il ferait descendre `protobuf` et `grpcio`) : il est chargé à la demande par `uv run --with`, versions figées dans les scripts. Streamlit envoie des statistiques d'usage par défaut : `.streamlit/config.toml` (racine du cours) les coupe et fixe l'écoute sur `127.0.0.1`.

**Pourquoi `127.0.0.1` et pas `localhost` pour vLLM, Ollama et Qdrant ?** Leurs ports sont publiés sur `127.0.0.1` uniquement (pas d'exposition réseau). Sous Windows, `localhost` est d'abord résolu en IPv6 (`::1`) et chaque **nouvelle connexion** attend ~2 s avant de se rabattre sur IPv4 : mesuré le 21/10/2026, 2,4 s contre 0,3 s par requête Qdrant, et chaque recherche dans la KB coûtait 2 s de trop. Langfuse (port publié sur toutes les interfaces) n'est pas concerné.

**Pourquoi `name: helpdesk-ops` dans le compose ?** Sans nom explicite, Compose prend celui du dossier (`infrastructure`) et réutilise les volumes de tout autre cours rangé dans un dossier du même nom : mot de passe Postgres refusé, traces et vecteurs mélangés. Constaté sur le poste de préparation le 20/10/2026.

## Dette technique / sécurité (assumée pour un usage formation)

- 🔒 Pas de TLS : tout est en `localhost`. **Ne pas exposer** les ports 3000 et 6333 sur le réseau de la salle.
- 🔒 `.env` contient des secrets : il est dans `.gitignore`, ne jamais le commiter.
- 🔒 Télémétrie Langfuse, Qdrant et vLLM désactivées (`VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1`) ; serveurs vLLM en `HF_HUB_OFFLINE=1` : les poids sont téléchargés une fois par `installer_reseau.sh`, dans un conteneur jetable. Aucune donnée ne sort du poste.
- 🔒 vLLM protégé par `VLLM_API_KEY`, comme Qdrant : le smoke test vérifie qu'une requête sans clé reçoit 401.
- ⚙️ Docker Compose n'offre ni haute disponibilité ni sauvegarde. En production : Kubernetes (chart Helm Langfuse, Qdrant en cluster ou Qdrant Cloud Hybrid / Private).
- ⚙️ Langfuse est figé sur **4.46.0** (`LANGFUSE_VERSION`, version testée en préparation ; le fichier officiel utilise le tag flottant `:4`, qui tirait v4.68 le 23/10/2026). vLLM (`v0.32.0`, `VLLM_VERSION`), Ollama (`0.34.4`) et Qdrant (`v1.19.1`) sont figés de la même façon. Monter une version = la changer dans `.env`, puis smoke test et notebooks.
- 🔒 Qdrant 1.19.1 : la faille critique GHSA-frc7-44gm-99qq (22/10/2026) ne touche que le **mode cluster** ; le nœud unique du poste n'est pas concerné. Ne pas activer `cluster.enabled`.
