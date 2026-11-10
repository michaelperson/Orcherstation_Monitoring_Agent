"""Génère le kit d'autonomie (kit_autonomie/) à partir de ses sources (kit_autonomie/_sources/).

Depuis la racine du dépôt :
    uv run --no-project --with markdown python kit_autonomie/_sources/build_kit.py            # pages HTML
    uv run --no-project --with markdown python kit_autonomie/_sources/build_kit.py --pdf      # + PDF du support (Edge ou Chrome)
    uv run --no-project --with markdown python kit_autonomie/_sources/build_kit.py --slides   # + slides en PDF (Windows + PowerPoint)
    uv run --no-project --with markdown python kit_autonomie/_sources/build_kit.py --zip      # + dist/HelpDesk-Ops_kit_autonomie.zip

Les sources à modifier : _sources/support/*.md (le support, un fichier par chapitre), _sources/contenu/**.md (les
guides), _sources/build_guide.py (le guide interactif), _sources/portail.html (la page d'accueil).
Les slides (07_Slides_formation/) ne sont pas dans Git (décision du 26/10) : seulement dans le zip.
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # consoles Windows en cp1252

import markdown

SRC = Path(__file__).resolve().parent
KIT = SRC.parent
RACINE = KIT.parent
ASSETS = KIT / "_assets"
SUPPORTS = RACINE / "supports"                       # decks du formateur (hors Git)

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--pdf", action="store_true", help="imprimer le support consolidé en PDF")
parser.add_argument("--slides", action="store_true", help="exporter les slides en PDF (PowerPoint)")
parser.add_argument("--zip", action="store_true", help="fabriquer le zip à distribuer")
args = parser.parse_args()

# --------------------------------------------------------------------------- mise en page commune
CSS = r"""
:root{--bg:#f7f6f2;--surface:#fff;--surface2:#f0eee8;--text:#1d1d1f;--muted:#5d5d63;--border:#dedbd2;--accent:#1f5fbf;
--accent-soft:#e3ecfa;--code-bg:#1e1f24;--code-text:#e8e6e1}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141518;--surface:#1c1d21;--surface2:#24262b;--text:#ecebe8;
--muted:#a3a3aa;--border:#33353b;--accent:#7aa7ff;--accent-soft:#1d2a44;--code-bg:#0f1013}}
:root[data-theme="dark"]{--bg:#141518;--surface:#1c1d21;--surface2:#24262b;--text:#ecebe8;--muted:#a3a3aa;--border:#33353b;
--accent:#7aa7ff;--accent-soft:#1d2a44;--code-bg:#0f1013}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.page{display:grid;grid-template-columns:280px minmax(0,1fr);max-width:1300px;margin:0 auto}
nav.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;overflow-x:hidden;padding:24px 14px;border-right:1px solid var(--border);font-size:.88rem}
nav.toc ul{list-style:none;padding-left:12px;margin:0}nav.toc>ul{padding-left:0}
nav.toc a{color:var(--text);text-decoration:none;display:block;padding:2px 6px;border-radius:6px}
nav.toc a:hover{background:var(--surface2)}
nav.toc .retour{display:block;margin-bottom:12px;color:var(--accent)}
main{padding:32px 40px 80px;min-width:0}
h1{font-size:2rem;line-height:1.2;margin:1.6em 0 .5em;padding-top:.6em;border-top:3px solid var(--accent)}
h1:first-child{margin-top:0;border-top:0;padding-top:0}
h2{font-size:1.4rem;margin:1.8em 0 .5em;line-height:1.3}h3{font-size:1.12rem;margin:1.4em 0 .4em}
a{color:var(--accent)}
code{font-family:ui-monospace,"Cascadia Code",Consolas,monospace;font-size:.9em}
:not(pre)>code{background:var(--surface2);padding:.05em .35em;border-radius:4px}
pre{background:var(--code-bg);color:var(--code-text);padding:14px 16px;border-radius:8px;overflow:auto;font-size:.84rem;line-height:1.5}
pre.mermaid{background:var(--surface);color:var(--text);border:1px solid var(--border);text-align:center}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.92rem;display:block;overflow-x:auto}
th,td{border:1px solid var(--border);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--surface2)}
blockquote{margin:12px 0;padding:10px 16px;background:var(--accent-soft);border-left:4px solid var(--accent);border-radius:0 8px 8px 0}
blockquote p{margin:.3em 0}
details{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 16px;margin:12px 0}
summary{cursor:pointer;font-weight:600}
li{margin:3px 0}
.theme{position:fixed;top:12px;right:14px;font:inherit;border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:8px;padding:4px 10px;cursor:pointer}
@media (max-width:900px){.page{grid-template-columns:1fr}nav.toc{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--border)}main{padding:20px 16px 60px}}
@media print{nav.toc,.theme{display:none}.page{display:block}main{padding:0}h1{page-break-before:always;border-top:0}
h1:first-child{page-break-before:avoid}pre{white-space:pre-wrap;word-break:break-word}details{border:0;padding:0}
pre,blockquote,.mermaid{page-break-inside:avoid}body{background:#fff;color:#000;font-size:11pt}}
"""

JS = r"""
<script src="../_assets/mermaid.min.js"></script>
<script>
const racine = document.documentElement;
const sombre = () => racine.dataset.theme ? racine.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
try { const t = localStorage.getItem("kit-theme"); if (t) racine.dataset.theme = t; } catch (e) {}
if (location.search.includes("print")) racine.dataset.theme = "light";
document.querySelector(".theme").addEventListener("click", () => {
  racine.dataset.theme = sombre() ? "light" : "dark";
  try { localStorage.setItem("kit-theme", racine.dataset.theme); } catch (e) {}
  location.reload();
});
if (location.search.includes("print")) document.querySelectorAll("details").forEach(d => d.open = true);
window.addEventListener("beforeprint", () => document.querySelectorAll("details").forEach(d => d.open = true));
if (window.mermaid) { mermaid.initialize({ startOnLoad: true, theme: sombre() ? "dark" : "default", securityLevel: "strict" }); }
</script>
"""


def md_vers_html(texte: str, titre: str, sortie: Path) -> None:
    """Markdown -> page HTML autonome (sommaire, thème clair/sombre, schémas Mermaid hors ligne)."""
    blocs = []

    def mettre_de_cote(m):
        blocs.append(m.group(1))
        return f"\n\nMERMAIDBLOC{len(blocs) - 1}FIN\n\n"
    texte = re.sub(r"```mermaid\n(.*?)```", mettre_de_cote, texte, flags=re.S)
    texte = texte.replace("<details>", '<details markdown="1">')
    texte = re.sub(r"^# (Chapitre (\d+) .*)$", r"# \1 {#chapitre-\2}", texte, flags=re.M)   # ancres stables
    texte = re.sub(r"^# (Introduction .*)$", r"# \1 {#introduction}", texte, flags=re.M)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "attr_list", "md_in_html", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "1-2"}})
    corps = md.convert(texte)
    for i, b in enumerate(blocs):
        corps = corps.replace(f"<p>MERMAIDBLOC{i}FIN</p>", f'<pre class="mermaid">{html.escape(b)}</pre>')
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(titre)}</title>
<style>{CSS}</style></head><body><button class="theme" type="button" title="Clair / sombre">◐</button>
<div class="page"><nav class="toc"><a class="retour" href="../00_COMMENCEZ_ICI.html">← Accueil du kit</a>{md.toc}</nav>
<main>{corps}</main></div>{JS}</body></html>"""
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(page, encoding="utf-8")
    print(f"html : {sortie.relative_to(RACINE)}")


# --------------------------------------------------------------------------- 1. pages
ASSETS.mkdir(exist_ok=True)
if not (ASSETS / "mermaid.min.js").exists():          # une fois : ensuite tout fonctionne hors ligne
    import urllib.request
    urllib.request.urlretrieve("https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js", ASSETS / "mermaid.min.js")

support = "\n\n".join(c.read_text(encoding="utf-8") for c in sorted((SRC / "support").glob("*.md")))
(KIT / "03_Support_consolide").mkdir(exist_ok=True)
(KIT / "03_Support_consolide" / "Support_consolide.md").write_text(support, encoding="utf-8")   # pour l'IA ou un éditeur
md_vers_html(support, "Support consolidé", KIT / "03_Support_consolide" / "Support_consolide.html")

for source, titre in [("01_Installation/Guide_installation.md", "Guide d'installation"),
                      ("02_Parcours_autonomie/Parcours_autonomie.md", "Parcours d'autonomie"),
                      ("05_Guide_Claude/Guide_Claude.md", "Guide Claude"),
                      ("06_Ressources/Ressources.md", "Ressources pour continuer")]:
    md_vers_html((SRC / "contenu" / source).read_text(encoding="utf-8"), titre, KIT / Path(source).with_suffix(".html"))
# La méthode IA par étapes : guide_ia/README.md reste l'unique source
methode = (RACINE / "guide_ia" / "README.md").read_text(encoding="utf-8")
methode = methode.replace("(modele_PROJET.md)", "(modeles/PROJET.md)").replace("(modele_AGENTS.md)", "(modeles/AGENTS.md)")
md_vers_html(methode, "Méthode IA par étapes", KIT / "05_Guide_Claude" / "Methode_IA_etapes.html")
for nom, cible in [("modele_AGENTS.md", "AGENTS.md"), ("modele_PROJET.md", "PROJET.md")]:
    shutil.copy2(RACINE / "guide_ia" / nom, KIT / "05_Guide_Claude" / "modeles" / cible)

subprocess.run([sys.executable, str(SRC / "build_guide.py"), str(KIT / "04_Guide_interactif_projet" / "Guide_projet_A_a_Z.html")], check=True)
shutil.copy2(SRC / "portail.html", KIT / "00_COMMENCEZ_ICI.html")


# --------------------------------------------------------------------------- 2. PDF du support
def navigateur() -> str:
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", "google-chrome", "chromium", "microsoft-edge"]:
        if Path(c).exists() or shutil.which(c):
            return c
    raise SystemExit("--pdf : ni Edge ni Chrome trouvé")


if args.pdf:
    page = (KIT / "03_Support_consolide" / "Support_consolide.html").as_uri() + "?print"
    subprocess.run([navigateur(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=30000",
                    "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={KIT / '03_Support_consolide' / 'Support_consolide.pdf'}", page], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("pdf  : kit_autonomie/03_Support_consolide/Support_consolide.pdf")

# --------------------------------------------------------------------------- 3. slides (hors Git)
SLIDES = KIT / "07_Slides_formation"
COPIES = {"De_la_chaine_au_graphe_BStorm.pdf": "1_Seances_presentees/J1_04-11_De_la_chaine_au_graphe.pdf",
          "2026-11-04_Jour2_06-11_BStorm.pdf": "1_Seances_presentees/J2_06-11_Seance.pdf",
          "2026-11-04_Jour2_06-11_BStorm_annexe.pdf": "1_Seances_presentees/J2_06-11_Annexe_fiches.pdf",
          "2026-11-07_Jour3_09-11_BStorm_annexe.pdf": "1_Seances_presentees/J3_09-11_Annexe_fiches.pdf",
          "2026-11-09_Jour4_10-11_BStorm.pdf": "1_Seances_presentees/J4_10-11_Seance.pdf",
          "2026-11-09_Jour4_10-11_BStorm_annexe.pdf": "1_Seances_presentees/J4_10-11_Annexe_fiches.pdf",
          "Support_J1_J2_BStorm.pdf": "2_Decks_de_reference/02_Support_J1_J2_fondations.pdf",
          "Préparer son poste avant la formation HelpDesk-Ops.pdf": "2_Decks_de_reference/00_Preparer_son_poste.pdf"}
EXPORTS = {"2026-11-07_Jour3_09-11_BStorm.pptx": "1_Seances_presentees/J3_09-11_Seance.pdf",
           "2026-10-31_Installer_et_brancher_BStorm.pptx": "2_Decks_de_reference/01_Installer_et_brancher.pdf",
           "2026-11-09_Agents_stateful_BStorm.pptx": "2_Decks_de_reference/03_Agents_stateful.pdf",
           "2026-11-09_Multi_agents_MCP_BStorm.pptx": "2_Decks_de_reference/04_Multi_agents_MCP.pdf",
           "2026-10-31_Monitoring_evaluation_BStorm.pptx": "2_Decks_de_reference/05_Monitoring_evaluation.pdf",
           "2026-10-31_Securite_conformite_mini_projet_BStorm.pptx": "2_Decks_de_reference/06_Securite_conformite_mini_projet.pdf"}
if args.slides:
    for source, cible in COPIES.items():
        (SLIDES / cible).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SUPPORTS / source, SLIDES / cible)
    commandes = "$pp = New-Object -ComObject PowerPoint.Application\n" + "".join(
        f'$p = $pp.Presentations.Open("{SUPPORTS / s}", $true, $false, $false); $p.SaveAs("{SLIDES / c}", 32); $p.Close()\n'
        for s, c in EXPORTS.items()) + "$pp.Quit()\n"
    subprocess.run(["powershell", "-NoProfile", "-Command", commandes], check=True)
    print(f"slides : {len(COPIES) + len(EXPORTS)} PDF dans kit_autonomie/07_Slides_formation")

# --------------------------------------------------------------------------- 4. zip à distribuer
if args.zip:
    suivis = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
                            check=True).stdout.splitlines()
    nouveaux = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=RACINE, capture_output=True,
                              text=True, encoding="utf-8", check=True).stdout.splitlines()
    if nouveaux:
        print("⚠️  fichiers non suivis, absents du zip :", *nouveaux[:10], sep="\n   ")
    fichiers = [RACINE / f for f in suivis if (RACINE / f).is_file()]
    fichiers += [p for p in SLIDES.rglob("*.pdf")] if SLIDES.exists() else []
    if not SLIDES.exists():
        print("⚠️  pas de slides : lancez d'abord --slides")
    assert not any(p.name == ".env" for p in fichiers), "un .env dans le zip"
    dist = RACINE / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / "HelpDesk-Ops_kit_autonomie.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(fichiers)):
            z.write(p, "helpdesk-ops/" + p.relative_to(RACINE).as_posix())
    print(f"zip  : {archive.relative_to(RACINE)} ({archive.stat().st_size / 1e6:.1f} Mo, {len(set(fichiers))} fichiers)")
