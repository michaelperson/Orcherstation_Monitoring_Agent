#!/usr/bin/env bash
# Serveur LangGraph local (jour 5) : le jalon J5 servi par l'API REST LangGraph, sur 127.0.0.1:2024.
# langgraph-cli n'est PAS dans uv.lock (il ferait descendre protobuf et grpcio) : il est chargé à la demande.
# Vérifié le 22/10/2026 dans langgraph-cli 0.4.37 / langgraph-api 0.10.3 :
#   - le CLI envoie une analytique d'usage (Supabase) sauf si LANGGRAPH_CLI_NO_ANALYTICS=1 ;
#   - le serveur interroge pypi.org au démarrage sauf si LANGGRAPH_NO_VERSION_CHECK=true ;
#   - sans clé de licence, le serveur n'envoie pas de métadonnées ;
#   - sous Windows, le .env est lu en cp1252 sans PYTHONUTF8=1 (UnicodeDecodeError).
# Pas de LangGraph Studio (interface hébergée sur smith.langchain.com) : on utilise l'API et Streamlit.
set -euo pipefail
cd "$(dirname "$0")/.."
export LANGGRAPH_CLI_NO_ANALYTICS=1 LANGGRAPH_NO_VERSION_CHECK=true PYTHONUTF8=1
exec uv run --project infrastructure --with "langgraph-cli[inmem]==0.4.37" --with "langgraph-api==0.10.3" --with "langgraph-runtime-inmem==0.30.3" \
    langgraph dev --no-browser --no-reload --host 127.0.0.1 --port 2024 --config langgraph.json
