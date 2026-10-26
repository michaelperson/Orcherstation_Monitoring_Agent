"""
generate_env.py : génère le fichier .env de la stack HelpDesk-Ops.

Pourquoi un script plutôt qu'un .env copié à la main ?
  - Chaque poste reçoit des secrets ALÉATOIRES (pas de "postgres:postgres" en salle).
  - Les clés du projet Langfuse sont PRÉ-PROVISIONNÉES (LANGFUSE_INIT_*) :
    au premier démarrage, Langfuse crée l'organisation, le projet, l'utilisateur
    et les clés API. Aucun clic manuel dans l'UI, donc 0 minute perdue le jour J.
  - Les mêmes clés sont écrites pour le SDK Python (LANGFUSE_PUBLIC_KEY /
    LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL), lu par les notebooks.
  - Qdrant est protégé par une clé API aléatoire (QDRANT_API_KEY), même en local :
    principe Zero Trust, aucun service sans authentification.

Usage :
    uv run generate_env.py            # crée .env (refuse d'écraser un .env existant)
    uv run generate_env.py --force    # régénère (⚠️ à faire AVANT le 1er `docker compose up`,
                                      #   sinon Postgres garde l'ancien mot de passe)

Aucune dépendance externe : bibliothèque standard uniquement.
"""

import argparse
import secrets
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def hex_secret(nbytes: int = 16) -> str:
    """Secret hexadécimal : sûr dans une URL, une ligne de commande ou du YAML."""
    return secrets.token_hex(nbytes)


def build_env() -> tuple[str, str]:
    pg_password = hex_secret()
    ch_password = hex_secret()
    redis_password = hex_secret()
    minio_password = hex_secret()  # MinIO exige ≥ 8 caractères : 32 ici
    user_password = secrets.token_urlsafe(12)

    public_key = f"pk-lf-{hex_secret(12)}"
    secret_key = f"sk-lf-{hex_secret(16)}"

    lines = [
        "# ---------------------------------------------------------------",
        "# Généré par generate_env.py. NE PAS COMMITER (voir .gitignore)",
        "# ---------------------------------------------------------------",
        "",
        "# ===== Modèles Ollama (lus par les notebooks) =====",
        "OLLAMA_BASE_URL=http://127.0.0.1:11434",   # 127.0.0.1 et non localhost : voir README (IPv6 sous Windows)
        "# Préparation sans GPU : mettre MODEL_AGENT=granite4.1:3b pour itérer vite",
        "MODEL_AGENT=granite4.1:8b",
        "MODEL_AGENT_ALT=gemma4:12b",
        "MODEL_SMALL=granite4.1:3b",
        "MODEL_JUDGE=gemma4:12b",
        "EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "# Dimension des vecteurs du modèle ci-dessus : à reporter dans la collection Qdrant",
        "EMBEDDING_DIM=384",
        "",
        "# ===== Qdrant (base vectorielle) =====",
        "QDRANT_URL=http://127.0.0.1:6333",
        f"QDRANT_API_KEY={hex_secret(24)}",
        "QDRANT_COLLECTION=kb_nordtech",
        "",
        "# ===== Zéro flux sortant (J3) =====",
        "# FastMCP vérifie sinon les mises à jour sur PyPI à chaque démarrage de serveur",
        "FASTMCP_CHECK_FOR_UPDATES=off",
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "HF_HUB_DISABLE_TELEMETRY=1",
        "",
        "# ===== SDK Python Langfuse v4 (lus par les notebooks) =====",
        "# ⚠️ v4 : LANGFUSE_BASE_URL remplace LANGFUSE_HOST (déprécié)",
        "LANGFUSE_BASE_URL=http://localhost:3000",
        f"LANGFUSE_PUBLIC_KEY={public_key}",
        f"LANGFUSE_SECRET_KEY={secret_key}",
        "LANGFUSE_TRACING_ENVIRONMENT=formation",
        "",
        "# ===== Initialisation automatique de Langfuse (headless) =====",
        "LANGFUSE_INIT_ORG_ID=nordtech",
        "LANGFUSE_INIT_ORG_NAME=NordTech-SA-fictif",
        "LANGFUSE_INIT_PROJECT_ID=helpdesk-ops",
        "LANGFUSE_INIT_PROJECT_NAME=HelpDesk-Ops",
        f"LANGFUSE_INIT_PROJECT_PUBLIC_KEY={public_key}",
        f"LANGFUSE_INIT_PROJECT_SECRET_KEY={secret_key}",
        "LANGFUSE_INIT_USER_EMAIL=apprenant@helpdesk.local",
        "LANGFUSE_INIT_USER_NAME=Apprenant",
        f"LANGFUSE_INIT_USER_PASSWORD={user_password}",
        "",
        "# ===== Secrets internes Langfuse =====",
        f"NEXTAUTH_SECRET={hex_secret(32)}",
        f"SALT={hex_secret(16)}",
        "# ENCRYPTION_KEY : 64 caractères hex exigés par Langfuse",
        f"ENCRYPTION_KEY={hex_secret(32)}",
        "TELEMETRY_ENABLED=false",
        "",
        f"POSTGRES_PASSWORD={pg_password}",
        f"DATABASE_URL=postgresql://postgres:{pg_password}@postgres:5432/postgres",
        f"CLICKHOUSE_PASSWORD={ch_password}",
        f"REDIS_AUTH={redis_password}",
        f"MINIO_ROOT_PASSWORD={minio_password}",
        f"LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY={minio_password}",
        f"LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY={minio_password}",
        f"LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY={minio_password}",
        "",
    ]
    return "\n".join(lines), user_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère le .env de la stack HelpDesk-Ops")
    parser.add_argument("--force", action="store_true", help="écrase un .env existant")
    args = parser.parse_args()

    if ENV_PATH.exists() and not args.force:
        raise SystemExit(f"❌ {ENV_PATH} existe déjà. Utilise --force pour le régénérer.")

    content, user_password = build_env()
    ENV_PATH.write_text(content, encoding="utf-8")

    print(f"✅ {ENV_PATH} créé.")
    print("   UI Langfuse : http://localhost:3000")
    print("   Login       : apprenant@helpdesk.local")
    print(f"   Mot de passe: {user_password}   (aussi dans .env)")
    print("   Qdrant      : http://localhost:6333/dashboard  (clé : QDRANT_API_KEY dans .env)")


if __name__ == "__main__":
    main()
