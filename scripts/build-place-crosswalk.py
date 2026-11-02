#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which marker on /map/ is each place that Roots & Routes draws?  site/src/data/place-crosswalk.json

    python3 scripts/build-place-crosswalk.py            # write the crosswalk
    python3 scripts/build-place-crosswalk.py --check    # exit 1 if the committed file differs from what the data gives

WHY IT EXISTS. /map/ (site/public/map-data.json) and Roots & Routes (data/tree-page/atlas-data.json) draw the same ground from different
datasets. Matched by name alone they disagree by up to 14,800 km for seven places (a Rookwood is not every Rookwood), so a link from one to the
other cannot be made from a name. A match here needs BOTH the map builder's own loose name key (scripts/build-map.py loose(), kept in step below)
AND a distance of at most MATCH_KM. A match more than FLAG_KM apart is kept and flagged, never silently trusted. A name that matches two markers
with the same display name is not linked: /map/?at=<name> would open the first of them.

The two places whose names differ between the datasets are mapped by hand (OVERRIDES), each with its reason.

WHAT READS IT: scripts/build-tree-page.py (the "on the archive map" link and the shelf state on a person's card, and site/public/roots-links.json,
which /map/ reads to offer "open in Roots & Routes"). Order: build-map.py, then this, then build-tree-page.py.
"""
import io, json, math, os, re, sys, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, "site", "public", "map-data.json")
RR = os.path.join(ROOT, "data", "tree-page", "atlas-data.json")
PM = os.path.join(ROOT, "data", "tree-page", "place_map.json")
OUT = os.path.join(ROOT, "site", "src", "data", "place-crosswalk.json")
MATCH_KM = 25.0     # the same name this close is the same place
FLAG_KM = 5.0       # a matched pair further apart than this is reported
# Roots & Routes names the place the way the roster writes it; the map names it the way its own builder folded it.
OVERRIDES = {
    "Fažana-Fasana": ("Fažana", "the roster writes both names of Fažana (Fasana) as one place; the map's marker is Fažana"),
    "Mione di Ovaro": ("Mione", "the roster adds the comune (Ovaro); the map's marker is the village, Mione"),
}


def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def loose(s):
    """The map builder's key (scripts/build-map.py loose()): a key that survives spelling. Keep in step with it."""
    s = re.sub(r"\(.*?\)", " ", strip(s)).split(",")[0]
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    for a, b in (("cz", "c"), ("ch", "c"), ("sz", "s"), ("sh", "s"), ("zh", "z"), ("tz", "c"), ("y", "i"), ("j", "i"), ("w", "v")):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)


def km(a, b):
    r = math.pi / 180
    dl, dn = (b[0] - a[0]) * r, (b[1] - a[1]) * r
    x = math.sin(dl / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dn / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def jl(p):
    return json.load(io.open(p, encoding="utf-8"))


def build():
    markers = jl(MAP)["places"]
    by_key = collections.defaultdict(list)
    by_name = collections.Counter(m["name"] for m in markers)
    for m in markers:
        by_key[loose(m["name"])].append(m)
    by_exact = {m["name"]: m for m in markers if by_name[m["name"]] == 1}
    rr = jl(RR)["places"]
    pm = jl(PM)
    coords = {}
    for k, v in pm.items():
        coords[v.get("name") or k] = (v["lat"], v["lon"])
    rows, why = [], {}
    for p in sorted(rr, key=lambda x: x["n"]):
        name = p["n"]
        pt = (p["lat"], p["lon"]) if p.get("lat") is not None else coords.get(name)
        row = {"rr": name, "rr_lat": pt[0] if pt else None, "rr_lon": pt[1] if pt else None, "atlas_id": p.get("id")}
        cand, note = None, None
        if name in OVERRIDES:
            tgt, note = OVERRIDES[name]
            cand = by_exact.get(tgt)
        elif pt:
            near = sorted(((km(pt, (c["lat"], c["lon"])), c) for c in by_key.get(loose(name), [])), key=lambda x: x[0])
            if near and near[0][0] <= MATCH_KM:
                cand = near[0][1]
        if cand is None:
            row.update({"map": None, "status": "absent", "layers": [], "shelf": None})
            if not pt: row["why"] = "no coordinates in Roots & Routes"
            elif by_key.get(loose(name)): row["why"] = "a marker with this name exists, but not within %d km" % MATCH_KM
            else: row["why"] = "no marker with this name"
        else:
            d = km(pt, (cand["lat"], cand["lon"])) if pt else None
            unique = by_name[cand["name"]] == 1
            cats = cand.get("cats") or {}
            row.update({"map": cand["name"] if unique else None, "map_lat": cand["lat"], "map_lon": cand["lon"], "km": round(d, 2) if d is not None else None,
                        "status": ("offset" if d is not None and d > FLAG_KM else "ok") if unique else "ambiguous",
                        "layers": sorted(cats), "shelf": cats.get("shelf") if cats.get("shelf") not in (None, "_none") else None})
            if note: row["note"] = note
            if unique:
                ev = cand.get("events") or []
                row["births"] = (ev[0][1] if ev and isinstance(ev[0], list) and len(ev[0]) > 1 and str(ev[0][0]).strip().startswith("Births") else None)
        rows.append(row)
    c = collections.Counter(r["status"] for r in rows)
    out = {"note": "Which marker on /map/ is each place Roots & Routes draws. Made by scripts/build-place-crosswalk.py; do not edit by hand. A match needs the map builder's name key AND a distance of at most %d km; one further than %d km is flagged 'offset'." % (MATCH_KM, FLAG_KM),
           "rules": {"match_km": MATCH_KM, "flag_km": FLAG_KM},
           "stats": {"places": len(rows), "ok": c["ok"], "offset": c["offset"], "ambiguous": c["ambiguous"], "absent": c["absent"],
                     "with_shelf": sum(1 for r in rows if r.get("shelf"))},
           "places": rows}
    return out


def main():
    check = "--check" in sys.argv
    out = build()
    text = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    if check:
        have = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != text:
            print("place-crosswalk: STALE. python3 scripts/build-place-crosswalk.py"); sys.exit(1)
        print("place-crosswalk: current (%d places)" % out["stats"]["places"]); return
    io.open(OUT, "w", encoding="utf-8").write(text)
    s = out["stats"]
    print("place-crosswalk: %d places: %d ok, %d offset more than %d km, %d ambiguous, %d not on the map; %d carry a shelf state"
          % (s["places"], s["ok"], s["offset"], FLAG_KM, s["ambiguous"], s["absent"], s["with_shelf"]))
    for r in out["places"]:
        if r["status"] in ("offset", "ambiguous", "absent"):
            print("  %-9s %-28s %s" % (r["status"], r["rr"], ("%.1f km from %s" % (r["km"], r["map"] or "(marker name shared)")) if r.get("km") is not None else r.get("why", "")))


if __name__ == "__main__":
    main()
