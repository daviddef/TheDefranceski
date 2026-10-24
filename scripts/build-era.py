#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The place table behind the "at the time" notes: which Record Atlas region each place on a person's page is in.

THE DECISION IS GEOMETRY, NOT A GUESS AT A NAME. data/era-ground.tsv has one row per place string exactly as a person page prints it (the
Place row of every deceased person who is not a duplicate), with the TOWN the string names (or '-' where the string names no single town: a
country, a province, a route "A -> B", two places, a homonym nobody settled) and data/era-towns.tsv has the town's point. The region is the
Record Atlas region whose ring (context.json, "ring": [lat, lon] vertices) CONTAINS that point:

    python3 scripts/build-era.py --decide <context.json>            rewrite the region and reason columns of data/era-ground.tsv
    python3 scripts/build-era.py --decide <context.json> --check    fail if the rows say anything else than the rings say
    python3 scripts/build-era.py                                    write site/src/data/era-places.json from the rows
    python3 scripts/build-era.py --check                            build gate: the file is what the rows build, every place a
                                                                    non-living person's page prints has a row, no row is stale
    python3 scripts/build-era.py --snapshot <context.json> [--report drops.json]
                                                                    also rebuild site/src/data/era-snapshot.json (version 5) from the
                                                                    Atlas's versioned contract (the deliberate refresh: nothing in a build
                                                                    ever reads the Atlas)
    python3 scripts/build-era.py --living-urls ../private/era-living.json
                                                                    write the page paths the notes must never appear on, for check:era

