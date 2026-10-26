#!/usr/bin/env bash
# installer_reseau.sh : installation en salle PAR LE RÉSEAU, en deux temps, sans préchargement.
# Postes : Ubuntu 24.04 x86_64, Docker + NVIDIA Container Toolkit, GPU NVIDIA.
#
#   J1, 08h35   bash infrastructure/installer_reseau.sh          # ≈ 13 Go : images, Python, granite4.1:8b
#   J1, ap.-m.  bash infrastructure/installer_reseau.sh --fond   # 3b, embeddings, gemma4:12b si VRAM ≥ 12 Go
#
# Phase J1 : tous les rôles (agent, alt, small, judge) pointent provisoirement sur MODEL_AGENT,
# pour que les notebooks et smoke_test.py fonctionnent avec un seul modèle téléchargé.
# Phase --fond : télécharge le reste puis rétablit les modèles prévus dans .env.
set -euo pipefail
cd "$(dirname "$0")"

UV_VERSION=0.12.19                      # version de préparation
SEUIL_VRAM_MO=12000                     # gemma4:12b ≈ 8 Go + contexte
CIBLES=../data/logs/modeles_cibles.env  # modèles prévus par generate_env.py
JOURNAL=../data/logs/installation_fond.log
COMPOSE=(docker compose -f docker-compose.yml)
command -v nvidia-smi >/dev/null && COMPOSE+=(-f docker-compose.gpu.yml)   # sans GPU : Ollama sur CPU
export PATH="$HOME/.local/bin:$PATH"
CACHE_FASTEMBED="$HOME/.cache/fastembed"
command -v cygpath >/dev/null && CACHE_FASTEMBED=$(cygpath -m "$CACHE_FASTEMBED")   # Git Bash : chemin Windows

vram_mo() {
  command -v nvidia-smi >/dev/null || { echo 0; return; }
  nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' '
}
valeur() { grep -m1 "^$1=" "$2" | cut -d= -f2-; }
poser() { sed -i "s|^$1=.*|$1=$2|" .env; }
pull() { echo "⬇️  $1"; "${COMPOSE[@]}" exec -T ollama ollama pull "$1"; }

if [[ "${1:-}" == "--fond" ]]; then
  [[ -f "$CIBLES" ]] || { echo "lancer d'abord la phase J1 (sans option)"; exit 1; }
  if [[ "${2:-}" != "--detache" ]]; then
    nohup bash "$PWD/$(basename "$0")" --fond --detache >"$JOURNAL" 2>&1 &
    echo "Téléchargements en arrière-plan (journal : data/logs/installation_fond.log). On peut continuer à travailler."
    exit 0
  fi
  pull "$(valeur MODEL_SMALL "$CIBLES")"
  poser MODEL_SMALL "$(valeur MODEL_SMALL "$CIBLES")"
  echo "⬇️  embeddings + BM25 (J3)"
  uv run --frozen python -c "from helpdesk_ops.kb import precharger_modeles; precharger_modeles()"
  VRAM=$(vram_mo)
  if (( VRAM >= SEUIL_VRAM_MO )); then
    for var in MODEL_AGENT_ALT MODEL_JUDGE; do pull "$(valeur $var "$CIBLES")"; done
    for var in MODEL_AGENT_ALT MODEL_JUDGE; do poser $var "$(valeur $var "$CIBLES")"; done
  else
    echo "VRAM ${VRAM} Mo < ${SEUIL_VRAM_MO} : MODEL_AGENT_ALT et MODEL_JUDGE restent sur $(valeur MODEL_AGENT .env)"
  fi
  uv run --frozen smoke_test.py
  echo "✅ installation complète"
  exit 0
fi

echo "== 1/5 Vérifications"
docker info >/dev/null 2>&1 || { echo "Docker inaccessible : utilisateur dans le groupe docker ?"; exit 1; }
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
command -v uv >/dev/null || curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh

echo "== 2/5 Images Docker et environnement Python, en parallèle"
"${COMPOSE[@]}" pull --quiet & PID_IMAGES=$!
uv sync --frozen & PID_UV=$!
wait $PID_UV || { echo "uv sync en échec"; exit 1; }
wait $PID_IMAGES || { echo "docker compose pull en échec"; exit 1; }

echo "== 3/5 .env (rôles provisoirement sur un seul modèle)"
[[ -f .env ]] || uv run --frozen generate_env.py
mkdir -p ../data/logs
[[ -f "$CIBLES" ]] || grep -E '^MODEL_(AGENT|AGENT_ALT|SMALL|JUDGE)=' .env > "$CIBLES"
grep -q '^FASTEMBED_CACHE_PATH=' .env || {
  echo ""
  echo "# Cache persistant (sinon FastEmbed écrit dans /tmp, vidé au redémarrage)"
  echo "FASTEMBED_CACHE_PATH=$CACHE_FASTEMBED"
} >> .env
AGENT=$(valeur MODEL_AGENT .env)
for var in MODEL_AGENT_ALT MODEL_SMALL MODEL_JUDGE; do poser $var "$AGENT"; done

echo "== 4/5 Stack et modèle $AGENT"
"${COMPOSE[@]}" up -d
pull "$AGENT"

echo "== 5/5 Smoke test (Langfuse : 2-3 min au premier démarrage)"
for _ in $(seq 1 36); do
  curl -fs http://127.0.0.1:3000/api/public/health >/dev/null 2>&1 && break
  sleep 5
done
uv run --frozen smoke_test.py
echo "✅ prêt pour J1. Cet après-midi : bash infrastructure/installer_reseau.sh --fond"
