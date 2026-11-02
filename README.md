# The Peutinger Table against a modern map

The Peutinger Table (Tabula Peutingeriana), a Roman road map about 6.75 m long and 34 cm high, set against a modern map: 465 places located by eye on Konrad Miller's 1887 facsimile, 3,523 road legs from OmnesViae measured as straight lines and along the Itiner-e network of Roman roads, and how far the shape is wrong while the distances are right.

Interactive page: https://maps.tristanhotham.com/peutinger/
Paper: https://doi.org/10.5281/zenodo.23882605
Blog post: https://blog.tristanhotham.com/2026/10/31/peutinger/

## Headline results

- Units: one written unit covers a median 1.41 km in a straight line outside Gaul (1,488 legs) and 2.15 km in Aquitania, Lugdunensis, Belgica and the Germanies (279 legs), 1.52 times as much: Roman miles and Gallic leagues. In Persia and India one unit ranges from 0.8 to 18.7 km (27 legs).
- Distances: for 1,558 surviving legs with a road distance, the median road is 1.10 of the stated distance and the median straight line 0.96; 53% agree with the road to within 25%, 70% within 50%. Rome to Vienna: 1,120 km by the map, 1,038 km along Itiner-e; to Constantinople 2,081 against 2,335; to Jerusalem 3,499 against 4,031.
- Shape: 12.6 km per cm of parchment east to west, 137.5 km north to south, a compression of 10.9. Most stretched region: North Africa (55 times); least: Persia and India (1.7).
- Space: Italy has 17.3% of the surviving scroll for 6.6% of the land of the provinces (2.62 times its share); Mesopotamia 2.29, Greece and Thrace 1.55; Egypt 0.24.
- Rome: 35.4% of the way along the surviving strip; 40.7% with one lost sheet; central with about 3.3 lost sheets.
- Total: about 79,414 km of road written on the surviving sheets (43,584 Roman miles, 4,598 leagues, 3,177 far-eastern units), 3,530 days on foot or 993 by courier relay. The reconstructed west adds about 17,313 km.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/05_build_site.py`; page data embedded; facsimile tiles in `tiles/`; loads `data/provinces.json`). |
| `header.png` | Social card, 1200 x 630. |
| `tiles/` | Miller's 1887 facsimile as 256 px JPEG tiles, zooms 0 to 7 (public domain). |
| `img/tabula_small.jpg`, `img/tabula_fig.jpg` | The facsimile at 4,000 and 9,000 px wide (fallback view, figures). |
| `data/places.csv` | All 3,322 OmnesViae stations: id, kind (TP surviving, OV reconstructed), name on the map, classical and modern names, coordinates, symbol, DARE province, region, distance to a Pleiades match. |
| `data/legs.csv` | All 3,523 legs as exported, with the reconstructed flag and road distance. |
| `data/legs_measured.csv` | The legs with unit zone, stated km, straight-line and road km and their ratios. |
| `data/map_positions.csv` | My by-eye positions on the facsimile (input). |
| `data/located.csv` | The 465 located places with names, coordinates, province, region, sheet and position. |
| `data/regions.csv` | Region table: located places, share of scroll and land, stretch, km per cm, road km. |
| `data/routes.csv` | Journeys from Rome by the map's figures and along Itiner-e. |
| `data/results.json`, `data/site.json`, `data/fit.json`, `data/world.json`, `data/land.json`, `data/provinces.json`, `data/road_meta.json`, `data/road_routes.json`, `data/sources.json` | Every number used; page data; image frame and sheet joins; outlines; road matching settings and long routes; source facts. |
| `code/` | Scripts, run in order, the page, paper and blog templates, and `qa.js`. |
| `release/` | Paper (`paper/`), blog post and figures (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |

## Method in brief

- Places on the scroll: 465 stations read on Miller's facsimile at full resolution, sheet by sheet, at the station picture or the start of its label (433 clear, 32 with some doubt), matched to OmnesViae by written name. At least 13 per sheet.
- Units: leagues (2.22 km) in Aquitania, Lugdunensis, Belgica and the Germanies; Roman miles (1.48 km) elsewhere; unknown in Persia and India.
- Distances: great circle between OmnesViae coordinates; road distance along Itiner-e, each station put on the nearest road within 5 km, shortest path kept if at most twice the straight line plus 10 km.
- Shape: whole-strip spans against parchment size; per region, an affine fit from ground km to scroll pixels, stretch = ratio of its singular values. Space: each pixel of the strip given to the region of its nearest located place, against the land of the DARE provinces of about AD 117.
- Rome: position along the painted strip, with lost sheets of median width added at the western end.
- Totals and journeys: written figures converted and added; shortest routes from Rome over all legs (249 legs without a figure filled in); 22.5, 45 and 80 km a day (Wikipedia).
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

- OmnesViae: Roman routeplanner, by René Voorburg, https://omnesviae.org/, JSON-LD export, built on Talbert, R. J. A. (2010) Rome's World: the Peutinger Map Reconsidered (Cambridge University Press) and Pleiades. No licence is stated; used here as factual data, with credit to OmnesViae and Talbert.
- Miller, K. (1887) Castori Romanorum cosmographi tabula quae dicitur Peutingeriana, facsimile, Wikimedia Commons (https://commons.wikimedia.org/wiki/File:TabulaPeutingeriana.jpg), public domain.
- Itiner-e: the digital atlas of ancient roads (de Soto, Pažout, Brughmans et al. 2025), https://doi.org/10.5281/zenodo.17122148, CC BY 4.0, as prepared in the roman-roads study.
- Digital Atlas of the Roman Empire (DARE, Johan Åhlfeldt), province outlines, CC BY-SA.
- Pleiades: a gazetteer of past places, version 4.1, https://pleiades.stoa.org/, CC BY 3.0.
- English Wikipedia, "Roman roads" (revision 1383149720), CC BY-SA 4.0, for travel speeds.
- Natural Earth (public domain). Optional relief tiles on the page: Esri.

## Citation

Hotham, T. (2026) The Peutinger Table against a modern map: shape, space and distance on a Roman road map. Zenodo. https://doi.org/10.5281/zenodo.23882605

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
