#!/usr/bin/env python3
"""Turn the burial harvest into structured data, and work out the ages.

The registers of the dead are the part of a parish's paper that genealogy
usually skips. They are also the only place a child who died before the next
census appears at all.
"""
import csv, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "burials.tsv")
OUT = os.path.join(ROOT, "site", "src", "data", "burials.json")

MONTH = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

PLACE = [
    (r"vitipolis|fiume|rijeka", "Rijeka"),
    (r"li[žz]njan", "Ližnjan"),
    (r"pore[čc]", "Poreč"),
    (r"rovinj", "Rovinj"),
    (r"ka[šs]telir", "Kaštelir"),
    (r"pola|pula", "Pula"),
    (r"pisino|pazin", "Pazin"),
    (r"omi[šs]", "Omiš"),
    (r"almissa", "Omiš"),
    (r"spalato|split", "Split"),
    (r"bakar", "Bakar"),
    (r"sovignacco|buzet", "Sovinjak"),
    (r"\btar\b", "Tar"),
]

def year(s):
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", s or "")
    return int(m.group(1)) if m else None

def full(s):
    """Return (y, m, d) where the record gives them."""
    if not s: return None
    y = year(s)
    mo = next((MONTH[k] for k in MONTH if k in s), None)
    d = re.search(r"\b(\d{1,2})\s+[A-Z][a-z]{2}\b", s)
    return (y, mo, int(d.group(1)) if d else None) if y else None

def place(*fields):
    blob = " ".join(f or "" for f in fields).lower()
    for pat, name in PLACE:
        if re.search(pat, blob):
            return name
    if "croatia" in blob or "croazia" in blob or "hrvatsk" in blob or "regnum" in blob or "kraljevina" in blob:
        return "Croatia, parish not named"
    return "not stated"

rows = []
for r in csv.reader(open(SRC, encoding="utf-8"), delimiter="\t"):
    if len(r) < 4 or not r[0].strip(): continue
    name, b, d, bu = (r[0].strip(), r[1].strip(), r[2].strip(), r[3].strip())
    kin = r[4].strip() if len(r) > 4 else ""
    by, dy = year(b), year(d) or year(bu)
    age = (dy - by) if (by and dy and dy >= by) else None
    rows.append({
        "name": name, "born": b, "died": d, "buried": bu, "kin": kin,
        "by": by, "dy": dy, "age": age,
        "place": place(bu, d, b),
        "infant": age is not None and age <= 1,
        "child": age is not None and age <= 12,
    })

rows.sort(key=lambda r: (r["dy"] or 9999, r["name"]))

known = [r for r in rows if r["age"] is not None]
infants = [r for r in rows if r["infant"]]
children = [r for r in rows if r["child"]]
by_place = {}
for r in rows: by_place[r["place"]] = by_place.get(r["place"], 0) + 1

summary = {
    "total": len(rows),
    "withAge": len(known),
    "infants": len(infants),
    "children": len(children),
    "medianAge": sorted(x["age"] for x in known)[len(known)//2] if known else None,
    "earliest": min((r["dy"] for r in rows if r["dy"]), default=None),
    "latest": max((r["dy"] for r in rows if r["dy"]), default=None),
    "places": sorted(by_place.items(), key=lambda kv: -kv[1]),
    "oldest": max(known, key=lambda r: r["age"])["name"] if known else None,
    "oldestAge": max(r["age"] for r in known) if known else None,
}
json.dump({"rows": rows, "summary": summary}, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, ensure_ascii=False, indent=1))
