#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The research map: every record book we can name, where it is, and how far we got.

One place, several providers. A parish can sit in FamilySearch's Croatian
collection, in its Italian one, in the Pazin state archive's own register list
and on Antenati, and each of those knows something the others do not — Pazin
alone says who holds the paper and whether it has been digitised at all.

Sources, and where each comes from:

    fs-hr     FamilySearch, Croatia Church Books 2040054. Walked from the
              collection's own waypoint tree in David's Chrome (the in-app
              browser's egress IP is blocked), landed at data/fs-catalogue.json.
    fs-it     FamilySearch, Udine civil registration 1939238 — the Carnia
              comuni, already in site/src/data/carnia-books.json.
    dapa      Državni arhiv u Pazinu's own register list, site/src/data/
              registers.json. Fourteen places, and the only source that says
              «digitised: no».

Coverage was three states until the cataloguing finished and made them useless:
1,219 places gold against three grey is not a picture, it is a wash. So the
shading now carries DEPTH — how much is actually on the shelf — and keeps one
colour for the only number that matters:

    none   nothing catalogued here at all
    thin   one or two volumes
    some   three to nine
    deep   ten or more
    read   the search register names the place as a source, whatever its size

    for c in HR BA SI RS HU IT AT ME; do
      curl -sO https://download.geonames.org/export/dump/$c.zip && unzip -o $c.zip $c.txt
    done
    python3 scripts/build-research-map.py --gaz .

Writes site/src/data/researchmap.json and one Atlas blob per source view.
"""
import sys, os, re, json, collections, unicodedata, urllib.parse
import xml.etree.ElementTree as ET

NS   = {"k": "http://www.opengis.net/kml/2.2"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PUB  = os.path.join(ROOT, "site", "public")
KML  = os.path.join(ROOT, "data", "genealogy-resources-croatia.kml")
FSC  = os.path.join(ROOT, "data", "fs-catalogue.json")

STOP = {"zupa", "jaksic", "velika", "sveti", "grad", "novi", "stari"}
LAYERS = {"Roman Catholic": "rc", "Orthodox": "orth", "Greek Catholic": "gc",
          "Jewish": "jew", "Military": "mil", "Reformed Christian": "ref",
          "Civil": "civil", "Evangelical": "ev"}
LABEL  = {"rc": "Roman Catholic", "orth": "Orthodox", "gc": "Greek Catholic",
          "jew": "Jewish", "mil": "Military", "ref": "Reformed",
          "civil": "Civil", "ev": "Evangelical"}
SOURCES = [
    ("fs-hr",    "FamilySearch — Croatia",  "Croatia, Church Books 1516–1994 (collection 2040054)"),
    ("fs-it",    "FamilySearch — Udine",    "Italy, Udine civil registration (collection 1939238)"),
    ("dapa",     "Pazin State Archive",     "Državni arhiv u Pazinu, its own register list"),
]
DAPA_TYPE = {"MKR": "Births", "MKV": "Marriages", "MKU": "Deaths", "SD": "Church Census"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\(.*?\)", " ", s).split(",")[0]
    return re.sub(r"[^a-z0-9]+", "", s)

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)

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
                if len(k) > 2 and (k not in g or rank > g[k][0]):
                    g[k] = (rank, round(lat, 5), round(lon, 5), cc)
    return {k: v[1:] for k, v in g.items()}

def depth(n, read):
    """Read beats everything; below that, colour by how deep the shelf is."""
    if read:   return "read"
    if n == 0: return "none"
    if n <= 2: return "thin"
    if n <= 9: return "some"
    return "deep"

YEARS = re.compile(r"\b(1[5-9]\d\d)\b")
def span(title):
    ys = [int(y) for y in YEARS.findall(title or "")]
    return (min(ys), max(ys)) if ys else (None, None)

def main():
    gdir = sys.argv[sys.argv.index("--gaz") + 1] if "--gaz" in sys.argv else None
    gaz  = gazetteer(gdir) if gdir else {}
    prev = {}
    out_path = os.path.join(DATA, "researchmap.json")
    if os.path.exists(out_path):
        for p in load("researchmap.json")["places"]:
            if p.get("lat"):
                prev[p["key"]] = (p["lat"], p["lon"], p.get("geo"))

    places = {}
    def P(name, key=None):
        k = key or norm(name)
        return places.setdefault(k, {"key": k, "name": name.replace(", Croatia", "").strip(),
                                     "alt": set(), "layers": set(), "c": None,
                                     "src": {}})

    # ---- 1. the KML: coordinates, confessions, and the places FS has dropped
    doc = ET.parse(KML).getroot().find("k:Document", NS)
    researchers = []
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
            if head not in LAYERS or not norm(nm):
                continue
            p = P(nm); p["alt"].add(nm); p["layers"].add(LAYERS[head])
            p["c"] = p["c"] or c

    # ---- 2. FamilySearch Croatia, from the walk
    fsc = json.load(open(FSC, encoding="utf-8")) if os.path.exists(FSC) else {"p": [], "b": {}, "f": []}
    for lay, name, wp in fsc["p"]:
        p = P(name); p["alt"].add(name); p["layers"].add(lay)
        sh = p["src"].setdefault("fs-hr", {"shelves": {}})
        books = fsc["b"].get(lay + "|" + name)
        tail = wp.split(":")[1]
        vols = None
        if books is not None:
            vols = []
            for rec in books:
                t, bid, extra = rec[0], rec[1], rec[2]
                ark = rec[3] if len(rec) > 3 else None
                lo, hi = span(t)
                wpf = f"{bid}:{tail},{extra}" if extra else f"{bid}:{tail}"
                v = {"t": t, "wp": wpf, "from": lo, "to": hi}
                if ark:
                    # the ark is what makes a title clickable: the Atlas builds
                    # familysearch.org/ark:/61903/<ark>?cc=<cc>&wc=<waypoint>
                    v.update({"ark": ark, "cc": "2040054", "wc": wpf})
                vols.append(v)
        sh["shelves"][lay] = {"wp": wp, "books": vols}   # None = not walked yet

    # ---- 3. FamilySearch Udine — the Carnia comuni
    for r in load("carnia-books.json")["comuni"]:
        p = P(r["name"])
        vols = [{"t": f["t"], "ark": f["ark"], "wc": f.get("wc"), "cc": "1939238",
                 "from": span(f["t"])[0], "to": span(f["t"])[1]} for f in r.get("films", [])]
        p["src"]["fs-it"] = {"shelves": {"civil": {"wp": None, "books": vols}}}

    # ---- 4. Pazin's own list — the only source that admits what is not digitised
    dapa = collections.defaultdict(list)
    for r in load("registers.json"):
        dapa[norm(r["place"])].append(r)
    for k, rows in dapa.items():
        p = P(rows[0]["place"], key=k)
        vols = []
        for r in rows:
            lo, hi = span((r.get("period") or "").replace("/", " "))
            vols.append({"t": f"{DAPA_TYPE.get(r['type'], r['type'])} {r.get('period','')}".strip(),
                         "held": r.get("held_at"), "digitised": r.get("digitised") == "yes",
                         "no": r.get("dapa_no"), "from": lo, "to": hi})
        p["src"]["dapa"] = {"shelves": {"all": {"wp": None, "books": vols}},
                            "notDigitised": sum(1 for v in vols if not v["digitised"])}

    # ---- 5. what has actually been read
    rows = load("searched.json")["rows"]
    where = [" ".join(str(r.get(x, "")) for x in ("src", "dest")) for r in rows]
    reads = collections.Counter()
    for k, p in places.items():
        if k in STOP or len(p["name"]) < 4:
            continue
        pat = re.compile(r"\b" + re.escape(p["name"]) + r"\b", re.I)
        reads[k] = sum(1 for t in where if pat.search(t))

    # ---- 6. coordinates
    atlas = {norm(p["name"]): p for p in load("atlas.json")["places"]}
    for p in load("places.json"):
        if p.get("coords"):
            atlas.setdefault(norm(p["name"]), {"lat": p["coords"][0], "lon": p["coords"][1]})
    def resolve(p):
        k = p["key"]
        if p["c"]:   return p["c"], "kml"
        if k in prev: return list(prev[k][:2]), prev[k][2]
        if k in atlas and atlas[k].get("lat"):
            return [atlas[k]["lat"], atlas[k]["lon"]], "atlas"
        if k in gaz: return list(gaz[k][:2]), "geonames"
        raw, cand = p["name"], []
        m = re.search(r"\(([^)]+)\)", raw)
        if m: cand.append(m.group(1))
        cand += [x.strip() for x in re.split(r"[-–/]", re.sub(r"\(.*?\)", "", raw)) if x.strip()]
        cand.append(re.sub(r"^(sv\.?|sveti|sveta)\s+", "", raw, flags=re.I))
        for x in cand:
            kk = norm(x)
            if len(kk) > 2 and kk in gaz:
                return list(gaz[kk][:2]), "geonames-part"
        return None, None

    out, src_count = [], collections.Counter()
    for k, p in sorted(places.items(), key=lambda kv: kv[1]["name"]):
        c, how = resolve(p)
        vols = {}
        for s, blk in p["src"].items():
            n = sum(len(sh["books"]) for sh in blk["shelves"].values() if sh["books"] is not None)
            walked = any(sh["books"] is not None for sh in blk["shelves"].values())
            vols[s] = {"n": n, "walked": walked}
        total = sum(v["n"] for v in vols.values())
        state = depth(total, reads.get(k))
        for s in p["src"]: src_count[s] += 1
        out.append({"key": k, "name": p["name"],
                    "alt": sorted(x for x in p["alt"] if x != p["name"]),
                    "lat": c[0] if c else None, "lon": c[1] if c else None, "geo": how,
                    "cat": state, "layers": sorted(p["layers"]),
                    "sources": p["src"], "counts": vols, "volumes": total,
                    "reads": reads.get(k, 0)})

    stats = {"places": len(out), "placed": sum(1 for o in out if o["lat"]),
             "volumes": sum(o["volumes"] for o in out),
             "read": sum(1 for o in out if o["cat"] == "read"),
             "listed": sum(1 for o in out if o["cat"] in ("thin", "some", "deep")),
             "untouched": sum(1 for o in out if o["cat"] == "none"),
             "byDepth": {x: sum(1 for o in out if o["cat"] == x)
                         for x in ("none", "thin", "some", "deep", "read")},
             "researchers": len(researchers),
             "bySource": {s: {"places": src_count[s],
                              "volumes": sum(o["counts"].get(s, {}).get("n", 0) for o in out),
                              "walked": sum(1 for o in out if o["counts"].get(s, {}).get("walked"))}
                          for s, _, _ in SOURCES},
             "byLayer": dict(collections.Counter(l for o in out for l in o["layers"])),
             "notDigitised": sum(o["sources"].get("dapa", {}).get("notDigitised", 0) for o in out),
             "fsPending": len(fsc.get("f", [])),
             "linked": sum(1 for o in out for b in o.get("sources", {}).get("fs-hr", {}).get("shelves", {}).values()
                           for b in (b["books"] or []) if b.get("ark"))}

    json.dump({"note": "Every record book this archive can name, by place and by provider.",
               "sources": [{"key": k, "label": l, "what": w} for k, l, w in SOURCES],
               "kml": "data/genealogy-resources-croatia.kml",
               "stats": stats, "places": out, "researchers": researchers},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 7. one Atlas blob per view -------------------------------------
    def blob(keys, path):
        pubs = []
        for o in out:
            if not o["lat"]:
                continue
            got = {s: b for s, b in o["sources"].items() if s in keys}
            if not got:
                continue
            n = sum(o["counts"][s]["n"] for s in got)
            walked = any(o["counts"][s]["walked"] for s in got)
            state = depth(n, o["reads"])
            who = " · ".join(LABEL.get(l, l) for l in o["layers"]) or "Civil"
            prov = " · ".join(dict((k, l) for k, l, _ in SOURCES)[s] for s in got)
            if not walked:
                what = f"{who}. Not walked yet — we hold the waypoint and nothing more."
            elif n == 0:
                what = f"{who}. Walked, and the shelf is empty — this collection films nothing here."
            else:
                what = f"{who}. {n} volume{'' if n == 1 else 's'} catalogued, from {prov}."
            nd = sum(b.get("notDigitised", 0) for b in got.values())
            if nd:
                what += f" {nd} of them are not digitised anywhere."
            ev, films = [], []
            for s, blk in sorted(got.items()):
                for sh in blk["shelves"].values():
                    for b in (sh["books"] or []):
                        yr = (f'{b["from"]}–{b["to"]}' if b.get("from") and b.get("to") != b.get("from")
                              else (str(b.get("from")) if b.get("from") else "—"))
                        tag = "" if s == "fs-hr" else f" [{dict((k,l) for k,l,_ in SOURCES)[s]}]"
                        note = "" if b.get("digitised", True) else "  — NOT DIGITISED"
                        if b.get("ark"):
                            films.append({"t": b["t"], "ark": b["ark"],
                                          "cc": b.get("cc"), "wc": b.get("wc")})
                        else:
                            ev.append([yr, re.sub(r"\s*\b1[5-9]\d\d\b[,\s\-–]*", " ",
                                                  b["t"]).strip(" ,-–") + tag + note])
            pubs.append({"name": o["name"], "lat": o["lat"], "lon": o["lon"], "cat": state,
                         "n": 0, "also": o["alt"], "what": what,
                         "when": None, "href": "/searched/" if o["reads"] else None,
                         "events": ev[:60], "films": films, "nfilms": len(films)})
        json.dump({"places": pubs, "stats": stats}, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False)
        return len(pubs)

    allk = {k for k, _, _ in SOURCES}
    n = blob(allk, os.path.join(PUB, "research-map-data.json"))
    per = {}
    for k, _, _ in SOURCES:
        per[k] = blob({k}, os.path.join(PUB, f"research-map-{k}.json"))
    print(json.dumps({"stats": stats, "blobAll": n, "blobPer": per}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
