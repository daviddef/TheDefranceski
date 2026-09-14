#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build site/src/data/movements.json — the arrows on the Atlas.

Fifty-six of them are David's own, drawn by hand on his Google My Map over
years. They are kept as his: labelled «from the family's own map», drawn
dashed, and never upgraded to evidence this archive does not hold. The
documented descent — the nine places the archive can order from records — is
the only line drawn solid.
"""
import json, io, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
def load(n): return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))

mymap = load("mymap.json")
atlas = load("atlas.json")

def km(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * 6371 * math.asin(math.sqrt(h))

moves = []
for layer in mymap["layers"]:
    for l in layer["lines"]:
        path = l.get("path") or []
        if len(path) < 2: continue
        a, b = path[0], path[-1]
        if km(a, b) < 1: continue
        moves.append({
            "n": (l.get("n") or "").strip() or "unnamed",
            "layer": layer["name"],
            "from": a, "to": b,
            "km": round(km(a, b)),
            "src": "mymap",
            "note": l.get("note", ""),
        })

# the archive's own documented descent, in the order it can prove
spine = sorted([p for p in atlas["places"] if p.get("order")], key=lambda p: p["order"])
line  = [[p["lat"], p["lon"]] for p in spine]
steps = []
for i in range(len(spine) - 1):
    a, b = spine[i], spine[i + 1]
    steps.append({"n": a["name"] + " → " + b["name"],
                  "from": [a["lat"], a["lon"]], "to": [b["lat"], b["lon"]],
                  "km": round(km([a["lat"], a["lon"]], [b["lat"], b["lon"]])),
                  "when": b.get("when", ""), "src": "spine"})

d = {
 "note": ("Fifty-six of these arrows are **David's own**, drawn by hand on his Google My Map. They are kept exactly "
          "as he drew them and are **drawn dashed**, because this archive has not verified them one by one and motion "
          "on a map is persuasive in a way that evidence is not. **The solid line is the documented descent** — the "
          "places the archive can order from records — and even that has a gap it cannot close."),
 "caution": ("**An arrow is a claim that someone moved.** Most of the surname's appearances earlier in one place and "
             "later in another are not journeys; they are two records. The one journey this archive holds a document "
             "for is Zuane De Franceschi of Mione, working in the County of Pazin in 1679."),
 "spine": {"path": line, "steps": steps,
           "names": [p["name"] for p in spine]},
 "moves": moves,
 "layers": sorted({m["layer"] for m in moves}),
 "counts": {"moves": len(moves), "spine": len(steps),
            "longest": max((m["km"] for m in moves), default=0)},
}
json.dump(d, io.open(os.path.join(DATA, "movements.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(d["counts"], indent=1))
print("layers:", d["layers"])
print("spine:", " → ".join(d["spine"]["names"]))
