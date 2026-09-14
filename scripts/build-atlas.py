#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild site/src/data/atlas.json — every place the archive can put a person in.

Until September 2026 the Atlas carried 52 hand-written pins while the roster
named 266 place strings. This walks the roster, folds the variants together,
attaches the people, and hangs the openable register volumes off the parish
each place belongs to, so a pin can hand you the books and not a search box.

    python3 scripts/build-atlas.py
"""
import json, io, os, re, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
def load(n):
    p = os.path.join(DATA, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None

def strip(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")
def norm(s): return re.sub(r"[^a-z0-9]+", " ", strip(s).lower()).strip()
def head(s): return norm(str(s).split(",")[0])

roster   = load("roster.json")["rows"]
places   = load("places.json")
prows    = places if isinstance(places, list) else places.get("rows", [])
# The builder rewrites atlas.json, so reading it back as the seed would let a
# bad label breed. The pristine seed is kept beside it and never written to.
_seed = load("atlas-seed.json") or load("atlas.json")
oldatlas = _seed["places"]
geo      = json.load(io.open("/tmp/harvest-geo.json", encoding="utf-8"))

pb  = load("parishbooks.json")  or {}
dal = load("dalmatia-books.json") or {}
car = load("carnia-books.json")   or {}
kv  = load("kvarner-books.json")  or {}

# ---- one coordinate per settlement -----------------------------------
coord, label = {}, {}
for p in prows:
    if isinstance(p, dict) and p.get("coords"):
        h = head(p["name"]); coord[h] = tuple(p["coords"]); label[h] = p["name"]
for a in oldatlas:
    h = head(a["name"]); coord.setdefault(h, (a["lat"], a["lon"])); label.setdefault(h, a["name"])
for h, v in geo.items():
    if v.get("lat") is not None:
        coord.setdefault(h, (v["lat"], v["lon"]))
        label.setdefault(h, v["full"].split(",")[0])

# ---- register volumes, keyed by the parish they belong to -------------
def films(store, cc, key="parishes"):
    out = {}
    if not store: return out
    if key == "links":                      # parishbooks.json shape
        for parish, books in (store.get("links") or {}).items():
            out[head(parish)] = [{"t": t, "ark": b["ark"], "wc": b["wc"], "cc": cc}
                                 for t, b in books.items()]
    else:
        for p in store.get(key, []):
            src = p.get("films") or []
            if src:
                out[head(p["name"])] = [{"t": f["t"], "ark": f["ark"], "wc": f["wc"], "cc": cc} for f in src]
    return out
REG = {}
REG.update(films(pb,  "2040054", "links"))
REG.update(films(dal, "2040054"))
REG.update(films(kv,  "2040054"))
REG.update(films(car, "1939238", "comuni"))

# ---- fold the roster onto the settlements ----------------------------
NOTPLACE = {"osterreich","austria","italy","croatia","croazia","dalmatia","istria","tirol","poland",
 "connecticut","south africa","colonia","santa maria assunta","immacolata concezione",
 "assunzione di maria santissima","santi angeli custodi","santa maria del carmelo",
 "provincia di parma","early fiume"}

people  = collections.defaultdict(list)
aliases = collections.defaultdict(collections.Counter)
dropped = collections.Counter()
for r in roster:
    seen = set()
    for k in ("place", "parish"):
        v = str(r.get(k) or "").strip()
        if not v: continue
        h = head(v)
        if h in NOTPLACE: dropped[h] += 1; continue
        if h not in coord: dropped[h] += 1; continue
        aliases[h][v] += 1
        if h in seen: continue
        seen.add(h)
        people[h].append({"n": r["name"], "b": r.get("b"), "d": r.get("d"),
                          "who": r.get("who"), "line": r.get("line"), "src": r.get("src")})

# The register data names parishes the way the film does — «Poreč (Poreč)»,
# «Senj (Senj)», «Lupoglav (Pazin)» — while the roster names the town. Twenty
# people sat on Poreč with its thirty-two volumes one bracket away.
REGHEAD = {}
for _k in REG:
    REGHEAD.setdefault(_k, _k)
    _bare = re.sub(r"\s*\(.*?\)\s*", " ", _k).strip()
    if _bare and _bare != _k: REGHEAD.setdefault(_bare, _k)

def filmsFor(h):
    """Every volume filmed for this pin, gathered across all its spellings."""
    out, seen = [], set()
    keys = {h}
    if h in REGHEAD: keys.add(REGHEAD[h])
    keys |= {x for x in coord if x in REG and coord.get(x) == coord.get(h)}
    # The register names a parish the way the film does. head() has already
    # flattened «Poreč (Poreč)» to "porec porec" and «Senj (Senj)» to "senj
    # senj", so a pin called "porec" matched nothing. Same word-set, same place.
    hw = set(h.split())
    for rk in REG:
        if set(rk.split()) == hw: keys.add(rk)
    for alt in keys:
        for f in REG.get(alt, []):
            if f["ark"] in seen: continue
            seen.add(f["ark"]); out.append(f)
    return out

# ---- fold heads that resolve to the SAME GROUND onto one pin ----------
# Almissa and Omiš are one town; so are Fiume, Vitipolis and Tarsatica, which
# is why the first build drew Rijeka three times. Keys are merged when their
# coordinates agree to about a hundred metres.
import math
def km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * 6371 * math.asin(math.sqrt(h))

def samePlace(h1, h2):
    """One town under two names — never two towns that merely stand close.

    Gologorica and Gračišće are 2.4 km apart on this archive's own figures and
    are the first and second steps of the documented descent. Proximity alone
    merged them once; it will not again. Names must agree, or one must be the
    other with a qualifier («Mione» and «Mione di Ovaro»)."""
    n1, n2 = norm(label.get(h1, h1)), norm(label.get(h2, h2))
    if not n1 or not n2: return False
    d = km(coord[h1], coord[h2])
    if n1 == n2: return d < 30
    w1, w2 = set(n1.split()), set(n2.split())
    if w1 < w2 or w2 < w1: return d < 12          # one qualifies the other
    return False

reps = []
groups = collections.defaultdict(list)
for h in list(people):
    hit = next((r for r in reps if samePlace(r, h)), None)
    if hit is None: reps.append(h); hit = h
    groups[hit].append(h)
merged_people, merged_alias, canon = {}, {}, {}
for _k, hs in groups.items():
    # the head that the atlas or the gazetteer already names is the canonical one
    hs.sort(key=lambda x: (x not in {head(a["name"]) for a in oldatlas}, len(x)))
    c = hs[0]
    canon[_k] = c
    seen, ppl = set(), []
    for h in hs:
        for q in people[h]:
            sig = (q["n"], q.get("b"))
            if sig in seen: continue
            seen.add(sig); ppl.append(q)
    merged_people[c] = ppl
    ac = collections.Counter()
    for h in hs: ac.update(aliases[h])
    merged_alias[c] = ac
people, aliases = merged_people, merged_alias

# ---- assemble ---------------------------------------------------------
meta = {head(a["name"]): a for a in oldatlas}
out = []
for h, ppl in people.items():
    m = meta.get(h, {})
    lat, lon = coord[h]
    ppl.sort(key=lambda x: (x.get("b") or 9999, x["n"]))
    out.append({
        "name": m.get("name") or label.get(h) or h.title(),
        "lat": lat, "lon": lon,
        "cat": m.get("cat") or "sweep",
        "when": m.get("when") or "",
        "what": m.get("what") or "",
        "href": m.get("href") or "",
        "order": m.get("order"),
        "n": len(ppl),
        "also": [a for a, _ in aliases[h].most_common(4) if norm(a) != h],
        "people": [{"n": p["n"], "y": p["b"], "d": p["d"], "w": p["who"]} for p in ppl[:60]],
        "more": max(0, len(ppl) - 60),
        "films": filmsFor(h)[:80],
        "nfilms": len(filmsFor(h)),
    })
# places the archive names in the atlas but where no roster person sits —
# skipped when a pin already stands on that ground
# A seed place already covered by a roster pin must hand its identity over —
# «Mione di Ovaro» and «Mione» are one village, and the first carries the
# order number that makes it part of the documented descent.
def standingOn(a):
    an = norm(a["name"]); aw = set(an.split())
    for p in out:
        pn = norm(p["name"]); d = km((a["lat"], a["lon"]), (p["lat"], p["lon"]))
        if an == pn and d < 30: return p
        pw = set(pn.split())
        if (aw < pw or pw < aw) and d < 12: return p
    return None
for a in oldatlas:
    p = standingOn(a)
    if p is not None:
        if a.get("order") and not p.get("order"):
            p["order"] = a["order"]; p["cat"] = a.get("cat") or p["cat"]
            p["name"] = a["name"]
            p["when"] = p["when"] or a.get("when", "")
            p["what"] = p["what"] or a.get("what", "")
            p["href"] = p["href"] or a.get("href", "")
        continue
    out.append({**a, "n": 0, "also": [], "people": [], "more": 0,
                "films": REG.get(head(a["name"]), [])[:80],
                "nfilms": len(REG.get(head(a["name"]), []))})
# final safety net — one town must not appear twice under the same name, however
# it got here. The archive's own files disagree about where Gračišće is by seven
# kilometres, which is what this catches.
def fold(rows):
    keep = []
    for r in rows:
        hit = None
        for k in keep:
            if norm(k["name"]) == norm(r["name"]) and km((k["lat"], k["lon"]), (r["lat"], r["lon"])) < 30:
                hit = k; break
            kw, rw = set(norm(k["name"]).split()), set(norm(r["name"]).split())
            if (kw < rw or rw < kw) and km((k["lat"], k["lon"]), (r["lat"], r["lon"])) < 12:
                hit = k; break
        if hit is None: keep.append(r); continue
        if r["n"] > hit["n"]:                      # the heavier pin keeps the ground
            hit["lat"], hit["lon"] = r["lat"], r["lon"]
        hit["n"] += r["n"]
        seen = {(q["n"], q.get("y")) for q in hit["people"]}
        for q in r["people"]:
            if (q["n"], q.get("y")) not in seen: hit["people"].append(q); seen.add((q["n"], q.get("y")))
        hit["more"] = max(hit["more"], r["more"])
        arks = {f["ark"] for f in hit["films"]}
        for f in r["films"]:
            if f["ark"] not in arks: hit["films"].append(f); arks.add(f["ark"])
        hit["nfilms"] = max(hit["nfilms"], r["nfilms"], len(hit["films"]))
        hit["also"] = list(dict.fromkeys(hit["also"] + r["also"]))[:4]
        hit["when"] = hit["when"] or r["when"]; hit["what"] = hit["what"] or r["what"]
        hit["href"] = hit["href"] or r["href"];  hit["order"] = hit["order"] or r["order"]
        if r["cat"] == "spine": hit["cat"] = "spine"
    return keep
out = fold(out)
out.sort(key=lambda x: (-x["n"], x["name"]))

atlas = load("atlas.json")
atlas["places"] = out
atlas["built"]  = "Rebuilt from the roster, 14 September 2026."
atlas["stats"]  = {"places": len(out), "withPeople": sum(1 for p in out if p["n"]),
                   "people": sum(p["n"] for p in out),
                   "withFilms": sum(1 for p in out if p["nfilms"]),
                   "films": sum(p["nfilms"] for p in out)}
json.dump(atlas, io.open(os.path.join(DATA, "atlas.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(atlas["stats"], indent=1))
print("unplaced strings still dropped:", sum(dropped.values()), "across", len(dropped), "forms")
for h, n in dropped.most_common(12): print(f"   {n:4d}  {h}")
