# Installer l'environnement chez vous

Ce guide installe sur **votre** ordinateur la même stack que pendant la formation, 100 % locale. En salle, le
modèle tournait sur un GPU avec vLLM. Chez vous, sans GPU NVIDIA, c'est **Ollama** qui le fait tourner sur le
processeur : c'est plus lent, mais le code ne change pas d'une ligne.

| Service | Adresse | Rôle |
|---|---|---|
| Langfuse | <http://localhost:3000> | traces, sessions, scores, prompts, datasets |
| Ollama | <http://127.0.0.1:11434> | le modèle de langage (granite4.1:8b, granite4.1:3b, gemma4:12b) |
| Qdrant | <http://localhost:6333/dashboard> | la base vectorielle du RAG (clé API obligatoire) |
| MinIO, Postgres, ClickHouse, Redis | internes | le stockage de Langfuse |

Durée : **1 à 2 heures**, dont l'essentiel en téléchargements (≈ 25 Go).

---

## 1. Votre machine

| | Minimum | Confortable |
|---|---|---|
| Mémoire vive | 16 Go (avec le petit modèle 3b) | 32 Go |
| Disque libre | 40 Go | 60 Go |
| Processeur | 4 cœurs récents | 8 cœurs et plus |
| GPU | aucun | NVIDIA ≥ 8 Go (Ollama l'utilise, voir 6.2) |
| Système | Windows 10/11 64 bits, macOS 13+, Linux 64 bits | |

> ⏱ **À quoi s'attendre sur un portable sans GPU** (mesuré pendant la préparation, i7, 8b) : une étape de tri,
> 5 s à 1 min 30 ; un agent avec outils, 2 à 7 minutes ; l'experiment sur 20 cas, 6 à 7 minutes. Pour itérer
> vite, passez au modèle 3b (section 5).

---

## 2. Installer les trois outils

### Docker

- **Windows** : [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/), moteur
  **WSL 2** (proposé par défaut). Puis donnez-lui assez de mémoire : créez `C:\Users\<vous>\.wslconfig` :

  ```ini
  [wsl2]
  memory=24GB      # 12GB si votre machine n'a que 16 Go : utilisez alors le modèle 3b
  ```

  puis, dans PowerShell : `wsl --shutdown`, et relancez Docker Desktop.
- **macOS** : [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/). *Settings ›
  Resources › Memory* : 16 Go ou plus.
- **Linux** : [Docker Engine](https://docs.docker.com/engine/install/) (pas le paquet *snap*), puis
  `sudo usermod -aG docker $USER`, déconnexion, reconnexion.

Vérification : `docker compose version` affiche une version 2.x.

### uv (il installe Python 3.12 tout seul)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fermez et rouvrez le terminal. Vérification : `uv --version` (0.12 ou plus).

### Un éditeur

[VS Code](https://code.visualstudio.com/) avec les extensions *Python* et *Jupyter* (ou PyCharm). Git est
recommandé : <https://git-scm.com/downloads>.

---

## 3. Récupérer le projet

Deux possibilités :

- **Depuis le zip reçu** : décompressez-le à un endroit **sans espace ni accent** dans le chemin, par exemple
  `C:\dev\helpdesk-ops` ou `~/dev/helpdesk-ops`. Il contient tout le dépôt, ce kit et les slides en PDF.
- **Depuis GitHub**, pour recevoir ensuite les corrections par `git pull` (tout sauf les slides) :

  ```bash
  git clone https://github.com/michaelperson/Orcherstation_Monitoring_Agent.git helpdesk-ops
  ```

> ⚠️ Windows : choisissez **un seul** monde. Soit tout sous Windows (PowerShell), soit tout sous WSL (dossier
> dans `/home/...`). Lancer `uv` sur le même dossier depuis les deux casse l'environnement Python : uv remplace
> sans prévenir le `.venv` de l'autre plateforme.

---

## 4. Démarrer la stack (5 commandes)

Toutes les commandes de cette section se lancent **depuis le dossier `infrastructure/`** du projet.

```bash
cd helpdesk-ops/infrastructure

# 1. Environnement Python : Python 3.12 + exactement les versions de uv.lock (quelques minutes, torch inclus)
uv sync

# 2. Secrets aléatoires, clés Langfuse, clé Qdrant. Sans GPU NVIDIA, il choisit Ollama tout seul.
uv run generate_env.py
#    → NOTEZ l'identifiant et le mot de passe Langfuse qu'il affiche (ils sont aussi dans infrastructure/.env)

# 3. Démarrer les services (Langfuse, Qdrant, Ollama...)
docker compose up -d

# 4. Télécharger les modèles (≈ 15 Go) et les embeddings du RAG
./pull_models.sh          # macOS / Linux
.\pull_models.ps1         # Windows (PowerShell)

# 5. Vérifier de bout en bout (6 contrôles)
uv run smoke_test.py
```

> ⏳ Au **premier** démarrage, Langfuse met **2 à 3 minutes** à être prêt (migrations de base). Si le smoke test
> échoue sur Langfuse, attendez et relancez-le.

Puis, **depuis la racine du projet** (le dossier au-dessus d'`infrastructure/`) :

```bash
uv run --project infrastructure jupyter lab
```

> ⚠️ `--project infrastructure` est indispensable : la racine n'a pas de `pyproject.toml`, et un simple
> `uv run` y utiliserait **en silence** le Python du système, sans les bibliothèques du cours.

Ouvrez <http://localhost:3000>, connectez-vous avec les identifiants notés à l'étape 2 : le projet HelpDesk-Ops
est déjà créé.

### Lancer une étape de la construction

```bash
# depuis la racine du projet
uv run --project infrastructure python construction/etape_03_stategraph.py "srv-erp-02 est-il en ligne ?"
uv run --project infrastructure python construction/etape_07_rag_specialistes_mcp.py --indexer   # une fois, avant l'étape 7
```

### Tester que tout le code est câblé (sans modèle, en quelques secondes)

```bash
uv run --project infrastructure pytest construction/test_etapes.py -q
```

---

## 5. Régler selon votre machine

Tout se règle dans `infrastructure/.env`, **sans redémarrer** la stack : les scripts et notebooks relisent ce
fichier à chaque lancement.

| Situation | Réglage dans `.env` |
|---|---|
| Itérer vite, ou machine à 16 Go | `MODEL_AGENT=granite4.1:3b` |
| Mémoire saturée quand le juge (gemma4) s'ajoute | `OLLAMA_MAX_LOADED_MODELS=1`, puis `docker compose up -d ollama` |
| Un agent répond « je transmets à un technicien » | ce n'est pas une réponse : c'est le **repli** après un timeout. Lisez l'erreur réelle dans le terminal ou dans Langfuse ; sur CPU, les timeouts des étapes 7 et 8 sont déjà à 600 s |

---

## 6. Cas particuliers

### 6.1 macOS (Apple Silicon)

Ollama dans Docker n'utilise pas le GPU du Mac : il tourne sur le processeur. Pour aller plus vite, installez
plutôt [Ollama pour macOS](https://ollama.com/download), qui utilise la puce, puis :

1. dans `infrastructure/.env` : `OLLAMA_BASE_URL=http://127.0.0.1:11434` (déjà la valeur par défaut) ;
2. démarrez la stack **sans** le conteneur Ollama : `docker compose up -d --scale ollama=0` ;
3. téléchargez les modèles avec l'Ollama natif : `ollama pull granite4.1:8b`, `granite4.1:3b`, `gemma4:12b` ;
4. embeddings : `uv run python -c "from helpdesk_ops.kb import precharger_modeles; precharger_modeles()"`.

### 6.2 Vous avez un GPU NVIDIA

Ollama l'utilisera avec la surcharge GPU (pilote NVIDIA récent ; sous Linux, le NVIDIA Container Toolkit) :

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Le mode vLLM de la salle (`docker-compose.vllm.yml`) demande un GPU de 24 Go : voir `infrastructure/README.md`.

### 6.3 Utiliser un modèle externe (OpenAI, Anthropic, Mistral…)

C'est possible : seule la fonction `creer_llm()` de `src/helpdesk_ops/config.py` (ou `get_llm()` dans votre
projet) change. Mais c'est une **décision de confidentialité et de coût** : les demandes et les documents
partent chez un fournisseur. Écrivez-la dans votre `PROJET.md` avant de la prendre, n'y envoyez jamais de
données réelles sans accord, et ne mettez jamais la clé API dans le code (`.env` uniquement).

---

## 7. Pannes fréquentes

| Symptôme | Cause probable | Que faire |
|---|---|---|
| `uv run` dit qu'un module est introuvable | lancé hors du projet, sans `--project infrastructure` | relancer depuis la racine avec `--project infrastructure` |
| Langfuse 401 / « refuse les clés » | Langfuse démarre encore, ou `.env` régénéré après le premier démarrage | attendre 3 min ; sinon remise à zéro (ci-dessous) |
| Qdrant 401 | clé du `.env` différente de celle du conteneur | même `.env` pour la stack et pour Python ; sinon remise à zéro |
| Une requête Qdrant ou Ollama prend 2 s de trop (Windows) | `localhost` résolu d'abord en IPv6 | utiliser `127.0.0.1` |
| `TLS handshake timeout` pendant un téléchargement | réseau ou pare-feu qui bloque les gros messages TLS | relancer ; voir la section « Réseau » de `infrastructure/README.md` |
| Ollama s'arrête, « out of memory » | deux gros modèles chargés ensemble | `OLLAMA_MAX_LOADED_MODELS=1`, modèle 3b, plus de mémoire pour WSL |
| `Client failed to connect: fileno` (MCP dans Jupyter, Windows) | stdio sans fichier journal | utiliser `transport_stdio()` du cours, qui en fournit un |
| `draw_ascii()` : ImportError | `grandalf` absent | il est dans le groupe dev : `uv sync` depuis `infrastructure/` |

Commandes utiles (depuis `infrastructure/`) :

| Besoin | Commande |
|---|---|
| État des services | `docker compose ps` |
| Journaux de Langfuse | `docker compose logs -f langfuse-web langfuse-worker` |
| Arrêter (données conservées) | `docker compose down` |
| **Remise à zéro complète** (traces, vecteurs, modèles) | `docker compose down -v`, puis `uv run generate_env.py --force`, puis reprendre la section 4 |

---

## 8. Sécurité de votre poste

- `infrastructure/.env` contient des secrets : ne le partagez pas et ne le commitez jamais.
- La stack n'a pas de TLS : elle n'écoute que sur votre machine. N'exposez pas les ports 3000 et 6333 sur un
  réseau.
- Télémétrie coupée (Langfuse, Qdrant, FastMCP, Streamlit, langgraph-cli) : rien ne sort de votre poste, hormis
  les téléchargements d'installation.
- Versions figées et testées ensemble (`uv.lock`, images Docker figées dans `.env`). La documentation Langfuse
  présente désormais un SDK Python v5 : le cours reste sur le **SDK v4**. Ne montez une version qu'en connaissance
  de cause, puis repassez le smoke test.

Pour aller plus loin : `infrastructure/README.md` (tous les détails techniques) et le
notebook `notebooks/J0_01_installer_et_brancher.ipynb`, qui reconstruit la stack service par service pour
comprendre comment chaque brique se branche.
