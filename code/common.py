"""Shared paths, groupings and helpers for the peutinger study ("The Peutinger Table against a modern map").

Raw inputs (raw/, read in place, never modified; steps 04 onward and the release run without raw/):
  raw/omnesviae.json
      JSON-LD export of OmnesViae (René Voorburg, https://omnesviae.org), built on the Tabula Peutingeriana with
      Richard Talbert's identifications ("Rome's World", 2010) and Pleiades. 3,323 Place items (TPPlace ids for the
      Tabula's own stations, OVPlace ids for the lost western part that OmnesViae reconstructs from the Antonine
      Itinerary), each with the label as written on the Tabula, a modern and sometimes a classical name, latitude and
      longitude, and Talbert's symbol code; and 3,523 TravelAction legs (from, to, dist, overWater, isReconstructed,
      crossesMountains, crossesRiver). No licence is stated: used here as factual data, with credit.
  raw/tabula_peutingeriana_miller1887.jpg
      Konrad Miller's 1887 facsimile of the whole Tabula (segments II to XII), 26,381 x 2,014 px. Wikimedia Commons,
      "TabulaPeutingeriana.jpg", public domain.
  ROADS  /home/claude/studies/roman-roads/data/network.json
      The road graph of the earlier roman-roads study: Itiner-e (de Soto, Pazout, Brughmans et al. 2025, CC BY 4.0)
      cleaned into nodes, edges with lengths in km and five short sea crossings.
  DARE   /home/claude/work/roman-roads/ext/roman-empire/data/provinces.geojson
      Provinces of about AD 117 from the Digital Atlas of the Roman Empire (J. Ahlfeldt), CC BY-SA.
  PLEI   /home/claude/rawstore/mappa-mundi/pleiades/places.csv, names.csv  Pleiades gazetteer (CC BY 3.0)
  WIKI   /home/claude/newdata/raw8/roman/wiki_Roman_roads.json  English Wikipedia "Roman roads" (CC BY-SA 4.0): the
         travel speeds quoted in the text.
  GEO    /home/claude/newdata/raw/geo/ne_*.geojson  Natural Earth (public domain)
"""
import json, gzip, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("PT_RAW", os.path.join(ROOT, "raw"))
ROADS = os.environ.get("PT_ROADS", "/home/claude/studies/roman-roads/data/network.json")
DARE = os.environ.get("PT_DARE", "/home/claude/work/roman-roads/ext/roman-empire/data/provinces.geojson")
PLEI = os.environ.get("PT_PLEI", "/home/claude/rawstore/mappa-mundi/pleiades")
WIKI = os.environ.get("PT_WIKI", "/home/claude/newdata/raw8/roman/wiki_Roman_roads.json")
GEO = os.environ.get("PT_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("PT_FONTS", "/home/claude/ref/fonts")
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img")
WORK = os.path.join(os.environ.get("PTTMP", "/dev/shm/peutinger"), "work")   # intermediates live in memory, not in the repo
for d in (DATA, WORK, IMG):
    os.makedirs(d, exist_ok=True)

SLUG = "peutinger"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
DOI = "10.5281/zenodo.23882605"                # filled in by the publisher
BLOG = "https://blog.tristanhotham.com/2026/10/31/peutinger/"          # filled in by the publisher
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")
OV_URL = "https://omnesviae.org/"
MILLER_URL = "https://commons.wikimedia.org/wiki/File:TabulaPeutingeriana.jpg"
ITINERE_DOI = "10.5281/zenodo.17122148"
PLEIADES_VER = "4.1"

# Units. The Tabula does not say which unit each figure is in, and neither does the OmnesViae export (dist is a bare
# number). By convention the figures are Roman miles (1,000 paces, about 1.48 km); in Gaul and the Rhineland, beyond the
# note "Lugduno caput Galliarum usque hic legas" at Lyon, they are Gallic leagues (1.5 Roman miles, about 2.22 km); in
# Persia they are often said to be parasangs. 04_results.py checks these conventions against the measured distances.
RM_KM = 1.48
LEAGUE_KM = 2.22
PARASANG_KM = 5.5           # a common modern value (about 30 stadia); used only as a reference line
LEAGUE_PROVINCES = {"Aquitania", "Lugdunensis", "Belgica", "Germania Inferior", "Germania Superior"}

# Speeds for days of travel (English Wikipedia, "Roman roads", as quoted in the roman-roads study)
SPEEDS = [("foot", "On foot", 22.5), ("cart", "Horse-drawn cart", 45.0), ("courier", "Courier (relay of horses)", 80.0)]

# Regions: groups of DARE provinces (about AD 117), plus three regions beyond the frontier. Order = legend order, west to east.
REGIONS = [
    ("Britain", "#5D8F9E", {"Britannia"}),
    ("Iberia", "#9C6B3A", {"Baetica", "Lusitania", "Tarraconensis"}),
    ("Gaul and the Rhine", "#2F5FA7", {"Narbonensis", "Aquitania", "Lugdunensis", "Belgica", "Germania Inferior", "Germania Superior",
                                       "Alpes Maritimae", "Alpes Cottiae", "Alpes Graiae et Poeninae"}),
    ("Italy and islands", "#B23A2A", None),          # every 'Italia, regio ...', Sicilia, Sardinia et Corsica
    ("North Africa", "#B07A12", {"Africa Proconsularis", "Numidia", "Mauretania Caesariensis", "Mauretania Tingitana"}),
    ("Alps and Danube", "#2E8A6E", {"Raetia", "Noricum", "Pannonia Superior", "Pannonia Inferior", "Dalmatia", "Moesia Superior",
                                    "Moesia Inferior", "Dacia"}),
    ("Greece and Thrace", "#6E4C9A", {"Macedonia", "Achaia", "Thracia"}),
    ("Asia Minor", "#D46A8C", {"Asia", "Bithynia et Pontus", "Galatia et Cappadocia", "Lycia et Pamphylia", "Cilicia", "Cyprus"}),
    ("Egypt and Cyrene", "#E07B39", {"Aegyptus", "Creta et Cyrene"}),
    ("Levant", "#8E3B2E", {"Syria", "Iudaea", "Arabia"}),
    ("Mesopotamia and Armenia", "#7A9A3A", {"Armenia Mesopotamia"}),
    ("Persia, Central Asia and India", "#3B3B3B", set()),
]
RNAMES = [r[0] for r in REGIONS]
RCOL = {r[0]: r[1] for r in REGIONS}


def region_of_province(p, lon, lat):
    if p is None:
        return None
    if p.startswith("Italia") or p in ("Sicilia", "Sardinia et Corsica"):
        return "Italy and islands"
    if p == "Creta et Cyrene":
        return "Greece and Thrace" if lat > 34.5 else "Egypt and Cyrene"
    for n, c, s in REGIONS:
        if s and p in s:
            return n
    return None


def region_outside(lon, lat):
    """Places beyond the provinces of AD 117 (or off their simplified coastlines by more than 60 km)."""
    if lon >= 50:
        return "Persia, Central Asia and India"
    if lon >= 38.5 or (lon >= 36 and lat >= 39):
        return "Mesopotamia and Armenia"
    if lon >= 34 and lat < 32:
        return "Levant"
    if lon < -1 and lat > 49.5:
        return "Britain"
    if lon < 3.4 and lat < 43.8 and lat > 35.9:
        return "Iberia"
    if lat < 37.6 and lon < 11.5:
        return "North Africa"
    if lat < 33.5 and lon < 25:
        return "North Africa" if lon < 19 else "Egypt and Cyrene"
    if lat >= 44 and lon >= 14:
        return "Alps and Danube"
    if lon < 8.5 and lat > 45:
        return "Gaul and the Rhine"
    return None


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def dash(v):
    """Remove em and en dashes and double hyphens from text (house style)."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {k: dash(x) for k, x in v.items()}
    return v


def nonan(v):
    """JSON has no NaN: turn float NaN into null."""
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, list):
        return [nonan(x) for x in v]
    if isinstance(v, dict):
        return {k: nonan(x) for k, x in v.items()}
    return v


def jsave(obj, path, indent=None):
    obj = nonan(obj)
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=indent, separators=None if indent else (",", ":"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"[\W_]+", " ", s).strip()


def get(R, path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f == "k": return f"{float(v) / 1000:.1f}"
    raise ValueError(f)


def gc_km(lat1, lon1, lat2, lon2):
    import numpy as np
    p1, p2, l1, l2 = map(np.radians, (lat1, lat2, lon1, lon2))
    return 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2))


# Destinations for the journeys from Rome (station ids in the OmnesViae export)
ROME = "TPPlace1203"
DEST = [("London", "OVPlace427"), ("Lyon", "TPPlace730"), ("Cologne", "TPPlace575"), ("Carthage", "TPPlace60"), ("Vienna", "TPPlace1542"),
        ("Constantinople", "TPPlace2082"), ("Athens", "TPPlace1890"), ("Antioch", "TPPlace2374"), ("Jerusalem", "TPPlace438"), ("Alexandria", "TPPlace367"),
        ("Ctesiphon", "TPPlace2695"), ("Seville", "OVPlace209"), ("Persepolis", "TPPlace2779")]
