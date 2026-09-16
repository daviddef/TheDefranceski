#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fold a harvest of first-image arks into site/src/data/fs-elsewhere.json.

Two FamilySearch collections file Croatian towns under another country's name —
Pola and Trieste under Italy, Prekmurje and Međimurje under Slovenia — and the
walk that found them recorded each volume's waypoint and no ark. Without an ark
a volume has no address, so 33 places on the map carried filmed registers and
not one clickable row. The Croatia Church Books harvest of 15 September never
touched these two.

A waypoint id is «PREFIX:ancestor,ancestor,…» and the API answers on the prefix
alone, which is the whole reason this harvest could be driven from a four-
kilobyte list instead of a thirty-four kilobyte one.

    python3 scripts/merge-elsewhere-arks.py <harvest.json>

where harvest.json is {waypointPrefix: ark}.
"""
import json, sys, os, io, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELS = os.path.join(ROOT, "site", "src", "data", "fs-elsewhere.json")

def main(src):
    got = json.load(io.open(src, encoding="utf-8"))
    d = json.load(io.open(ELS, encoding="utf-8"))
    new = same = miss = 0
    bycc = collections.Counter()
    for rec in d["places"].values():
        for b in rec["books"]:
            ark = got.get((b.get("wp") or "").split(":", 1)[0])
            if not ark:
                if not b.get("ark"):
                    miss += 1
                continue
            if b.get("ark") == ark:
                same += 1
            else:
                b["ark"] = ark
                new += 1
                bycc[rec["cc"]] += 1
    json.dump(d, io.open(ELS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = sum(len(r["books"]) for r in d["places"].values())
    have = sum(1 for r in d["places"].values() for b in r["books"] if b.get("ark"))
    print(json.dumps({"harvested": len(got), "new": new, "unchanged": same,
                      "still_without": miss, "volumes": tot, "linkable": have,
                      "byCollection": dict(bycc)}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main(sys.argv[1])
