#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write private/lines-living.json: the person ids that must never be listed on the lines page (the kit's checklines --living).

    python3 scripts/build-lines-living.py

From the COMMITTED roster alone, so CI builds the same file: every row marked living, and every row the shared rule calls
living from what the row holds (living_v2.row_is_living: a birth year in the window and no death record). Ids only, no names.
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_v2 as L2

ROOT = L2.ROOT
rows = json.load(io.open(os.path.join(ROOT, "site", "src", "data", "roster.json"), encoding="utf-8"))["rows"]
slugs = sorted({r["pid"] for r in rows if r.get("pid") and (r.get("living") or L2.row_is_living(r))})
out = os.path.join(ROOT, "private", "lines-living.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
io.open(out, "w", encoding="utf-8").write(json.dumps({"slugs": slugs}, indent=1) + "\n")
print("lines-living: %d person id(s) written to private/lines-living.json" % len(slugs))
