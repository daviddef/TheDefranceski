#!/usr/bin/env python3
"""How much of the two Pazin reels has this archive actually read?

Why this exists. On 30 September 2026 David asked «have you finished all the
other files before moving to other registers?» The honest answer was no, and
nobody could say by how much, because the figure had never been counted. It
was 4.0% — thirteen books opened and none finished, because every find pointed
at another book and the reading followed it.

A coverage figure that is felt rather than counted always feels higher than it
is. This counts it: every frame number cited anywhere in site/src/data is
tested against the book map in data/pazin-reels.json, which was built from the
films' own printed title cards.

It SPEAKS rather than blocks, like check-story. The number should go up, and a
book that reaches 100% should be said to be finished only then.

    python3 scripts/check-coverage.py [--book "Status Animarum 1826"]
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, "data", "pazin-reels.json")
DATA = os.path.join(ROOT, "site", "src", "data")

FRAME = re.compile(r"M0(?:1068|1069|1070)\d{3}")


def main():
    if not os.path.isfile(MAP):
        print("check-coverage: SKIP — no book map at data/pazin-reels.json")
        return 0
    books = json.load(open(MAP, encoding="utf-8"))["books"]

    cited = set()
    for p in glob.glob(os.path.join(DATA, "*.json")):
        try:
            cited |= set(FRAME.findall(open(p, encoding="utf-8").read()))
        except OSError:
            continue
    nums = {int(f[1:]) for f in cited}

    only = None
    if "--book" in sys.argv:
        only = sys.argv[sys.argv.index("--book") + 1].lower()

    tot = read = 0
    rows = []
    for b in books:
        a, z = int(b["from"][1:]), int(b["to"][1:])
        n = z - a + 1
        r = sum(1 for x in nums if a <= x <= z)
        if only and only not in (b["book"] + " " + b["years"]).lower():
            continue
        tot += n
        read += r
        rows.append((b["zupa"], b["book"], b["years"], n, r))

    print("check-coverage: the two Pazin reels, frame by frame")
    for zupa, bk, yrs, n, r in rows:
        print("   %-11s %-17s %-24s %4d frames  %4d cited  %5.1f%%"
              % (zupa, bk, yrs[:24], n, r, 100 * r / n))
    if tot:
        print("   %-55s %4d frames  %4d cited  %5.1f%%"
              % ("TOTAL", tot, read, 100 * read / tot))
    print("   ⚠ a cited FRAME is not a walked PAGE. Title cards and book")
    print("     boundaries count here, so the true reading is lower. And the")
    print("     film shoots some openings TWICE — page 68 of the 1826 census is")
    print("     M01069386 AND M01069387, both read — so the frame count also")
    print("     overstates the number of distinct pages by an unknown amount.")
    print("     Two attempts to detect duplicates automatically FAILED: ink")
    print("     coverage and pixel difference both put the confirmed duplicate")
    print("     inside the range of ordinary consecutive pages, because two")
    print("     exposures of one page differ in film position and lighting,")
    print("     while two sparse pages of one register look alike.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
