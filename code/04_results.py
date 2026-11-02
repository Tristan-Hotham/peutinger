"""Step 4. Every number used anywhere (data/results.json), the reusable tables (data/located.csv, data/regions.csv,
data/legs.csv with derived columns, data/routes.csv) and the page data (data/site.json). Reads only data/.

Definitions
  * surviving / reconstructed: see 01_parse.py. All headline figures are for the surviving Tabula; the reconstructed
    west (OmnesViae's stations and legs from the Antonine Itinerary) is reported separately.
  * unit zone of a leg: from the province of its first station. 'League' in Aquitania, Lugdunensis, Belgica and the two
    Germanies (the Tabula's note at Lyon, "usque hic legas", leagues up to here); 'Far east' in the region Persia,
    Central Asia and India; 'Mile' everywhere else. Stated km = the figure x 1.48 (Roman mile) or x 2.22 (league); in
    the far east the unit is unknown and the figures are converted as Roman miles only where a total needs a number.
  * measured distances: great-circle between the two stations' OmnesViae coordinates; road distance along the
    Itiner-e network (02_roads.py). A leg's error = measured km / stated km. Legs with no figure, a figure of 0, or a
    station without coordinates are left out.
  * located places: the stations I found by eye on Miller's facsimile (data/map_positions.csv, full-size pixels).
    Scroll position x runs west to east, y top to bottom.
  * stretch: for each region with at least 8 located places, the affine map (least squares) from local east and
    north km (equirectangular about the region's mean) to scroll pixels. East-west scale = length of its column for
    'east' (px per km), north-south scale = length of its column for 'north' (ew_ns = their ratio). Stretch (aniso) =
    ratio of the map's two singular values: how many times more parchment a km gets in the most-stretched ground
    direction than in the least, whatever the orientation. scroll_bearing = the compass direction on the ground that
    the map lays along the scroll from left to right. Pixels to parchment centimetres: the surviving 6.75 m strip
    over Miller's map width. Whole scroll: the east-west and north-south spans of the located places against the
    parchment's length and height.
  * space: each pixel of the painted strip is given to the region of the nearest located place (a Voronoi split, at
    1/10 resolution); a region's share of the scroll is its share of those pixels. Land share: share of the land
    area of the provinces of AD 117 (DARE outlines, equal-area projection); not defined beyond the frontier.
  * days: stated km / speed (Wikipedia, "Roman roads": 22.5 km a day on foot, the middle of 20 to 25; 45 by cart,
    the middle of 40 to 50; 80 by courier relay). Routes from Rome: shortest paths over all legs with a figure
    (surviving and reconstructed), weighted by stated km."""
import itertools
import numpy as np, pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.stats import spearmanr
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as stransform
from common import *

R = {}
P = pd.read_csv(f"{DATA}/places.csv").set_index("id")
L = pd.read_csv(f"{DATA}/legs.csv")
FIT = jload(f"{DATA}/fit.json"); RM = jload(f"{DATA}/road_meta.json"); SRC = jload(f"{DATA}/sources.json")
pc = lambda a, b: round(100 * a / b, 1) if b else None
MX0, MX1 = FIT["map_x"]; MY0, MY1 = FIT["map_y"]
SEG = FIT["segments"]
PARCH_CM = 675.0                       # the surviving parchment, about 6.75 m long and 34 cm high (Talbert 2010)
PARCH_H_CM = 34.0
CM_PER_PX = PARCH_CM / (MX1 - MX0)

# ---------- source ----------
TP = P[P.kind == "TP"]; OV = P[P.kind == "OV"]
R["source"] = {"places": len(P), "tp": len(TP), "ov": len(OV), "tp_coords": int(TP.lat.notna().sum()), "ov_coords": int(OV.lat.notna().sum()),
               "legs": len(L), "legs_dist": int(L.dist.notna().sum()), "legs_nodist": int(L.dist.isna().sum()),
               "legs_surv": int((~L.reconstructed).sum()), "legs_recon": int(L.reconstructed.sum()),
               "pleiades_checked": int(P.pleiades_km.notna().sum()), "pleiades_10km": int((P.pleiades_km <= 10).sum()),
               "pleiades_10km_pct": pc((P.pleiades_km <= 10).sum(), P.pleiades_km.notna().sum()), "pleiades_version": PLEIADES_VER,
               "symbols": int(TP.symbol.notna().sum()), "aquae_sym": int(TP.symbol.astype(str).str.startswith("C").sum()),
               "aquae_named": int((TP.symbol.astype(str).str.startswith("C") & TP.label.str.lower().str.replace("v", "u").str.contains("aqu")).sum()),
               "personified": sorted(TP[TP.symbol.astype(str).str.startswith("F")].label.str.title().tolist()),
               "parchment_m": PARCH_CM / 100, "parchment_cm_high": PARCH_H_CM, "segments": len(SEG), "miller_w": SRC["miller_px"][0], "miller_h": SRC["miller_px"][1],
               "map_px_w": MX1 - MX0, "map_px_h": MY1 - MY0, "tiles": FIT["tiles"]}
