#!/usr/bin/env bash
# installer_reseau.sh : installation en salle PAR LE RÉSEAU, en deux temps, sans préchargement.
# Postes : Ubuntu 24.04 x86_64, Docker + NVIDIA Container Toolkit, GPU NVIDIA (pilote ≥ 580 pour vLLM).
#
#   J1, 08h35   bash infrastructure/installer_reseau.sh          # ≈ 28 Go : images (dont vLLM 9,2 Go), Python, granite4.1:8b
#               (≈ 18 Go avec --cle : granite4.1:8b et les embeddings viennent de la clé)
#   J1, ap.-m.  bash infrastructure/installer_reseau.sh --fond   # ≈ 15 Go : 3b, gemma4:12b, embeddings
#
# Moteur : vLLM si nvidia-smi répond (salle), sinon Ollama sur CPU (poste de préparation).
# Phase J1 : tous les rôles (agent, alt, small, judge) pointent provisoirement sur MODEL_AGENT,
# pour que les notebooks et smoke_test.py fonctionnent avec un seul modèle téléchargé.
# Phase --fond : télécharge le reste puis rétablit les modèles prévus dans .env.
#
# Option --cle <dossier> (les deux phases) : les modèles de la clé USB du formateur (fabriquée par
# cle_modeles.py) sont copiés d'abord ; seuls les modèles absents de la clé passent par le réseau.
#   bash infrastructure/installer_reseau.sh --cle /media/$USER/<CLE>/helpdesk-modeles
set -euo pipefail

CLE=""
ARGS=()
while (( $# )); do
  case "$1" in
    --cle) CLE=$(cd "$2" && pwd); shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"
cd "$(dirname "$0")"

UV_VERSION=0.12.19                      # version de préparation
SEUIL_VRAM_MO=12000                     # Ollama : gemma4:12b ≈ 8 Go + contexte
SEUIL_VRAM_VLLM_MO=22000                # vLLM : budget prévu pour 24 Go (docker-compose.vllm.yml)
CIBLES=../data/logs/modeles_cibles.env  # modèles prévus par generate_env.py
JOURNAL=../data/logs/installation_fond.log
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUTF8=1                     # --fond écrit dans un fichier : sous Windows, Python passerait en cp1252 (emojis)
CACHE_FASTEMBED="$HOME/.cache/fastembed"
command -v cygpath >/dev/null && CACHE_FASTEMBED=$(cygpath -m "$CACHE_FASTEMBED")   # Git Bash : chemin Windows

vram_mo() {
  command -v nvidia-smi >/dev/null || { echo 0; return; }
  nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '
}
valeur() { grep -m1 "^$1=" "$2" | cut -d= -f2-; }
poser() { sed -i "s|^$1=.*|$1=$2|" .env; }

if [[ -f .env ]]; then MOTEUR=$(valeur LLM_BACKEND .env || true); fi
MOTEUR=${MOTEUR:-$(command -v nvidia-smi >/dev/null && echo vllm || echo ollama)}
if [[ $MOTEUR == vllm ]]; then
  COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.vllm.yml)
else
  COMPOSE=(docker compose -f docker-compose.yml)
  command -v nvidia-smi >/dev/null && COMPOSE+=(-f docker-compose.gpu.yml)   # sans GPU : Ollama sur CPU
fi

# Dépôt Hugging Face servi par vLLM pour chaque nom de modèle (surcharges possibles dans .env : VLLM_HF_*)
depot_hf() {
  case "$1" in
    granite4.1:8b) valeur VLLM_HF_AGENT .env 2>/dev/null || echo ibm-granite/granite-4.1-8b-fp8 ;;
    granite4.1:3b) valeur VLLM_HF_SMALL .env 2>/dev/null || echo ibm-granite/granite-4.1-3b-fp8 ;;
    gemma4:12b)    valeur VLLM_HF_JUGE .env 2>/dev/null || echo google/gemma-4-12B-it-qat-w4a16-ct ;;
    *) echo "modèle sans dépôt vLLM connu : $1" >&2; return 1 ;;
  esac
}

