"""Step 2. Road distance for every leg, along the Itiner-e network of Roman roads (via the earlier roman-roads study).

Method
  * The network: the roman-roads study's graph of Itiner-e road sections (data/network.json: nodes and edges with
    their length in km) and the sections' geometry (data/roads.geojson.gz, the same 14,769 sections, simplified).
    Its five short sea crossings are left out, so a road distance is always a land route.
  * Each station with coordinates is snapped to the nearest point on any road section within SNAP_KM (5 km); its
    position along that section (a share of the section's length) makes it a point on the graph. Stations farther
    than 5 km from every mapped road get no road distance.
  * Road distance of a leg = the shortest path between the two snapped points (along the section if both lie on the
    same one, otherwise out to an end of each section and across the graph). The snapping gaps are not added: a
    station a few km off the mapped line is taken to sit on the road (the network and the identifications are both
    approximate, and adding the gaps would inflate short legs). It is kept
    only when it is no more than DETOUR times the great-circle distance plus 10 km: a longer path means the network
    has no road there and the shortest path wanders round the gap.
Output: WORK/road.csv (leg id, road_km), merged into data/legs.csv by 03_image.py; data/road_meta.json."""
import numpy as np, pandas as pd
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from common import *

SNAP_KM, DETOUR = 5.0, 2.0
RG = os.path.join(os.path.dirname(ROADS), "roads.geojson.gz")
N = jload(ROADS); F = jload(RG)["features"]
E = np.array([e[:3] for e in N["edges"]], float); n = len(N["nodes"])
assert len(F) == len(E) and all(f["properties"]["from_node"] == int(e[0]) and f["properties"]["to_node"] == int(e[1]) for f, e in zip(F, E))
A = sp.coo_matrix((np.r_[E[:, 2], E[:, 2]], (np.r_[E[:, 0], E[:, 1]].astype(int), np.r_[E[:, 1], E[:, 0]].astype(int))), shape=(n, n)).tocsr()
print("network nodes", n, "sections", len(E), "km", round(E[:, 2].sum()))
LAT0 = 40.0
pj = lambda lon, lat: (np.radians(lon) * 6371 * np.cos(np.radians(LAT0)), np.radians(lat) * 6371)   # km, good enough to snap
lines = []
for f in F:
    c = np.array(f["geometry"]["coordinates"])
    x, y = pj(c[:, 0], c[:, 1]); lines.append(LineString(np.column_stack([x, y])))
tree = STRtree(lines)
P = pd.read_csv(f"{DATA}/places.csv").set_index("id")
L = pd.read_csv(f"{DATA}/legs.csv")
snap = {}
for i, r in P[P.lat.notna()].iterrows():
    x, y = pj(r.lon, r.lat); pt = Point(x, y)
    k = tree.nearest(pt)
    if lines[k].distance(pt) <= SNAP_KM * 1.5:          # rough test in the projected plane, then the true gap below
        frac = lines[k].project(pt, normalized=True)
        cx, cy = lines[k].interpolate(frac, normalized=True).coords[0]
        lon2 = np.degrees(cx / (6371 * np.cos(np.radians(LAT0)))); lat2 = np.degrees(cy / 6371)
        tg = float(gc_km(r.lat, r.lon, lat2, lon2))
        if tg <= SNAP_KM:
            snap[i] = (k, frac, tg)
print("stations with coordinates", int(P.lat.notna().sum()), "on a road within", SNAP_KM, "km:", len(snap))
ok = L["from"].isin(snap.keys()) & L["to"].isin(snap.keys())
Lk = L[ok].copy()
nodes = sorted({int(E[snap[s][0], j]) for s in set(Lk["from"]) | set(Lk["to"]) for j in (0, 1)})
D = dijkstra(A, directed=False, indices=nodes, limit=2500)
row = {v: i for i, v in enumerate(nodes)}
road = []
for a, b in zip(Lk["from"], Lk["to"]):
    ka, fa, ga = snap[a]; kb, fb, gb = snap[b]
    la, lb = E[ka, 2], E[kb, 2]
    if ka == kb:
        d = abs(fa - fb) * la
    else:
        ends_a = ((int(E[ka, 0]), fa * la), (int(E[ka, 1]), (1 - fa) * la))
        ends_b = ((int(E[kb, 0]), fb * lb), (int(E[kb, 1]), (1 - fb) * lb))
        d = min(da + D[row[u], v] + db for u, da in ends_a for v, db in ends_b)
    road.append(d)
Lk["road_km"] = road
Lk["gc_km"] = gc_km(P.lat.reindex(Lk["from"]).values, P.lon.reindex(Lk["from"]).values, P.lat.reindex(Lk["to"]).values, P.lon.reindex(Lk["to"]).values)
good = np.isfinite(Lk.road_km) & (Lk.road_km <= DETOUR * Lk.gc_km + 10) & (Lk.gc_km > 0)
Lk.loc[~good, "road_km"] = np.nan
Lk["road_km"] = np.maximum(Lk.road_km, Lk.gc_km)
print("legs with both ends on a road", len(Lk), "with a road distance", int(good.sum()))
Lk[["id", "road_km"]].round(2).to_csv(f"{WORK}/road.csv", index=False)
# long journeys from Rome along the network (no sea crossings), for comparison with the Tabula's own totals
rk = snap[ROME]; sr = [int(E[rk[0], 0]), int(E[rk[0], 1])]
DRo = dijkstra(A, directed=False, indices=sr)
jr = {}
for nm, t in DEST:
    if t not in snap: jr[nm] = None; continue
    kb, fb, gb = snap[t]; lb = E[kb, 2]
    ends_a = ((0, rk[1] * E[rk[0], 2]), (1, (1 - rk[1]) * E[rk[0], 2])); ends_b = ((int(E[kb, 0]), fb * lb), (int(E[kb, 1]), (1 - fb) * lb))
    d = min(da + DRo[i, v] + db for i, da in ends_a for v, db in ends_b)
    jr[nm] = round(float(d)) if np.isfinite(d) else None
print("road from Rome", jr)
jsave(jr, f"{DATA}/road_routes.json", indent=1)
jsave({"snap_km": SNAP_KM, "detour": DETOUR, "snapped": len(snap), "legs_snapped": len(Lk), "legs_road": int(good.sum()),
       "network_km": round(float(E[:, 2].sum())), "sections": len(E)}, f"{DATA}/road_meta.json", indent=1)
