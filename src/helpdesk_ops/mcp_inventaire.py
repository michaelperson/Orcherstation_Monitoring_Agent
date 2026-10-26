"""Serveur MCP « inventaire du parc » de NordTech SA (jalon J3), avec FastMCP.

Trois façons de l'utiliser, de la plus simple à la plus réaliste :
- en processus : `MCPAdapter(mcp)` (notebooks, tests) ;
- processus séparé, stdio : `MCPAdapter(transport_stdio())` (dans un script, `MCPAdapter(Path(__file__))` suffit ;
  dans Jupyter sous Windows, le stderr du noyau n'a pas de descripteur de fichier : il faut un `log_file`) ;
- serveur HTTP : `python -m helpdesk_ops.mcp_inventaire --http 8765` puis `MCPAdapter("http://127.0.0.1:8765/mcp")`.

Les **annotations** (`readOnlyHint`, `destructiveHint`, `idempotentHint`) décrivent chaque outil au
client. Ce sont des **déclarations du serveur**, pas des garanties : un serveur malveillant peut
mentir. Le client décide de sa liste blanche (`filtrer_outils`), OWASP ASI04.
Données fictives ; utilisateurs pseudonymisés.
"""
import sys
from pathlib import Path

from fastmcp import FastMCP

POSTES = {
    "PC-0142": {"service": "Comptabilité", "utilisateur": "collab-3fa91c", "modele": "portable 14 pouces", "os": "Windows 11 24H2", "achat": "2021-03", "statut": "en service"},
    "PC-0157": {"service": "Comptabilité", "utilisateur": "collab-8b20d4", "modele": "portable 14 pouces", "os": "Windows 11 24H2", "achat": "2023-09", "statut": "en service"},
    "PC-0203": {"service": "Logistique", "utilisateur": "collab-71e0aa", "modele": "fixe", "os": "Windows 10 22H2", "achat": "2019-11", "statut": "en service"},
    "PC-0219": {"service": "Logistique", "utilisateur": "collab-c45f12", "modele": "portable 15 pouces", "os": "Windows 11 24H2", "achat": "2024-02", "statut": "en réparation"},
    "PC-0311": {"service": "Direction", "utilisateur": "collab-0d9e77", "modele": "portable 13 pouces", "os": "Windows 11 24H2", "achat": "2025-05", "statut": "en service"},
    "PC-0402": {"service": "Help-desk", "utilisateur": "collab-5aa3b8", "modele": "fixe", "os": "Windows 11 24H2", "achat": "2022-06", "statut": "en service"},
}

INTERVENTIONS = {
    "PC-0142": ["2026-09-12 : écran noir, station d'accueil remplacée", "2026-10-02 : lenteurs, nettoyage du disque"],
    "PC-0203": ["2025-12-01 : disque dur remplacé", "2026-06-18 : mise à jour bloquée (0x80070005)", "2026-10-09 : lenteurs persistantes"],
    "PC-0219": ["2026-10-14 : clavier défectueux, envoyé en réparation"],
}

mcp = FastMCP("inventaire-parc", instructions="Inventaire fictif des postes de travail de NordTech SA.")


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def lister_postes(service: str) -> list[dict]:
    """Liste les postes de travail d'un service (ex. 'Comptabilité', 'Logistique') avec leur statut."""
    return [{"poste": nom, **{k: v for k, v in p.items() if k != "utilisateur"}}
            for nom, p in POSTES.items() if p["service"].lower() == service.strip().lower()]


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def detail_poste(poste: str) -> dict:
    """Fiche d'un poste (ex. 'PC-0203') : service, modèle, système, date d'achat, statut, utilisateur pseudonymisé."""
    fiche = POSTES.get(poste.strip().upper())
    return {"poste": poste.upper(), **fiche} if fiche else {"erreur": f"poste inconnu : {poste}"}


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def historique_interventions(poste: str) -> list[str]:
    """Historique des interventions du help-desk sur un poste (ex. 'PC-0203'), du plus ancien au plus récent."""
    return INTERVENTIONS.get(poste.strip().upper(), [])


@mcp.tool(annotations={"destructiveHint": True, "idempotentHint": False, "readOnlyHint": False})
def reinitialiser_poste(poste: str, motif: str) -> str:
    """Réinitialise complètement un poste (efface toutes les données locales). Action irréversible."""
    # Simulation : rien n'est effacé. Dans un vrai parc, cet outil ne devrait JAMAIS être exposé à un agent N1.
    return f"réinitialisation de {poste} planifiée (motif : {motif})"


def transport_stdio(log_file: Path | None = None):
    """Transport stdio vers ce serveur, lancé avec le Python courant ; son stderr va dans un journal.

    Sans `log_file`, fastmcp transmet `sys.stderr` au sous-processus : dans un notebook Jupyter sous
    Windows, cela échoue (« Client failed to connect: fileno », constaté en préparant le cours).
    Le journal sert aussi d'audit : ce que le serveur a fait, hors de la console.
    """
    from fastmcp.client.transports import PythonStdioTransport
    if log_file is None:
        from helpdesk_ops.config import trouver_env
        dossier = trouver_env().parent.parent / "data" / "logs"
        dossier.mkdir(parents=True, exist_ok=True)
        if not (dossier / ".gitignore").exists():
            (dossier / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
        log_file = dossier / "mcp_inventaire.log"
    return PythonStdioTransport(script_path=Path(__file__), python_cmd=sys.executable, log_file=log_file)


def annotations(outil) -> dict:
    """Annotations MCP d'un outil LangChain produit par MCPAdapter (vide si absentes)."""
    return ((getattr(outil, "metadata", None) or {}).get("mcp", {}).get("tool", {}).get("annotations") or {})


def filtrer_outils(outils: list, *, autorises: set[str] | None = None, refuser_destructifs: bool = True) -> list:
    """Liste blanche côté client : par nom (si fournie) ET refus des outils qui se déclarent destructifs
    ou ne se déclarent pas en lecture seule. Ne jamais faire confiance à la seule bonne foi du serveur."""
    retenus = []
    for outil in outils:
        a = annotations(outil)
        if autorises is not None and outil.name not in autorises:
            continue
        if refuser_destructifs and (a.get("destructive_hint") or not a.get("read_only_hint")):
            continue
        retenus.append(outil)
    return retenus


if __name__ == "__main__":
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--http") + 1])
        mcp.run(transport="http", host="127.0.0.1", port=port)   # jamais 0.0.0.0 : pas d'exposition réseau
    else:
        mcp.run()   # stdio
