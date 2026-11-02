"""Header card, blog figures (release/blog/b_*.png, 1800 px wide) and paper figures (release/paper/f_*.png).
Numbers from data/results.json; positions from data/located.csv and data/site.json."""
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from figstyle import *

R = jload(f"{DATA}/results.json"); SITE = jload(f"{DATA}/site.json")
BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
LOC = pd.read_csv(f"{DATA}/located.csv")
LOC["col"] = LOC.region.map(RCOL)
LEGS = pd.read_csv(f"{DATA}/legs_measured.csv")
FAC, PX, KF = facsimile()
HALO = [pe.withStroke(linewidth=3.2, foreground="#FFFCF4")]
MX0, MX1 = FIT["map_x"]; MY0, MY1 = FIT["map_y"]
GEOEXT = (-8, 90, 6, 56)


PHOTO = {"maps", "warp"}          # figures built on the facsimile: JPEG in the paper, to keep the PDF small


def both(fig, name, blog=True):
    if name in PHOTO:
        fig.savefig(f"{WORK}/tmp.png", dpi=200, facecolor=fig.get_facecolor())
        Image.open(f"{WORK}/tmp.png").convert("RGB").save(os.path.join(PA, "f_" + name + ".jpg"), quality=85, optimize=True)
    else:
        fig.savefig(os.path.join(PA, "f_" + name + ".png"), dpi=200, facecolor=fig.get_facecolor())
    if blog:
        fn = os.path.join(BL, "b_" + name + ".png")
        fig.savefig(fn, dpi=150, facecolor=fig.get_facecolor())
        if name in PHOTO:
            Image.open(fn).convert("RGB").save(fn, optimize=True)
    plt.close(fig)


def label(ax, x, y, t, dx=0, dy=0, ha="left", fs=10, col=FG, weight=None, halo=HALO):
    ax.annotate(t, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va="center", fontsize=fs, color=col, path_effects=halo, zorder=8, fontweight=weight)


def strip(ax, x0=MX0, x1=MX1, y0=MY0 - 40, y1=MY1 + 30, dots=True, s=8, lw=.3):
    a, b = PX([x0, x1], [y0, y1])
    ax.imshow(FAC.crop((int(a[0]), int(b[0]), int(a[1]), int(b[1]))), extent=(x0, x1, y1, y0), interpolation="lanczos")
    if dots:
        d = LOC[(LOC.x >= x0) & (LOC.x <= x1)]
        ax.scatter(d.x, d.y, s=s, c=d.col, edgecolors="white", linewidths=lw, zorder=5)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis("off")


def region_legend(fig, x, y, ncol=6, fs=9.5, regs=None):
    regs = regs or [g for g in RNAMES if (LOC.region == g).any()]
    fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=RCOL[g], mec="white", ms=7.5, label=g) for g in regs], loc="upper left",
               bbox_to_anchor=(x, y), ncol=ncol, frameon=False, fontsize=fs, handletextpad=.2, columnspacing=1.0)


# ---------- 1. the scroll and the modern map ----------
P_ = pd.read_csv(f"{DATA}/places.csv").set_index("id")
seg = LEGS[LEGS.gc_km.notna()].copy()
for c in ("from", "to"):
    seg[c + "_lon"] = P_.lon.reindex(seg[c]).values; seg[c + "_lat"] = P_.lat.reindex(seg[c]).values
from matplotlib.collections import LineCollection
NAMED = (("TPPlace548", "Kent"), ("TPPlace730", "Lyon"), ("TPPlace1203", "Rome"), ("TPPlace60", "Carthage"), ("TPPlace2082", "Constantinople"),
         ("TPPlace2374", "Antioch"), ("TPPlace2779", "Persepolis"), ("TPPlace2798", "Muziris"))
