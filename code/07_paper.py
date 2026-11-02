"""Build the paper: fill code/paper_template.tex from data/results.json, add tables, compile with xelatex.
Output: release/paper/<NAME>.pdf and .tex (figures f_*.png sit beside them). The DOI stays as the 10.5281/zenodo.23882605 placeholder."""
import subprocess
import pandas as pd
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Peutinger_Table"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$").replace("~", "\\textasciitilde{}").replace("\u1e21", "g")

# statements made in words in the paper only
assert R["units"]["Far east"]["n"] < 40 and R["units"]["india"]["km_per_unit_gc"] > 5
assert R["dist"]["road_over2_pct"] < 20


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pc": return f"{round(float(v))}\\%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    return tex(str(v))


G = pd.read_csv(f"{DATA}/regions.csv")
num = lambda v, f: "" if pd.isna(v) else (f.format(v))
rows = "".join(f"{tex(r.region)} & {r.located} & {r.scroll_pct:.1f} & {num(r.land_pct, '{:.1f}')} & {num(r.space_ratio, '{:.2f}')} & {num(r.aniso, '{:.1f}')} & {num(r.km_per_cm_ew, '{:.1f}')} & {num(r.km_per_cm_ns, '{:.1f}')} & {int(r.road_km):,}\\\\\n" for r in G.itertuples())
TR = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{Regions: located places; share of the surviving scroll and of the land of the provinces (\\%); ratio of the two; stretch; km per cm of parchment east-west and north-south from the regional fit; km of road written on the surviving sheets.}\\label{tab:regions}"
      "\\begin{tabular}{lrrrrrrrr}\\toprule Region & Located & Scroll & Land & Ratio & Stretch & EW & NS & Road km\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
L = pd.read_csv(f"{DATA}/located.csv").sort_values("x")
rows = "".join(f"{tex(r.tp_label)} & {tex(r.modern) if isinstance(r.modern, str) else ''} & {r.seg} & {int(r.x):,} & {int(r.y):,} & {r.conf}\\\\\n" for r in L.itertuples())
TL = ("{\\footnotesize\\setlength{\\tabcolsep}{4pt}\\begin{longtable}{p{4.6cm}p{5.2cm}lrrl}\\caption{The " + str(len(L)) + " places located on Miller's facsimile, west to east: name as written (OmnesViae), modern place, sheet, position in facsimile pixels and confidence.}\\label{tab:located}\\\\"
      "\\toprule Name on the map & Today & Sheet & x & y & Read\\\\\\midrule\\endfirsthead\\toprule Name on the map & Today & Sheet & x & y & Read\\\\\\midrule\\endhead\n" + rows + "\\bottomrule\\end{longtable}}")
t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = t.replace("\\href{https://doi.org/{{meta.doi}}}{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
t = t.replace("\\url{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
t = re.sub(r"\{\{(?!TABLE_)([^}|]+)(\|(\w+))?\}\}", lambda m: tfmt(get(R, m.group(1)), m.group(3) or "raw"), t)
for k, v in (("REGIONS", TR), ("LOCATED", TL)):
    t = t.replace("{{TABLE_%s}}" % k, v)
assert "{{" not in t and "--" not in t and "\u2014" not in t and "\u2013" not in t, re.findall(r"\{\{[^}]*\}\}", t)[:4]
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(3):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:12])
for ext in (".aux", ".log", ".out", ".bbl", ".blg"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("\u2014") + txt.count("\u2013") + txt.count("--"))
