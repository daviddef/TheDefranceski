#!/usr/bin/env python3
"""Is this archive counting its own readers, or somebody else's?

Written 12 October 2026, the day this archive spent several hours logging
every pageview to thedefranceski.goatcounter.com.

WHY A WHOLE GATE FOR ONE ATTRIBUTE. Base.astro picks this archive out of the
ring with `a.base === BASE_URL`, and that was a unique key for exactly as long
as every archive was a GitHub Pages project site. Moving to a custom domain
sets base to "". Five archives did it, find() returned the first of them, and
the counter code is read straight off that entry — so the move silently
redirected this archive's statistics into another family's account. Visits
logged there cannot be separated out afterwards. It is the only fault found
this week that destroys data rather than displaying it wrongly.

AND THE CHECK THAT SHOULD HAVE CAUGHT IT COULD NOT SEE IT. The same collision
hit SocialHead, the kit fixed that in e275c14 with whoami(), and this layout
does not go through SocialHead. So a scratch build was verified on canonical,
og:url, og:site_name and theme-color — all four correct, all four from
SocialHead — while the counter beside them was wrong. FOUR FIELDS FROM ONE
SOURCE SAY NOTHING ABOUT A FIFTH FROM ANOTHER, which is the general lesson and
the reason this reads the BUILT HTML rather than the layout that writes it.
A source file states an intention. Only the output states what was shipped.
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# PORTABLE ON PURPOSE. tools/outdir.py is this archive's own resolver for
# "which build am I grading", and it exists in no other archive in the estate
# — checked, not assumed, on 12 October: Booyzen, Our Family, Mazza, Lerena
# and Defranceschi all lack it. This gate is worth having in all of them, and
# a hard import would have handed each of them an ImportError instead of a
# check. So outdir is used where it exists and the same rule is applied
# directly where it does not: ARCHIVE_OUT wins, because it is the operator
# speaking, and site/dist is the default every workflow uploads.
try:
    import outdir
    DIST = outdir.out()
except ImportError:
    _o = os.environ.get("ARCHIVE_OUT")
    DIST = os.path.join(ROOT, "site", _o) if _o else os.path.join(ROOT, "site", "dist")
RING = os.path.join(ROOT, "site", "node_modules", "@daviddef",
                    "archive-kit", "kit", "data", "archives.json")


def origin_of(u):
    m = re.match(r"(https?://[^/]+)", (u or "").strip())
    return m.group(1) if m else ""


def main():
    cfg = os.path.join(ROOT, "site", "astro.config.mjs")
    m = re.search(r"\bsite:\s*['\"]([^'\"]+)['\"]", open(cfg, encoding="utf-8").read())
    if not m:
        print("  warn  counter    astro.config.mjs names no site; cannot tell whose counter this is")
        return 0
    mine = origin_of(m.group(1))

    try:
        ring = json.load(open(RING, encoding="utf-8"))["archives"]
    except Exception as e:
        print(f"  warn  counter    the kit's archives.json is unreadable ({e}); not graded")
        return 0

    # BY ORIGIN, never by base. Matching the way the bug did would reproduce it.
    me = next((a for a in ring if origin_of(a.get("url")) == mine), None)
    if not me:
        print(f"  FAIL  counter    no archive in the ring has origin {mine} — astro.config's site "
              f"and this archive's url in the kit disagree, and every page is about to be "
              f"attributed to whichever entry sorts first")
        return 1
    want = (me.get("counter") or "").strip()
    if not want:
        print(f"  ok    counter    {me['name']} declares no counter; nothing is being logged")
        return 0

    pages = glob.glob(os.path.join(DIST, "**", "index.html"), recursive=True)
    if not pages:
        print(f"  warn  counter    no built pages under {DIST}; not graded")
        return 0

    seen, bad = {}, []
    pat = re.compile(r'data-goatcounter="https?://([^./"]+)\.goatcounter\.com')
    for f in pages:
        for host in pat.findall(open(f, encoding="utf-8", errors="ignore").read()):
            seen[host] = seen.get(host, 0) + 1
            if host != want:
                bad.append((os.path.relpath(f, DIST), host))

    if bad:
        others = sorted({h for _, h in bad})
        print(f"  FAIL  counter    {len(bad)} built page(s) log to {', '.join(others)} and not to "
              f"{want} — THIS ARCHIVE IS COUNTING SOMEBODY ELSE'S READERS, and visits logged to "
              f"another account cannot be separated out afterwards")
        for f, h in bad[:3]:
            print(f"          {f} → {h}")
        print(f"          Base.astro must pick its entry by ORIGIN, not by base: every archive on "
              f"a custom domain has base \"\" and find() returns the first of them.")
        return 1

    print(f"  ok    counter    {len(pages)} built page(s) log to {want}.goatcounter.com, "
          f"which is this archive's own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