pull_une_fois() {
  if [[ $MOTEUR == vllm ]]; then
    # Téléchargé dans le volume vllm_cache par un conteneur jetable : les serveurs restent hors ligne
    # Cache local d'abord (clé USB ou téléchargement précédent), réseau seulement s'il manque
    local depot; depot=$(depot_hf "$1")
    "${COMPOSE[@]}" run --rm --no-deps -T -e HF_HUB_OFFLINE=0 --entrypoint python3 vllm-agent -c "
from huggingface_hub import snapshot_download
try:
    print('déjà en cache :', snapshot_download('$depot', local_files_only=True))
except Exception:
    print(snapshot_download('$depot'))"
  else
    "${COMPOSE[@]}" exec -T ollama ollama pull "$1"
  fi
}

pull() {
  # 3 essais : constaté le 27/10, « TLS handshake timeout » passager vers registry.ollama.ai.
  # Un téléchargement interrompu reprend où il s'était arrêté (Ollama comme Hugging Face).
  local essai
  for essai in 1 2 3; do
    echo "⬇️  $1 (essai $essai sur 3)"
    pull_une_fois "$1" && return 0
    (( essai < 3 )) && sleep 20
  done
  echo "❌ $1 : téléchargement en échec après 3 essais. Relancer le script : il reprend où il s'est arrêté."
  return 1
}

importer_cle() {
  [[ -n $CLE ]] || return 0
  [[ -f "$CLE/MANIFESTE.json" ]] || { echo "❌ $CLE/MANIFESTE.json introuvable : est-ce bien le dossier de la clé ?"; exit 1; }
  echo "== Modèles depuis la clé : $CLE"
  if [[ $MOTEUR == vllm && -d "$CLE/vllm/hub" ]]; then
    # Dans le volume vllm_cache, sans écraser ce qui y est déjà (relance sans risque)
    "${COMPOSE[@]}" run --rm --no-deps -T -v "$CLE/vllm/hub:/cle:ro" --entrypoint sh vllm-agent \
      -c 'mkdir -p /root/.cache/huggingface/hub && cp -rn /cle/. /root/.cache/huggingface/hub/ && ls /root/.cache/huggingface/hub'
  fi
  FASTEMBED_CACHE_PATH="$CACHE_FASTEMBED" uv run --frozen python cle_modeles.py importer --cle "$CLE"
}

# Rôle → variable d'URL vLLM (alt et judge partagent le serveur gemma4)
url_de() { case "$1" in MODEL_AGENT) echo VLLM_URL_AGENT ;; MODEL_SMALL) echo VLLM_URL_SMALL ;;
                         MODEL_AGENT_ALT) echo VLLM_URL_ALT ;; MODEL_JUDGE) echo VLLM_URL_JUDGE ;; esac; }
retablir() { poser "$1" "$(valeur "$1" "$CIBLES")"; local u; u=$(url_de "$1"); poser "$u" "$(valeur "$u" "$CIBLES")"; }

if [[ "${1:-}" == "--fond" ]]; then
  [[ -f "$CIBLES" ]] || { echo "lancer d'abord la phase J1 (sans option)"; exit 1; }
  if [[ "${2:-}" != "--detache" ]]; then
    nohup bash "$PWD/$(basename "$0")" --fond --detache ${CLE:+--cle "$CLE"} >"$JOURNAL" 2>&1 &
    echo "Téléchargements en arrière-plan (journal : data/logs/installation_fond.log). On peut continuer à travailler."
    exit 0
  fi
  importer_cle
  pull "$(valeur MODEL_SMALL "$CIBLES")"
  retablir MODEL_SMALL
  [[ $MOTEUR == vllm ]] && "${COMPOSE[@]}" up -d --wait --wait-timeout 900 vllm-small
  echo "⬇️  embeddings + BM25 (J3)"
  uv run --frozen python -c "from helpdesk_ops.kb import precharger_modeles; precharger_modeles()"
  VRAM=$(vram_mo)
  if [[ $MOTEUR == vllm ]] || (( VRAM >= SEUIL_VRAM_MO )); then
    pull "$(valeur MODEL_JUDGE "$CIBLES")"   # vLLM : alt et judge = le même gemma4:12b
    [[ $MOTEUR == ollama ]] && pull "$(valeur MODEL_AGENT_ALT "$CIBLES")"
    for var in MODEL_AGENT_ALT MODEL_JUDGE; do retablir $var; done
    [[ $MOTEUR == vllm ]] && echo "ℹ️  gemma4:12b ne démarre qu'en J4 : bash infrastructure/vllm_mode.sh juge"
  else
    echo "VRAM ${VRAM} Mo < ${SEUIL_VRAM_MO} : MODEL_AGENT_ALT et MODEL_JUDGE restent sur $(valeur MODEL_AGENT .env)"
  fi
  uv run --frozen smoke_test.py
  echo "✅ installation complète"
  exit 0
