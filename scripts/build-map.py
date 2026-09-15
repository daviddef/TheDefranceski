#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One map, three questions — site/public/map-data.json.

The archive had grown three maps off the same ground. The research map
carried 1,235 record-book places and asked «how far have we got with the
shelf». The atlas carried 160 places and asked «where can we put a person».
The graves map carried 64 and asked «where is this family in the ground».
Forty-three of the atlas's places were already on the research map, eleven of
the graves map's were, and after the people layer was added to the research
map in September 2026 one map was a strict superset of another. Three pages,
three geocoders, three legends, and a reader holding all of it in their head.

So they are merged. ONE set of places. Each place carries up to three
categories — one per question — and the page switches which one is being
coloured and filtered. The PANEL never switches: a marker that is a parish,
a home and a grave says all three things at once, which is the whole reason
for merging them.

    python3 scripts/build-research-map.py --gaz <dir>     # the shelf
    python3 scripts/build-atlas.py                        # the people
    python3 scripts/build-graves-map.py                   # the ground
    python3 scripts/build-map.py                          # this

Writes site/public/map-data.json and site/src/data/map.json (the stats and
the merge report, for the page to quote).
"""
import json, io, os, re, math, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PUB  = os.path.join(ROOT, "site", "public")
def load(p):
    return json.load(io.open(p, encoding="utf-8"))

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def loose(s):
    """A key that survives spelling. Digraphs are folded because the same town
    is «Fažana» in one catalogue and «Fasana» in another, and doubled letters
    are collapsed because a clerk's hand is not a database."""
    s = re.sub(r"\(.*?\)", " ", strip(s)).split(",")[0]
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    for a, b in (("cz","c"),("ch","c"),("sz","s"),("sh","s"),("zh","z"),
                 ("tz","c"),("y","i"),("j","i"),("w","v")):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)

def km(a, b):
    """Rough great-circle. Only ever used to ask «is this the same town or a
    different town with the same name», so rough is enough."""
    (la1, lo1), (la2, lo2) = a, b
    dla = math.radians(la2 - la1)
    dlo = math.radians(lo2 - lo1) * math.cos(math.radians((la1 + la2) / 2))
    return 6371 * math.hypot(dla, dlo)

# Two places may share a name and be different towns — Split in Dalmatia and
# any other Split there might be. Sixty kilometres is generous for a parish
# and tight enough that no two real settlements of the same name merge.
NEAR = 60

places, index = [], {}

def key_in(rec, name):
    k = loose(name)
    if not k or len(k) < 3:
        return None
    for i in index.get(k, []):
        if km((places[i]["lat"], places[i]["lon"]), (rec["lat"], rec["lon"])) < NEAR:
            return i
    return None

def register(i, names):
    for nm in names:
        k = loose(nm)
        if k and len(k) >= 3:
            index.setdefault(k, []).append(i)

def add(rec, scheme, cat, n, what, when, href, events, films, ppl, more, order):
    """Fold one source's place into the merged set, matching on its own name
    and on every «also written» it carries — which is what puts Csáktornya and
    Čakovec, Fiume and Rijeka, on one dot."""
    names = [rec["name"]] + list(rec.get("also") or [])
    hit = None
    for nm in names:
        hit = key_in(rec, nm)
        if hit is not None:
            break
    if hit is None:
        p = {"name": rec["name"], "lat": rec["lat"], "lon": rec["lon"],
             "also": list(rec.get("also") or []),
             "cats": {}, "ns": {}, "blocks": {},
             "events": [], "films": [], "people": [], "more": 0,
             "when": None, "href": None, "order": None}
        places.append(p)
        register(len(places) - 1, names)
        hit = len(places) - 1
    p = places[hit]
    # Names already registered stay registered; new spellings are added so a
    # later source can find this place by any of them.
    register(hit, names)
    for a in (rec.get("also") or []):
        if a not in p["also"]:
            p["also"].append(a)
    p["cats"][scheme] = cat
    p["ns"][scheme] = n or 0
    if what:
        p["blocks"][scheme] = what
    p["when"] = p["when"] or when
    p["href"] = p["href"] or href
    p["order"] = p["order"] or order
    p["events"] += events or []
    known = {f.get("ark") for f in p["films"]}
    for f in films or []:
        if f.get("ark") not in known:
            p["films"].append(f); known.add(f.get("ark"))
    seen = {(q.get("n"), q.get("y")) for q in p["people"]}
    for q in ppl or []:
        if (q.get("n"), q.get("y")) not in seen:
            p["people"].append(q); seen.add((q.get("n"), q.get("y")))
    p["more"] = max(p["more"], more or 0)

