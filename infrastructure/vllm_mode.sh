#!/usr/bin/env bash
# vllm_mode.sh : bascule les serveurs vLLM. Sur 24 Go, les trois modèles ne tiennent pas ensemble.
#
#   bash infrastructure/vllm_mode.sh agents   # J1 → J4 matin : granite4.1:8b (agent) + granite4.1:3b (small)
#   bash infrastructure/vllm_mode.sh juge     # J4 : gemma4:12b seul (juge J4-04, 3ᵉ modèle d'Ex4.1)
#   bash infrastructure/vllm_mode.sh          # affiche l'état des serveurs
#
# Une bascule prend 1 à 3 min (chargement des poids, graphes CUDA) : la faire pendant une explication.
set -euo pipefail
cd "$(dirname "$0")"

# Comme helpdesk_ops.config : un .env sans LLM_BACKEND (antérieur au 27/10) = Ollama
if ! grep -q '^LLM_BACKEND=vllm' .env 2>/dev/null; then
  echo "Moteur Ollama : rien à basculer, il charge les modèles à la demande."
  exit 0
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.vllm.yml --profile juge)
ATTENTE=(--wait --wait-timeout 900)    # 1er démarrage d'un serveur : compilation, jusqu'à ≈ 10 min

case "${1:-}" in
  agents)
    "${COMPOSE[@]}" stop vllm-juge
    "${COMPOSE[@]}" up -d "${ATTENTE[@]}" vllm-agent vllm-small
    echo "✅ mode agents : granite4.1:8b (:8001) + granite4.1:3b (:8002)"
    ;;
  juge)
    "${COMPOSE[@]}" stop vllm-small vllm-agent
    "${COMPOSE[@]}" up -d "${ATTENTE[@]}" vllm-juge
    echo "✅ mode juge : gemma4:12b (:8003). Retour : bash infrastructure/vllm_mode.sh agents"
    ;;
  "")
    "${COMPOSE[@]}" ps vllm-agent vllm-small vllm-juge
    ;;
  *)
    echo "usage : $0 [agents|juge]"
    exit 2
    ;;
esac
