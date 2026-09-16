#!/usr/bin/env python3
"""Where this family is buried — the other map.

The research map is a map of shelves: which registers exist and how far anyone
has got with them. This is a map of ground. Two quite different things are on
it and the colour keeps them apart:

    stone     a headstone somebody photographed, mostly in the diaspora
    register  a line in a parish burial book, mostly in Istria and Kvarner
    both      a place that has produced each kind

That distinction is the point. A stone is a place you can stand; a register
entry is a clerk's sentence about somebody whose grave nobody has found. The
archive holds 96 of the first and 102 of the second, and they barely overlap —
which is itself the shape of the emigration.

    python3 scripts/build-graves-map.py --gaz <dir with cities500.txt + HR.txt …>
"""
import sys, os, re, json, collections, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gazcheck

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PUB  = os.path.join(ROOT, "site", "public")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)

def gazetteer(d):
    """cities500 is every populated place on earth over five hundred people,
    which is the right size for a family that buried its dead in Broken Hill,
    the Bronx and a village above Ovaro."""
    g = {}
    path = os.path.join(d, "cities500.txt")
    if not os.path.exists(path):
        return g
    for line in open(path, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 15:
            continue
        try:
            lat, lon, pop = float(f[4]), float(f[5]), int(f[14] or 0)
        except ValueError:
            continue
        cc = f[8]
        for n in {f[1], f[2]} | {x.strip() for x in (f[3] or "").split(",") if x.strip()}:
            k = norm(n)
            if len(k) < 3:
                continue
            key = (k, cc)
            if key not in g or pop > g[key][2]:
                g[key] = (round(lat, 5), round(lon, 5), pop)
            if k not in g or pop > g.get(k, (0, 0, -1))[2]:
                g[k] = (round(lat, 5), round(lon, 5), pop)
    return g

CC = {"USA": "US", "Australia": "AU", "Italy": "IT", "Switzerland": "CH",
      "Canada": "CA", "Brazil": "BR", "Croatia": "HR", "Germany": "DE"}

# Places the gazetteer cannot resolve from the string the source gives, or
# resolves to the wrong continent. Each one is here because it was checked.
FIX = {
    "middlevillagequeenscountynewyorkusa": (40.7176, -73.8801),
    "woodsidequeenscountynewyorkusa":      (40.7454, -73.9026),
    "eastfarmingdalesuffolkcountynewyorkusa": (40.7304, -73.4265),
    "hartsdalewestchestercountynewyorkusa": (41.0176, -73.7996),
    "millbrookdutchesscountynewyorkusa":   (41.7859, -73.6937),
    "brooklynkingscountynewyorkusa":       (40.6782, -73.9442),
    "bronxbronxcountynewyorkusa":          (40.8448, -73.8648),
    "fawknervictoriaaustralia":            (-37.7150, 144.9600),
    "lilydaleyarrarangesshirevictoriaaustralia": (-37.7560, 145.3490),
    "willowbankcityofipswichqueenslandaustralia": (-27.7000, 152.6830),
    "horshamruralcityofhorshamvictoriaaustralia": (-36.7167, 142.2000),
    "centenarymemorialgardens":            (-27.5800, 152.9200),
    "concesiobrescia":                     (45.6040, 10.2170),
    "sandanieledelfriuli":                 (46.1580, 13.0090),
    # cities500 stops at five hundred people and Sterna in Grozjnan has
    # seventy, so the bare name fell through to Sterna in Evros, GREECE,
    # and put two Istrian burials on the Turkish border. GeoNames HR.txt:
    # 3189889 Sterna 45.41306 13.79361 P PPL HR.
    "sterna":                              (45.41306, 13.79361),
}

def resolve(place, country, gaz):
    if not place:
        return None
    k = norm(place)
    if k in FIX:
        return FIX[k]
    cc = CC.get(country)
    parts = [p.strip() for p in place.split(",") if p.strip()]
    # try the most specific name first, then widen
    for i in range(len(parts)):
        cand = norm(parts[i])
        if len(cand) < 3:
            continue
        if cc and (cand, cc) in gaz:
            return gaz[(cand, cc)][:2]
    for i in range(len(parts)):
        cand = norm(parts[i])
        if cand in gaz:
            return gaz[cand][:2]
    return None

def main():
    gdir = sys.argv[sys.argv.index("--gaz") + 1] if "--gaz" in sys.argv else None
    # cities500 alone is 235,808 places; under a hundred thousand keys means
    # the file was not found and every «unplaced» below would be a lie.
    gaz = gazcheck.require(gazetteer(gdir) if gdir else {}, gdir, 100000)
    atlas = {norm(p["name"]): p for p in load("atlas.json")["places"]}

    places = {}
    def P(name, country=""):
        k = norm(name)
        return places.setdefault(k, {"key": k, "name": name, "country": country,
                                     "stones": [], "register": [], "cems": set(),
                                     "lat": None, "lon": None})

    unplaced = {"stone": [], "register": []}

    for r in load("graves.json")["rows"]:
        if not r.get("place"):
            unplaced["stone"].append(r.get("name", "")); continue
        p = P(r["place"], r.get("country", ""))
        p["stones"].append(r)
        if r.get("cem"):
            p["cems"].add(r["cem"])

    for r in load("burials.json")["rows"]:
        pl = (r.get("place") or "").strip()
        if not pl or pl.lower().startswith(("not stated", "croatia, parish")):
            unplaced["register"].append(r.get("name", "")); continue
        p = P(pl, "Croatia")
        p["register"].append(r)

    out = []
    for k, p in sorted(places.items(), key=lambda kv: kv[1]["name"]):
        c = resolve(p["name"], p["country"], gaz)
        if not c and k in atlas and atlas[k].get("lat"):
            c = (atlas[k]["lat"], atlas[k]["lon"])
        ns, nr = len(p["stones"]), len(p["register"])
        cat = "both" if ns and nr else ("stone" if ns else "register")
        years = [x.get("d") for x in p["stones"] if x.get("d")] + \
                [x.get("dy") for x in p["register"] if x.get("dy")]
        out.append({"key": k, "name": p["name"], "country": p["country"],
                    "lat": c[0] if c else None, "lon": c[1] if c else None,
                    "cat": cat, "stones": ns, "register": nr, "n": ns + nr,
                    "cems": sorted(p["cems"]),
                    "first": min(years) if years else None,
                    "last": max(years) if years else None,
                    "people": ([{"n": x["name"], "y": x.get("d"), "w": x.get("cem", ""),
                                 "u": x.get("url", ""), "k": "stone"} for x in p["stones"]] +
                               [{"n": x["name"], "y": x.get("dy"), "w": "parish burial register",
                                 "u": "", "k": "register"} for x in p["register"]])})

    stats = {"places": len(out), "placed": sum(1 for o in out if o["lat"]),
             "people": sum(o["n"] for o in out),
             "stones": sum(o["stones"] for o in out),
             "register": sum(o["register"] for o in out),
             "cemeteries": sum(len(o["cems"]) for o in out),
             "byCat": dict(collections.Counter(o["cat"] for o in out)),
             "byCountry": dict(collections.Counter(o["country"] for o in out if o["country"])),
             "unplacedStone": len(unplaced["stone"]),
             "unplacedRegister": len(unplaced["register"]),
             "earliest": min([o["first"] for o in out if o["first"]] or [None]),
             "latest": max([o["last"] for o in out if o["last"]] or [None])}

    gazcheck.guard(os.path.join(DATA, "gravesmap.json"), "stats.placed",
                   stats["placed"], "placed burial-grounds")
    json.dump({"note": "Where this family is buried — headstones photographed, and burial registers read.",
               "stats": stats, "places": out, "unplaced": unplaced},
              open(os.path.join(DATA, "gravesmap.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    pubs = []
    for o in out:
        if not o["lat"]:
            continue
        bits = []
        if o["stones"]:
            bits.append(f"{o['stones']} headstone{'' if o['stones'] == 1 else 's'} photographed")
        if o["register"]:
            bits.append(f"{o['register']} read out of a parish burial register")
        what = (o["country"] + ". " if o["country"] else "") + " · ".join(bits) + "."
        if o["cems"]:
            what += " " + " · ".join(o["cems"][:4])
        ev = [[str(x["y"] or "—"), f"{x['n']} — {x['w']}"] for x in
              sorted(o["people"], key=lambda x: (x["y"] or 9999))]
        pubs.append({"name": o["name"], "lat": o["lat"], "lon": o["lon"], "cat": o["cat"],
                     "n": o["n"], "also": [], "what": what,
                     "when": (f"{o['first']}–{o['last']}" if o["first"] and o["last"] != o["first"]
                              else (str(o["first"]) if o["first"] else None)),
                     "href": "/graves/" if o["stones"] else "/burials/",
                     "events": ev[:80], "films": [], "nfilms": 0})
    json.dump({"places": pubs, "stats": stats},
              open(os.path.join(PUB, "graves-map-data.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print(json.dumps(stats, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
