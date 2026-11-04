#!/usr/bin/env python3
"""The Record Atlas's dated mass-death events, in full, for the events this archive's places touch.

Roots & Routes' slice (data/tree-page/atlas-data.json) already says which events touch each place (places[].ev) but keeps only the first
190 characters of what each event says and 170 of its toll. A person's page quotes both whole, so this copies those events, complete,
from the Atlas's data/mass-death-events.json into site/src/data/atlas-events.json: {event id: {...}}.

    RECORD_ATLAS=~/Projects/Family\\ Projects/Record\\ Atlas python3 scripts/build-atlas-events.py
"""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
atlas = os.path.expanduser(os.environ.get("RECORD_ATLAS", "~/Projects/Family Projects/Record Atlas"))
sl = json.load(open(os.path.join(root, "data/tree-page/atlas-data.json"), encoding="utf-8"))
want = {i for p in sl["places"] for i in p.get("ev", [])}
src = {e["id"]: e for e in json.load(open(os.path.join(atlas, "data/mass-death-events.json"), encoding="utf-8"))["events"]}
out = {}
for i in sorted(want):
    e = src.get(i)
    if not e: print("missing in the Atlas:", i); continue
    t = e.get("toll") or {}
    out[i] = {"name": e["name"], "type": e["type"], "from": e["from"], "to": e["to"], "says": e.get("says", ""),
              "toll": t.get("text", ""), "open": e.get("open", ""), "wiki": e.get("wiki", ""),
              "url": next((s["url"] for s in e.get("sources", []) if s.get("url")), "")}
json.dump(out, open(os.path.join(root, "site/src/data/atlas-events.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} events written for {len(want)} wanted")
