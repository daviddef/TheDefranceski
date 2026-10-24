#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This archive's own sovereignty bands (site/src/data/sovereignty.json) against the Record Atlas's eras for the regions it seeded from them.

The Atlas wrote istria-central, istria-south, istria-west, kvarner, carnia and dalmatia from this archive's sovereignty.json (their eras'
`basis` is `seeded:defranceschi-sovereignty`). Year by year, 1200 to 2025, this compares the regime our lane names with the regime the Atlas's
era names, for the lane -> region pairs below, and counts where they disagree. COUNTS AND ERA IDS ONLY: no person, no place that belongs to one.

    python3 scripts/compare-sovereignty.py <context.json> [--json out.json]

Lanes: istria -> istria-central; sistria -> istria-south and istria-west (the west is a copy of the south); kvarner, carnia, dalmatia one to one.
Kinds of disagreement: `differ` (both name a regime and the regimes are not the same), `atlas-only` (the Atlas has an era over the year and our lane
has no band), `lane-only` (our lane has a band and the Atlas has no era over the year).
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PAIRS = [("istria", "istria-central"), ("sistria", "istria-south"), ("sistria", "istria-west"), ("kvarner", "kvarner"), ("carnia", "carnia"), ("dalmatia", "dalmatia")]
FROM, TO = 1200, 2025


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("contract")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    sov = json.load(open(os.path.join(ROOT, "site", "src", "data", "sovereignty.json"), encoding="utf-8"))
    lanes = {l["id"]: l["bands"] for l in sov["lanes"]}
    doc = json.load(open(a.contract, encoding="utf-8"))
    regions = {r["id"]: r.get("eras") or [] for r in doc["regions"]}

    def lane_at(lane, y):
        for f, t, reg, _ in lanes[lane]:
            if f <= y < t:
                return reg
        return None

    def era_at(region, y):
        hit = [e for e in regions[region] if e["from"] <= y and (e["to"] is None or y < e["to"])]
        return hit[0] if len(hit) == 1 else (None if not hit else hit[0])

    agree = 0
    kinds = collections.Counter()
    by_era = collections.defaultdict(lambda: collections.Counter())
    for lane, region in PAIRS:
        for y in range(FROM, TO + 1):
            l, e = lane_at(lane, y), era_at(region, y)
            if l is None and e is None:
                continue
            if l is not None and e is not None and l == e["regime"]:
                agree += 1
                continue
            kind = "differ" if (l is not None and e is not None) else ("atlas-only" if e is not None else "lane-only")
            kinds[kind] += 1
            by_era[(region, e["id"] if e else "(no era)")][kind] += 1
    total = sum(kinds.values())
    print("sovereignty.json against the Atlas's seeded eras (%d-%d, %d lane -> region pairs): %d region-years agree, %d disagree" % (FROM, TO, len(PAIRS), agree, total))
    print("  by kind: " + ", ".join("%s %d" % (k, v) for k, v in sorted(kinds.items())))
    rows = []
    for (region, eid), c in sorted(by_era.items()):
        rows.append({"region": region, "era": eid, "years": sum(c.values()), **dict(c)})
        print("  %-18s %-26s %3d  %s" % (region, eid, sum(c.values()), dict(c)))
    ids = {r["era"] for r in rows if r["era"] != "(no era)"}
    print("  %d Atlas eras differ from our lane in at least one year; %d region-years fall where the Atlas has no era" %
          (len(ids), sum(r["years"] for r in rows if r["era"] == "(no era)")))
    if a.json:
        json.dump({"agree": agree, "disagree": total, "kinds": dict(kinds), "rows": rows}, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
