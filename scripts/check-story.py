#!/usr/bin/env python3
"""Every finding must reach the story, not just the log.

Why this exists. On 28 September 2026 David wrote: «every piece of your work is
telling a story about the Defranceschi families and lines, so every new finding
needs to be incorporated into that story otherwise we are here for nothing.»

He was right, and the audit that followed proved it. Three findings of that day
— that Antonio de Franceschi was a bell-ringer, that Elena was dead by 1777,
and that an Antun Defranceski sat in the Zagreb administration — existed ONLY
in the worklist, the search log and a roster note. A reader following the
Svetvincenat narrative would never have met any of them. The work was done and
the story did not know.

The distinction this script enforces:

  LOG      worklist.json, searched.json, corrections.json, sources.json,
           method.json — receipts. What was searched, what was fixed, how.
  STORY    families.json, lines.json, rivers.json, households.json, and the
           topic files (carlo, atsea, namesakes, clusters, spines) — the pages
           a reader actually reads.
  roster.json is both and counts as neither: a person page is story, but a
           finding that lives ONLY on one person's page has not been told.

A row in `searched.json` with outcome "hit" is a claim that something was
found. This checks that each such row points at a story page through its `ev`
links. A hit whose evidence links go only to /searched/, /worklist/ or
/corrections/ is a finding that never left the filing cabinet.

    python3 scripts/check-story.py            # report
    python3 scripts/check-story.py --strict   # non-zero exit on any orphan
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

# links that are receipts, not story
LOG_HREFS = re.compile(r"^/(searched|worklist|corrections|sources|method)/")

def main():
    strict = "--strict" in sys.argv
    S = json.load(open(os.path.join(DATA, "searched.json"), encoding="utf-8"))
    rows = S.get("rows", [])

    # A row marked `internal` is an audit of THIS ARCHIVE'S OWN DATA -- a place
    # string tested against its province, an evidence file checked for orphans --
    # not a finding about the family. Its honest home is /method/, which is a log
    # by design, so demanding a story link would only teach people to fake one.
    # The flag is explicit and carries `internalWhy`, so each exemption is
    # somebody's stated decision rather than a silent hole in the count.
    internal = [r for r in rows if r.get("internal")]
    hits = [r for r in rows
            if (r.get("outcome") or "").lower() == "hit" and not r.get("internal")]
    orphans = []
    for r in hits:
        ev = r.get("ev") or []
        hrefs = [e[0] for e in ev if isinstance(e, (list, tuple)) and e]
        story = [h for h in hrefs if not LOG_HREFS.match(h)]
        if not story:
            orphans.append((r.get("when", "?"), (r.get("src") or "")[:66], len(hrefs)))

    print("check-story: %d searches recorded, %d of them hits (%d internal audits exempt)"
          % (len(rows), len(hits), len(internal)))
    if not orphans:
        print("            every hit points at a page a reader reads")
        return 0

    print("            %d hit(s) point only at logs — found, and never told:" % len(orphans))
    for when, src, n in orphans:
        print("   %-14s %-66s (%d link%s, all logs)" % (when, src, n, "" if n == 1 else "s"))
    print()
    print("   A hit is a claim that something was found. Give each of these an `ev`")
    print("   link to the page where the story is told — a person, a line, a household,")
    print("   a topic page — or write that page first.")
    return 1 if strict else 0

if __name__ == "__main__":
    sys.exit(main())
