"""Blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.23882605, https://doi.org/10.5281/zenodo.23882605 and https://blog.tristanhotham.com/2026/10/31/peutinger/ stay as placeholders for the publisher."""
import json as _json, shutil, zipfile, importlib.util
from common import *

spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "code", "05_build_site.py"))
spec.loader.exec_module(importlib.util.module_from_spec(spec))          # shared fact checks
R = jload(f"{DATA}/results.json")
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Peutinger_Table"
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}
G, rt = R["regions"], R["routes"]

# numbers written in words or alt text in the blog and collage
assert 50 < G["North Africa"]["aniso"] < 60 and 20 < G["Alps and Danube"]["aniso"] < 22 and 18 < G["Egypt and Cyrene"]["aniso"] < 20
assert round(G["Greece and Thrace"]["aniso"]) == 11 and round(G["Italy and islands"]["aniso"]) == 10 and 7 <= G["Gaul and the Rhine"]["aniso"] < G["Asia Minor"]["aniso"] < 8.5
assert 5.5 < G["Levant"]["aniso"] < 6.5 and G["Persia, Central Asia and India"]["aniso"] < 2 and 1.5 < G["Mesopotamia and Armenia"]["aniso"] < 2.5
u = R["units"]["by_province"]
assert all(2.0 < u[p]["km_per_unit_gc"] < 2.35 for p in LEAGUE_PROVINCES)
assert all(1.2 <= v["km_per_unit_gc"] <= 1.7 for p, v in u.items() if p not in LEAGUE_PROVINCES)
assert 1450 < R["dist"]["n_road"] < 1600                                                        # "about 1,500"
assert [round(R["rome"]["frac"]), round(R["rome"]["frac_one_lost"]), round(R["rome"]["frac_k_lost"])] == [35, 41, 49]
assert [rt[k]["foot"] for k in ("Lyon", "Vienna", "Cologne", "London", "Constantinople", "Athens", "Seville", "Antioch", "Jerusalem", "Alexandria", "Ctesiphon", "Persepolis")] == \
       [40, 50, 66, 78, 92, 98, 110, 132, 156, 169, 175, 193]
assert rt["Seville"]["recon_legs"] > rt["Seville"]["legs"] / 4
assert round(R["shape"]["km_per_cm_ew"]) == 13 and round(R["shape"]["km_per_cm_ns"]) == 138           # collage

post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = re.sub(r"\{\{(?!IMG)([^}|]+)(\|(\w+))?\}\}", lambda m: m.group(0) if m.group(1) in KEEP else fmt(get(R, m.group(1)), m.group(3)), post)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u_), post, re.M) for u_ in used) and "wp:image" not in post
from PIL import Image
for img in used:
    assert os.path.exists(f"{REL}/blog/{img}"), img
    assert Image.open(f"{REL}/blog/{img}").size[0] == 1800, img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{([^|}]+)\}\}", post)) <= KEEP
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
for bad in ("\u2014", "\u2013", "--", "DSIT", "DCMS"):
    assert bad not in vis, bad
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
sh, d = R["shape"], R["dist"]
meta = {"title": "The Peutinger Table: a Roman road map that squashed the world",
        "slug": "peutinger",
        "excerpt": f"I set a Roman road map 6.75 m long beside a modern one. It squashes the world {sh['stretch_whole']:.0f} times north to south, yet {d['road_within25_pct']:.0f}% of its road distances are within 25% of the real road, and it switches to Gallic leagues exactly where it says it does.",
        "seo_description": f"The Peutinger Table beside a modern map: {R['located']['n']} places, {d['n_road']:,} road legs measured, a world squashed {sh['stretch_whole']:.0f} times, and where Rome falls.",
        "tags": ["maps", "history", "Roman roads", "Peutinger Table", "Tabula Peutingeriana", "cartography", "data visualisation", "Roman Empire"],
        "header_alt": f"Title card reading 'Peutinger Table' in black and red on pale parchment, above a thin strip of Miller's facsimile of the whole Roman road map dotted with coloured markers, a small modern map of Europe, North Africa and the Middle East with the same places, and the figures '{sh['stretch_whole']:.0f}x squashed north to south' and '{d['road_within25_pct']:.0f}% of legs within 25% of the road'."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# Zenodo
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/peutinger_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for dd in ("code", "data", "img"):
        for fn in sorted(os.listdir(os.path.join(ROOT, dd))):
            if fn.endswith(".pyc") or fn == "__pycache__":
                continue
            z.write(os.path.join(ROOT, dd, fn), f"peutinger/{dd}/{fn}")
    for fn in ("README.md", "LICENSE", "index.html"):
        z.write(os.path.join(ROOT, fn), f"peutinger/{fn}")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), "peutinger/reddit/collage.py")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&")
zmeta = {"title": "The Peutinger Table Against a Modern Map: Shape, Space and Distance on a Roman Road Map",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {BLOG}.</p><p>Sources: OmnesViae (R. Voorburg, omnesviae.org) after R. J. A. Talbert, Rome's World (2010), used as factual data with credit; K. Miller's 1887 facsimile (Wikimedia Commons, public domain); Itiner-e (CC BY 4.0); DARE (CC BY-SA); Pleiades (CC BY 3.0); Natural Earth.</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["Tabula Peutingeriana", "Peutinger Table", "Roman roads", "historical cartography", "map distortion", "itineraries", "Itiner-e", "open data", "maps"],
         "license": "cc-by-4.0", "language": "eng",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": OV_URL, "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": ITINERE_DOI, "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": "https://pleiades.stoa.org/", "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj
jsave(zmeta, f"{Z}/metadata.json", indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
