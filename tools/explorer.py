#!/usr/bin/env python3
"""Fold households and lineage links into one graph the browser can walk.

Each node is a household (a parent pair with their recorded children).
Edges are the descent links the linker was willing to defend, carrying the
child through whom the link runs and how confident it is.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "site", "src", "data")

hh = json.load(open(os.path.join(D, "households.json")))
lin = json.load(open(os.path.join(D, "lineages.json")))

# households.json has no explicit ids; the linker numbered them h001.. in order
for i, h in enumerate(hh):
    h["id"] = "h%03d" % (i + 1)
by = {h["id"]: h for h in hh}

up, down = {}, {}
for L in lin["links"]:
    c, p = L["child"], L["parent"]
    if c not in by or p not in by:
        continue
    up.setdefault(c, []).append({"id": p, "via": L["via"], "gap": L["gap"], "conf": L["confidence"]})
    down.setdefault(p, []).append({"id": c, "via": L["via"], "gap": L["gap"], "conf": L["confidence"]})

nodes = []
for h in hh:
    kids = [{"name": c["name"], "sex": c.get("sex", ""), "y": c.get("by"),
             "d": c.get("dy"), "ours": bool(c.get("ours")), "id": c.get("id"),
             "key": c.get("key")}
            for c in h.get("children", [])]
    nodes.append({
        "id": h["id"],
        "father": h.get("father") or "—",
        "mother": h.get("mother") or "—",
        "place": h.get("place") or "unknown",
        "region": h.get("region") or "",
        "from": h.get("from"), "to": h.get("to"),
        "n": h.get("n", len(kids)),
        "line": h.get("line", "male"),
        "children": kids,
        "up": up.get(h["id"], []),
        "down": down.get(h["id"], []),
    })

# a household with no parent and at least one child household heads a tree
roots = [n["id"] for n in nodes if not n["up"] and n["down"]]

out = {"nodes": nodes, "roots": roots,
       "places": sorted({n["place"] for n in nodes}),
       "ambiguous": lin.get("ambiguous", [])}
json.dump(out, open(os.path.join(D, "explorer.json"), "w"), indent=1, ensure_ascii=False)

linked = sum(1 for n in nodes if n["up"] or n["down"])
print(f"{len(nodes)} households, {len(lin['links'])} links, "
      f"{linked} connected, {len(roots)} heads of descent")
