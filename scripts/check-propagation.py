#!/usr/bin/env python3
"""Catch a correction that was published but never propagated.

Why this exists. On 28 September 2026 this archive corrected the mother of a
1743 baptism from «Francisca» to «Pascasia», wrote it up on /corrections/, on
the person's page and on the worklist — and left the wrong name standing in
`households.json`, where it was still the basis of a household, still the basis
of the «two contemporary Jacobos» split, and still the transcription a reader
would meet. The child was filed under the wrong household for five days AFTER
the correction was published.

A correction is not done when it is written. It is done when the old claim is
gone from every file that asserts it. This script is the difference.

How it works: each rule is (label, wrong-pattern, allowed-files). The wrong
pattern is text that should no longer appear as a live claim. Files that are
ALLOWED to contain it are those that quote the error on purpose — the
corrections page, the worklist's own narrative, and the person page that tells
the story of the fix. Anywhere else is a leak.

    python3 scripts/check-propagation.py
"""
import json, os, re, sys

# Resolve from this file, not the cwd: the gate runs its checks from site/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

# (label, regex, files permitted to contain it)
RULES = [
    ("Casparus's mother given as Francisca",
     r"Casparus[^\"]{0,140}Francisca ejus",
     {"corrections.json", "worklist.json", "roster.json", "dossiers.json", "searched.json", "searchindex.json"}),
    ("'Francisca bore Casparus'",
     r"Francisca bore Casparus",
     # the corrections page quotes the withdrawn sentence verbatim, as it must
     {"corrections.json", "dossiers.json", "searchindex.json"}),
    ("the chancellor called Bosponi",
     r"Bosponi",
     # searched.json and families.json name the old form in the sentence
     # that corrects it; both are telling the story of the fix
     {"corrections.json", "worklist.json", "roster.json", "dossiers.json",
      "searchindex.json", "searched.json", "families.json"}),
    ("the chaplain called Zolonta",
     r"Zolonta",
     {"corrections.json", "worklist.json", "searchindex.json"}),
    ("Antonio 'six times in ten months' left unqualified",
     r"six times in ten months(?!\s*\*\()",
     # worklist.json quotes the old count in the sentence that revises it
     {"corrections.json", "roster.json", "dossiers.json", "searchindex.json",
      "worklist.json"}),
    ("Antonio asserted dead by November 1780 (the blotted «q.m» reading)",
     r"Antonio (?:was |is )?dead by (?:\*\*)?November 1780",
     # the corrections page and the pages that tell the story of the fix quote it
     {"corrections.json", "worklist.json", "roster.json", "families.json",
      "searched.json", "dossiers.json", "searchindex.json"}),
    ("Gregorio still given the withdrawn patronymic in a display name",
     r"Gregorio Defranceschi q\.m Antonio",
     {"corrections.json", "worklist.json", "roster.json", "families.json",
      "searched.json", "dossiers.json", "searchindex.json", "decisions.json"}),
]

def main():
    leaks = []
    for fn in sorted(os.listdir(DATA)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(DATA, fn)
        try:
            s = json.dumps(json.load(open(path, encoding="utf-8")), ensure_ascii=False)
        except Exception:
            continue
        for label, pat, allowed in RULES:
            if fn in allowed:
                continue
            n = len(re.findall(pat, s))
            if n:
                leaks.append((fn, label, n))

    if leaks:
        print("check-propagation: FAIL — a published correction has not reached every file")
        for fn, label, n in leaks:
            print("   %-22s %-46s x%d" % (fn, label, n))
        print("\n   Either fix the file, or add it to that rule's allowed set in")
        print("   scripts/check-propagation.py and say why it quotes the error on purpose.")
        return 1

    print("check-propagation: ok — %d correction(s) reached every file that asserts them" % len(RULES))
    return 0

if __name__ == "__main__":
    sys.exit(main())