assert R["source"]["personified"] == ["Antiochia", "Constantinopolis", "Roma"], R["source"]["personified"]

# ---------- legs ----------
for e in ("from", "to"):
    for c in ("lat", "lon", "province", "region", "label"):
        L[f"{e}_{c}"] = P[c].reindex(L[e]).values
L["gc_km"] = gc_km(L.from_lat, L.from_lon, L.to_lat, L.to_lon)
prov = L.from_province.where(L.from_province.notna(), L.to_province)
regn = L.from_region.where(L.from_region.notna(), L.to_region)
L["region"] = regn
L["zone"] = np.where(prov.isin(LEAGUE_PROVINCES), "League", np.where(regn == "Persia, Central Asia and India", "Far east", "Mile"))
L["unit_km"] = np.where(L.zone == "League", LEAGUE_KM, RM_KM)
L["stated_km"] = L.dist * L.unit_km
L.loc[~(L.dist > 0), "stated_km"] = np.nan
L["gc_ratio"] = L.gc_km / L.stated_km
L["road_ratio"] = L.road_km / L.stated_km
S = L[~L.reconstructed]; RC = L[L.reconstructed]
Sm = S[(S.dist > 0) & S.gc_km.notna()]


def zone_stats(d):
    k = d.gc_km / d.dist; rd = d.road_km / d.dist
    return {"n": int(len(d)), "km_per_unit_gc": round(float(k.median()), 2), "km_per_unit_road": round(float(rd.median()), 2) if rd.notna().any() else None,
            "n_road": int(rd.notna().sum()), "q25": round(float(k.quantile(.25)), 2), "q75": round(float(k.quantile(.75)), 2)}


R["units"] = {z: zone_stats(Sm[Sm.zone == z]) for z in ("Mile", "League", "Far east")}
U = R["units"]
U["league_over_mile"] = round(U["League"]["km_per_unit_gc"] / U["Mile"]["km_per_unit_gc"], 2)
U["league_over_mile_road"] = round(U["League"]["km_per_unit_road"] / U["Mile"]["km_per_unit_road"], 2)
U["narbonensis"] = zone_stats(Sm[Sm.from_province == "Narbonensis"])
U["by_province"] = {p: zone_stats(d) for p, d in Sm.groupby("from_province") if len(d) >= 25}
fe = Sm[Sm.zone == "Far east"]; kfe = fe.gc_km / fe.dist
U["far_east_min"] = round(float(kfe.min()), 1); U["far_east_max"] = round(float(kfe.max()), 1)
U["far_east_parasang_like"] = int(((kfe > 4) & (kfe < 7.5)).sum()); U["far_east_mile_like"] = int((kfe < 2.2).sum())
U["india"] = zone_stats(fe[fe.from_lon > 66]); U["persia"] = zone_stats(fe[fe.from_lon <= 66])
U["rm_km"] = RM_KM; U["league_km"] = LEAGUE_KM; U["parasang_km"] = PARASANG_KM
# would Gaul fit better in miles? error of the league zone if read as Roman miles
lz = Sm[(Sm.zone == "League") & Sm.road_km.notna()]
U["gaul_as_miles_err"] = round(float((lz.road_km / (lz.dist * RM_KM)).median()), 2)
U["gaul_as_leagues_err"] = round(float((lz.road_km / (lz.dist * LEAGUE_KM)).median()), 2)
assert 1.4 < U["league_over_mile"] < 1.65                     # "about one and a half": the league is 1.5 Roman miles
assert U["Mile"]["km_per_unit_gc"] < RM_KM < U["Mile"]["km_per_unit_road"]

