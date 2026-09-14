#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fold the FamilySearch waypoint harvest into the research map.

The harvest itself is done in the browser, because FamilySearch's security
service blocks the in-app browser's egress IP and only David's own Chrome gets
through. It walks the collection's own tree — seven confession roots, then one
call per parish — and leaves a dictionary in the page:

    window.__PAR  [[layer, parish, waypoint], ...]        the parish list
    window.__CAT  {"layer|parish": [[title, waypoint]]}   the books

That is pulled out in chunks and written to data/fs-catalogue.json, which this
script reads. It is the catalogue of *what exists*, independent of David's map
and independent of what this archive has read.

    python3 scripts/ingest-fs-catalogue.py

Volume counts here replace the ones the research map derived from the archive's
own three regional files, because this walk is the whole collection rather than
the parishes somebody happened to need.
"""
import json, os, re, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
CAT  = os.path.join(ROOT, "data", "fs-catalogue.json")

LABEL = {"rc": "Roman Catholic", "orth": "Orthodox", "gc": "Greek Catholic",
         "jew": "Jewish", "mil": "Military", "ref": "Reformed",
         "civil": "Civil", "ev": "Evangelical"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\(.*?\)", " ", s).split(",")[0]
    return re.sub(r"[^a-z0-9]+", "", s)

# A volume title is a run of «Event (Hrvatski) years» clauses. Splitting it
# gives the event types and the true year span, which is what a coverage map
# needs and what a single string cannot answer.
EVENT = re.compile(r"(Births|Marriages|Deaths|Church Census|Confirmations|Index)\s*"
                   r"\(([^)]*)\)\s*([0-9,\s\-–]*)")

def parse(title):
    kinds, years = [], []
    for m in EVENT.finditer(title or ""):
        kinds.append(m.group(1))
        for y in re.findall(r"\b(1[5-9]\d\d)\b", m.group(3) or ""):
            years.append(int(y))
    if not years:
        years = [int(y) for y in re.findall(r"\b(1[5-9]\d\d)\b", title or "")]
    return sorted(set(kinds)), (min(years) if years else None), (max(years) if years else None)

def main():
    raw = json.load(open(CAT, encoding="utf-8"))
    par, cat = raw["parishes"], raw["books"]

    places = collections.defaultdict(lambda: {"names": set(), "shelves": {}})
    for lay, name, wp in par:
        k = norm(name)
        p = places[k]
        p["names"].add(name)
        books = cat.get(lay + "|" + name, [])
        vols = []
        for t, bwp in books:
            kinds, lo, hi = parse(t)
            vols.append({"t": t, "wp": bwp, "kinds": kinds, "from": lo, "to": hi})
        p["shelves"][lay] = {"wp": wp, "books": vols}

    out = []
    for k, p in sorted(places.items(), key=lambda kv: sorted(kv[1]["names"])[0]):
        allb = [b for s in p["shelves"].values() for b in s["books"]]
        yrs  = [b["from"] for b in allb if b["from"]] + [b["to"] for b in allb if b["to"]]
        out.append({"key": k, "name": sorted(p["names"], key=len)[0],
                    "names": sorted(p["names"]),
                    "layers": sorted(p["shelves"]),
                    "shelves": p["shelves"],
                    "volumes": len(allb),
                    "earliest": min(yrs) if yrs else None,
                    "latest": max(yrs) if yrs else None,
                    "kinds": sorted({x for b in allb for x in b["kinds"]})})

    stats = {"places": len(out), "shelves": sum(len(o["shelves"]) for o in out),
             "volumes": sum(o["volumes"] for o in out),
             "empty": sum(1 for o in out if not o["volumes"]),
             "byLayer": dict(collections.Counter(l for o in out for l in o["layers"])),
             "volumesByLayer": dict(collections.Counter(
                 {l: sum(len(s["books"]) for lay, s in o["shelves"].items() if lay == l)
                  for o in out for l in o["layers"]})),
             "earliest": min([o["earliest"] for o in out if o["earliest"]] or [None]),
             "latest": max([o["latest"] for o in out if o["latest"]] or [None])}

    json.dump({"note": "Croatia, Church Books 1516–1994 (collection 2040054), walked from "
                       "the collection's own waypoint tree rather than from any map. "
                       "Every parish in every confession, and every volume in each.",
               "collection": "2040054", "stats": stats, "places": out},
              open(os.path.join(DATA, "fscatalogue.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
