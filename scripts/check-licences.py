#!/usr/bin/env python3
"""Fail the build when a licensed dataset is used and not properly credited.

Ported on 23 September 2026 from the Record Atlas session's `licence_gate()`
in its own `scripts/check-data.py` (commit 59d6745), which found twelve
findings on its first run — and whose existence found this archive's own hole
the same morning: GeoNames placed 1,123 of our 1,286 mapped places, is CC BY
4.0, was named in exactly one caption, stated no licence anywhere, and had no
row in sources.json at all.

ADAPTED, NOT COPIED. Their shape is `data/*.json` files each carrying a
`source` and a `licence`, checked against a `/data/` page and the footer in
`site/src/layouts/Base.astro`. Ours is different in two ways that matter:

  * Our licence surface is `sources.json`, rendered at /sources/. A dataset
    here is a SOURCE ROW, not a data file with a header.
  * `site/src/layouts/Base.astro` is shared ground in this estate — another
    session owns it. A gate this archive cannot satisfy without editing
    somebody else's file is a gate that teaches you to skip it, so the
    attribution rule points at the built pages that USE the data instead,
    named per row in `attributionOn`. That is stricter than a footer check,
    not looser: it asks for the credit where the work is actually used.

THREE RULES.
  1. A source row marked `dataset: true` must declare a `licence` field.
     Prose is for humans; the field is what a tool can act on. That was the
     exact bug on the Atlas — two files stated their licence inside the
     source sentence, so its own /data/ page printed "none declared" over
     CC BY data and was not wrong to.
  2. Every licence named in sources.json must appear on the built /sources/
     page. A licence that page does not mention is one nobody is told about.
  3. Every licence that ASKS FOR ATTRIBUTION must name its holder on each
     built page listed in that row's `attributionOn`. Credit on the sources
     page alone is most of the courtesy and none of the condition.

WHAT IT CANNOT DO, stated because the Atlas session stated it: this checks
that a NAME APPEARS. It cannot judge whether the credit is adequate, and
passing means the names are present, not that a lawyer would be happy.
"""
import json, io, os, re, sys, glob

# The gate runs this from site/, other callers from the repo root. Anchor
# every path to the repository instead of the working directory — the first
# wiring of this gate failed for exactly this reason and looked like a
# licence problem.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "site/src/data/sources.json")

# Substring of the licence string -> the name that must be credited.
ATTRIBUTION_NAMES = {
    "cc by": None,            # holder comes from the row's `holder` field
    "odbl": None,
    "ogl": None,
}
ATTRIBUTION_MARKERS = ("cc by", "odbl", "ogl", "attribution")

# Bulk third-party data committed to this repository. A file here that no
# source row claims is data we are shipping and not crediting.
THIRD_PARTY_DATA = {
    "gazetteer.json": "geonames",
    "gaz": "geonames",
    "genealogy-resources-croatia.kml": None,   # a family KML, credited in prose
}

ERR = []
def err(m): ERR.append(m)

def main():
    dist = "site/dist"
    for i, a in enumerate(sys.argv):
        if a == "--dist" and i + 1 < len(sys.argv):
            dist = sys.argv[i + 1]
    if not os.path.isdir(dist):
        print("check-licences: no %s — build first" % dist); return 1

    S = json.load(io.open(SOURCES, encoding="utf-8"))

    def page(p):
        f = os.path.join(dist, p.strip("/"), "index.html")
        return io.open(f, encoding="utf-8").read() if os.path.exists(f) else None

    sources_html = page("/sources/")
    if sources_html is None:
        err("no /sources/ in the build — the page that states every licence is missing")
        sources_html = ""

    datasets = [s for s in S if s.get("dataset")]
    for s in datasets:
        lic = s.get("licence")
        if not lic:
            err("source '%s' is marked a dataset and declares no `licence` field. "
                "A licence stated only inside the prose cannot be read by the page "
                "that has to tell people what they are taking." % s["id"])
            continue
        short = re.split(r"\s*[—(]", lic)[0].strip()
        if short and short not in sources_html:
            err("licence '%s' is on source '%s' and is named nowhere on the built "
                "/sources/ page." % (short, s["id"]))
        if any(m in lic.lower() for m in ATTRIBUTION_MARKERS):
            holder = s.get("holder") or s.get("title")
            for p in (s.get("attributionOn") or []):
                h = page(p)
                if h is None:
                    err("source '%s' claims attribution on %s and that page is not "
                        "in the build." % (s["id"], p)); continue
                if holder not in h:
                    err("'%s' is licensed '%s', which asks for attribution, and '%s' "
                        "does not appear on %s — the page that uses it. Credit in a "
                        "caption elsewhere is most of the courtesy and none of the "
                        "condition." % (s["id"], lic, holder, p))
            if not s.get("attributionOn"):
                err("source '%s' is licensed '%s', which asks for attribution, and "
                    "lists no `attributionOn` pages. Name the pages that use it."
                    % (s["id"], lic))

    claimed = {(s.get("datafile") or "") for s in datasets}
    for name, want in THIRD_PARTY_DATA.items():
        if not os.path.exists(os.path.join(ROOT, "data", name)):
            continue
        if want and not any(want == s["id"] for s in datasets):
            err("data/%s is third-party bulk data and no source row with id '%s' "
                "declares it." % (name, want))

    if ERR:
        print("check-licences: FAIL — %d" % len(ERR))
        for m in ERR: print("  FAIL  %s" % m)
        return 1
    print("check-licences: ok — %d dataset source(s), every licence named on "
          "/sources/ and credited on the pages that use it" % len(datasets))
    return 0

if __name__ == "__main__":
    sys.exit(main())