fig = plt.figure(figsize=(12, 8.4), facecolor=BG)
XM = (MX0 + MX1) / 2
for row, (xa, xb) in enumerate(((MX0, XM), (XM, MX1))):
    ax = fig.add_axes([.01, .70 - row * .205, .98, .2])
    strip(ax, xa, xb, s=6, lw=.25)
    ax.set_ylim(MY1 + 300, MY0 - 330)
    for sg in SITE["segments"]:
        if xa <= (sg["x0"] + sg["x1"]) / 2 <= xb:
            ax.text((sg["x0"] + sg["x1"]) / 2, MY1 + 120, "sheet " + sg["seg"], ha="center", va="center", fontsize=7.5, color=MUT)
    for n, t in NAMED:
        r = LOC[LOC.id == n].iloc[0]
        if xa <= r.x <= xb:
            if t == "Carthage":
                ax.plot([r.x, r.x], [r.y, MY1 + 190], color=FG, lw=.7, zorder=6); ax.text(r.x, MY1 + 200, t, ha="center", va="top", fontsize=9, color=FG, zorder=7)
            else:
                ax.plot([r.x, r.x], [MY0 - 150, r.y], color=FG, lw=.7, zorder=6); ax.text(r.x, MY0 - 175, t, ha="center", va="bottom", fontsize=9, color=FG, zorder=7)
ax = fig.add_axes([.01, .02, .66, .45]); world(ax, (-10, 92, 6, 57), aspect_lat=34); ax.set_anchor("W")
for rec, col, al in ((False, "#C2412D", .55), (True, "#9A9284", .5)):
    s_ = seg[seg.reconstructed == rec]
    ax.add_collection(LineCollection([[(a, b), (c, d)] for a, b, c, d in zip(s_.from_lon, s_.from_lat, s_.to_lon, s_.to_lat)], colors=col, linewidths=.5, alpha=al, zorder=3))
ax.scatter(LOC.lon, LOC.lat, s=8, c=LOC.col, edgecolors="white", linewidths=.25, zorder=5)
OFFG = {"Kent": (-6, 6, "right"), "Lyon": (-6, -6, "right"), "Rome": (6, -8, "left"), "Carthage": (-6, -8, "right"), "Constantinople": (0, 10, "center"),
        "Antioch": (-6, -9, "right"), "Persepolis": (6, -6, "left"), "Muziris": (6, 0, "left")}
for n, t in NAMED:
    r = LOC[LOC.id == n].iloc[0]; dx, dy, ha = OFFG[t]
    label(ax, r.lon, r.lat, t, dx, dy, ha, fs=8.5)
fig.text(.01, .965, "The Peutinger Table and the same places today", fontproperties=DISPB, fontsize=17, color=FG)
fig.text(.01, .935, f"Top: Miller's 1887 facsimile in two halves, sheets II to XII, with the {R['located']['n']} places I located by eye. Bottom: the same places, and the", fontsize=8.6, color=MUT)
fig.text(.01, .915, "Tabula's road legs as straight lines (red: surviving sheets; grey: the lost west, rebuilt from the Antonine Itinerary).", fontsize=8.6, color=MUT)
fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=RCOL[g], mec="white", ms=7.5, label=g) for g in RNAMES if (LOC.region == g).any()],
           loc="upper left", bbox_to_anchor=(.69, .45), ncol=1, frameon=False, fontsize=9.5, handletextpad=.3, labelspacing=.6, title="Region", title_fontsize=9.5)
both(fig, "maps")

# ---------- 2. Italy, with the real coastline bent onto the scroll ----------
x0, x1 = 5000, 12600
fig = plt.figure(figsize=(12, 2.9), facecolor=BG)
ax = fig.add_axes([.01, .02, .98, .7]); strip(ax, x0, x1, dots=True, s=14, lw=.4)
for line in SITE["warp"]:
    a = np.array(line)
    if a[:, 0].max() < x0 or a[:, 0].min() > x1: continue
    ax.plot(a[:, 0], a[:, 1], color=BLUE, lw=1.6, alpha=.9, zorder=6, solid_capstyle="round")
