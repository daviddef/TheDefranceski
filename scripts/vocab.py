#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The two word sets this archive writes in its logs, and the one place that says which word stands for which.

12 November 2026 (the research-menu trial). Both logs had drifted: searched.json said the same outcome with eleven
words, corrections.json said severity with twelve, and the pages knew only the first few of each, so some rows
printed a raw word or sorted to the top.

OUTCOMES (searched.json `outcome`). One word for each of six states. Every word the old rows used still means what it
meant; this is the same map the Record Atlas importer applies (its OUTCOME: hit/yield/found are one state,
nothing/nil/miss another, partial/mixed one), so no Atlas mark changes. The chosen pair is found / nil.

SEVERITY (corrections.json `sev`). Three degrees (serious, moderate, minor) and two kinds that are not a degree
(process: how the archive worked, not what it claimed; note: not this archive's claim). The original word is kept
in `sevWas` on any row it changed, so nothing is lost and the choice can be redone.

    python3 scripts/vocab.py --apply      rewrite the two files to the canonical words
    python3 scripts/vocab.py --check      exit 1 if any row uses a word that is not canonical (the gate runs this)
"""
import json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

OUTCOME = {
    "found": "found", "hit": "found", "yield": "found",
    "nil": "nil", "nothing": "nil", "miss": "nil", "clean": "nil", "empty": "nil", "null": "nil",
    "partial": "partial", "mixed": "partial", "part": "partial",
    "blocked": "blocked", "pending": "pending", "correction": "correction",
}
OUTCOME_CANON = ["found", "partial", "nil", "blocked", "pending", "correction"]

SEV = {
    "serious": "serious", "major": "serious",
    "moderate": "moderate",
    "minor": "minor", "ordinary": "minor", "modest": "minor", "small": "minor", "quiet": "minor", "fixed": "minor",
    "process": "process", "struck": "process",
    "note": "note",
}
SEV_CANON = ["serious", "moderate", "minor", "process", "note"]


def _load(name):
    p = os.path.join(DATA, name)
    raw = open(p, encoding="utf-8").read()
    return p, raw, json.loads(raw)


def _dump(p, raw, d):
    # keep each file's own layout: searched.json indent 1 + newline, corrections.json indent 2, no newline
    ind = 1 if p.endswith("searched.json") else 2
    out = json.dumps(d, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
    open(p, "w", encoding="utf-8").write(out)


def apply():
    p, raw, d = _load("searched.json")
    ch = collections.Counter()
    for r in d["rows"]:
        w = r.get("outcome")
        n = OUTCOME.get(str(w).strip().lower()) if w is not None else None
        if n and n != w:
            ch[(w, n)] += 1
            r.setdefault("outcomeWas", w)
            r["outcome"] = n
    _dump(p, raw, d)
    print("searched.json:", sum(ch.values()), "outcome words rewritten", dict(ch))
    p, raw, d = _load("corrections.json")
    ch = collections.Counter()
    for r in d["rows"]:
        w = r.get("sev")
        n = SEV.get(str(w).strip().lower()) if w is not None else None
        if n and n != w:
            ch[(w, n)] += 1
            r.setdefault("sevWas", w)
            r["sev"] = n
    _dump(p, raw, d)
    print("corrections.json:", sum(ch.values()), "severity words rewritten", dict(ch))


def check():
    bad = []
    d = _load("searched.json")[2]
    for i, r in enumerate(d["rows"]):
        if r.get("outcome") not in OUTCOME_CANON:
            bad.append("searched.json row %d (%s): outcome %r is not one of %s" % (i, str(r.get("key") or r.get("src"))[:50], r.get("outcome"), OUTCOME_CANON))
    d = _load("corrections.json")[2]
    for i, r in enumerate(d["rows"]):
        if r.get("sev") not in SEV_CANON:
            bad.append("corrections.json row %d (%s): sev %r is not one of %s" % (i, str(r.get("what"))[:50], r.get("sev"), SEV_CANON))
    for b in bad[:20]:
        print("FAIL", b)
    print("vocab:", "OK, every outcome and every severity is a canonical word" if not bad else "%d row(s) off the vocabulary" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    elif "--check" in sys.argv:
        sys.exit(check())
    else:
        print(__doc__)