fi

echo "== 1/5 Vérifications (moteur : $MOTEUR)"
docker info >/dev/null 2>&1 || { echo "Docker inaccessible : utilisateur dans le groupe docker ?"; exit 1; }
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  if [[ $MOTEUR == vllm ]]; then
    PILOTE=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
    (( PILOTE >= 580 )) || { echo "❌ pilote NVIDIA $PILOTE < 580 : l'image vLLM (CUDA 13) ne démarrera pas. Plan B : LLM_BACKEND=ollama (README)"; exit 1; }
    (( $(vram_mo) >= SEUIL_VRAM_VLLM_MO )) || echo "⚠️  VRAM $(vram_mo) Mo : le budget vLLM est prévu pour 24 Go (baisser VLLM_MEM_* dans .env)"
  fi
fi
command -v uv >/dev/null || curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh

echo "== 2/5 Images Docker et environnement Python, en parallèle"
# .env d'abord : le compose vLLM exige VLLM_API_KEY. generate_env.py n'utilise que la bibliothèque standard.
[[ -f .env ]] || uv run --no-project --python 3.12 generate_env.py --moteur "$MOTEUR"
tirer_images() {
  # --policy missing : seulement les images absentes (relance rapide). 3 essais : constaté le 27/10,
  # un « TLS handshake timeout » passager de Docker Hub arrêtait l'installation, images pourtant en cache.
  local essai
  for essai in 1 2 3; do
    "${COMPOSE[@]}" pull --quiet --policy missing && return 0
    echo "⚠️  docker compose pull : essai $essai sur 3 en échec (réseau ?)"
    (( essai < 3 )) && sleep 20
  done
  return 1
}
tirer_images & PID_IMAGES=$!
uv sync --frozen & PID_UV=$!
wait $PID_UV || { echo "uv sync en échec"; exit 1; }
wait $PID_IMAGES || { echo "docker compose pull en échec après 3 essais : relancer le script (il reprend où il s'est arrêté)"; exit 1; }

echo "== 3/5 .env (rôles provisoirement sur un seul modèle)"
mkdir -p ../data/logs
[[ -f "$CIBLES" ]] || grep -E '^(MODEL_(AGENT|AGENT_ALT|SMALL|JUDGE)|VLLM_URL_[A-Z]+)=' .env > "$CIBLES"
grep -q '^FASTEMBED_CACHE_PATH=' .env || {
  echo ""
  echo "# Cache persistant (sinon FastEmbed écrit dans /tmp, vidé au redémarrage)"
  echo "FASTEMBED_CACHE_PATH=$CACHE_FASTEMBED"
} >> .env
AGENT=$(valeur MODEL_AGENT .env)
for var in MODEL_AGENT_ALT MODEL_SMALL MODEL_JUDGE; do
  poser $var "$AGENT"
  poser "$(url_de $var)" "$(valeur VLLM_URL_AGENT .env)"
done

echo "== 4/5 Stack et modèle $AGENT"
importer_cle
if [[ $MOTEUR == vllm ]]; then
  pull "$AGENT"                         # avant le démarrage : le serveur est hors ligne
  # Tout sauf vllm-small, dont les poids arrivent avec --fond
  mapfile -t SERVICES < <("${COMPOSE[@]}" config --services | grep -v '^vllm-small$')
  "${COMPOSE[@]}" up -d "${SERVICES[@]}"
  echo "⏳ vllm-agent : 1er démarrage jusqu'à ≈ 10 min (chargement, compilation)"
  "${COMPOSE[@]}" up -d --wait --wait-timeout 900 vllm-agent
else
  "${COMPOSE[@]}" up -d
  pull "$AGENT"
fi

echo "== 5/5 Smoke test (Langfuse : 2-3 min au premier démarrage)"
for _ in $(seq 1 36); do
  curl -fs http://127.0.0.1:3000/api/public/health >/dev/null 2>&1 && break
  sleep 5
done
uv run --frozen smoke_test.py
echo "✅ prêt pour J1. Cet après-midi : bash infrastructure/installer_reseau.sh --fond"
