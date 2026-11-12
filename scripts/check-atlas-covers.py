#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Does the Record Atlas really list every volume this archive's Parish Books page stopped listing? (12 November 2026)

For every parish the page now links to the Atlas (site/src/data/atlas-places.json), each volume's FamilySearch waypoint (the `wc`
of parishbooks.json, kvarner-books.json, dalmatia-books.json, carnia-books.json) must stand under that same Atlas place in the
Atlas's own volume catalogue (data/fs-volumes.json + data/fs-volumes-world.json.gz, the files its place pages are built from).
Exit 1 if any is missing. Needs the Atlas checkout (read-only), so it is run by hand when the page changes, not in CI.

    python3 scripts/check-atlas-covers.py [--atlas "<Record Atlas checkout>"]
"""
import json, os, sys, gzip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "site", "src", "data")
ATLAS = "/Volumes/DJ - Crucial - 4TB-SSD/Claude Projects/Family Projects/Record Atlas"
if "--atlas" in sys.argv:
    ATLAS = sys.argv[sys.argv.index("--atlas") + 1]


def wcs(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "wc" and isinstance(v, str):
                acc.add(v.split(":")[0])
            else:
                wcs(v, acc)
    elif isinstance(o, list):
        for x in o:
            wcs(x, acc)


byplace = {}
for f in ("fs-volumes.json", "fs-volumes-world.json.gz"):
    p = os.path.join(ATLAS, "data", f)
    d = json.loads(gzip.open(p, "rt", encoding="utf-8").read() if p.endswith(".gz") else open(p, encoding="utf-8").read())
    for place, vols in (d.get("byPlace") or {}).items():
        for v in vols:
            w = (v.get("waypoint") or v.get("wp") or "").split(":")[0]
            if w:
                byplace.setdefault(place, set()).add(w)

ids = json.load(open(os.path.join(D, "atlas-places.json"), encoding="utf-8"))["ids"]
groups = {}
pb = json.load(open(os.path.join(D, "parishbooks.json"), encoding="utf-8"))
for k, vv in pb["links"].items():
    groups.setdefault(k, set()).update(v["wc"].split(":")[0] for v in vv.values())
for f, key in (("kvarner-books", "parishes"), ("dalmatia-books", "parishes"), ("carnia-books", "comuni")):
    for r in json.load(open(os.path.join(D, f + ".json"), encoding="utf-8"))[key]:
        a = set()
        wcs(r, a)
        groups.setdefault(r["name"], set()).update(a)

tot = ok = 0
bad = []
linked = unlinked = 0
for name, ws in sorted(groups.items()):
    pid = ids.get(name)
    if not pid:
        unlinked += 1
        continue
    linked += 1
    for w in ws:
        tot += 1
        if w in byplace.get(pid, set()):
            ok += 1
        else:
            bad.append((name, pid, w))
print("parishes linked to the Atlas: %d; parishes with no Atlas place (full list kept on the page): %d" % (linked, unlinked))
print("waypoints under the linked Atlas place: %d of %d" % (ok, tot))
for b in bad[:20]:
    print("  MISSING", b)
sys.exit(1 if bad else 0)