# distances: stated against measured, surviving legs in the mile and league zones
D = Sm[Sm.zone != "Far east"]
Dr = D[D.road_km.notna()]
R["dist"] = {"n_gc": len(D), "n_road": len(Dr), "gc_median": round(float(D.gc_ratio.median()), 3), "road_median": round(float(Dr.road_ratio.median()), 3),
             "gc_short_pct": round(100 * (1 - float(D.gc_ratio.median()))), "road_long_pct": round(100 * (float(Dr.road_ratio.median()) - 1)),
             "road_within20_pct": pc(((Dr.road_ratio > 1 / 1.2) & (Dr.road_ratio < 1.2)).sum(), len(Dr)),
             "road_within25_pct": pc(((Dr.road_ratio >= .8) & (Dr.road_ratio <= 1.25)).sum(), len(Dr)),
             "gc_within25_pct": pc(((D.gc_ratio >= .8) & (D.gc_ratio <= 1.25)).sum(), len(D)),
             "road_within33_pct": pc(((Dr.road_ratio > .75) & (Dr.road_ratio < 1 / .75)).sum(), len(Dr)),
             "road_within50_pct": pc(((Dr.road_ratio > 2 / 3) & (Dr.road_ratio < 1.5)).sum(), len(Dr)),
             "road_over2_pct": pc(((Dr.road_ratio > 2) | (Dr.road_ratio < .5)).sum(), len(Dr)),
             "spearman_road": round(float(spearmanr(Dr.stated_km, Dr.road_km).correlation), 3),
             "spearman_gc": round(float(spearmanr(D.stated_km, D.gc_km).correlation), 3),
             "median_leg_rm": round(float(S[S.dist > 0].dist.median())), "median_leg_km": round(float(D.stated_km.median()), 1),
             "road_iqr": [round(float(Dr.road_ratio.quantile(.25)), 2), round(float(Dr.road_ratio.quantile(.75)), 2)],
             "snapped": RM["snapped"], "network_km": RM["network_km"], "snap_km": RM["snap_km"], "detour": RM["detour"]}
# longer legs: total stated against total road along chains (sum over all legs with a road figure)
R["dist"]["sum_stated_km"] = round(float(Dr.stated_km.sum())); R["dist"]["sum_road_km"] = round(float(Dr.road_km.sum()))
R["dist"]["sum_ratio"] = round(float(Dr.road_km.sum() / Dr.stated_km.sum()), 3)
R["dist"]["by_region"] = {g: {"n": int(len(d)), "road_median": round(float(d.road_ratio.median()), 2), "gc_median": round(float(d.gc_ratio.median()), 2)}
                          for g, d in D.groupby("region") if len(d) >= 15}
rc = RC[(RC.dist > 0) & RC.gc_km.notna()]
R["recon"] = {"stations": len(OV), "legs": len(RC), "legs_dist": int((RC.dist > 0).sum()), "flagged": int(L.flag_reconstructed.sum()),
              "gc_median": round(float(rc.gc_ratio.median()), 3), "road_median": round(float(rc.road_ratio.median()), 3), "n_road": int(rc.road_ratio.notna().sum()),
              "stated_rm": int(RC[RC.dist > 0].dist.sum()), "stated_km": round(float(RC.stated_km.sum())),
              "regions": {g: int(n) for g, n in OV.region.value_counts().items()}}

# ---------- total road length and days ----------
SS = S[S.dist > 0]
far = SS.zone == "Far east"
R["total"] = {"legs": int(len(SS)), "units": int(SS.dist.sum()), "rm_mile_zone": int(SS[SS.zone == "Mile"].dist.sum()),
              "leagues": int(SS[SS.zone == "League"].dist.sum()), "far_units": int(SS[far].dist.sum()), "far_legs": int(far.sum()),
              "km": round(float(SS.stated_km.sum())), "km_no_far": round(float(SS[~far].stated_km.sum())),
              "km_with_recon": round(float(L[L.dist > 0].stated_km.sum())), "nodist_legs": int(S.dist.isna().sum()),
              "network_km": RM["network_km"]}
T = R["total"]
T["km_rounded_k"] = round(T["km"] / 1000)
T["days"] = {k: round(T["km"] / v) for k, _, v in SPEEDS}
T["years_foot"] = round(T["km"] / 22.5 / 365, 1)
T["pct_of_itinere"] = round(100 * T["km"] / RM["network_km"])
T["by_region"] = {g: {"km": round(float(d.stated_km.sum())), "legs": int(len(d))} for g, d in SS.groupby("region")}
R["speeds"] = {k: {"label": lab, "kmd": v} for k, lab, v in SPEEDS}
R["speeds"]["wiki_revid"] = SRC["wiki_roman_roads_revid"]

