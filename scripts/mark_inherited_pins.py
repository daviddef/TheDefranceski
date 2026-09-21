#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mark map pins that have inherited a containing place's coordinate.

A neighbouring archive — the D'Arcy one-name study — found thirty-six of its
places sitting on a containing place's point and stamped «exact»: Berkeley,
the town that archive is about, pinned on the geographic centre of England.
Its detector ports in twenty lines, so it was run here rather than assumed not
to apply.

The rule, and the reason it is written this way:

    A place has inherited its pin when its coordinate sits within a kilometre
    of another place whose full name is a comma-tail of its own.

The test is on the recorded STRING first and distance second. Distance alone
would have to guess about two towns that genuinely sit a few hundred metres
apart, and would guess wrong; «Lug, Beli Manastir» naming «Beli Manastir» as
its own tail is not a coincidence that needs adjudicating.

This map's four hits are not the same fault as the D'Arcy one. All four carry
`geo: "kml"` — the coordinate is FamilySearch's own, out of its Croatia
collection, which parks a daughter village's dot beside its district town's.
Stankovci sits 274 m from Benkovac in the file and thirteen kilometres from it
in life. The pin is not wrong because a gazetteer guessed; it is wrong because
the source clusters. The reader is shown a dot meaning «somewhere in this
district» either way, so the dot now says so.

Adds to each inherited place:  pin = "parent",  pinFrom = <the place it
inherited from>.  Idempotent: re-running re-derives both from scratch.
"""
import json, math, sys, io


def _km(a, b, c, e):
    R = 6371.0
    dla, dlo = math.radians(c - a), math.radians(e - b)
    x = (math.sin(dla / 2) ** 2
         + math.cos(math.radians(a)) * math.cos(math.radians(c))
         * math.sin(dlo / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))


def _tail(child, parent):
    c = [x.strip().lower() for x in child.split(",")]
    q = [x.strip().lower() for x in parent.split(",")]
    return len(q) < len(c) and c[-len(q):] == q


def mark(places, km=1.0):
    """Stamp inherited pins in place. Returns the number marked."""
    for o in places:
        o.pop("pin", None)
        o.pop("pinFrom", None)
    placed = [o for o in places
              if o.get("lat") is not None and o.get("lon") is not None
              and o.get("name")]
    n = 0
    for o in placed:
        for q in placed:
            if q is o or not _tail(o["name"], q["name"]):
                continue
            if _km(o["lat"], o["lon"], q["lat"], q["lon"]) < km:
                o["pin"] = "parent"
                o["pinFrom"] = q["name"]
                n += 1
                break
    return n


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "site/src/data/researchmap.json"
    d = json.load(open(path, encoding="utf-8"))
    places = d["places"] if isinstance(d, dict) else d
    n = mark(places)
    if isinstance(d, dict):
        d.setdefault("stats", {})["inheritedPins"] = n
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("inherited pins marked: %d of %d placed" %
          (n, sum(1 for o in places if o.get("lat") is not None)))
    for o in places:
        if o.get("pin") == "parent":
            print("   %-28s <- %s" % (o["name"][:28], o["pinFrom"]))
