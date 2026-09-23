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
  3. REPORT rows with a birth year inside the living window and no death year
           and no living flag. Not a failure: David's rule is «family only, as
           written», so a stranger found in a public index keeps their dates.
           It is a list to read, and it is how the two women would have been
           found in March instead of by grepping for a string in September.
"""
import json, io, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "site/src/data/roster.json")
WINDOW = 95

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
            if b and not r.get("d") and not r.get("deceased") and (year - b) < WINDOW:
                review.append((year - b, nm, pid, b))

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