# ---- 1. the shelf ------------------------------------------------------
shelf = load(os.path.join(PUB, "research-map-data.json"))
for r in shelf["places"]:
    if r["cat"] == "people":          # added to that map before this one existed
        continue
    add(r, "shelf", r["cat"], 0, r.get("what"), r.get("when"), r.get("href"),
        r.get("events"), r.get("films"), None, 0, None)

# ---- 2. the people -----------------------------------------------------
atlas = load(os.path.join(DATA, "atlas.json"))
for r in atlas["places"]:
    if r.get("lat") is None:
        continue
    add(r, "people", r.get("cat") or "other", r.get("n") or 0,
        r.get("what"), r.get("when"), r.get("href"),
        None, r.get("films"), r.get("people"), r.get("more") or 0, r.get("order"))

# ---- 3. the ground -----------------------------------------------------
graves = load(os.path.join(PUB, "graves-map-data.json"))
for r in graves["places"]:
    if r.get("lat") is None:
        continue
    add(r, "graves", r["cat"], r.get("n") or 0, r.get("what"), r.get("when"),
        r.get("href"), r.get("events"), None, None, 0, None)

# ---- the panel says all three things, whichever colour is showing -------
TAG = {"shelf": "", "people": "Our people here — ", "graves": "In the ground here — "}
for p in places:
    bits = []
    for sc in ("shelf", "people", "graves"):
        if p["blocks"].get(sc):
            bits.append(TAG[sc] + p["blocks"][sc])
    p["what"] = "  ".join(bits)
    p["nfilms"] = len(p["films"])
    p["n"] = p["ns"].get("shelf", 0)
    p["cat"] = p["cats"].get("shelf", "_none")
    del p["blocks"]

places.sort(key=lambda x: (x["name"] or ""))

both = collections.Counter()
for p in places:
    both[" + ".join(sorted(p["cats"]))] += 1

stats = {
    "places": len(places),
    "bySchemes": dict(both),
    "shelf":  sum(1 for p in places if "shelf" in p["cats"]),
    "people": sum(1 for p in places if "people" in p["cats"]),
    "graves": sum(1 for p in places if "graves" in p["cats"]),
    "merged": sum(1 for p in places if len(p["cats"]) > 1),
    "allThree": sum(1 for p in places if len(p["cats"]) == 3),
    "peoplePlaced": sum(p["ns"].get("people", 0) for p in places),
    "burials": sum(p["ns"].get("graves", 0) for p in places),
    "volumes": sum(p["nfilms"] for p in places),
    "byShelf": collections.Counter(p["cats"]["shelf"] for p in places if "shelf" in p["cats"]),
    "byPeople": collections.Counter(p["cats"]["people"] for p in places if "people" in p["cats"]),
    "byGraves": collections.Counter(p["cats"]["graves"] for p in places if "graves" in p["cats"]),
    "sums": {"research": len([r for r in shelf["places"] if r["cat"] != "people"]),
             "atlas": len([r for r in atlas["places"] if r.get("lat") is not None]),
             "graves": len([r for r in graves["places"] if r.get("lat") is not None])},
}
stats["saved"] = sum(stats["sums"].values()) - stats["places"]

mv = load(os.path.join(DATA, "movements.json"))
mm = load(os.path.join(DATA, "mymap.json"))
areas = [{"n": x.get("n") or L["name"], "layer": L["name"], "ring": x["ring"]}
         for L in mm["layers"] for x in L["areas"]]

json.dump({"places": places, "stats": stats, "moves": mv["moves"],
           "spine": mv.get("spine"), "areas": areas,
           "mnote": mv.get("note"), "mcaution": mv.get("caution")},
          io.open(os.path.join(PUB, "map-data.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
json.dump({"note": __doc__.strip().split("\n\n")[1], "stats": stats,
           "researchStats": shelf["stats"], "atlasStats": atlas["stats"],
           "gravesStats": graves["stats"]},
          io.open(os.path.join(DATA, "map.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False, indent=1, default=dict))