The rule for a point in more than one ring: the SMALLEST ring is the more specific claim and wins (a ring of the Carnia is inside the Veneto's
ring and says more), unless the next ring is within a factor of 3 of its area (two peers that overlap, istria-central and istria-south) and the
point is more than 15 km from the smaller ring's edge: then neither can be preferred and the place has no region. Within 15 km of an edge the
kit's own edge rule (erasnap.py, rule i/j of kit/docs/era-notes.md) takes over: it compares the neighbouring rings and keeps the place only
where they agree. A town whose row in data/era-towns.tsv carries an `exclude` reason (a ring known to reach over ground that was not the
region's) has no region either. A point in no ring has none.

THE POLICY ON ERAS THE ATLAS HAS NOT ASSESSED. A region era's `contested` and `approx` are null where nobody has assessed it. The kit refuses such an
era by default; this archive builds its snapshot with --unassessed allow, on purpose and on the record (the snapshot's policy says so, the gate
prints how many notes rest on an unassessed era). The other policies are the kit's defaults: --approx margin, --contested scope, --margin-years 5
(an era flagged approximate or contested about its bounds is used only for a year more than max(5, the Atlas's margin) from each bound; rule l).
Rulers are OFF (nothing here passes `rulers`).

Only places of people who are NOT living and are not duplicate pages are read.
"""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SITE = os.path.join(ROOT, "site")
KIT_TOOLS = os.path.join(SITE, "node_modules", "@daviddef", "archive-kit", "kit", "tools")
DATA = os.path.join(SITE, "src", "data")
GROUND = os.path.join(ROOT, "data", "era-ground.tsv")
TOWNS = os.path.join(ROOT, "data", "era-towns.tsv")
OUT = os.path.join(DATA, "era-places.json")
SNAP = os.path.join(DATA, "era-snapshot.json")
EDGE_KM = 15.0
PEER_FACTOR = 3.0


def rows_of(path):
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        yield line.rstrip("\n").split("\t")


def ground():
    rows = {}
    header = None
    for cols in rows_of(GROUND):
        if cols[0] == "place":
            header = cols
            continue
        place, region, why, town = (cols + ["", "", "", ""])[:4]
        if not place or not region or not why:
            raise SystemExit("era-ground.tsv: a row needs a place, a region (or '-') and a reason: %r" % cols[0][:60])
        if place in rows:
            raise SystemExit("era-ground.tsv: a place appears twice (a row must say one thing)")
        rows[place] = [region, why, town or ""]
    return rows


def towns():
    out = {}
    for cols in rows_of(TOWNS):
        if cols[0] == "town":
            continue
        cols = (cols + ["", "", "", "", ""])[:5]
        out[cols[0]] = (float(cols[1]), float(cols[2]), cols[3], cols[4])
    return out


def roster():
    return json.load(open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]


def has_name(s):
    return any(c.isalnum() for c in str(s))


def place_of_page(r):
    """The place string a person page prints in its Place row, or None where it draws no note at all (rule c)."""
    if r.get("living") or r.get("sameAs"):
        return None
    p = r.get("place")
    return p if p and has_name(p) else None


def event_places():
    out = {}
    for r in roster():
        p = place_of_page(r)
        if p:
            out[p] = out.get(p, 0) + 1
    return out


# --- ring geometry (a flat projection, as the kit's edge rule measures; nothing here is imported from the kit) ---
def contains(lat, lon, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def area_km2(ring):
    k = math.cos(math.radians(sum(p[0] for p in ring) / len(ring)))
    a = 0.0
    n = len(ring)
    for i in range(n):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % n]
        a += x1 * k * y2 - x2 * k * y1
    return abs(a) / 2 * 111.195 ** 2


def edge_km(lat, lon, ring):
    k = math.cos(math.radians(lat))
    best = 1e9
    n = len(ring)
    for i in range(n):
        ay, ax = ring[i]
        by, bx = ring[(i + 1) % n]
        px, py = (lon - ax) * k * 111.195, (lat - ay) * 111.195
        qx, qy = (bx - ax) * k * 111.195, (by - ay) * 111.195
        ll = qx * qx + qy * qy
        t = 0 if ll == 0 else max(0.0, min(1.0, (px * qx + py * qy) / ll))
        best = min(best, math.hypot(px - t * qx, py - t * qy))
    return best


def load_rings(contract):
    d = json.load(open(contract, encoding="utf-8"))
    return {r["id"]: r["ring"] for r in d["regions"] if r.get("ring") and r.get("eras")}


def decide_town(lat, lon, exclude, rings):
    """-> (region or '-', reason)"""
    if exclude:
        return "-", "excluded: " + exclude
    hit = sorted((area_km2(r), k) for k, r in rings.items() if contains(lat, lon, r))
    if not hit:
        return "-", "inside no ring of the Atlas's regions"
    own = hit[0][1]
    d = edge_km(lat, lon, rings[own])
    if len(hit) == 1:
        return own, "inside the ring of %s (%.0f km from its edge)" % (own, d)
    nxt = hit[1]
    if nxt[0] < PEER_FACTOR * hit[0][0] and d > EDGE_KM:
        return "-", "inside the rings of %s and %s, two peers, and %.0f km from the edge of the smaller: neither is preferred" % (own, nxt[1], d)
    others = ", ".join(k for _, k in hit[1:])
    return own, "inside the rings of %s (the smallest, %.0f km from its edge) and %s" % (own, d, others)


def decided(contract):
    rings = load_rings(contract)
    pts = towns()
    rows = ground()
    new = {}
    for place, (region, why, town) in rows.items():
        if not town:
            new[place] = (region, why, town)
            continue
        if town not in pts:
            raise SystemExit("era-ground.tsv: town %r has no row in era-towns.tsv" % town)
        lat, lon, _, excl = pts[town]
        r, w = decide_town(lat, lon, excl, rings)
        new[place] = (r, "%s: %s" % (town, w), town)
    return rows, new


def write_ground(new):
    head = [l for l in open(GROUND, encoding="utf-8") if l.startswith("#")]
    with open(GROUND, "w", encoding="utf-8") as f:
        f.writelines(head)
        f.write("place\tregion\twhy\ttown\n")
        for place in sorted(new):
            region, why, town = new[place]
            f.write("%s\t%s\t%s\t%s\n" % (place, region, why, town))


def build():
    rows = ground()
    used = event_places()
    pts = towns()
    table = {}
    for place in sorted(rows):
        region, _, town = rows[place]
        if region == "-":
            table[place] = None
            continue
        table[place] = {"region": region}
        if town:
            if town not in pts:
                raise SystemExit("era-ground.tsv: town %r has no row in era-towns.tsv" % town)
            table[place].update(lat=pts[town][0], lon=pts[town][1])
    return rows, used, table


def living_urls():
    urls = []
    for r in roster():
        if r.get("living"):
            urls.append("/person/%s/" % r["pid"])
    byname = {}
    for r in roster():
        if r.get("who"):
            byname.setdefault(r["who"], []).append(r)
    for who, rs in byname.items():
        if all(r.get("living") for r in rs):
            urls.append(who if who.endswith("/") else who + "/")
    return sorted(set(urls))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--decide", default=None, help="a local copy of the Record Atlas's context.json: decide the region of each town by ring geometry")
    ap.add_argument("--snapshot", default=None, help="a local copy of the Record Atlas's context.json (the versioned contract): also rebuild era-snapshot.json")
    ap.add_argument("--report", default=None, help="write the per-region count of refused eras (and why) here (JSON)")
    ap.add_argument("--living-urls", default=None, help="write the living page paths here (JSON list) and stop")
    a = ap.parse_args()
    if a.living_urls:
        urls = living_urls()
        if not urls:
            raise SystemExit("build-era: no living page found; a list of none would make the living gate a verdict on nothing")
        os.makedirs(os.path.dirname(os.path.abspath(a.living_urls)), exist_ok=True)
        open(a.living_urls, "w", encoding="utf-8").write(json.dumps(urls, indent=0) + "\n")
        print("era living list: %d page path(s)" % len(urls))
        return 0
    if a.decide:
        old, new = decided(a.decide)
        diff = [p for p in new if new[p][:2] != tuple(old[p][:2])]
        if a.check:
            if diff:
                print("  FAIL  era-ground  %d row(s) say something other than the rings of %s say (run scripts/build-era.py --decide)" % (len(diff), os.path.basename(a.decide)))
                return 1
            print("  ok    era-ground  every region in data/era-ground.tsv is what the ring geometry of the contract says")
            return 0
        write_ground(new)
        print("era-ground.tsv: %d rows, %d changed" % (len(new), len(diff)))
    rows, used, table = build()
    missing = sorted(set(used) - set(rows))
    stale = sorted(set(rows) - set(used))
    out = {"_about": "Built by scripts/build-era.py from data/era-ground.tsv and data/era-towns.tsv. Place as printed -> {region, lat, lon}, or null where no Atlas "
                     "region covers it. Read by kit erasnap.py.", "places": table}
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.check:
        bad = False
        if missing:
            print("  FAIL  era-ground  %d place string(s) a deceased person's page prints have no row in data/era-ground.tsv "
                  "(decide a town, or '-', for each)" % len(missing))
            bad = True
        if stale:
            print("  FAIL  era-ground  %d row(s) in data/era-ground.tsv match no place (stale)" % len(stale))
            bad = True
        try:
            have = open(OUT, encoding="utf-8").read()
        except OSError:
            have = None
        if have != text:
            print("  FAIL  era-ground  site/src/data/era-places.json is not what the rows build (run scripts/build-era.py)")
            bad = True
        if not bad:
            mapped = sum(1 for v in table.values() if v)
            print("  ok    era-ground  %d place strings decided (%d mapped to a region, %d to none); the table matches" % (len(table), mapped, len(table) - mapped))
        return 1 if bad else 0
    open(OUT, "w", encoding="utf-8").write(text)
    print("era-places.json: %d place strings (%d mapped)" % (len(table), sum(1 for v in table.values() if v)))
    if missing:
        print("  WARNING %d place string(s) have no row in data/era-ground.tsv" % len(missing))
        return 1
    if a.snapshot:
        cmd = [sys.executable, os.path.join(KIT_TOOLS, "erasnap.py"), "--contract", a.snapshot,
               "--places", OUT, "--out", SNAP, "--unassessed", "allow"]
        if a.report:
            cmd += ["--report", a.report]
        return subprocess.run(cmd).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
