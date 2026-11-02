"""Reddit collage (2400 x 3200): the whole Peutinger Table in four rows, the same places on a modern map, and the
headline numbers. Light background; labels sit on plain sea or paper; numbers from data/results.json."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from figstyle import *

R = jload(f"{DATA}/results.json"); SITE = jload(f"{DATA}/site.json")
LOC = pd.read_csv(f"{DATA}/located.csv"); LOC["col"] = LOC.region.map(RCOL)
LEGS = pd.read_csv(f"{DATA}/legs_measured.csv"); P = pd.read_csv(f"{DATA}/places.csv").set_index("id")
FAC, PX, KF = facsimile()
MX0, MX1 = FIT["map_x"]; MY0, MY1 = FIT["map_y"]
HALO = [pe.withStroke(linewidth=3, foreground=SEA)]
fig = plt.figure(figsize=(8, 32 / 3), dpi=300, facecolor=BG)
fig.text(.05, .957, "The Roman road map that squashed the world", fontproperties=DISPB, fontsize=21, color=FG)
fig.text(.05, .922, "The Peutinger Table, set against a modern map", fontproperties=DISP, fontsize=24, color=RED)
fig.text(.05, .897, f"A strip of parchment {R['source']['parchment_m']:.2f} m long and {R['source']['parchment_cm_high']:.0f} cm high, from Kent to India. I found {R['located']['n']} of its", fontsize=8.2, color=MUT)
fig.text(.05, .883, "places by eye and measured its road legs against the Roman roads mapped today.", fontsize=8.2, color=MUT)

# the scroll in four rows
q = (MX1 - MX0) / 4
for i in range(4):
    x0, x1 = MX0 + i * q, MX0 + (i + 1) * q
    ax = fig.add_axes([.03, .768 - i * .093, .94, .082])
    a, b = PX([x0, x1], [MY0 - 30, MY1 + 25])
    ax.imshow(FAC.crop((int(a[0]), int(b[0]), int(a[1]), int(b[1]))), extent=(x0, x1, MY1 + 25, MY0 - 30), interpolation="lanczos")
    d = LOC[(LOC.x >= x0) & (LOC.x < x1)]
    ax.scatter(d.x, d.y, s=5, c=d.col, edgecolors="white", linewidths=.25, zorder=5)
    if MX0 <= R["rome"]["x"] and x0 <= R["rome"]["x"] < x1:
        ax.scatter([R["rome"]["x"]], [R["rome"]["y"]], s=60, facecolors="none", edgecolors=RED, linewidths=1.3, zorder=6)
    ax.set_xlim(x0, x1); ax.set_ylim(MY1 + 25, MY0 - 30); ax.axis("off"); ax.set_aspect("auto")
    segs = [s["seg"] for s in SITE["segments"] if s["x1"] > x0 and s["x0"] < x1]
    fig.text(.03, .768 - i * .093 + .084, f"sheets {segs[0]} to {segs[-1]}" + ("  ·  red ring: Rome" if x0 <= R["rome"]["x"] < x1 else ""), fontsize=6.6, color=MUT)

# the modern map
ax = fig.add_axes([.02, .135, .6, .32]); world(ax, (-9, 75, 22, 56), aspect_lat=40); ax.set_anchor("NW")
seg = LEGS[LEGS.gc_km.notna() & ~LEGS.reconstructed.astype(bool)].copy()
xy = [[(P.lon[a], P.lat[a]), (P.lon[b], P.lat[b])] for a, b in zip(seg["from"], seg["to"])]
ax.add_collection(LineCollection(xy, colors="#C2412D", linewidths=.35, alpha=.5, zorder=3))
ax.scatter(LOC.lon, LOC.lat, s=4.5, c=LOC.col, edgecolors="white", linewidths=.2, zorder=5)
for t, lo, la, ha in (("Rome", 10.6, 39.6, "center"), ("Carthage", 4.6, 38.1, "center"), ("Constantinople", 31.5, 43.6, "center"),
                      ("Antioch", 31.6, 35.6, "center")):
    ax.text(lo, la, t, ha=ha, va="center", fontsize=6.4, color=FG, path_effects=HALO, zorder=8)
fig.text(.03, .46, "The same places today", fontproperties=DISPB, fontsize=11, color=FG)
fig.text(.03, .447, "red lines: the Tabula's legs between stations", fontsize=6.8, color=MUT)

# legend under the map
regs = [g for g in RNAMES if (LOC.region == g).any()]
fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=RCOL[g], mec="white", ms=5.5, label=g) for g in regs], loc="upper left",
           bbox_to_anchor=(.03, .145), ncol=3, frameon=False, fontsize=6.4, handletextpad=.2, columnspacing=.9, labelspacing=.5)

# headline numbers
st = [(f"{R['shape']['stretch_whole']:.0f}x", RED, f"squashed: 1 cm of parchment covers {R['shape']['km_per_cm_ew']:.0f} km\neast to west but {R['shape']['km_per_cm_ns']:.0f} km north to south"),
      (f"{R['dist']['road_within25_pct']:.0f}%", BLUE, f"of {R['dist']['n_road']:,} legs agree with the Roman road\nto within 25%; the median road is\n{R['dist']['road_long_pct']}% longer than the written figure"),
      (f"{R['units']['league_over_mile']:.2f}", GREEN, "times more ground per unit in northern\nGaul: leagues, as the map's note at Lyon says"),
      (f"{R['rome']['frac']:.0f}%", GOLD, f"of the way along is Rome; it is central only\nif about {R['rome']['lost_for_centre']:.0f} lost sheets are added back"),
      (f"{R['total']['km']:,}", FG, f"km of road written on the surviving sheets:\n{R['total']['days']['foot']:,} days on foot")]
for i, (big, col, small) in enumerate(st):
    y = .465 - i * .074
    fig.text(.64, y, big, fontproperties=DISP, fontsize=17, color=col, va="top")
    fig.text(.64, y - .027, small, fontsize=6.2, color=FG, va="top", linespacing=1.3)
fig.text(.05, .033, "Data: OmnesViae (R. Voorburg) after Talbert's Tabula Peutingeriana; K. Miller's 1887 facsimile (public domain); Itiner-e roads",
         fontsize=5.9, color=MUT)
fig.text(.05, .022, "(CC BY 4.0); DARE provinces; Natural Earth. Places on the scroll located by eye. Dr Tristan Hotham · maps.tristanhotham.com/peutinger", fontsize=5.9, color=MUT)
out = os.path.join(ROOT, "reddit", "peutinger_table.png")
fig.savefig(out, dpi=300, facecolor=BG); plt.close(fig)
from PIL import Image
im = Image.open(out); assert im.size == (2400, 3200), im.size
im.convert("RGB").save(out, optimize=True)
print("collage", out, os.path.getsize(out) // 1024, "KB")
