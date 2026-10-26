#!/usr/bin/env bash
# pull_models.sh : pré-télécharge les modèles dans le conteneur Ollama.
# À lancer AVANT la formation (≈ 15 Go au total) : le Wi-Fi de salle ne suffira pas.
set -euo pipefail
cd "$(dirname "$0")"

# Lecture des noms de modèles depuis .env (une seule source de vérité)
set -a; source .env; set +a

for model in "$MODEL_AGENT" "$MODEL_AGENT_ALT" "$MODEL_SMALL" "$MODEL_JUDGE"; do
  echo "⬇️  $model"
  docker compose exec -T ollama ollama pull "$model"
done
docker compose exec -T ollama ollama list

# Embeddings (HF multilingue) et BM25 français pour le RAG du jour 3 : téléchargés une fois, puis hors ligne
echo "⬇️  embeddings + BM25 (Qdrant/bm25)"
uv run python -c "from helpdesk_ops.kb import precharger_modeles; precharger_modeles(); print('✅ modèles d embeddings en cache')"
