#!/usr/bin/env python3
"""Build site/src/data/changes.json — one reverse-chronological feed.

Merges the Search Register (every search, including the ones that found
nothing) with Corrections (every claim taken back), so a reader can see
what the archive did on a given day and what it had to undo.

    python3 scripts/build-changes.py
"""
import json, os, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
load = lambda n: json.load(open(os.path.join(DATA, n), encoding="utf-8"))

MON = {m: i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}

def key(when):
    """Sortable key from the archive's own informal dates: '9 Sept 2026'."""
    w = str(when or "").replace("Sept", "Sep")
    m = re.search(r"(\d{1,2})?\s*([A-Z][a-z]{2})[a-z]*\s*(\d{4})", w)
    if not m: return (0, 0, 0)
    d, mon, y = m.group(1), m.group(3), m.group(3)
    return (int(m.group(3)), MON.get(m.group(2), 0), int(m.group(1) or 0))

rows = []
for r in load("searched.json")["rows"]:
    rows.append({"when": r.get("when", ""), "kind": r.get("outcome", "search"),
                 "what": r.get("what", ""), "src": r.get("src", ""),
                 "text": r.get("got", ""), "href": "/research-log/"})
for r in load("corrections.json")["rows"]:
    rows.append({"when": r.get("when", ""), "kind": "correction",
                 "what": r.get("what", ""), "src": "A claim taken back",
                 "text": "**This archive said** " + r.get("said", "") +
                         "\n\n**What is true** " + r.get("true", "") +
                         "\n\n**How it happened** " + r.get("how", ""),
                 "href": r.get("where") or "/corrections/"})

rows.sort(key=lambda r: key(r["when"]), reverse=True)
days = []
for r in rows:
    if not days or days[-1]["when"] != r["when"]:
        days.append({"when": r["when"], "rows": []})
    days[-1]["rows"].append(r)

out = {
 "title": "What changed",
 "eyebrow": f"{len(rows)} entries · {sum(1 for r in rows if r['kind']=='correction')} of them corrections",
 "dek": "Every search this archive has run and every claim it has taken back, newest first.",
 "lead": "Most family archives publish only what they found. This one publishes **what it looked for, what it found, what it did not find, and what it got wrong** — in one feed, in the order it happened.\n\nA search that returned nothing is kept because **an absence from a named source is a finding**, and because the next person should not have to repeat it. A correction is kept because an archive that only shows its successes is not telling you how reliable it is.",
 "days": days,
 "close": "This page is generated from the Search Register and the Corrections list; neither is written for it. If something is here twice, it is because it was both a search and a mistake.",
}
json.dump(out, open(os.path.join(DATA, "changes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"changes.json · {len(rows)} entries across {len(days)} days")
