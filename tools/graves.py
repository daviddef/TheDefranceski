#!/usr/bin/env python3
"""The grave gazetteer: where the name is actually cut into stone.

One row per memorial recorded on Find a Grave for any spelling of the surname.
Grouped by country and by cemetery, because the clusters are the finding — a
single Connecticut churchyard holds more of this name than the whole of Croatia.
"""
import csv, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "graves.tsv")
OUT = os.path.join(ROOT, "site", "src", "data", "graves.json")

SPELLING = [
    (r"^Defranceski|^De Franceski", "Defranceski"),
    (r"^DeFranceschi|^deFranceschi", "DeFranceschi"),
    (r"^De Franceschi|^de Franceschi", "De Franceschi"),
    (r"^Defranceschi", "Defranceschi"),
]

def years(s):
    y = re.findall(r"\b(1[6-9]\d\d|20\d\d)\b", s)
    b = int(y[0]) if len(y) > 1 else None
    d = int(y[-1]) if y else None
    if len(y) == 1:
        b, d = None, int(y[0])
    return b, d

rows = []
for r in csv.reader(open(SRC, encoding="utf-8"), delimiter="\t"):
    if len(r) < 5 or not r[0].strip():
        continue
    mid, name, span, cem, place = (x.strip() for x in r[:5])
    plot = r[5].strip() if len(r) > 5 else ""
    b, d = years(span)
    country = place.split(",")[-1].strip()
    sp = next((lab for pat, lab in SPELLING if re.match(pat, name)), "other")
    rows.append({"id": mid, "name": name, "span": span, "b": b, "d": d,
                 "age": (d - b) if (b and d and d >= b) else None,
                 "cem": cem, "place": place, "plot": plot,
                 "country": country, "spelling": sp,
                 "url": f"https://www.findagrave.com/memorial/{mid}"})

rows.sort(key=lambda r: (r["country"], r["cem"], r["name"]))

def tally(key):
    t = {}
    for r in rows: t[r[key]] = t.get(r[key], 0) + 1
    return sorted(t.items(), key=lambda kv: (-kv[1], kv[0]))

cem = {}
for r in rows:
    cem.setdefault((r["cem"], r["place"]), []).append(r["name"])
clusters = sorted(((c, p, len(n)) for (c, p), n in cem.items()), key=lambda x: -x[2])

summary = {
    "total": len(rows),
    "countries": tally("country"),
    "spellings": tally("spelling"),
    "clusters": [{"cem": c, "place": p, "n": n} for c, p, n in clusters if n > 1],
    "earliest": min((r["d"] for r in rows if r["d"]), default=None),
    "latest": max((r["d"] for r in rows if r["d"]), default=None),
    "croatia": [r for r in rows if r["country"] == "Croatia"],
    "australia": [r for r in rows if r["country"] == "Australia"],
}
json.dump({"rows": rows, "summary": summary}, open(OUT, "w"), indent=1, ensure_ascii=False)
print(f"{len(rows)} memorials")
for k, v in summary["countries"]: print(f"  {v:3d}  {k}")
print("clusters >1:")
for c in summary["clusters"][:8]: print(f"  {c['n']:3d}  {c['cem']} — {c['place']}")
