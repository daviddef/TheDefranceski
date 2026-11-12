#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which Record Atlas place page is each parish of the register-volume pages? (12 November 2026, the Atlas-overlap trim)

The Parish Books page used to list every FamilySearch volume of every parish; the Atlas holds those (its place pages list the
volumes by waypoint), so the page now gives the parish, how far back it goes, how many volumes, and a link to the parish's own
Atlas page. This writes site/src/data/atlas-places.json: archive parish name -> Atlas place id, only where the name matches ONE
Atlas place in the right country (exact name or an alias). A name that matches none or several gets no link (never a guess).

    python3 scripts/build-atlas-place-ids.py [--atlas "<Record Atlas checkout>"]
The Atlas checkout is read-only here. The output is committed so CI builds the same page without the checkout.
"""
import json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
ATLAS = "/Volumes/DJ - Crucial - 4TB-SSD/Claude Projects/Family Projects/Record Atlas"
if "--atlas" in sys.argv:
    ATLAS = sys.argv[sys.argv.index("--atlas") + 1]


def key(s):
    return unicodedata.normalize("NFC", str(s)).strip().lower()


OVERRIDES = {"Lupoglav (Pazin)": "lupoglav"}   # the only Lupoglav the Atlas has, in Istria; checked by hand, 12 Nov 2026


def main():
    places = json.load(open(os.path.join(ATLAS, "data", "places.json"), encoding="utf-8"))
    places = places["places"] if isinstance(places, dict) else places
    by = {}
    for p in places:
        for n in [p.get("name")] + list(p.get("names") or []):
            if n:
                by.setdefault((key(n), p.get("country")), set()).add(p["id"])
    want = {}   # name -> country
    pb = json.load(open(os.path.join(DATA, "parishbooks.json"), encoding="utf-8"))
    for r in pb["list"]:
        want[r["parish"]] = "HR"
    kv = json.load(open(os.path.join(DATA, "kvarner-books.json"), encoding="utf-8"))
    for r in kv["parishes"]:
        want[r["name"]] = "HR"
    dal = json.load(open(os.path.join(DATA, "dalmatia-books.json"), encoding="utf-8"))
    for r in dal["parishes"]:
        want[r["name"]] = "HR"
    car = json.load(open(os.path.join(DATA, "carnia-books.json"), encoding="utf-8"))
    for r in car["comuni"]:
        want[r["name"]] = "IT"
    out, none, many = {}, [], []
    for name, cc in sorted(want.items()):
        # a name with a qualifier, «Hum (Buzet)», links only when the Atlas carries that very name: the bare «Hum» may be another village
        ids = by.get((key(name), cc)) or ({OVERRIDES[name]} if name in OVERRIDES else set())
        if len(ids) == 1:
            out[name] = next(iter(ids))
        elif not ids:
            none.append(name)
        else:
            many.append((name, sorted(ids)))
    json.dump({"note": "archive parish name -> Record Atlas place id; built by scripts/build-atlas-place-ids.py from the Atlas's data/places.json; only one-to-one matches", "ids": out},
              open(os.path.join(DATA, "atlas-places.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("linked %d of %d names; none %d, ambiguous %d" % (len(out), len(want), len(none), len(many)))
    print("  no match:", none[:15])
    print("  ambiguous:", many[:8])


main()