# routes from Rome: every leg, weighted by its stated km; a leg with no figure (or a figure of 0) is weighted by its
# road distance or, failing that, its great-circle distance times the median road/great-circle ratio, or, with
# neither, the median stated leg; such legs are counted
G = L.copy()
RG_GC = float((L.road_km / L.gc_km).median())
MED_LEG = float(L[L.dist > 0].stated_km.median())
G["w"] = G.stated_km.where(G.dist > 0, G.road_km.where(G.road_km.notna(), G.gc_km * RG_GC)).fillna(MED_LEG)   # no figure, no coordinates: a typical leg
G["filled"] = ~(G.dist > 0)
G = G[G.w.notna() & (G.w > 0)]
ids = sorted(set(G["from"]) | set(G["to"])); ix = {s: i for i, s in enumerate(ids)}
W = coo_matrix((G.w.values, (G["from"].map(ix).values, G["to"].map(ix).values)), shape=(len(ids), len(ids))).tocsr()
ncomp, lab = connected_components(W, directed=False)
DR, pred = dijkstra(W, directed=False, indices=ix["TPPlace1203"], return_predecessors=True)
comp_rome = lab[ix["TPPlace1203"]]
R["network"] = {"stations": len(ids), "components": int(ncomp), "rome_component": int((lab == comp_rome).sum()), "road_gc": round(RG_GC, 3), "median_leg_km": round(MED_LEG, 1),
                "rome_degree": int(((L["from"] == "TPPlace1203") | (L["to"] == "TPPlace1203")).sum()), "legs_filled": int(G.filled.sum())}
EDGE = {}
for r in G.itertuples():
    for a, b in ((r._2, r.to), (r.to, r._2)):
        if (a, b) not in EDGE or r.w < EDGE[(a, b)][0]:
            EDGE[(a, b)] = (r.w, r.filled, r.reconstructed)


def route(to):
    if to not in ix: return None
    d = DR[ix[to]]
    if not np.isfinite(d): return None
    path = [to]; j = ix[to]
    while j != ix["TPPlace1203"]:
        j = pred[j]; path.append(ids[j])
    steps = [EDGE[(a, b)] for a, b in zip(path[1:], path[:-1])]
    nrec = sum(1 for e in steps if e[2]); nfill = sum(1 for e in steps if e[1])
    regs_on = []
    for q in path[::-1]:
        g = P.region.get(q)
        if isinstance(g, str) and (not regs_on or regs_on[-1] != g): regs_on.append(g)
    return {"km": round(float(d)), "stations": len(path) - 1, "foot": round(float(d) / 22.5), "cart": round(float(d) / 45), "courier": round(float(d) / 80, 1),
            "gc_km": round(float(gc_km(41.89, 12.49, P.lat[to], P.lon[to]))), "recon_legs": int(nrec), "filled_legs": int(nfill), "legs": len(steps), "regions": regs_on, "label": P.label[to], "modern": P.modern[to] if isinstance(P.modern[to], str) else None}


R["routes"] = {n: route(s) for n, s in DEST}
RR = jload(f"{DATA}/road_routes.json")
for n, v in R["routes"].items():
    if v and RR.get(n):
        v["road_km"] = RR[n]; v["vs_road"] = round(v["km"] / RR[n], 2)
reach = [(DR[ix[s]], s) for s in ids if np.isfinite(DR[ix[s]]) and isinstance(P.label[s], str) and pd.notna(P.lat[s]) and P.kind[s] == "TP"]
fd, fs = max(reach)
R["farthest"] = {"km": round(float(fd)), "label": P.label[fs], "modern": P.modern[fs] if isinstance(P.modern[fs], str) else None, "id": fs,
                 "foot": round(float(fd) / 22.5), "cart": round(float(fd) / 45), "courier": round(float(fd) / 80),
                 "lat": None if pd.isna(P.lat[fs]) else round(float(P.lat[fs]), 2), "lon": None if pd.isna(P.lon[fs]) else round(float(P.lon[fs]), 2)}
