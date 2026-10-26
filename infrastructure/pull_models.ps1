# pull_models.ps1 : version Windows (poste de préparation) de pull_models.sh
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Lecture de .env : lignes CLE=VALEUR, commentaires ignorés
$envVars = @{}
Get-Content .env | Where-Object { $_ -match '^\s*[A-Z_]+=.*' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    $envVars[$k.Trim()] = $v.Trim()
}

$models = @($envVars["MODEL_AGENT"], $envVars["MODEL_AGENT_ALT"], $envVars["MODEL_SMALL"], $envVars["MODEL_JUDGE"]) | Select-Object -Unique
foreach ($m in $models) {
    Write-Host "⬇️  $m"
    docker compose exec -T ollama ollama pull $m
}
docker compose exec -T ollama ollama list

# Embeddings (HF multilingue) et BM25 français pour le RAG du jour 3 : téléchargés une fois, puis hors ligne
Write-Host "⬇️  embeddings + BM25 (Qdrant/bm25)"
uv run python -c "from helpdesk_ops.kb import precharger_modeles; precharger_modeles(); print('modeles d embeddings en cache')"