for n, t, dx, dy in (("TPPlace1203", "Rome", 0, 16), ("TPPlace1140", "Ravenna", 0, -12), ("TPPlace1125", "Aquileia", 0, -12), ("TPPlace1466", "Naples", 0, 12),
                     ("TPPlace60", "Carthage", 0, 12), ("TPPlace1375", "Brindisi", 0, -12)):
    r = LOC[LOC.id == n].iloc[0]
    if x0 < r.x < x1: label(ax, r.x, r.y, t, dx, dy, "center", fs=9.5, weight="bold")
fig.text(.01, .9, "Italy on the scroll, with today's coastline bent to fit", fontproperties=DISPB, fontsize=16, color=FG)
fig.text(.01, .8, f"Blue: Natural Earth's coastline, carried onto the facsimile by a smooth surface through the {R['located']['n']} located places. The real Adriatic (top)", fontsize=8.6, color=MUT)
fig.text(.01, .745, "and Tyrrhenian (middle) coasts fall on the Tabula's seas. Sheets IV to VII of Miller's facsimile.", fontsize=8.6, color=MUT)
both(fig, "warp")

# ---------- 3. units ----------
U = R["units"]["by_province"]
LEA = set(LEAGUE_PROVINCES)
D = sorted(U.items(), key=lambda kv: kv[1]["km_per_unit_gc"])
fig, ax = plt.subplots(figsize=(12, 6.4), facecolor=BG); ax.set_facecolor(BG); fig.subplots_adjust(left=.24, right=.97, top=.84, bottom=.1)
for i, (p, v) in enumerate(D):
    c = BLUE if p in LEA else RED
    ax.plot([v["q25"], v["q75"]], [i, i], color=c, lw=5, alpha=.3, solid_capstyle="butt")
    ax.scatter([v["km_per_unit_gc"]], [i], s=60, color=c, edgecolors="white", zorder=3)
for v, t in ((RM_KM, "Roman mile, 1.48 km"), (LEAGUE_KM, "Gallic league, 2.22 km")):
    ax.axvline(v, color=FG, ls=(0, (4, 3)), lw=1); ax.text(v, len(D) - .2, t, ha="center", va="bottom", fontsize=10, color=FG, bbox=dict(fc=BG, ec="none", pad=1.5))
ax.set_yticks(range(len(D))); ax.set_yticklabels([p for p, _ in D], fontsize=10.5); ax.tick_params(axis="y", length=0); spines(ax); ax.spines["left"].set_visible(False)
ax.set_xlim(.8, 3); ax.set_xlabel("km covered by one unit written on the map (median, straight line)"); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
fig.text(.02, .93, f"Leagues north of Lyon: one unit covers {R['units']['league_over_mile']:.2f} times as much ground in Gaul", fontproperties=DISPB, fontsize=16, color=FG)
fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc=BLUE, mec="white", ms=9, label="Aquitania, Lugdunensis, Belgica, the Germanies"),
                    Line2D([], [], marker="o", ls="", mfc=RED, mec="white", ms=9, label="other provinces"),
                    Line2D([], [], color=MUT, lw=5, alpha=.4, label="middle half of legs")], loc="upper left", bbox_to_anchor=(.24, .9), ncol=3, frameon=False, fontsize=9.5)
both(fig, "units")

# ---------- 4. stated against road ----------
Dd = LEGS[(~LEGS.reconstructed) & (LEGS.zone != "Far east") & LEGS.road_km.notna() & (LEGS.stated_km > 0)].copy()
Dd["region"] = Dd.region.fillna("Italy and islands")
fig, ax = plt.subplots(figsize=(12, 7.4), facecolor=BG); ax.set_facecolor(BG); fig.subplots_adjust(left=.08, right=.72, top=.86, bottom=.1)
xx = np.array([2, 300])
ax.fill_between(xx, xx * .8, xx * 1.25, color=RULE, alpha=.9, zorder=1)
ax.plot(xx, xx, color=FG, ls=(0, (4, 3)), lw=1, zorder=2)
for g in RNAMES:
    d = Dd[Dd.region == g]
    if len(d): ax.scatter(d.stated_km, d.road_km, s=12, color=RCOL[g], alpha=.6, lw=0, label=g, zorder=3)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(2, 300); ax.set_ylim(2, 300); spines(ax)
