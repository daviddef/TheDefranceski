#!/usr/bin/env python3
"""Report the true state of the overloaded confidence field.

Worklist 149 says `conf` is "a grade, a negation and a person marker under one
key", across "four data files and five pages". That undercounts it. This script
exists so the next person to attempt the split starts from the real number
instead of the remembered one, and so the number can be re-checked in a second
rather than re-derived by hand.

What it finds, and why each is a problem:

  two key names      `conf` and `confidence` mean the same thing in different
                     files, so every renderer has to know which file it is
                     reading before it knows which key to look at.
  three spellings    `doc`/`documented` and `inf`/`inferred` are the same grade
                     written two ways. A lookup table keyed on one silently
                     falls through on the other -- which is exactly how the
                     credulous defaults got in.
  a second vocabulary `probable`/`strong` is a different scale altogether and
                     shares the key with the doc/inf/lore one.
  non-grades         `neg` is a negative FINDING and `living` is a PERSON
                     MARKER. Neither is a confidence. Both reach grading
                     components that have no case for them.
  free prose         in four files the same key holds a sentence, not a grade.

    python3 scripts/audit-conf.py
"""
import json, glob, os, collections, sys

CANON   = {"doc", "inf", "lore"}
SPELLED = {"documented": "doc", "inferred": "inf"}
OTHER   = {"probable", "strong", "family"}
NOTGRADE= {"neg": "a negative finding", "living": "a person marker"}

def walk(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("conf", "confidence"):
                out.append((k, v))
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)

def classify(v):
    if not isinstance(v, str):      return "non-string"
    s = v.strip()
    if s in CANON:                  return "grade (canonical)"
    if s in SPELLED:                return "grade (spelled out)"
    if s in OTHER:                  return "other vocabulary"
    if s in NOTGRADE:               return "NOT A GRADE"
    if len(s) > 22 or " " in s:     return "free prose"
    return "unknown token"

def main():
    files, keys, kinds, tokens = {}, collections.Counter(), collections.Counter(), collections.Counter()
    for f in sorted(glob.glob("site/src/data/*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        out = []
        walk(d, out)
        if out:
            files[os.path.basename(f)] = out
            for k, v in out:
                keys[k] += 1
                kinds[classify(v)] += 1
                if isinstance(v, str) and len(v) <= 22:
                    tokens[v.strip()] += 1

    total = sum(keys.values())
    print("files carrying the field   %d" % len(files))
    print("values in total            %d" % total)
    print("key names                  %s" % ", ".join("%s x%d" % kv for kv in keys.most_common()))
    print()
    print("by kind:")
    for k, n in kinds.most_common():
        print("   %-22s %d" % (k, n))
    print()
    print("the values that are not grades at all:")
    found = False
    for name, meaning in NOTGRADE.items():
        n = tokens.get(name, 0)
        if n:
            found = True
            where = [f for f, out in files.items() if any(v == name for _, v in out)]
            print("   %-8s x%-3d %-22s in %s" % (name, n, meaning, ", ".join(where)))
    if not found:
        print("   none — the split is done")
    print()
    print("per file:")
    for f, out in sorted(files.items()):
        c = collections.Counter("%s=%s" % (k, v if isinstance(v, str) and len(v) <= 22 else "<prose>") for k, v in out)
        print("   %-20s %s" % (f, "  ".join("%s x%d" % (a, b) for a, b in c.most_common())))
    return 0

if __name__ == "__main__":
    sys.exit(main())
