"""README.md, LICENSE and reddit/post.md, with numbers from data/results.json."""
from common import *

R = jload(f"{DATA}/results.json")
s, u, d, sh, ro, t, g, lo = R["source"], R["units"], R["dist"], R["shape"], R["rome"], R["total"], R["regions"], R["located"]
rt = R["routes"]
N = lambda v: f"{round(v):,}"
readme = f"""# The Peutinger Table against a modern map

The Peutinger Table (Tabula Peutingeriana), a Roman road map about {s['parchment_m']:.2f} m long and {s['parchment_cm_high']:.0f} cm high, set against a modern map: {lo['n']} places located by eye on Konrad Miller's 1887 facsimile, {N(s['legs'])} road legs from OmnesViae measured as straight lines and along the Itiner-e network of Roman roads, and how far the shape is wrong while the distances are right.

Interactive page: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}

## Headline results

- Units: one written unit covers a median {u['Mile']['km_per_unit_gc']:.2f} km in a straight line outside Gaul ({N(u['Mile']['n'])} legs) and {u['League']['km_per_unit_gc']:.2f} km in Aquitania, Lugdunensis, Belgica and the Germanies ({u['League']['n']} legs), {u['league_over_mile']:.2f} times as much: Roman miles and Gallic leagues. In Persia and India one unit ranges from {u['far_east_min']:.1f} to {u['far_east_max']:.1f} km ({u['Far east']['n']} legs).
- Distances: for {N(d['n_road'])} surviving legs with a road distance, the median road is {d['road_median']:.2f} of the stated distance and the median straight line {d['gc_median']:.2f}; {d['road_within25_pct']:.0f}% agree with the road to within 25%, {d['road_within50_pct']:.0f}% within 50%. Rome to Vienna: {N(rt['Vienna']['km'])} km by the map, {N(rt['Vienna']['road_km'])} km along Itiner-e; to Constantinople {N(rt['Constantinople']['km'])} against {N(rt['Constantinople']['road_km'])}; to Jerusalem {N(rt['Jerusalem']['km'])} against {N(rt['Jerusalem']['road_km'])}.
- Shape: {sh['km_per_cm_ew']:.1f} km per cm of parchment east to west, {sh['km_per_cm_ns']:.1f} km north to south, a compression of {sh['stretch_whole']:.1f}. Most stretched region: North Africa ({g['North Africa']['aniso']:.0f} times); least: Persia and India ({g['Persia, Central Asia and India']['aniso']:.1f}).
- Space: Italy has {g['Italy and islands']['scroll_pct']:.1f}% of the surviving scroll for {g['Italy and islands']['land_pct']:.1f}% of the land of the provinces ({g['Italy and islands']['space_ratio']:.2f} times its share); Mesopotamia {g['Mesopotamia and Armenia']['space_ratio']:.2f}, Greece and Thrace {g['Greece and Thrace']['space_ratio']:.2f}; Egypt {g['Egypt and Cyrene']['space_ratio']:.2f}.
- Rome: {ro['frac']:.1f}% of the way along the surviving strip; {ro['frac_one_lost']:.1f}% with one lost sheet; central with about {ro['lost_for_centre']:.1f} lost sheets.
- Total: about {N(t['km'])} km of road written on the surviving sheets ({N(t['rm_mile_zone'])} Roman miles, {N(t['leagues'])} leagues, {N(t['far_units'])} far-eastern units), {N(t['days']['foot'])} days on foot or {N(t['days']['courier'])} by courier relay. The reconstructed west adds about {N(R['recon']['stated_km'])} km.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/05_build_site.py`; page data embedded; facsimile tiles in `tiles/`; loads `data/provinces.json`). |
| `header.png` | Social card, 1200 x 630. |
| `tiles/` | Miller's 1887 facsimile as 256 px JPEG tiles, zooms 0 to 7 (public domain). |
| `img/tabula_small.jpg`, `img/tabula_fig.jpg` | The facsimile at 4,000 and 9,000 px wide (fallback view, figures). |
| `data/places.csv` | All {N(s['places'])} OmnesViae stations: id, kind (TP surviving, OV reconstructed), name on the map, classical and modern names, coordinates, symbol, DARE province, region, distance to a Pleiades match. |
| `data/legs.csv` | All {N(s['legs'])} legs as exported, with the reconstructed flag and road distance. |
| `data/legs_measured.csv` | The legs with unit zone, stated km, straight-line and road km and their ratios. |
| `data/map_positions.csv` | My by-eye positions on the facsimile (input). |
| `data/located.csv` | The {lo['n']} located places with names, coordinates, province, region, sheet and position. |
| `data/regions.csv` | Region table: located places, share of scroll and land, stretch, km per cm, road km. |
| `data/routes.csv` | Journeys from Rome by the map's figures and along Itiner-e. |
| `data/results.json`, `data/site.json`, `data/fit.json`, `data/world.json`, `data/land.json`, `data/provinces.json`, `data/road_meta.json`, `data/road_routes.json`, `data/sources.json` | Every number used; page data; image frame and sheet joins; outlines; road matching settings and long routes; source facts. |
| `code/` | Scripts, run in order, the page, paper and blog templates, and `qa.js`. |
| `release/` | Paper (`paper/`), blog post and figures (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |

## Method in brief

- Places on the scroll: {lo['n']} stations read on Miller's facsimile at full resolution, sheet by sheet, at the station picture or the start of its label ({lo['high']} clear, {lo['medium']} with some doubt), matched to OmnesViae by written name. At least {lo['min_per_segment']} per sheet.
- Units: leagues ({LEAGUE_KM} km) in Aquitania, Lugdunensis, Belgica and the Germanies; Roman miles ({RM_KM} km) elsewhere; unknown in Persia and India.
- Distances: great circle between OmnesViae coordinates; road distance along Itiner-e, each station put on the nearest road within {d['snap_km']:.0f} km, shortest path kept if at most twice the straight line plus 10 km.
- Shape: whole-strip spans against parchment size; per region, an affine fit from ground km to scroll pixels, stretch = ratio of its singular values. Space: each pixel of the strip given to the region of its nearest located place, against the land of the DARE provinces of about AD 117.
- Rome: position along the painted strip, with lost sheets of median width added at the western end.
- Totals and journeys: written figures converted and added; shortest routes from Rome over all legs ({R['network']['legs_filled']} legs without a figure filled in); 22.5, 45 and 80 km a day (Wikipedia).
- Caveats: OmnesViae's identifications used as given; positions by eye on a facsimile; units by province; Itiner-e roads lean long; affine fits are rough; scroll shares depend on the located sample. The reconstructed west (OmnesViae's OV stations, from the Antonine Itinerary) is reported separately throughout.

## How to rerun

Needs Python 3 with numpy, pandas, scipy, shapely, pyproj, matplotlib, Pillow and fontTools, xelatex and pdftotext; node with Playwright for `code/qa.js`. Steps 01 to 03 read `raw/` (not published: `omnesviae.json` and the facsimile), the roman-roads study's network, DARE provinces, Pleiades, the Wikipedia text and Natural Earth (paths in `code/common.py`); from step 04 on only `data/`, `img/` and `tiles/` are needed. Intermediate files go to `/dev/shm/peutinger/work` (set `PTTMP` to change).

```
python3 code/01_parse.py        # stations, legs, provinces, Pleiades check, outlines
python3 code/02_roads.py        # road distances along Itiner-e
python3 code/03_image.py        # tiles, web images, sheet joins
python3 code/04_results.py      # results.json, tables, page data
python3 code/05_build_site.py   # index.html
python3 code/06_figures.py      # header, blog and paper figures
python3 code/07_paper.py        # paper PDF
python3 reddit/collage.py       # collage
python3 code/08_readme.py       # README, LICENSE, Reddit post
python3 code/09_release.py      # blog post, Zenodo files
```

## Sources and licences

- OmnesViae: Roman routeplanner, by René Voorburg, {OV_URL}, JSON-LD export, built on Talbert, R. J. A. (2010) Rome's World: the Peutinger Map Reconsidered (Cambridge University Press) and Pleiades. No licence is stated; used here as factual data, with credit to OmnesViae and Talbert.
- Miller, K. (1887) Castori Romanorum cosmographi tabula quae dicitur Peutingeriana, facsimile, Wikimedia Commons ({MILLER_URL}), public domain.
- Itiner-e: the digital atlas of ancient roads (de Soto, Pažout, Brughmans et al. 2025), https://doi.org/{ITINERE_DOI}, CC BY 4.0, as prepared in the roman-roads study.
- Digital Atlas of the Roman Empire (DARE, Johan Åhlfeldt), province outlines, CC BY-SA.
- Pleiades: a gazetteer of past places, version {s['pleiades_version']}, https://pleiades.stoa.org/, CC BY 3.0.
- English Wikipedia, "Roman roads" (revision {R['speeds']['wiki_revid']}), CC BY-SA 4.0, for travel speeds.
- Natural Earth (public domain). Optional relief tiles on the page: Esri.

## Citation

Hotham, T. (2026) The Peutinger Table against a modern map: shape, space and distance on a Roman road map. Zenodo. https://doi.org/{DOI}

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

{AI}
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)

lic = open("/home/claude/studies/rocket-launches/LICENSE", encoding="utf-8").read().split("\n\n\nThis licence covers")[0]
lic += """