ax.set_xticks([5, 10, 20, 50, 100, 200]); ax.set_xticklabels(["5", "10", "20", "50", "100", "200"]); ax.set_yticks([5, 10, 20, 50, 100, 200]); ax.set_yticklabels(["5", "10", "20", "50", "100", "200"])
ax.set_xlabel("km written on the map (miles or leagues, converted)"); ax.set_ylabel("km along the Roman road (Itiner-e)")
ax.legend(loc="center left", bbox_to_anchor=(1.02, .5), frameon=False, fontsize=10, markerscale=2)
ax.text(2.4, 2.4 * 1.25 * 1.7, "within 25%", fontsize=9.5, color=MUT, rotation=0)
fig.text(.02, .93, f"Wrong shape, right numbers: {R['dist']['road_within25_pct']:.0f}% of {R['dist']['n_road']:,} legs within 25% of the road distance", fontproperties=DISPB, fontsize=16, color=FG)
both(fig, "distance")

# ---------- 5. stretch ----------
RS = [r for r in SITE["region_stats"] if r.get("aniso")]
RS = sorted(RS, key=lambda r: r["aniso"])
fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG); ax.set_facecolor(BG); fig.subplots_adjust(left=.27, right=.95, top=.82, bottom=.12)
DIRS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
for i, r in enumerate(RS):
    ax.barh(i, np.log(r["aniso"]), color=RCOL[r["region"]], height=.62, alpha=.9)
    ax.text(np.log(r["aniso"]) + .05, i, f"{r['aniso']:.0f}x" if r["aniso"] >= 10 else f"{r['aniso']:.1f}x", va="center", fontsize=10.5, color=FG)
ax.set_yticks(range(len(RS))); ax.set_yticklabels([r["region"] for r in RS], fontsize=11); ax.tick_params(axis="y", length=0)
ax.set_xticks(np.log([1, 2, 5, 10, 20, 50])); ax.set_xticklabels(["1x", "2x", "5x", "10x", "20x", "50x"]); ax.set_xlim(0, np.log(90)); spines(ax); ax.spines["left"].set_visible(False)
ax.set_xlabel("parchment per km in the most-stretched direction, over the least (log)"); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
fig.text(.02, .93, f"A world pressed flat: {R['shape']['km_per_cm_ew']:.0f} km per cm east to west, {R['shape']['km_per_cm_ns']:.0f} km per cm north to south", fontproperties=DISPB, fontsize=16, color=FG)
fig.text(.02, .875, "Region by region, how unevenly the scroll stretches the ground (straight-line fit from ground to scroll, regions with at least 8 located places)", fontsize=9, color=MUT)
both(fig, "stretch")

# ---------- 6. space ----------
RS2 = SITE["region_stats"]
fig, ax = plt.subplots(figsize=(12, 6.6), facecolor=BG); ax.set_facecolor(BG); fig.subplots_adjust(left=.27, right=.95, top=.84, bottom=.1)
for i, r in enumerate(RS2[::-1]):
    ax.barh(i + .17, r["scroll_pct"], height=.32, color=RCOL[r["region"]])
    if r["land_pct"] is not None: ax.barh(i - .17, r["land_pct"], height=.32, color=MUT, alpha=.45)
    else: ax.text(.3, i - .17, "beyond the frontier", va="center", fontsize=8.5, color=MUT)
    if r.get("space_ratio"): ax.text(max(r["scroll_pct"], r["land_pct"] or 0) + .4, i, f"x{r['space_ratio']:.2f}", va="center", fontsize=10, color=FG)
ax.set_yticks(range(len(RS2))); ax.set_yticklabels([r["region"] for r in RS2[::-1]], fontsize=11); ax.tick_params(axis="y", length=0); spines(ax); ax.spines["left"].set_visible(False)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%")); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True); ax.set_xlim(0, 25)
fig.legend(handles=[Patch(color=RED, label="share of the surviving scroll (region colour)"), Patch(color=MUT, alpha=.45, label="share of the land of the provinces, about AD 117")],
           loc="upper left", bbox_to_anchor=(.27, .9), ncol=2, frameon=False, fontsize=9.5)