pd.DataFrame([{"to": n, **(v or {})} for n, v in R["routes"].items()]).to_csv(f"{DATA}/routes.csv", index=False)

# ---------- located places ----------
M = pd.read_csv(f"{DATA}/map_positions.csv")
M["id"] = "TPPlace" + M.tp_id.astype(str)
assert M.id.is_unique and M.id.isin(P.index).all()
M = M.join(P[["label", "modern", "classic", "lat", "lon", "province", "region", "symbol"]].rename(columns={"label": "tp_label"}), on="id")
M["seg"] = [next(s["seg"] for s in SEG if s["x0"] <= x < s["x1"]) for x in M.x]
M["scroll_frac"] = (M.x - MX0) / (MX1 - MX0)
Mg = M[M.lat.notna()].copy()
assert len(Mg) == len(M)
LAT0, LON0 = 38.0, 25.0
Mg["E"] = np.radians(Mg.lon - LON0) * 6371 * np.cos(np.radians(LAT0)); Mg["N"] = np.radians(Mg.lat - LAT0) * 6371
R["located"] = {"n": len(M), "high": int((M.conf == "high").sum()), "medium": int((M.conf == "medium").sum()),
                "regions": {g: int((M.region == g).sum()) for g in RNAMES}, "segments": {s["seg"]: int((M.seg == s["seg"]).sum()) for s in SEG},
                "min_per_segment": int(min((M.seg == s["seg"]).sum() for s in SEG))}

# overall shape
A = np.c_[Mg.E, Mg.N, np.ones(len(Mg))]
cx, *_ = np.linalg.lstsq(A, Mg.x, rcond=None); cy, *_ = np.linalg.lstsq(A, Mg.y, rcond=None)
r2 = lambda a, c, y: 1 - np.sum((a @ c - y) ** 2) / np.sum((y - y.mean()) ** 2)
ew = float(np.hypot(cx[0], cy[0])); ns = float(np.hypot(cx[1], cy[1]))
lon_lo, lon_hi = Mg.lon.min(), Mg.lon.max(); lat_lo, lat_hi = Mg.lat.min(), Mg.lat.max()
ew_km = float(np.radians(lon_hi - lon_lo) * 6371 * np.cos(np.radians((lat_lo + lat_hi) / 2))); ns_km = float(np.radians(lat_hi - lat_lo) * 6371)
R["shape"] = {"x_r2_E": round(float(r2(np.c_[Mg.E, np.ones(len(Mg))], np.linalg.lstsq(np.c_[Mg.E, np.ones(len(Mg))], Mg.x, rcond=None)[0], Mg.x)), 3),
              "y_r2_N": round(float(r2(np.c_[Mg.N, np.ones(len(Mg))], np.linalg.lstsq(np.c_[Mg.N, np.ones(len(Mg))], Mg.y, rcond=None)[0], Mg.y)), 3),
              "x_spearman_lon": round(float(spearmanr(Mg.lon, Mg.x).correlation), 3), "y_spearman_lat": round(float(spearmanr(-Mg.lat, Mg.y).correlation), 3),
              "ew_px_per_km": round(ew, 3), "ns_px_per_km": round(ns, 3),
              "ew_km": round(ew_km), "ns_km": round(ns_km), "real_ratio": round(ew_km / ns_km, 2), "scroll_ratio": round((MX1 - MX0) / (MY1 - MY0), 1),
              "west": P.label[Mg.loc[Mg.lon.idxmin(), "id"]], "east": P.label[Mg.loc[Mg.lon.idxmax(), "id"]],
              "north": P.label[Mg.loc[Mg.lat.idxmax(), "id"]], "south": P.label[Mg.loc[Mg.lat.idxmin(), "id"]],
              "cm_per_px": round(CM_PER_PX, 5)}
SH = R["shape"]
SH["squash"] = round(SH["scroll_ratio"] / SH["real_ratio"], 1)
# a simple, robust overall figure: the scroll's whole length over the real east-west span, and its height over the north-south span
SH["km_per_cm_ew"] = round(ew_km / PARCH_CM, 1); SH["km_per_cm_ns"] = round(ns_km / PARCH_H_CM, 1)
SH["stretch_whole"] = round(SH["km_per_cm_ns"] / SH["km_per_cm_ew"], 1)


