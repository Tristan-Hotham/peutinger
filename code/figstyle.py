"""House style for static figures: fonts (static instances cut from the variable Fraunces in /home/claude/ref/fonts,
written to WORK), the palette, Natural Earth outlines, and the facsimile image."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
import numpy as np
from PIL import Image
from common import *

FD = os.path.join(WORK, "fonts"); os.makedirs(FD, exist_ok=True)
if not os.path.exists(f"{FD}/Fraunces-Black.ttf"):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for w, nm in ((900, "Black"), (700, "Bold")):
        instancer.instantiateVariableFont(TTFont(f"{FONTS}/FrauncesVar.ttf"), {"wght": w, "opsz": 144, "SOFT": 0, "WONK": 0}).save(f"{FD}/Fraunces-{nm}.ttf")
DISP = fm.FontProperties(fname=f"{FD}/Fraunces-Black.ttf")
DISPB = fm.FontProperties(fname=f"{FD}/Fraunces-Bold.ttf")
SERP = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Regular.ttf")
SERI = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-It.ttf")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 12, "axes.edgecolor": "#68625A", "axes.labelcolor": "#22201C",
                     "xtick.color": "#68625A", "ytick.color": "#68625A"})
BG, FG, MUT, LAND, RULE, SEA = "#F7F2E7", "#22201C", "#68625A", "#E7DFCB", "#E0D6C1", "#E9EEEC"
RED, BLUE, GOLD, GREEN = "#B23A2A", "#2F5FA7", "#B07A12", "#2E8A6E"
W = jload(f"{DATA}/world.json")


def rings(geom):
    cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in cs:
        yield np.array(poly[0])


def world(ax, ext, land=LAND, ec="#FFFFFF", lw=.4, sea=SEA, aspect_lat=None):
    """Plate carree map with the cosine of the mid latitude as aspect, so shapes are not squashed."""
    ax.set_facecolor(sea)
    for f in W["features"]:
        for r in rings(f["geometry"]):
            ax.add_patch(MPoly(r, closed=True, fc=land, ec=ec, lw=lw, zorder=1))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_aspect(1 / np.cos(np.radians(aspect_lat if aspect_lat is not None else (ext[2] + ext[3]) / 2)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


def spines(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


FIT = jload(f"{DATA}/fit.json")


def facsimile():
    """The 9,000 px facsimile and a function from full-size facsimile pixels to its pixels."""
    im = Image.open(f"{IMG}/tabula_fig.jpg")
    c = FIT["crop"]; k = im.width / (c[2] - c[0])
    return im, (lambda x, y: ((np.asarray(x) - c[0]) * k, (np.asarray(y) - c[1]) * k)), k