fig.text(.02, .93, f"Who gets the parchment: Italy has {R['regions']['Italy and islands']['space_ratio']:.1f} times its share of the land", fontproperties=DISPB, fontsize=16, color=FG)
both(fig, "space")

# ---------- 7. Rome along the scroll ----------
fig = plt.figure(figsize=(12, 5.2), facecolor=BG)
SEGS = SITE["segments"]; mw = R["rome"]["seg_median_px"]; X0 = SEGS[0]["x0"]; X1 = SEGS[-1]["x1"]
for row, lost in enumerate((0, 1, 3)):
    ax = fig.add_axes([.04, .62 - row * .25, .92, .16]); ax.axis("off")
    off = (3 - lost) * mw; base = off + lost * mw
    ax.set_xlim(0, (X1 - X0) + 3 * mw); ax.set_ylim(-1.2, 1.6)
    for k in range(lost):
        ax.add_patch(Rectangle((off + k * mw, -.5), mw - 30, 1, fill=False, ec=MUT, ls=(0, (4, 3)), lw=1)); ax.text(off + k * mw + mw / 2, 0, "lost", ha="center", va="center", fontsize=9, color=MUT)
    for s in SEGS:
        ax.add_patch(Rectangle((base + s["x0"] - X0, -.5), s["x1"] - s["x0"] - 30, 1, fc=LAND, ec="#CEC2A8", lw=.8))
        if row == 0: ax.text(base + (s["x0"] + s["x1"]) / 2 - X0, -1.05, s["seg"], ha="center", va="center", fontsize=9, color=MUT)
    L0, L1 = off, base + X1 - X0; mid = (L0 + L1) / 2; rx = base + R["rome"]["x"] - X0
    ax.plot([mid, mid], [-.8, .8], color=FG, ls=(0, (3, 3)), lw=1)
    ax.scatter([rx], [0], s=160, color=GOLD, edgecolors=FG, zorder=5)
    pct = 100 * (rx - L0) / (L1 - L0)
    ax.text(rx, 1.15, f"Rome {pct:.0f}% along", ha="center", fontsize=11, color=FG, fontweight="bold")
    ax.text(-200, 0, {0: "as it survives", 1: "one sheet lost", 3: "three sheets lost"}[lost], ha="right", va="center", fontsize=10, color=FG)
fig.subplots_adjust(left=.14)
for a in fig.axes: a.set_position([.15, a.get_position().y0, .82, a.get_position().height])
fig.text(.02, .93, f"Rome sits in the middle only if about {R['rome']['lost_for_centre']:.0f} sheets are lost", fontproperties=DISPB, fontsize=16, color=FG)
fig.text(.02, .88, "The eleven surviving sheets to scale (Miller's numbering), with sheets of median width added at the western end. Dashed line: the middle.", fontsize=9, color=MUT)
both(fig, "rome")

# ---------- 8. days from Rome ----------
RT = [(k, v) for k, v in R["routes"].items() if v and k != "Carthage"]
RT = sorted(RT, key=lambda kv: kv[1]["km"])
fig, ax = plt.subplots(figsize=(12, 6.2), facecolor=BG); ax.set_facecolor(BG); fig.subplots_adjust(left=.16, right=.95, top=.84, bottom=.1)
for i, (k, v) in enumerate(RT):
    c = MUT if v["recon_legs"] > v["legs"] / 4 else RED
    ax.barh(i, v["foot"], color=c, height=.6, alpha=.85); ax.barh(i, v["courier"], color=FG, height=.25)
    ax.text(v["foot"] + 2, i, f"{v['foot']} days on foot, {v['courier']:.0f} by courier ({v['km']:,} km)", va="center", fontsize=9.5, color=FG)
