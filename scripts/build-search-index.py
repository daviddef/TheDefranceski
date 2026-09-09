#!/usr/bin/env python3
"""Rebuild site/src/data/searchindex.json from the data files.

Idempotent: drops the kinds this script owns, then regenerates them.
Run it after any change to roster.json or to a narrative data file, so
that every person in the roster is findable in the search box.

    python3 scripts/build-search-index.py
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OWNED = {"Person", "Register reading"}

def p(name): return os.path.join(DATA, name)
def load(name):
    with open(p(name)) as f: return json.load(f)

def plain(s):
    """Strip the markdown the narrative rows are written in."""
    s = re.sub(r"[*_`>#]", " ", str(s or ""))
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[«»·—–]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

idx = load("searchindex.json")
kept = [x for x in idx if x.get("k") not in OWNED]

# ---- every person in the roster ----
roster = load("roster.json")
LINE = dict(roster.get("legend") or [])
people = []
for r in roster["rows"]:
    yrs = "–".join([str(r["b"]) if r.get("b") else "", str(r["d"]) if r.get("d") else ""]).strip("–")
    sub = " · ".join([x for x in (r.get("place") or "", yrs) if x]) or "no place recorded"
    q = " ".join([
        r["name"], r.get("place") or "", yrs, r.get("note") or "",
        r.get("parish") or "", r.get("line") or "", LINE.get(r.get("line"), ""),
        roster["srclabel"].get(r["src"], r["src"]),
    ])
    people.append({
        "k": "Person",
        "t": r["name"],
        "s": sub,
        "h": r.get("who") or r.get("href") or "/people/",
        "q": plain(q).lower(),
    })

# ---- the narrative sections that hold register readings ----
readings = []
SECTIONS = [
    ("fiume.json", ("rows", "more", "rovinj", "vodnjan"), "/fiume-1626/"),
    ("omis.json", ("rows", "zadarpalace"), "/omis-line/"),
    ("atsea.json", ("rows",), "/at-sea/"),
    ("america.json", ("rows",), "/the-eleven/"),
]
for fn, keys, href in SECTIONS:
    if not os.path.exists(p(fn)): continue
    doc = load(fn)
    for key in keys:
        sec = doc.get(key)
        rows = sec.get("rows") if isinstance(sec, dict) else sec
        if not isinstance(rows, list): continue
        head = sec.get("heading") if isinstance(sec, dict) else doc.get("title", "")
        for row in rows:
            if not isinstance(row, dict) or not row.get("lab"): continue
            body = " ".join(plain(row.get(k)) for k in ("q", "why", "text") if row.get(k))
            readings.append({
                "k": "Register reading",
                "t": plain(row["lab"]),
                "s": plain(head or doc.get("title", "")),
                "h": href,
                "q": (plain(row["lab"]) + " " + body).lower()[:1400],
            })

out = kept + people + readings
with open(p("searchindex.json"), "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"kept {len(kept)} · people {len(people)} · readings {len(readings)} · total {len(out)}")