This licence covers the code in code/, reddit/collage.py and the page scripts.
The text of the page, paper and blog post, the figures and the derived data
files in data/ are released under CC BY 4.0. Konrad Miller's 1887 facsimile of
the Tabula Peutingeriana (tiles/ and img/, from Wikimedia Commons) is in the
public domain. Station names, identifications, coordinates and leg distances
come from OmnesViae (René Voorburg, omnesviae.org), after Richard Talbert's
Rome's World (2010); no licence is stated for that data, which is used here as
factual data with credit. Road distances are derived from Itiner-e (CC BY 4.0).
Province outlines in data/provinces.json are derived from the Digital Atlas of
the Roman Empire (DARE, Johan Åhlfeldt), CC BY-SA. Pleiades matches are derived
from Pleiades (pleiades.stoa.org), CC BY 3.0. Facts quoted from Wikipedia are
CC BY-SA 4.0. Natural Earth is public domain.
"""
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write(lic)

post = f"""## Title

[OC] I put the Peutinger Table, a 6.75 m Roman road map, next to a real map. It squashes the world {sh['stretch_whole']:.0f}x north to south, but {d['road_within25_pct']:.0f}% of its road distances are within 25% of the real road

## Body

The Peutinger Table is a medieval copy of a Roman map of the roads from Britain to India, on a strip of parchment about {s['parchment_m']:.2f} m long and {s['parchment_cm_high']:.0f} cm high. I found {lo['n']} of its places by eye on an 1887 facsimile and measured {N(d['n_road'])} of its road legs against the Roman road network mapped by the Itiner-e project. One cm of parchment covers about {sh['km_per_cm_ew']:.0f} km east to west but {sh['km_per_cm_ns']:.0f} km north to south. Yet the numbers hold up: in northern Gaul each unit covers {u['league_over_mile']:.2f} times as much ground as elsewhere, exactly the switch from Roman miles to Gallic leagues the map announces at Lyon, and by its own figures Rome to Vienna is {N(rt['Vienna']['km'])} km against {N(rt['Vienna']['road_km'])} km along the mapped roads. Rome is only {ro['frac']:.0f}% of the way along what survives; it would be central if about {ro['lost_for_centre']:.0f} sheets are lost, not one. Caveats: positions located by eye; identifications from OmnesViae and Talbert used as given. Interactive side-by-side map: {PAGE}

## Source comment

Sources: OmnesViae (René Voorburg) after Richard Talbert's Rome's World (2010), for stations and distances; Konrad Miller's 1887 facsimile (Wikimedia Commons, public domain); Itiner-e Roman roads (CC BY 4.0); DARE provinces (CC BY-SA); Pleiades (CC BY 3.0); Natural Earth.

Tools: Python (pandas, scipy, shapely, matplotlib); MapLibre for the interactive maps.

Interactive version: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}
"""
for t_ in (readme, post, lic):
    for bad in ("—", "–", "--", "DSIT", "DCMS"):
        assert bad not in t_.replace("```", "").replace("|---|---|", ""), bad
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(post)
print("readme, licence, post ok")
