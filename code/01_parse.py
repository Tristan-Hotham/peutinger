"""Step 1. Read the OmnesViae export of the Tabula Peutingeriana into two tables, place every station in a province and
a region, check its coordinates against Pleiades, and write the outlines used by the page and the figures.

Definitions
  * station: a Place item. TPPlace ids are stations drawn on the surviving Tabula (Talbert's numbering, which runs
    roughly west to east along the scroll); OVPlace ids are stations OmnesViae adds for the lost western end
    (Britain, Spain, western Gaul and Mauretania), taken from the Antonine Itinerary.
  * leg: a TravelAction, one stretch of road between two stations with the number written beside it (dist). A leg is
    'reconstructed' when OmnesViae flags it (isReconstructed) or when either end is an OVPlace. Everything else is
    'surviving': drawn on the parchment we have.
  * province: the DARE province of about AD 117 that contains the station, or the nearest one within 60 km (the
    simplified coastlines cut off some harbours); otherwise a region beyond the frontier (common.region_outside).
  * Pleiades check: the label, classical and modern names are matched (normalised spelling) against Pleiades names
    and titles; the distance to the nearest matching Pleiades place with a precise location is recorded. A station
    whose coordinates are more than 100 km from every such match is flagged for review (pleiades_flag); the flags
    are reviewed in 04_results.py, which leaves out legs that touch a confirmed bad coordinate.
Outputs: data/places.csv, data/legs.csv, data/world.json, data/sources.json."""
import numpy as np, pandas as pd
from shapely.geometry import shape, Point, mapping
from shapely.strtree import STRtree
from common import *

G = jload(f"{RAW}/omnesviae.json")["@graph"]
pl, lg = [], []
for x in G:
    i = x["@id"].split("#")[1]
    if x["@type"] == "Place":
        pl.append({"id": i, "kind": "TP" if i.startswith("TP") else "OV", "num": int(re.sub(r"\D", "", i)), "label": x.get("label"),
                   "classic": x.get("classic"), "modern": (x.get("modern") or "").strip() or None, "alt": x.get("alt"),
                   "lat": x.get("lat"), "lon": x.get("lng"), "symbol": x.get("symbol")})
    elif x["@type"] == "TravelAction":
        assert len(x["from"]) == 1 and len(x["to"]) == 1
        lg.append({"id": i, "from": x["from"][0]["@id"].split("#")[1], "to": x["to"][0]["@id"].split("#")[1], "dist": x.get("dist"),
                   "over_water": bool(x.get("overWater")), "flag_reconstructed": bool(x.get("isReconstructed")),
                   "mountains": bool(x.get("crossesMountains")), "river": x.get("crossesRiver")})
P = pd.DataFrame(pl); L = pd.DataFrame(lg)
assert len(P) == 3323 and len(L) == 3523, (len(P), len(L))
# one station (TPPlace2728, Nagae) is listed twice, once without coordinates: keep the located copy
P = P.sort_values("lat", na_position="last").drop_duplicates("id").sort_values(["kind", "num"]).set_index("id")
# five legs are listed twice (two readings of the same figure, or one with and one without a figure): keep both, with distinct ids
L["id"] = L["id"] + L.groupby("id").cumcount().map(lambda c: "" if c == 0 else f"_{c + 1}")
assert L.id.is_unique and L["from"].isin(P.index).all() and L["to"].isin(P.index).all()
L["reconstructed"] = L.flag_reconstructed | L["from"].str.startswith("OV") | L["to"].str.startswith("OV")
print("places", P.kind.value_counts().to_dict(), "with coords", int(P.lat.notna().sum()), "; legs", len(L), "with dist", int(L.dist.notna().sum()),
      "reconstructed", int(L.reconstructed.sum()))

# ---------- provinces and regions ----------
PR = jload(DARE)["features"]
geoms = [shape(f["geometry"]).buffer(0) for f in PR]
ROMAN_NUM = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"}
names = [("Italia, regio " + f["properties"]["name"]) if f["properties"]["name"] in ROMAN_NUM else f["properties"]["name"] for f in PR]   # the regions of Italy are named by number
tree = STRtree(geoms)
prov, reg = [], []
for i, r in P.iterrows():
    if pd.isna(r.lat):
        prov.append(None); reg.append(None); continue
    pt = Point(r.lon, r.lat); p = None
    for k in tree.query(pt):
        if geoms[k].contains(pt):
            p = names[k]; break
    if p is None:
        k = tree.nearest(pt)
        if geoms[k].distance(pt) * 111 * np.cos(np.radians(r.lat)) < 60:
            p = names[k]
    g = region_of_province(p, r.lon, r.lat) if p and p != "Armenia Mesopotamia" else None
    if p == "Armenia Mesopotamia":
        g = "Mesopotamia and Armenia"
    if g is None:
        g = region_outside(r.lon, r.lat)
    prov.append(p); reg.append(g)
P["province"] = prov; P["region"] = reg
miss = P[P.lat.notna() & P.region.isna()]
assert len(miss) == 0, miss[["label", "modern", "lat", "lon"]].head(30).to_string()
print(P.region.value_counts().to_dict())