def local(d):
    lat0, lon0 = d.lat.mean(), d.lon.mean()
    e = np.radians(d.lon - lon0) * 6371 * np.cos(np.radians(lat0)); n = np.radians(d.lat - lat0) * 6371
    A = np.c_[e, n, np.ones(len(d))]
    ax, *_ = np.linalg.lstsq(A, d.x, rcond=None); ay, *_ = np.linalg.lstsq(A, d.y, rcond=None)
    ew = float(np.hypot(ax[0], ay[0])); ns = float(np.hypot(ax[1], ay[1]))
    res = np.hypot(A @ ax - d.x, A @ ay - d.y)
    J = np.array([[ax[0], ax[1]], [ay[0], ay[1]]])           # d(x, y) / d(east, north)
    g = np.linalg.solve(J, [1.0, 0.0])                      # the ground direction drawn along the scroll, west to east
    brg = float((np.degrees(np.arctan2(g[0], g[1])) + 360) % 360)
    sv = np.linalg.svd(J, compute_uv=False)
    return ew, ns, float(np.median(res)), float(e.max() - e.min()), float(n.max() - n.min()), brg, float(sv[0] / sv[1])


# Voronoi share of the painted strip (1/10 resolution)
from scipy.spatial import cKDTree
gx, gy = np.meshgrid(np.arange(MX0, MX1, 10) + 5, np.arange(MY0, MY1, 10) + 5)
_, nn = cKDTree(np.c_[M.x, M.y]).query(np.c_[gx.ravel(), gy.ravel()])
vor = pd.Series(M.region.values[nn]).value_counts(normalize=True)
# land area of the provinces by region
PRV = jload(f"{DATA}/provinces.json")["features"]
EA = Transformer.from_crs(4326, 6933, always_xy=True)
area = {}
for f in PRV:
    g = f["properties"]["region"]; area[g] = area.get(g, 0) + stransform(EA.transform, shape(f["geometry"])).area / 1e6
emp = sum(area.values())
stn = TP[TP.region.notna()].region.value_counts(normalize=True)
regs = []
for g in RNAMES:
    d = Mg[Mg.region == g]
    row = {"region": g, "located": int(len(d)), "scroll_pct": round(100 * float(vor.get(g, 0)), 1), "stations_pct": round(100 * float(stn.get(g, 0)), 1),
           "land_pct": round(100 * area[g] / emp, 1) if g in area else None, "land_km2": round(area[g]) if g in area else None,
           "road_km": T["by_region"].get(g, {}).get("km"), "stations": int((TP.region == g).sum()), "recon_stations": int((OV.region == g).sum())}
    if len(d) >= 8:
        ew, ns, res, espan, nspan, brg, aniso = local(d)
        row.update({"ew_px_per_100km": round(100 * ew, 1), "ns_px_per_100km": round(100 * ns, 1), "ew_ns": round(ew / ns, 1),
                    "km_per_cm_ew": round(1 / (ew * CM_PER_PX), 1), "km_per_cm_ns": round(1 / (ns * CM_PER_PX), 1), "fit_res_px": round(res), "scroll_bearing": round(brg), "aniso": round(aniso, 1),
                    "span_ew_km": round(espan), "span_ns_km": round(nspan)})
    row["space_ratio"] = round(row["scroll_pct"] / row["land_pct"], 2) if row["land_pct"] else None
    regs.append(row)
RG = pd.DataFrame(regs)
RG.to_csv(f"{DATA}/regions.csv", index=False)
R["regions"] = {r["region"]: r for r in regs}
GR = R["regions"]
st = RG.dropna(subset=["aniso"])
R["stretch_rank"] = st.sort_values("aniso", ascending=False).region.tolist()
R["stretch_median"] = round(float(st.aniso.median()), 1)
R["ew_ns_median"] = round(float(st.ew_ns.median()), 1)
sp = RG.dropna(subset=["space_ratio"]).sort_values("space_ratio", ascending=False)
R["space_rank"] = sp.region.tolist()
R["scroll_rank"] = RG.sort_values("scroll_pct", ascending=False).region.tolist()

