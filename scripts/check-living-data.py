#!/usr/bin/env python3
"""Contradictions in the living flags, checked in the DATA rather than the build.

The kit's `checkliving` asks whether a living person's NAME reached the built
pages. That is the right question and it does not catch these, all of which
were live in this repository on 23 September 2026:

  * A man with `d: 1999` — an arrival card, a headstone and a death year —
    carrying `living: true`, because a script printed «Anton restored» and
    never wrote the file. The revert existed only in memory and in the log.
  * Two women born in 1940 and 1945 whose dates of birth were printed in a
    household list for months, four clicks from a caption promising the
    archive would not do that. They were never flagged, and the list writes
    them as bare forenames under a dash — «— Ursula» — with the surname in
    the heading above, so no name-phrase check could see them either.

RULES.
  1. FAIL  `living: true` together with a death year. One of the two is wrong.
  2. FAIL  `living: true` together with a printed birth year `b`. The rule in
           this archive is name and town and nothing else.
  3. FAIL  a row with a birth year, no death, no public source and an age of 80
           or less, that is not marked living. Until 16 October 2026 this was a
           REPORT inside a private 95-year window, because «family only, as
           written» let a stranger keep their dates. There is one rule now, for
           everyone, and it is the kit's (living_rule.py).
"""
import json, io, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "site/src/data/roster.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_v2 as L2
WINDOW = L2.LIVING_YEARS + 1          # the estate's 80 years (living-people standard v2), not a private 95; L2.CUTOFF is the boundary year

def main():
    rows = json.load(io.open(ROSTER, encoding="utf-8"))["rows"]
    year = datetime.date.today().year
    fails, review = [], []

    for r in rows:
        nm, pid = r.get("name", "?"), r.get("pid", "?")
        if r.get("living"):
            if r.get("d"):
                fails.append("%s (%s) is flagged living AND has a death year (%s). "
                             "One of the two is wrong." % (nm, pid, r["d"]))
            if r.get("b"):
                fails.append("%s (%s) is flagged living AND carries a printed birth "
                             "year (%s). Living people get a name and a town." % (nm, pid, r["b"]))
        else:
            b = r.get("b")
            # `deceased: true` is for a death this archive knows about and
            # cannot date — the family tree records it, the archive will not
            # invent a year. It answers the question without guessing.
            if b and L2.row_is_living(r, year):
                # v2: the rule calls this person living and the row is published with a birth year
                fails.append("%s (%s) is published with a birth year (%s) and the rule (80 or younger, no "
                             "death recorded; a public source does not change that) calls them living." % (nm, pid, b))

    for m in fails:
        print("  FAIL  %s" % m)
    if review:
        review.sort()
        print("  %d row(s) with a printed birth year, no death year, and no living flag "
              "— read these, they are the shape of the Ursula/Renate bug:" % len(review))
        for age, nm, pid, b in review[:25]:
            print("        age %-4s %-42s %s" % (age, nm[:42], pid))
        if len(review) > 25:
            print("        … and %d more" % (len(review) - 25))
    if fails:
        print("check-living-data: FAIL — %d contradiction(s)" % len(fails))
        return 1
    print("check-living-data: ok — no living/death contradictions, %d row(s) flagged for "
          "review" % len(review))
    return 0

if __name__ == "__main__":
    sys.exit(main())