# ---------- Pleiades check ----------
pp = pd.read_csv(f"{PLEI}/places.csv", dtype=str, keep_default_na=False)
nn = pd.read_csv(f"{PLEI}/names.csv", dtype=str, keep_default_na=False)
pp = pp[(pp.representative_latitude != "") & (pp.location_precision == "precise")]
PLX = {r.id: (float(r.representative_latitude), float(r.representative_longitude), r.title) for r in pp.itertuples()}
KEY = {}
for r in nn.itertuples():
    for f in (r.attested_form, r.romanized_form_1, r.romanized_form_2, r.romanized_form_3):
        for v in re.split(r"[,/;]", f):
            k = norm(v).replace(" ", "")
            if len(k) >= 4 and r.place_id in PLX: KEY.setdefault(k, set()).add(r.place_id)
for pid, (la, lo, t) in PLX.items():
    for v in re.split(r"[,/;]", re.sub(r"\([^)]*\)", "", t)):
        k = norm(v).replace(" ", "")
        if len(k) >= 4: KEY.setdefault(k, set()).add(pid)


def keys(r):
    out = set()
    for s in (r.label, r.classic):
        if isinstance(s, str):
            k = norm(s).replace("v", "u").replace(" ", "")
            out |= {k, norm(s).replace(" ", "")}
    return {k for k in out if len(k) >= 4}


dmin, pmatch = [], []
for i, r in P.iterrows():
    best = None
    if pd.notna(r.lat):
        for k in keys(r):
            for pid in KEY.get(k, ()):
                la, lo, t = PLX[pid]; d = float(gc_km(r.lat, r.lon, la, lo))
                if best is None or d < best[0]:
                    best = (d, pid, t)
    dmin.append(round(best[0], 1) if best else None); pmatch.append(f"{best[1]} {best[2]}" if best else None)
P["pleiades_km"] = dmin; P["pleiades_match"] = pmatch
P["pleiades_flag"] = P.pleiades_km > 100
chk = P[P.pleiades_km.notna()]
print("pleiades matched", len(chk), "within 10 km", int((chk.pleiades_km <= 10).sum()), "within 25", int((chk.pleiades_km <= 25).sum()),
      "flag >100", int(P.pleiades_flag.sum()))
P[P.pleiades_flag][["label", "classic", "modern", "lat", "lon", "pleiades_km", "pleiades_match", "region"]].to_csv(f"{WORK}/pleiades_flags.csv")
P.reset_index().to_csv(f"{DATA}/places.csv", index=False)
L.to_csv(f"{DATA}/legs.csv", index=False)

# ---------- outlines ----------
iso_of = lambda p: p["ISO_A3_EH"] if p.get("ISO_A3_EH") not in ("-99", None) else p["ADM0_A3"]


def rnd(c, k=2):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return [round(c[0], k), round(c[1], k)]
    return [rnd(x, k) for x in c]


W50 = jload(f"{GEO}/ne_50m_admin_0_countries.geojson")
feats = []
for f in W50["features"]:
    gs = shape(f["geometry"])
    if gs.bounds[2] < -35 or gs.bounds[0] > 125 or gs.bounds[3] < -15:   # the Americas, East Asia, Oceania and the far south are never in view
        continue
    gs = gs.simplify(0.03, preserve_topology=True)
    if gs.is_empty: continue
    gm = mapping(gs)
    feats.append({"type": "Feature", "properties": {"iso": iso_of(f["properties"]), "name": f["properties"].get("NAME_EN") or f["properties"]["NAME"]},
                  "geometry": {"type": gm["type"], "coordinates": rnd(gm["coordinates"])}})
jsave({"type": "FeatureCollection", "features": feats}, f"{DATA}/world.json")
# Natural Earth land, simplified, for the modern coastlines bent onto the scroll (04_results.py) and the figures
LAND = []
for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]:
    g = shape(f["geometry"])
    for p_ in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
        b = p_.bounds
        if b[2] < -15 or b[0] > 100 or b[3] < 0 or b[1] > 62 or p_.area < 0.02: continue
        q = p_.simplify(0.02, preserve_topology=True)
        LAND.append({"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [rnd(list(q.exterior.coords), 3)]}})
jsave({"type": "FeatureCollection", "features": LAND}, f"{DATA}/land.json")
# province outlines (DARE, CC BY-SA) for the page layer and the area shares, simplified
pf = []
for g, n in zip(geoms, names):
    s = g.simplify(0.05, preserve_topology=True); gm = mapping(s)
    pf.append({"type": "Feature", "properties": {"name": n, "region": region_of_province(n, s.centroid.x, s.centroid.y) or "Mesopotamia and Armenia"},
               "geometry": {"type": gm["type"], "coordinates": rnd(gm["coordinates"])}})
jsave({"type": "FeatureCollection", "features": pf}, f"{DATA}/provinces.json")

# ---------- source facts carried forward ----------
import html as _html
wk = jload(WIKI)
wt = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>|<sup.*?</sup>", "", wk["html"], flags=re.S))).replace("\xa0", " "))
for s_ in ("pedestrians traveled 20 to 25 kilometres", "Horse-drawn carts could travel up to 40 to 50 kilometres", "relay of horses could carry a letter 80 kilometres"):
    assert s_ in wt, s_
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(f"{RAW}/tabula_peutingeriana_miller1887.jpg")
jsave({"wiki_roman_roads_revid": wk["revid"], "miller_px": list(im.size), "omnesviae_places": len(P), "omnesviae_legs": len(L)}, f"{DATA}/sources.json", indent=1)
print("ok")