ax.set_yticks(range(len(RT))); ax.set_yticklabels([k for k, _ in RT], fontsize=11); ax.tick_params(axis="y", length=0); spines(ax); ax.spines["left"].set_visible(False)
ax.set_xlim(0, 300); ax.set_xlabel("days from Rome, adding up the Tabula's own figures"); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
fig.legend(handles=[Patch(color=RED, alpha=.85, label="on foot, 22.5 km a day"), Patch(color=FG, label="courier relay, 80 km a day"), Patch(color=MUT, alpha=.85, label="mostly on the rebuilt west")],
           loc="upper left", bbox_to_anchor=(.16, .9), ncol=3, frameon=False, fontsize=9.5)
fig.text(.02, .93, f"Days from Rome by the map: {R['routes']['Constantinople']['foot']} to Constantinople, {R['routes']['Jerusalem']['foot']} to Jerusalem on foot", fontproperties=DISPB, fontsize=16, color=FG)
both(fig, "days")

# ---------- 9. where the sheet joins fall (paper only) ----------
fig = plt.figure(figsize=(12, 6.4), facecolor=BG); ax = fig.add_axes([.01, .06, .98, .82])
world(ax, (-8, 60, 22, 56), aspect_lat=40)
ax.scatter(LOC.lon, LOC.lat, s=12, c=LOC.col, edgecolors="white", linewidths=.3, zorder=5)
for f in SITE["joins"]["features"]:
    c = np.array(f["geometry"]["coordinates"]); ax.plot(c[:, 0], c[:, 1], color=FG, lw=1.4, ls=(0, (3, 2)), zorder=6)
jl = {}
for f in SITE["joins"]["features"]:
    c = np.array(f["geometry"]["coordinates"]); j = f["properties"]["join"]
    if j not in jl or len(c) > len(jl[j]): jl[j] = c
for n_, (j, c) in enumerate(sorted(jl.items(), key=lambda kv: kv[1][:, 0].mean())):
    if n_ % 2: continue
    k = np.argmax(c[:, 1]); lo, la = c[k]
    if -8 < lo < 60 and 22 < la < 56: label(ax, lo, la, j, 0, 7, "center", fs=8.5)
fig.text(.01, .94, "Where the joins between the parchment sheets fall on the ground", fontproperties=DISPB, fontsize=16, color=FG)
fig.text(.01, .905, "Dashed: lines of equal position along the scroll at each join (every other one labelled), from a smooth fit through the located places, within 250 km of one.", fontsize=8.6, color=MUT)
both(fig, "joins", blog=False)

# ---------- header card 1200 x 630 ----------
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
a1 = fig.add_axes([.0, .5, 1, .17]); strip(a1, s=3, lw=.15)
fig.text(.04, .83, "Peutinger", fontproperties=DISP, fontsize=58, color=FG)
fig.text(.355, .83, "Table", fontproperties=DISP, fontsize=58, color=RED)
fig.text(.045, .74, "A Roman road map 6.75 m long, set against a modern one", fontproperties=SERP, fontsize=17, color=FG)
a3 = fig.add_axes([.02, .02, .58, .45]); world(a3, (-8, 72, 20, 56), aspect_lat=40); a3.set_anchor("W")
a3.scatter(LOC.lon, LOC.lat, s=6, c=LOC.col, edgecolors="white", linewidths=.2, zorder=5)
fig.text(.62, .38, f"{R['shape']['stretch_whole']:.0f}x", fontproperties=DISP, fontsize=40, color=RED)
fig.text(.62, .32, "squashed north to south", fontsize=11, color=FG)
fig.text(.62, .2, f"{R['dist']['road_within25_pct']:.0f}%", fontproperties=DISP, fontsize=40, color=BLUE)
fig.text(.62, .14, "of legs within 25% of the road", fontsize=11, color=FG)
fig.text(.62, .05, f"{R['located']['n']} places located · {R['total']['km']:,} km of road", fontsize=10, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG); plt.close(fig)
from PIL import Image as _I
assert _I.open(os.path.join(ROOT, "header.png")).size == (1200, 630)
for f in os.listdir(BL):
    if f.startswith("b_"): assert _I.open(os.path.join(BL, f)).size[0] == 1800, f
print("figures", sorted(os.listdir(BL)), sorted(os.listdir(PA)))
