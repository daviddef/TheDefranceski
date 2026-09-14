#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The research map: every Croatian record book on the map, and how far we have got.

David spent years building a Google My Map of the record books — FamilySearch
first, then the other confessions — and a My Map dies with the account. Worse,
its KML export is barely portable: only ninety of its twelve hundred record
pins carry coordinates, because the rest are address pins that Google geocodes
at draw time. What every pin *does* carry is a FamilySearch browse waypoint,
and that is the part worth keeping: it is the key that opens the parish.

This reads the KML, resolves the missing coordinates against the GeoNames
dumps, joins each place to what this archive already holds for it, and writes
two files: the page's own data, and the blob the Atlas component fetches.

    for c in HR BA SI RS HU IT AT ME; do
      curl -sO https://download.geonames.org/export/dump/$c.zip && unzip -o $c.zip $c.txt
    done
    python3 scripts/build-research-map.py --gaz .

Coverage is three states and they mean different things:
    untouched  we hold the waypoint and nothing else
    listed     we hold the parish's volume inventory
    read       a row in the search register names the place as a source

The «read» flag is derived by matching place names against the register's own
source and destination fields — never its prose, which mentions places for all
sorts of reasons. It is approximate, and the page says so.
"""
import sys, os, re, json, collections, unicodedata, urllib.parse
import xml.etree.ElementTree as ET

NS   = {"k": "http://www.opengis.net/kml/2.2"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
KML  = os.path.join(ROOT, "data", "genealogy-resources-croatia.kml")

# Places whose names are also ordinary words or surnames, and which the
# name-matcher therefore claims we have read when we have not.
STOP = {"zupa", "jaksic", "velika", "sveti", "grad", "novi", "stari"}

LAYERS = {"Roman Catholic": "rc", "Orthodox": "orth", "Greek Catholic": "gc",
          "Jewish": "jew", "Military": "mil", "Reformed Christian": "ref",
          "Civil": "civil", "Evangelical": "ev"}
LABEL  = {"rc": "Roman Catholic", "orth": "Orthodox", "gc": "Greek Catholic",
          "jew": "Jewish", "mil": "Military", "ref": "Reformed", "civil": "Civil",
          "ev": "Evangelical"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\(.*?\)", " ", s).split(",")[0]
    return re.sub(r"[^a-z0-9]+", "", s)

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)

# ---- the gazetteer, built from the GeoNames country dumps -----------------
def gazetteer(d):
    g = {}
    for cc in ("HR", "BA", "SI", "RS", "HU", "IT", "AT", "ME"):
        p = os.path.join(d, cc + ".txt")
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            f = line.rstrip("\n").split("\t")
            if len(f) < 15 or f[6] not in ("P", "A"):
                continue
            try:
                lat, lon, pop = float(f[4]), float(f[5]), int(f[14] or 0)
            except ValueError:
                continue
            rank = (cc == "HR", f[6] == "P", pop)
            for n in {f[1], f[2]} | {x for x in (f[3] or "").split(",") if x}:
                k = norm(n)
                if len(k) > 2 and rank > g.get(k, ((), ))[0:1][0] if k in g else len(k) > 2:
                    if k not in g or rank > g[k][0]:
                        g[k] = (rank, round(lat, 5), round(lon, 5), cc)
    return {k: v[1:] for k, v in g.items()}

def main():
    gdir = sys.argv[sys.argv.index("--gaz") + 1] if "--gaz" in sys.argv else None
    gaz  = gazetteer(gdir) if gdir else {}
    prev = {}
    out_path = os.path.join(DATA, "researchmap.json")
    if os.path.exists(out_path):                      # keep coordinates already resolved
        for p in load("researchmap.json")["places"]:
            if p.get("lat"):
                prev[p["key"]] = (p["lat"], p["lon"], p.get("geo"))

    doc = ET.parse(KML).getroot().find("k:Document", NS)
    places, researchers = {}, []
    for folder in doc.findall("k:Folder", NS):
        head = (folder.find("k:name", NS).text or "").split(" (")[0]
        for pm in folder.findall("k:Placemark", NS):
            nm   = (pm.find("k:name", NS).text or "").strip()
            data = {D.get("name"): (D.find("k:value", NS).text or "")
                    for D in pm.findall(".//k:Data", NS)}
            crd  = pm.find(".//k:coordinates", NS)
            c    = None
            if crd is not None and (crd.text or "").strip():
                lon, lat, *_ = crd.text.strip().split(",")
                c = [round(float(lat), 5), round(float(lon), 5)]
            if head == "Other Research Sites":
                researchers.append({"place": nm, "id": data.get("Oznaka istraživača"),
                                    "zupa": data.get("Župa"), "vjera": data.get("Vjera"),
                                    "prezimena": data.get("Prezimena"),
                                    "izvori": data.get("Izvori podataka"),
                                    "since": data.get("Od kada se bavite rodoslovljem?"),
                                    "drzava": data.get("Država"), "c": c})
                continue
            if head not in LAYERS:
                continue
            k = norm(nm)
            if not k:
                continue
            wp = None
            m = re.search(r"owc=([^&\s<]+)", data.get("description", ""))
            if m:
                wp = urllib.parse.unquote(m.group(1)).split("?")[0]
            p = places.setdefault(k, {"key": k, "name": nm.replace(", Croatia", "").strip(),
                                      "alt": set(), "layers": set(), "c": None, "wp": None,
                                      "wps": {}})
            p["alt"].add(nm); p["layers"].add(LAYERS[head])
            p["c"]  = p["c"]  or c
            p["wp"] = p["wp"] or wp
            # A town with books in two confessions has two shelves and two
            # waypoints. Keeping one of them threw away ninety-four of them.
            if wp: p["wps"][LAYERS[head]] = wp

    # ---- what this archive already holds ----------------------------------
    vols, films = {}, {}
    for r in load("parishbooks.json")["list"]:
        vols[norm(r["parish"])] = ("Istria", r["volumes"])
    lk = load("parishbooks.json")["links"]
    for parish, books in lk.items():
        films[norm(parish)] = [{"t": t, "ark": b["ark"], "cc": "2040054", "wc": b.get("wc")}
                               for t, b in books.items()]
    # Kvarner keeps its volumes under «films», like Dalmatia, and a stale
    # «books» title-list on six of its forty parishes. Reading «books» here
    # under-counted Kvarner by thirty-four parishes and produced a gap on this
    # map that did not exist. Both fields are read, films first.
    for r in load("kvarner-books.json")["parishes"]:
        vs = r.get("films") or r.get("books") or []
        vols.setdefault(norm(r["name"]), ("Kvarner", len(vs)))
        if r.get("films"):
            films.setdefault(norm(r["name"]), [{"t": f["t"], "ark": f["ark"],
                                                "cc": "2040054", "wc": f.get("wc")}
                                               for f in r["films"]])
    for r in load("dalmatia-books.json")["parishes"]:
        vols.setdefault(norm(r["name"]), ("Dalmatia", len(r.get("films", []))))
        films.setdefault(norm(r["name"]), [{"t": f["t"], "ark": f["ark"], "cc": "2040054",
                                            "wc": f.get("wc")} for f in r.get("films", [])])

    atlas = {norm(p["name"]): p for p in load("atlas.json")["places"]}
    for p in load("places.json"):
        if p.get("coords"):
            atlas.setdefault(norm(p["name"]), {"lat": p["coords"][0], "lon": p["coords"][1]})

    rows = load("searched.json")["rows"]
    where = [" ".join(str(r.get(x, "")) for x in ("src", "dest")) for r in rows]
    reads = collections.Counter()
    for k, p in places.items():
        if k in STOP or len(p["name"]) < 4:
            continue
        pat = re.compile(r"\b" + re.escape(p["name"]) + r"\b", re.I)
        reads[k] = sum(1 for t in where if pat.search(t))

    # ---- resolve coordinates ---------------------------------------------
    def resolve(p):
        k = p["key"]
        if p["c"]:                       return p["c"], "kml"
        if k in prev:                    return list(prev[k][:2]), prev[k][2]
        if k in atlas and atlas[k].get("lat"):
            return [atlas[k]["lat"], atlas[k]["lon"]], "atlas"
        if k in gaz:                     return list(gaz[k][:2]), "geonames"
        raw = p["name"]
        cand = []
        m = re.search(r"\(([^)]+)\)", raw)
        if m: cand.append(m.group(1))
        cand += [x.strip() for x in re.split(r"[-–/]", re.sub(r"\(.*?\)", "", raw)) if x.strip()]
        cand.append(re.sub(r"^(sv\.?|sveti|sveta)\s+", "", raw, flags=re.I))
        for x in cand:
            kk = norm(x)
            if len(kk) > 2 and kk in gaz:
                return list(gaz[kk][:2]), "geonames-part"
        return None, None

    out, src = [], collections.Counter()
    for k, p in sorted(places.items(), key=lambda kv: kv[1]["name"]):
        c, how = resolve(p)
        src[how or "unplaced"] += 1
        region, n = vols.get(k, (None, 0))
        state = "read" if reads.get(k) else ("listed" if n else "untouched")
        out.append({"key": k, "name": p["name"], "alt": sorted(x for x in p["alt"] if x != p["name"]),
                    "lat": c[0] if c else None, "lon": c[1] if c else None, "geo": how,
                    "cat": state, "layers": sorted(p["layers"]), "wp": p["wp"],
                    "wps": p["wps"],
                    "n": n, "region": region, "reads": reads.get(k, 0),
                    "films": films.get(k, [])})

    stats = {"places": len(out), "placed": sum(1 for o in out if o["lat"]),
             "withWaypoint": sum(1 for o in out if o["wp"]),
             "shelves": sum(len(o["wps"]) for o in out),
             "multiConfession": sum(1 for o in out if len(o["wps"]) > 1),
             "volumes": sum(o["n"] for o in out),
             "read": sum(1 for o in out if o["cat"] == "read"),
             "listed": sum(1 for o in out if o["cat"] == "listed"),
             "untouched": sum(1 for o in out if o["cat"] == "untouched"),
             "researchers": len(researchers),
             "byLayer": dict(collections.Counter(l for o in out for l in o["layers"]))}

    json.dump({"note": __doc__.strip().split("\n\n")[1],
               "source": "https://www.google.com/maps/d/u/0/edit?mid=1ej5KHbogwUcbxZON4Oyi14M2p9zTfKY",
               "kml": "data/genealogy-resources-croatia.kml",
               "stats": stats, "places": out, "researchers": researchers},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- the blob the Atlas fetches --------------------------------------
    pubs = []
    for o in out:
        if not o["lat"]:
            continue
        who = " · ".join(LABEL[l] for l in o["layers"])
        if o["cat"] == "untouched":
            what = f"{who}. Not walked yet — this archive holds the FamilySearch waypoint and nothing more."
        elif o["cat"] == "listed":
            what = f"{who}. {o['n']} volume{'' if o['n']==1 else 's'} inventoried here; none of them read yet."
        else:
            what = (f"{who}. Named as a source in {o['reads']} row"
                    f"{'' if o['reads']==1 else 's'} of the search register"
                    + (f", and {o['n']} volumes inventoried." if o["n"] else "."))
        pubs.append({"name": o["name"], "lat": o["lat"], "lon": o["lon"], "cat": o["cat"],
                     "n": 0, "also": o["alt"], "what": what,
                     "when": o["region"], "href": "/searched/" if o["cat"] == "read" else None,
                     "films": o["films"], "nfilms": len(o["films"])})
    json.dump({"places": pubs, "stats": stats},
              open(os.path.join(ROOT, "site", "public", "research-map-data.json"), "w",
                   encoding="utf-8"), ensure_ascii=False)

    print("places", stats["places"], "placed", stats["placed"],
          "read", stats["read"], "listed", stats["listed"], "untouched", stats["untouched"])
    print("coords from:", dict(src))

if __name__ == "__main__":
    main()
