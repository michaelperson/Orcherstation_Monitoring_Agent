# Serveur LangGraph local (jour 5) : voir serveur_langgraph.sh pour les explications.
Set-Location (Join-Path $PSScriptRoot "..")
$env:LANGGRAPH_CLI_NO_ANALYTICS = "1"
$env:LANGGRAPH_NO_VERSION_CHECK = "true"
$env:PYTHONUTF8 = "1"
uv run --project infrastructure --with "langgraph-cli[inmem]==0.4.37" --with "langgraph-api==0.10.3" --with "langgraph-runtime-inmem==0.30.3" `
    langgraph dev --no-browser --no-reload --host 127.0.0.1 --port 2024 --config langgraph.json
