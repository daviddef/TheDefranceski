#!/usr/bin/env python3
"""Catch a page that still announces the absence of something the archive has.

Why this exists. On 29 September 2026 this archive built pages for five of the
six women who married into the direct line — Salomon, Fernasar, Kalanj,
Kovačina and the Senj line. On 30 September the front page and the tree page
were still printing «no archive of her own line yet» under every one of them.
David found it by looking at his own front page; no check did.

Nothing already in the gate could have caught it:

  * check-propagation.py reads site/src/data/*.json. The claim was not in the
    data at all — it was a hardcoded fallback string in two .astro templates.
  * the link checkers test that every href RESOLVES. These pages had no
    broken links; they had no links, and a sentence saying that was correct.
  * an orphan-page sweep found zero orphans, because the maternal pages were
    properly linked from /maternal/ and the nav. Only the SPINES lied.

That is a distinct class of bug: not a dead link and not a wrong fact, but a
TRUE-SOUNDING CLAIM OF ABSENCE that went stale the moment the thing arrived.
A link checker cannot see it, because the missing link is exactly what the
sentence asserts.

How it works. For each subject below we name the phrase that denies her and
the page that disproves it. The check is run against the BUILT SITE, because
that is what a reader meets, and because the bug lived in a template rather
than in data. Two assertions per subject:

  1. Her page is actually built. A denial removed while the page it points at
     does not exist would be a worse failure than the one this replaces.
  2. The denial does not appear anywhere near her name in any built page.

To add a woman: build her page, then add a row. The row is the assertion that
the archive holds her line; the check is what keeps the rest of the site
honest about it.

    python3 scripts/check-absence.py [--dist site/dist]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The phrase a spine prints when it believes it has nothing. Matched
# case-insensitively; both spines worded it slightly differently.
DENIAL = re.compile(r"no archive of her own line yet", re.I)

# How close the denial has to sit to her name to count as being ABOUT her.
# The spine rows put the two within a few tags of each other; 600 characters
# of rendered HTML is comfortably inside one row and well short of the next.
WINDOW = 600

# (her name as the page renders it, the page that disproves the denial)
SUBJECTS = [
    ("Francisca Salomon",      "maternal/salomon"),
    ("Maria née Fernasar", "maternal/fernasar"),
    ("Anna Kalanj",            "kalanj"),
    ("Ursula, born Kovačina", "maternal/kovacina"),
    ("Hedviga, born Blažević", "senj-line"),
]

# Pages that quote the retired sentence on purpose — the story of the fix.
ALLOWED = {"corrections", "worklist", "method", "maternal"}


def main():
    dist = os.path.join(ROOT, "site", "dist")
    if "--dist" in sys.argv:
        dist = sys.argv[sys.argv.index("--dist") + 1]
        if not os.path.isabs(dist):
            dist = os.path.join(ROOT, dist)

    if not os.path.isdir(dist):
        print("check-absence: SKIP — no built site at %s" % dist)
        return 0

    problems = []

    # 1. every page we claim as proof must exist
    for name, page in SUBJECTS:
        if not os.path.isfile(os.path.join(dist, page, "index.html")):
            problems.append(("(not built)", "%s — /%s/ is named as her page and was not built"
                             % (name, page)))

    # 2. no built page may deny a line we hold
    for root, _, files in os.walk(dist):
        for f in files:
            if f != "index.html":
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(os.path.dirname(path), dist).replace(os.sep, "/")
            if rel.split("/")[0] in ALLOWED:
                continue
            try:
                html = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            hits = list(DENIAL.finditer(html))
            if not hits:
                continue
            for name, _page in SUBJECTS:
                for m in hits:
                    a = max(0, m.start() - WINDOW)
                    b = min(len(html), m.end() + WINDOW)
                    if name in html[a:b]:
                        problems.append(("/%s/" % rel, "denies %s, whose line this archive holds" % name))
                        break

    if problems:
        print("check-absence: FAIL — a page announces the absence of something the archive has")
        seen = set()
        for where, what in problems:
            if (where, what) in seen:
                continue
            seen.add((where, what))
            print("   %-34s %s" % (where, what))
        print("\n   Link her page from that row instead of printing the denial, or, if the")
        print("   page quotes the retired sentence on purpose, add it to ALLOWED in")
        print("   scripts/check-absence.py and say why.")
        return 1

    print("check-absence: ok — %d line(s) the archive holds, none of them denied on any page"
          % len(SUBJECTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
