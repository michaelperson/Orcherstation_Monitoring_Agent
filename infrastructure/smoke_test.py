"""
smoke_test.py : vérifie qu'un poste est prêt pour la formation HelpDesk-Ops.

Contrôles, dans l'ordre (le premier échec arrête le test) :
  1. Variables d'environnement (.env) présentes
  2. Versions des bibliothèques clés (bornes de pyproject.toml)
  3. Ollama joignable et modèles téléchargés
  4. Appel LLM simple + appel avec tool-calling (le cœur de la formation)
  5. Qdrant joignable avec la clé API (et refus sans clé)
  6. Langfuse joignable, clés valides, et une trace de test envoyée

Usage :   uv run smoke_test.py            (depuis le dossier infrastructure/)
Code retour : 0 = tout est vert, 1 = au moins un contrôle en échec (utilisable en CI)
"""

import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Bornes minimales attendues (majeure, mineure) : alignées sur pyproject.toml
MIN_VERSIONS = {
    "langchain": (1, 4),
    "langgraph": (1, 2),
    "langfuse": (4, 15),
    "langchain-ollama": (1, 1),
    "pydantic": (2, 13),
    "qdrant-client": (1, 19),
}

REQUIRED_ENV = [
    "OLLAMA_BASE_URL",
    "MODEL_AGENT",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
]


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")
    sys.exit(1)


def check_env() -> None:
    print("1. Variables d'environnement")
    missing = [v for v in REQUIRED_ENV if not os.getenv(v)]
    if missing:
        fail(f"manquantes : {missing}. As-tu lancé `uv run generate_env.py` ?")
    if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
        fail("LANGFUSE_HOST est déprécié en SDK v4 : utilise LANGFUSE_BASE_URL")
    ok("toutes présentes")


def check_versions() -> None:
    print("2. Versions des bibliothèques")
    for pkg, minimum in MIN_VERSIONS.items():
        installed = version(pkg)
        major_minor = tuple(int(x) for x in installed.split(".")[:2])
        if major_minor < minimum:
            fail(f"{pkg} {installed} < {minimum[0]}.{minimum[1]} : lance `uv sync`")
        ok(f"{pkg} {installed}")


def check_ollama() -> None:
    import httpx

    print("3. Ollama")
    base_url = os.environ["OLLAMA_BASE_URL"]
    try:
        tags = httpx.get(f"{base_url}/api/tags", timeout=5).json()
    except httpx.HTTPError as exc:
        fail(f"injoignable sur {base_url} ({exc}). `docker compose ps` ?")

    installed = {m["name"] for m in tags.get("models", [])}
    ok(f"joignable, {len(installed)} modèle(s) installé(s)")

    for var in ["MODEL_AGENT", "MODEL_AGENT_ALT", "MODEL_SMALL", "MODEL_JUDGE"]:
        name = os.getenv(var)
        if not name:
            continue
        # Ollama ajoute ":latest" quand aucun tag n'est précisé
        candidates = {name, f"{name}:latest"}
        if installed & candidates:
            ok(f"{var} = {name}")
        else:
            fail(f"{var} = {name} absent : lance pull_models.sh / pull_models.ps1")


def check_llm_and_tools() -> None:
    from langchain_core.tools import tool
    from langchain_ollama import ChatOllama

    print("4. LLM + tool-calling")
    llm = ChatOllama(
        model=os.environ["MODEL_AGENT"],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=0,
    )

    start = time.perf_counter()
    reply = llm.invoke("Réponds uniquement par le mot : OK")
    ok(f"réponse simple en {time.perf_counter() - start:.1f}s → {reply.content.strip()[:40]!r}")

    @tool
    def statut_serveur(nom: str) -> str:
        """Retourne le statut d'un serveur de l'inventaire NordTech."""
        return f"{nom}: en ligne"

    start = time.perf_counter()
    reply = llm.bind_tools([statut_serveur]).invoke(
        "Quel est le statut du serveur srv-mail-01 ? Utilise l'outil."
    )
    elapsed = time.perf_counter() - start
    if not reply.tool_calls:
        fail(f"le modèle n'a PAS appelé l'outil ({elapsed:.1f}s). Modèle trop faible ?")
    ok(f"tool-call en {elapsed:.1f}s → {reply.tool_calls[0]['name']}({reply.tool_calls[0]['args']})")


def check_qdrant() -> None:
    import httpx
    from qdrant_client import QdrantClient

    print("5. Qdrant")
    url = os.environ["QDRANT_URL"]
    # Zero Trust : sans clé, le serveur DOIT refuser la requête
    try:
        sans_cle = httpx.get(f"{url}/collections", timeout=5).status_code
    except httpx.HTTPError as exc:
        fail(f"injoignable sur {url} ({exc}). `docker compose ps` ?")
    if sans_cle not in (401, 403):
        fail(f"Qdrant répond sans clé API (HTTP {sans_cle}) : QDRANT__SERVICE__API_KEY non appliquée")
    ok(f"requête sans clé refusée (HTTP {sans_cle})")

    import warnings
    with warnings.catch_warnings():   # « Api key is used with an insecure connection » : attendu en local
        warnings.simplefilter("ignore")
        client = QdrantClient(url=url, api_key=os.environ["QDRANT_API_KEY"], timeout=5)
        try:
            collections = [c.name for c in client.get_collections().collections]
        except Exception as exc:   # 401 : clé du .env différente de celle du conteneur
            fail(f"clé refusée ({type(exc).__name__}). .env régénéré ? → docker compose up -d qdrant")
    ok(f"authentifié, {len(collections)} collection(s) : {collections or '—'}")


def check_langfuse() -> None:
    from langfuse import get_client, propagate_attributes

    print("6. Langfuse")
    langfuse = get_client()
    if not langfuse.auth_check():
        fail("clés refusées ou serveur injoignable (Langfuse met 2-3 min à démarrer)")
    ok(f"authentifié sur {os.environ['LANGFUSE_BASE_URL']}")

    with propagate_attributes(tags=["smoke-test"], session_id="smoke-test"):
        with langfuse.start_as_current_observation(name="smoke-test", as_type="span") as span:
            span.update(output="ok")
            trace_id = langfuse.get_current_trace_id()
    langfuse.flush()
    ok(f"trace envoyée → {langfuse.get_trace_url(trace_id=trace_id)}")


if __name__ == "__main__":
    print("🔎 Smoke test HelpDesk-Ops\n")
    check_env()
    check_versions()
    check_ollama()
    check_llm_and_tools()
    check_qdrant()
    check_langfuse()
    print("\n🎉 Poste prêt pour la formation.")
