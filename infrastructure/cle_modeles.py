"""cle_modeles.py : les modèles du J1 sur clé USB, pour soulager le réseau de la salle.

    # Formateur, la veille (réseau requis une fois) : ≈ 10 Go, clé de 16 Go en exFAT ou NTFS
    uv run cle_modeles.py fabriquer --dest E:\\helpdesk-modeles
    uv run cle_modeles.py fabriquer --dest E:\\helpdesk-modeles --tout     # + 3b et gemma4 : ≈ 25 Go

    # Poste de la salle : appelé par installer_reseau.sh --cle /media/$USER/<CLE>/helpdesk-modeles
    uv run cle_modeles.py importer --cle /media/$USER/<CLE>/helpdesk-modeles
    uv run cle_modeles.py verifier --cle /media/$USER/<CLE>/helpdesk-modeles

Sur la clé, les caches Hugging Face sont copiés SANS liens symboliques (snapshots/ et refs/ seulement) :
exFAT n'en stocke pas, et Hugging Face lit très bien cette disposition hors ligne.
Les poids vLLM vont dans le volume Docker vllm_cache (copie faite par installer_reseau.sh) ;
les embeddings vont dans les caches de l'utilisateur (~/.cache/huggingface, FASTEMBED_CACHE_PATH).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

# Dépôts servis par vLLM (mêmes valeurs par défaut que docker-compose.vllm.yml et installer_reseau.sh)
MODELES_J1 = ["ibm-granite/granite-4.1-8b-fp8"]
MODELES_FOND = ["ibm-granite/granite-4.1-3b-fp8", "google/gemma-4-12B-it-qat-w4a16-ct"]
EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MANIFESTE = "MANIFESTE.json"


def dossier_cache(depot: str) -> str:
    return "models--" + depot.replace("/", "--")


def copier_sans_liens(source: Path, dest: Path) -> None:
    """Copie refs/ et snapshots/ d'un modèle du cache HF en remplaçant les liens par les fichiers."""
    for partie in ("refs", "snapshots"):
        if (source / partie).exists():
            shutil.copytree(source / partie, dest / partie, symlinks=False, dirs_exist_ok=True)


def empreinte(fichier: Path) -> str:
    h = hashlib.sha256()
    with fichier.open("rb") as f:
        for bloc in iter(lambda: f.read(8 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def fichiers(racine: Path) -> list[Path]:
    return sorted(p for p in racine.rglob("*") if p.is_file() and p.name != MANIFESTE)


def fabriquer(dest: Path, tout: bool) -> None:
    from huggingface_hub import snapshot_download
    from huggingface_hub.constants import HF_HUB_CACHE

    depots = MODELES_J1 + (MODELES_FOND if tout else [])
    (dest / "vllm" / "hub").mkdir(parents=True, exist_ok=True)
    for depot in depots:
        print(f"⬇️  {depot}")
        snapshot_download(depot)                                    # cache HF du poste formateur
        copier_sans_liens(Path(HF_HUB_CACHE) / dossier_cache(depot), dest / "vllm" / "hub" / dossier_cache(depot))

    print(f"⬇️  embeddings ({EMBEDDINGS}) et BM25")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from helpdesk_ops.kb import precharger_modeles
    precharger_modeles()                                            # remplit les caches HF et FastEmbed
    copier_sans_liens(Path(HF_HUB_CACHE) / dossier_cache(EMBEDDINGS),
                      dest / "embeddings" / "huggingface" / "hub" / dossier_cache(EMBEDDINGS))
    fastembed = Path(os.environ.get("FASTEMBED_CACHE_PATH") or Path.home() / ".cache" / "fastembed")
    shutil.copytree(fastembed, dest / "embeddings" / "fastembed", symlinks=False, dirs_exist_ok=True)

    print("🔏 empreintes SHA-256 (quelques minutes)")
    manifeste = {"depots_vllm": depots, "embeddings": EMBEDDINGS,
                 "fichiers": {str(p.relative_to(dest).as_posix()): [p.stat().st_size, empreinte(p)] for p in fichiers(dest)}}
    (dest / MANIFESTE).write_text(json.dumps(manifeste, indent=1, ensure_ascii=False), encoding="utf-8")
    taille = sum(t for t, _ in manifeste["fichiers"].values())
    print(f"✅ {dest} : {len(manifeste['fichiers'])} fichiers, {taille / 1e9:.1f} Go")
    plus_gros = max(t for t, _ in manifeste["fichiers"].values())
    if plus_gros >= 4 * 2**30:
        print(f"⚠️  un fichier fait {plus_gros / 1e9:.1f} Go : la clé doit être en exFAT ou NTFS (FAT32 refuse > 4 Go)")


def verifier(cle: Path) -> bool:
    manifeste = json.loads((cle / MANIFESTE).read_text(encoding="utf-8"))
    erreurs = 0
    for chemin, (taille, sha) in manifeste["fichiers"].items():
        p = cle / chemin
        if not p.exists() or p.stat().st_size != taille or empreinte(p) != sha:
            print(f"❌ {chemin}")
            erreurs += 1
    print(f"{'✅' if not erreurs else '❌'} {len(manifeste['fichiers']) - erreurs}/{len(manifeste['fichiers'])} fichiers intacts")
    return erreurs == 0


def importer(cle: Path) -> None:
    """Embeddings vers les caches de l'utilisateur (les poids vLLM sont copiés par installer_reseau.sh)."""
    from huggingface_hub.constants import HF_HUB_CACHE

    source = cle / "embeddings" / "huggingface" / "hub"
    for modele in source.iterdir():
        cible = Path(HF_HUB_CACHE) / modele.name
        if (cible / "snapshots").exists():
            print(f"= {modele.name} déjà en cache")
            continue
        shutil.copytree(modele, cible, dirs_exist_ok=True)
        print(f"✅ {modele.name} → {cible}")
    fastembed = Path(os.environ.get("FASTEMBED_CACHE_PATH") or Path.home() / ".cache" / "fastembed")
    shutil.copytree(cle / "embeddings" / "fastembed", fastembed, dirs_exist_ok=True)
    print(f"✅ BM25 → {fastembed}")


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = parser.add_subparsers(dest="action", required=True)
    f = sous.add_parser("fabriquer", help="formateur : télécharger les modèles et remplir la clé")
    f.add_argument("--dest", type=Path, required=True)
    f.add_argument("--tout", action="store_true", help="aussi granite 3b et gemma4 (--fond)")
    for nom in ("importer", "verifier"):
        sous.add_parser(nom).add_argument("--cle", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "fabriquer":
        fabriquer(args.dest, args.tout)
    elif args.action == "verifier":
        sys.exit(0 if verifier(args.cle) else 1)
    else:
        importer(args.cle)
