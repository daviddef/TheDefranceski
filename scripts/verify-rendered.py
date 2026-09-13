#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check that every row in the archive's list data actually reaches the page.

On 13 September 2026 the Search Register was found to be drawing 112 of its 197
rows: the template grouped by a field whose values had drifted, and anything it
did not recognise was dropped in silence. Three of the hidden rows had been
written and published that same day.

This script exists so that cannot happen again. For each data file below it takes
a distinctive string from every row and looks for it in the built page. Anything
missing is reported. It is advisory, not gating — a row may legitimately be held
back — but a silent loss now shows up.
"""
import json, re, sys, html, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "site/src/data")
B = os.path.join(ROOT, "site/dist")

# data file · rows key · built page · field to look for
CHECKS = [
    ("searched.json",    "rows",   "searched",     "src"),
    ("corrections.json", "rows",   "corrections",  "what"),
    ("errands.json",     "rows",   "errands",      "what"),
    ("trees.json",       "rows",   "trees",        "name"),
    ("namesakes.json",   None,     "namesakes",    "name"),
    ("marriedin.json",   "rows",   "married-in",   "name"),
    ("imperial.json",    "roll",   "imperial",     "who"),
    ("plates.json",      None,     "gallery",      "title"),
]

def norm(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def page_text(slug):
    p = os.path.join(B, slug, "index.html")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", t)
    return norm(t)

def main():
    problems = 0
    for fname, key, slug, field in CHECKS:
        path = os.path.join(D, fname)
        if not os.path.exists(path):
            continue
        data = json.load(open(path, encoding="utf-8"))
        rows = data[key] if key else data
        if not isinstance(rows, list):
            continue
        txt = page_text(slug)
        if txt is None:
            print("  ?  %-14s no built page at /%s/" % (fname, slug))
            continue
        missing = []
        for r in rows:
            if not isinstance(r, dict) or field not in r:
                continue
            probe = norm(r[field])[:60]
            if len(probe) < 8:
                continue
            if probe not in txt:
                missing.append(str(r[field])[:70])
        mark = "OK " if not missing else "!! "
        print("  %s %-16s %3d rows -> /%s/%s" % (
            mark, fname, len(rows), slug,
            "" if not missing else "   %d MISSING" % len(missing)))
        for m in missing[:6]:
            print("       missing: %s" % m)
        if len(missing) > 6:
            print("       ... and %d more" % (len(missing) - 6))
        problems += len(missing)
    print("\n  %d row(s) present in data but not on the page." % problems)
    return 0   # advisory only

if __name__ == "__main__":
    sys.exit(main())
