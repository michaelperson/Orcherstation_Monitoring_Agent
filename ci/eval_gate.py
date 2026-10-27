"""Gate d'évaluation : les experiments de J4 (et le jeu red-team de J5) deviennent un test qui peut échouer.

    uv run --project infrastructure python ci/eval_gate.py                 # tout
    uv run --project infrastructure python ci/eval_gate.py --rapide        # garde-fou + routage seulement

Code de sortie 1 si un score passe sous son seuil (ci/seuils.json) : le pipeline s'arrête, rien n'est déployé.
Les runs sont enregistrés dans Langfuse (dataset « helpdesk-ops-eval ») : le rapport donne les chiffres, Langfuse
le détail cas par cas. Nécessite la stack locale (vLLM ou Ollama, Qdrant, Langfuse) : en CI, un runner auto-hébergé.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def version_code() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=RACINE,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "hors-git"


def garde_fou(decider) -> dict:
    """Jeu red-team : taux de décisions justes, et liste des cas ratés."""
    cas = json.loads((RACINE / "data" / "eval" / "redteam.json").read_text(encoding="utf-8"))["cas"]
    rates = [c["id"] for c in cas if decider(c["question"]) != c["attendu"]]
    return {"garde_fou_juste": round(1 - len(rates) / len(cas), 3), "garde_fou_rates": rates}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows (cp1252) : ≥, ✅, ❌
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--seuils", type=Path, default=RACINE / "ci" / "seuils.json")
    p.add_argument("--rapport", type=Path, default=RACINE / "ci" / "rapport_gate.md")
    p.add_argument("--rapide", action="store_true", help="sans l'experiment d'appel d'outils (le plus long)")
    p.add_argument("--scores", type=Path, help="réutiliser des scores déjà mesurés (JSON) : on ne juge que les seuils")
    args = p.parse_args()
    fichier_scores = RACINE / "ci" / "scores_gate.json"
    seuils = json.loads(args.seuils.read_text(encoding="utf-8"))
    debut = time.perf_counter()
    if args.scores:
        scores = json.loads(args.scores.read_text(encoding="utf-8"))
        return juger(scores, seuils, args.rapport, debut)

    from helpdesk_ops import evaluation as ev
    from helpdesk_ops.config import creer_llm
    from helpdesk_ops.observabilite import init_observabilite
    from helpdesk_ops.securite import creer_garde_fou

    langfuse, _ = init_observabilite()
    llm = creer_llm("agent")
    modele = getattr(llm, "model", "?")
    version = version_code()
    decider = creer_garde_fou(llm)

    scores = garde_fou(decider)
    dataset = langfuse.get_dataset(ev.synchroniser_dataset(langfuse, ev.chemin_dataset()))   # renvoie le NOM du dataset
    meta = {"modele": modele, "version_code": version, "origine": "ci"}
    routage = dataset.run_experiment(name="helpdesk-routage", run_name=f"gate · {version} · {modele}",
                                     task=ev.tache_routage(llm, decider=decider), evaluators=[ev.ev_routage, ev.ev_latence],
                                     run_evaluators=[ev.ev_moyennes], max_concurrency=1, metadata=meta)
    scores.update(ev.resume(routage))
    if not args.rapide:
        outils = dataset.run_experiment(name="helpdesk-outils", run_name=f"gate · {version} · {modele}",
                                        task=ev.tache_outil(llm), evaluators=[ev.ev_outil_valide, ev.ev_outil_attendu, ev.ev_latence],
                                        run_evaluators=[ev.ev_moyennes], max_concurrency=1, metadata=meta)
        scores.update({k: v for k, v in ev.resume(outils).items() if k.startswith("outil")})
    langfuse.flush()
    scores.update({"modele": modele, "version_code": version})
    fichier_scores.write_text(json.dumps(scores, ensure_ascii=False, indent=1), encoding="utf-8")
    return juger(scores, seuils, args.rapport, debut)


def juger(scores: dict, seuils: dict, chemin_rapport: Path, debut: float) -> int:
    """Compare chaque score à son seuil, écrit le rapport (et le résumé GitHub), renvoie le code de sortie."""
    lignes, echecs = [], []
    for nom, seuil in seuils.items():
        if nom.startswith("_"):
            continue
        valeur = scores.get(nom)
        if valeur is None:
            statut = "non mesuré"
        else:
            ok = valeur >= seuil["min"] if "min" in seuil else valeur <= seuil["max"]
            statut = "✅" if ok else "❌"
            if not ok:
                echecs.append(nom)
        borne = f"≥ {seuil['min']}" if "min" in seuil else f"≤ {seuil['max']}"
        lignes.append(f"| `{nom}` | {valeur if valeur is not None else '—'} | {borne} | {statut} |")

    rapport = "\n".join([
        f"## Gate d'évaluation HelpDesk-Ops · {'ÉCHEC' if echecs else 'OK'}", "",
        f"Code `{scores.get('version_code', '?')}` · modèle `{scores.get('modele', '?')}` · {round(time.perf_counter() - debut)} s", "",
        "| Score | Mesuré | Seuil | |", "|---|---|---|---|", *lignes, "",
        f"Garde-fou, cas ratés : {', '.join(scores.get('garde_fou_rates', [])) or 'aucun'}",
        "Détail cas par cas : Langfuse → Datasets → helpdesk-ops-eval → Runs.", ""])
    chemin_rapport.write_text(rapport, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):   # GitHub Actions affiche ce fichier dans le résumé du run
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(rapport)
    print(rapport)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