# ---------- Rome ----------
rome = M[M.id == "TPPlace1203"].iloc[0]
segw = [s["x1"] - s["x0"] for s in SEG]
mw = float(np.median(segw)); Wd = MX1 - MX0; xr = rome.x - MX0
R["rome"] = {"x": int(rome.x), "y": int(rome.y), "frac": round(100 * xr / Wd, 1), "seg": rome.seg, "seg_median_px": round(mw),
             "frac_one_lost": round(100 * (xr + mw) / (Wd + mw), 1), "lost_for_centre": round((Wd - 2 * xr) / mw, 1),
             "y_frac": round(100 * (rome.y - MY0) / (MY1 - MY0)), "degree": R["network"]["rome_degree"],
             "cm_from_left": round(xr * CM_PER_PX), "cm_from_right": round((MX1 - rome.x) * CM_PER_PX)}
R["rome"]["lost_for_centre_int"] = int(round(R["rome"]["lost_for_centre"]))
R["rome"]["frac_k_lost"] = round(100 * (xr + R["rome"]["lost_for_centre_int"] * mw) / (Wd + R["rome"]["lost_for_centre_int"] * mw), 1)
# where the middle of the surviving scroll falls
mid = MX0 + Wd / 2
near = M.iloc[(M.x - mid).abs().argsort()[:1]].iloc[0]
R["rome"]["middle_place"] = near.tp_label; R["rome"]["middle_modern"] = near.modern; R["rome"]["middle_seg"] = near.seg
R["segments"] = [{"seg": s["seg"], "x0": s["x0"], "x1": s["x1"], "w": s["x1"] - s["x0"], "located": int((M.seg == s["seg"]).sum()),
                  "main": M[M.seg == s["seg"]].region.value_counts().index[0]} for s in SEG]

# ---------- thin-plate fits for the page and figures ----------
from scipy.interpolate import RBFInterpolator
XYgeo = np.c_[Mg.E, Mg.N]
rbf_x = RBFInterpolator(XYgeo, Mg.x.values, kernel="thin_plate_spline", smoothing=5.0)
rbf_y = RBFInterpolator(XYgeo, Mg.y.values, kernel="thin_plate_spline", smoothing=5.0)
# contour lines on the modern map: where each parchment join falls (only within 250 km of a located place)
lon_g = np.arange(-6, 92, .25); lat_g = np.arange(5, 55.01, .25)
LO, LA = np.meshgrid(lon_g, lat_g)
EE = np.radians(LO - LON0) * 6371 * np.cos(np.radians(LAT0)); NN = np.radians(LA - LAT0) * 6371
XX = rbf_x(np.c_[EE.ravel(), NN.ravel()]).reshape(LO.shape)
dd, _ = cKDTree(XYgeo).query(np.c_[EE.ravel(), NN.ravel()])
XX[(dd.reshape(LO.shape) > 250)] = np.nan
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
cs = plt.contour(LO, LA, XX, levels=[s["x0"] for s in SEG[1:]])
joins = []
for lev, segs in zip(cs.levels, cs.allsegs):
    name = next(s["seg"] for s in SEG if s["x0"] == lev)
    prev = SEG[[s["seg"] for s in SEG].index(name) - 1]["seg"]
    for c in segs:
        if len(c) >= 4:
            joins.append({"type": "Feature", "properties": {"join": f"{prev}/{name}"}, "geometry": {"type": "LineString", "coordinates": [[round(a, 2), round(b, 2)] for a, b in c[::2]]}})
plt.close("all")
# modern coastlines bent onto the scroll (land within 150 km of a located place), in facsimile pixels
from shapely.geometry import shape as _shape, LineString as _LS
LAND = jload(f"{DATA}/land.json")["features"]
warp = []
tr_geo = cKDTree(XYgeo)
for f in LAND:
    for ring in f["geometry"]["coordinates"]:
        co = np.array(ring)
        e = np.radians(co[:, 0] - LON0) * 6371 * np.cos(np.radians(LAT0)); nn_ = np.radians(co[:, 1] - LAT0) * 6371
        dd_, _ = tr_geo.query(np.c_[e, nn_])
        px = rbf_x(np.c_[e, nn_]); py = rbf_y(np.c_[e, nn_])
        ok = (dd_ <= 150) & (px > MX0 - 50) & (px < MX1 + 50) & (py > MY0 - 80) & (py < MY1 + 80)
        run = []
        for a, b, k in zip(px, py, ok):
            if k: run.append((a, b))
            else:
                if len(run) >= 3: warp.append(run)
                run = []
        if len(run) >= 3: warp.append(run)
warp = [[[int(round(a)), int(round(b))] for a, b in _LS(r).simplify(2.0).coords] for r in warp]
R["warp"] = {"smoothing": 5.0, "joins": len(joins), "lines": len(warp), "km": 150}

