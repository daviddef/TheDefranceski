#!/usr/bin/env python3
"""Catch a `walked` claim that is wider than the frames actually cited.

Why this exists. On 1 October 2026 three rows of the search register claimed
`walked: true` over sixty frames of the Gologorica baptism book. Twenty-seven
had been opened. The reading had proceeded at roughly every third frame, which
is a sample, not a walk.

`walked` is the one field that tells the next person a book is FINISHED. The
Record Atlas states it plainly: overstating it is the worst error available,
because a sampled book marked walked is worse than an unread one — nobody goes
back to it.

This compares each row's `pages` range against the frame numbers this archive
has actually cited anywhere in site/src/data, and speaks when a walked row
covers frames that are nowhere cited. It cannot prove a walk (a page read and
found empty leaves no citation), so it SPEAKS rather than blocks, and a row
that is genuinely walked but sparsely cited should say so in its own text.

    python3 scripts/check-walked.py
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
FRAME = re.compile(r"M0(\d{7})")
RANGE = re.compile(r"M0(\d{7})\s*[–—-]\s*M0(\d{7})")


def main():
    cited = set()
    for p in glob.glob(os.path.join(DATA, "*.json")):
        try:
            cited |= {int(m) for m in FRAME.findall(open(p, encoding="utf-8").read())}
        except OSError:
            continue

    try:
        rows = json.load(open(os.path.join(DATA, "searched.json"), encoding="utf-8"))["rows"]
    except Exception:
        print("check-walked: SKIP — no search register")
        return 0

    loud = []
    for r in rows:
        if not r.get("walked"):
            continue
        m = RANGE.search(str(r.get("pages", "")))
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if b <= a:
            continue
        span = b - a + 1
        seen = sum(1 for n in range(a, b + 1) if n in cited)
        if span >= 6 and seen * 3 < span:      # fewer than a third cited
            loud.append((r.get("src", "")[:56], a, b, span, seen))

    print("check-walked: %d row(s) claim a walked range" %
          sum(1 for r in rows if r.get("walked")))
    if loud:
        print("   ⚠ these claim a WALK over frames that are mostly never cited:")
        for src, a, b, span, seen in loud:
            print("     M0%d-M0%d  %3d frames, %2d cited  · %s" % (a, b, span, seen, src))
        print("   A page read and found empty leaves no citation, so this is not proof.")
        print("   But `walked` means EVERY entry read. If that is true here, say so in")
        print("   the row's own text; if it is not, set walked:false and list the frames.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
