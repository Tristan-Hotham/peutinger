"""Step 3. The facsimile for the web and the figures, the parchment segments, and the road distances merged into legs.

  * Crop: Miller's 1887 facsimile (26,381 x 2,014 px) is cut to the map and its margin, x 380 to 26,100 and y 180 to
    1,620 (CROP), 25,720 x 1,440 px. All positions in data/map_positions.csv are in full-size facsimile pixels.
  * Tiles: the crop is laid on a Web Mercator world 32,768 px wide (zoom 7) at one image pixel per world pixel,
    centred on the equator, and cut into 256 px JPEG tiles for zooms 0 to 7 (zoom 7 = full size).
    The page converts facsimile pixels to these pseudo coordinates (fit.json gives the offsets).
  * Images: img/tabula_small.jpg (4,000 px wide, the page's fallback) and img/tabula_fig.jpg (9,000 px wide, figures).
  * Segments: the solid vertical rules Miller printed in the top margin mark the joins of the eleven surviving
    parchment segments (II to XII); they are found as columns that are dark across the margin. The map's left and
    right edges are the first and last columns of painted map (MAP_X0, MAP_X1, read off the image).
Outputs: tiles/, img/, data/fit.json, data/legs.csv (with road_km)."""
import shutil
import numpy as np, pandas as pd
from PIL import Image
from common import *

Image.MAX_IMAGE_PIXELS = None
CROP = (380, 180, 26100, 1620)
MAP_X0, MAP_X1 = 455, 26020           # painted map, left (torn edge of segment II) and right (end of segment XII)
MAP_Y0, MAP_Y1 = 322, 1545            # top and bottom of the painted strip (outer sea bands included)
im = Image.open(f"{RAW}/tabula_peutingeriana_miller1887.jpg").convert("RGB")
FW, FH = im.size
g = np.asarray(im.convert("L").crop((0, 215, FW, 290))).astype(float)
dark = (g < 150).mean(axis=0)
cols = np.where(dark > 0.8)[0]
runs = []
for c in cols:
    if runs and c - runs[-1][-1] <= 3: runs[-1].append(c)
    else: runs.append([c])
bounds = [int(round(np.mean(r))) for r in runs if MAP_X0 < np.mean(r) < MAP_X1]
assert len(bounds) == 10, bounds                       # ten joins between eleven segments
edges = [MAP_X0] + bounds + [MAP_X1]
SEG = [{"seg": ["II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][i], "x0": edges[i], "x1": edges[i + 1]} for i in range(11)]
print("segment widths", [s["x1"] - s["x0"] for s in SEG])

C = im.crop(CROP); CW, CH = C.size
WORLD7 = 256 * 2 ** 7
X0, Y0 = (WORLD7 - CW) // 2, (WORLD7 - CH) // 2
T = os.path.join(ROOT, "tiles")
if os.path.exists(T): shutil.rmtree(T)
PAPER = (232, 222, 196)
ntiles, nbytes = 0, 0
for z in range(0, 8):
    s = 2 ** (z - 7)
    W = max(1, round(CW * s)); H = max(1, round(CH * s))
    Z = C.resize((W, H), Image.LANCZOS)
    ox, oy = X0 * s, Y0 * s
    for tx in range(int(ox // 256), int((ox + W - 1) // 256) + 1):
        for ty in range(int(oy // 256), int((oy + H - 1) // 256) + 1):
            tile = Image.new("RGB", (256, 256), PAPER)
            tile.paste(Z, (int(round(ox - tx * 256)), int(round(oy - ty * 256))))
            os.makedirs(f"{T}/{z}/{tx}", exist_ok=True)
            fn = f"{T}/{z}/{tx}/{ty}.jpg"; tile.save(fn, quality=72, optimize=True, progressive=True)
            ntiles += 1; nbytes += os.path.getsize(fn)
print("tiles", ntiles, nbytes // 1024, "KB")
for w, nm, q in ((4000, "tabula_small.jpg", 80), (9000, "tabula_fig.jpg", 80)):
    C.resize((w, round(CH * w / CW)), Image.LANCZOS).save(f"{IMG}/{nm}", quality=q, optimize=True, progressive=True)
print({f: os.path.getsize(f"{IMG}/{f}") // 1024 for f in os.listdir(IMG)})
jsave({"full": [FW, FH], "crop": list(CROP), "world7": WORLD7, "x0": X0, "y0": Y0, "tile_maxzoom": 7, "map_x": [MAP_X0, MAP_X1], "map_y": [MAP_Y0, MAP_Y1],
       "segments": SEG, "img_small": [4000, round(CH * 4000 / CW)], "img_fig": [9000, round(CH * 9000 / CW)], "tiles": ntiles, "tile_kb": nbytes // 1024},
      f"{DATA}/fit.json", indent=1)

# road distances into the leg table
L = pd.read_csv(f"{DATA}/legs.csv")
if "road_km" in L: L = L.drop(columns="road_km")
L = L.merge(pd.read_csv(f"{WORK}/road.csv"), on="id", how="left")
L.to_csv(f"{DATA}/legs.csv", index=False)
print("legs with road_km", int(L.road_km.notna().sum()))