# ---------- tables ----------
Lout = L[["id", "from", "to", "from_label", "to_label", "dist", "zone", "unit_km", "stated_km", "gc_km", "road_km", "gc_ratio", "road_ratio", "region",
          "reconstructed", "flag_reconstructed", "over_water", "mountains", "river"]].copy()
Lout.round(3).to_csv(f"{DATA}/legs_measured.csv", index=False)
Mo = M[["tp_id", "id", "label", "tp_label", "modern", "classic", "lat", "lon", "province", "region", "symbol", "x", "y", "conf", "seg", "scroll_frac"]].copy()
Mo.round(4).to_csv(f"{DATA}/located.csv", index=False)

# ---------- page data ----------
RI = {g: i for i, g in enumerate(RNAMES)}
legs_by = {}
for r in L.itertuples():
    for a, b in ((r._2, r.to), (r.to, r._2)):
        legs_by.setdefault(a, []).append([b, None if pd.isna(r.dist) else (int(r.dist) if float(r.dist).is_integer() else float(r.dist)),
                                          r.zone[0], None if pd.isna(r.stated_km) else round(r.stated_km), None if pd.isna(r.gc_km) else round(r.gc_km),
                                          None if pd.isna(r.road_km) else round(r.road_km), 1 if r.reconstructed else 0])
loc_ids = set(M.id)
stations = []
for i, r in P[P.lat.notna()].iterrows():
    stations.append([i, r.label, r.modern if isinstance(r.modern, str) else "", RI.get(r.region, 11), round(r.lat, 3), round(r.lon, 3), 1 if r.kind == "OV" else 0,
                     1 if i in loc_ids else 0, r.province if isinstance(r.province, str) else ""])
loc_rows = [[r.id, r.tp_label, r.modern if isinstance(r.modern, str) else "", RI[r.region], int(r.x), int(r.y), r.conf, round(r.lat, 3), round(r.lon, 3), r.seg,
             r.province if isinstance(r.province, str) else ""] for r in M.itertuples()]
names = {i: P.label[i] for i in set(L["from"]) | set(L["to"]) if isinstance(P.label[i], str)}
leg_lines = []
for r in L[L.gc_km.notna()].itertuples():
    q = r.road_ratio if pd.notna(r.road_ratio) else (r.gc_ratio / R["dist"]["gc_median"] * R["dist"]["road_median"] if pd.notna(r.gc_ratio) else None)
    cls = -1 if q is None else (0 if 1 / 1.25 <= q <= 1.25 else (1 if 1 / 1.6 <= q <= 1.6 else 2))
    leg_lines.append([round(r.from_lon, 3), round(r.from_lat, 3), round(r.to_lon, 3), round(r.to_lat, 3), 1 if r.reconstructed else 0, cls])
site = {"regions": [[g, RCOL[g]] for g in RNAMES], "located": loc_rows, "loc_cols": ["id", "label", "modern", "reg", "x", "y", "conf", "lat", "lon", "seg", "prov"],
        "stations": stations, "st_cols": ["id", "label", "modern", "reg", "lat", "lon", "recon", "loc", "prov"],
        "legs_by": legs_by, "names": names, "leg_lines": leg_lines, "joins": {"type": "FeatureCollection", "features": joins},
        "segments": SEG, "fit": {"x0": FIT["x0"], "y0": FIT["y0"], "crop": FIT["crop"], "world7": FIT["world7"], "maxzoom": FIT["tile_maxzoom"],
                                 "small": "img/tabula_small.jpg", "small_wh": FIT["img_small"], "map_x": FIT["map_x"], "map_y": FIT["map_y"]},
        "rome": [int(rome.x), int(rome.y)], "region_stats": regs, "warp": warp}
jsave(site, f"{DATA}/site.json")
R["meta"] = {"page": PAGE, "repo": REPO, "slug": SLUG, "ov_url": OV_URL, "miller_url": MILLER_URL, "itinere_doi": ITINERE_DOI}
jsave(R, f"{DATA}/results.json", indent=1)
print(json.dumps({k: R[k] for k in ("source", "units", "dist", "total", "shape", "rome", "farthest", "network")}, indent=0, default=str)[:6000])
print(RG.to_string())
print({k: (v or {}).get("km") for k, v in R["routes"].items()})
