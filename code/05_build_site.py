"""Build index.html from code/page_template.html. Every number in the text is a {{path|format}} token filled from
data/results.json; page data (results, site.json, world.json) is embedded; the facsimile tiles are in tiles/ and the
province outlines are loaded from data/provinces.json. Facts stated in words are checked here. The full-screen map
snippet (code/fullscreen_snippet.html) is pasted before </body>. 10.5281/zenodo.23882605, https://doi.org/10.5281/zenodo.23882605 and https://blog.tristanhotham.com/2026/10/31/peutinger/ stay as
placeholders for the publisher."""
import json
from common import *

R = jload(f"{DATA}/results.json")
SITE = jload(f"{DATA}/site.json")
KEEP = {"DOI", "BLOG_URL", "DOI_URL"}
U, D, G, SH, RO, T = R["units"], R["dist"], R["regions"], R["shape"], R["rome"], R["total"]

# facts stated in words (page, blog, paper, collage)
assert R["source"]["segments"] == 11 and len(R["segments"]) == 11                          # "eleven sheets"
assert R["source"]["personified"] == ["Antiochia", "Constantinopolis", "Roma"]              # "one of only three cities drawn as a person"
assert 1.4 < U["league_over_mile"] < 1.65                                                    # "very close to the one and a half of a league"
assert U["narbonensis"]["km_per_unit_gc"] < 1.5 < U["League"]["km_per_unit_gc"]             # "falls straight back"
assert 0.95 < U["gaul_as_leagues_err"] < 1.08 and U["gaul_as_miles_err"] > 1.4               # "right to within a few per cent"
assert U["Mile"]["km_per_unit_gc"] < RM_KM < U["Mile"]["km_per_unit_road"]                  # figures sit between straight line and road
assert D["gc_median"] < 1 < D["road_median"]
assert U["far_east_parasang_like"] >= 3 and U["far_east_mile_like"] >= 3 and U["india"]["km_per_unit_gc"] > 5   # "some like miles, some like parasangs, India fits nothing"
rt = R["routes"]
assert all(abs(rt[k]["vs_road"] - 1) < .1 for k in ("Cologne", "Vienna"))                  # "the errors cancel"
assert all(.84 < rt[k]["vs_road"] < .9 for k in ("Antioch", "Jerusalem"))                   # "by about an eighth"
assert rt["Constantinople"]["vs_road"] < 1
assert rt["Carthage"]["regions"] == ["Italy and islands", "Alps and Danube", "Greece and Thrace", "Asia Minor", "Levant", "Egypt and Cyrene", "North Africa"]
assert rt["Carthage"]["recon_legs"] == 0
assert (SH["west"], SH["east"], SH["north"], SH["south"]) == ("Gesocribate", "Palibotra", "Lvgdvno", "Mvzeris")
assert SH["x_spearman_lon"] > .95 and SH["y_spearman_lat"] < .8                            # "almost perfectly", "much looser"
assert G["Italy and islands"]["scroll_bearing"] in range(110, 160) and G["North Africa"]["scroll_bearing"] in range(110, 160)   # north-west to south-east
assert R["stretch_rank"][:5] == ["North Africa", "Alps and Danube", "Egypt and Cyrene", "Greece and Thrace", "Italy and islands"]
assert R["stretch_rank"][-2:] == ["Mesopotamia and Armenia", "Persia, Central Asia and India"]
assert G["Asia Minor"]["aniso"] < G["Gaul and the Rhine"]["aniso"] + 1 and G["Levant"]["aniso"] < G["Italy and islands"]["aniso"]
assert R["space_rank"][:4] == ["Italy and islands", "Mesopotamia and Armenia", "Greece and Thrace", "Levant"]
assert all(.8 <= G[k]["space_ratio"] <= 1.1 for k in ("Gaul and the Rhine", "North Africa", "Asia Minor"))   # "about their fair share"
assert G["Egypt and Cyrene"]["space_ratio"] < .5
assert G["Britain"]["located"] <= 3 and G["Iberia"]["located"] <= 1                         # "barely appear"
assert abs(R["recon"]["gc_median"] - D["gc_median"]) < .05                                   # "behave just like the Tabula's"
assert RO["middle_modern"] == "Skopje" and RO["frac"] < 40 and 2.5 < RO["lost_for_centre"] < 3.6   # "about three sheets"
assert R["located"]["min_per_segment"] >= 10                                                 # "they cover every sheet"
assert 9 < T["years_foot"] < 10.5                                                            # "close to 10 years"
assert R["meta"]["page"] == PAGE


def build():
    tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
    html = re.sub(r"\{\{(?!DOI\}\}|BLOG_URL\}\}|DOI_URL\}\})([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(R, m.group(1)), m.group(3)), tpl)
    left = set(re.findall(r"\{\{([^}]*)\}\}", html))
    assert left <= KEEP, left
    J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*RESULTS*/", J(R)).replace("/*SITE*/", J(SITE))
    html = html.replace("/*WORLD*/", open(f"{DATA}/world.json", encoding="utf-8").read())
    html = html.replace("/*FULLSCREEN*/", open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read())
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv"):
        assert bad not in vis, bad
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        for bad in ("—", "–"):
            assert bad not in scr, bad
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()) // 1024, "KB")


if __name__ == "__main__":
    build()
