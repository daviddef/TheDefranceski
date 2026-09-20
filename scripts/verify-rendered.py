#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check that every row in the archive's list data actually reaches the page.

On 13 September 2026 the Search Register was found to be drawing 112 of its 197
rows: the template grouped by a field whose values had drifted, and anything it
did not recognise was dropped in silence. Three of the hidden rows had been
written and published that same day.

This script exists so that cannot happen again. For each data file below it takes
a distinctive string from every row and looks for it in the built page. Anything
missing is reported. It is advisory, not gating — a row may legitimately be held
back — but a silent loss now shows up.

21 September 2026 — the guard had the same fault it was written to catch.

It reported marriedin.json as losing 34 of its 74 rows. It was not. Two silent
failures were stacked on top of each other, and both are fixed here.

The first: the index of in-law families was folded into /marriages/, and
/married-in/ became a redirect. The script kept reading /married-in/index.html,
which by then was a 412-byte meta-refresh stub with no rows in it at all — and
went on printing a row count as though it were still looking at the page. A
check that follows a dead address does not fail; it reports confidently about
nothing. It now follows the archive's own redirects to the page that replaced
it, and prints the hop so a move is visible rather than silent.

The second is worse, because it is the 13 September fault exactly. Any probe
under eight characters was dropped with `continue` — no count, no warning. On
that page 40 of the 74 rows have names shorter than eight characters, so Skoko,
Buich, Bembo, Corva and thirty-six others had never been checked by this script
in its life. The 34 it named as missing were not the losses; they were merely
the names long enough to look at. Short probes are now matched on a word
boundary instead of being skipped, and anything still unprobeable is counted
and printed rather than passed over.
"""
import json, re, sys, html, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "site/src/data")
B = os.path.join(ROOT, "site/dist")

# data file · rows key · built page · field to look for
CHECKS = [
    ("searched.json",    "rows",   "searched",     "src"),
    ("corrections.json", "rows",   "corrections",  "what"),
    ("errands.json",     "rows",   "errands",      "what"),
    ("trees.json",       "rows",   "trees",        "name"),
    ("namesakes.json",   None,     "namesakes",    "name"),
    # The in-law index is a section of /marriages/ now, not a page of its own.
    # The redirect at /married-in/ would carry us there anyway; naming the real
    # page means the output says where it actually looked.
    ("marriedin.json",   "rows",   "marriages",    "name"),
    ("imperial.json",    "roll",   "imperial",     "who"),
    ("plates.json",      None,     "gallery",      "title"),
]

REFRESH = re.compile(r"""<meta[^>]+http-equiv=["']?refresh["']?[^>]*?url=([^"'>\s]+)""", re.I)

def norm(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def dist_path(url):
    """Map a published URL onto a file in dist/, whatever base it carries.

    The site is served under /TheDefranceski, so a redirect target reads
    /TheDefranceski/marriages. Rather than hard-code the base — which would rot
    the day the archive moves to its own domain — shed leading segments until
    something on disk answers."""
    path = re.split(r"[?#]", url, 1)[0]
    parts = [p for p in path.split("/") if p]
    for i in range(len(parts) + 1):
        cand = os.path.join(B, *parts[i:], "index.html")
        if os.path.exists(cand):
            return cand, "/" + "/".join(parts[i:]) + "/"
    return None, None

def locate(slug):
    """The built page for a slug, following redirects. Returns (path, hops)."""
    p = os.path.join(B, slug, "index.html")
    if not os.path.exists(p):
        return None, []
    hops = []
    for _ in range(4):
        m = REFRESH.search(open(p, encoding="utf-8", errors="ignore").read())
        if not m:
            break
        nxt, shown = dist_path(html.unescape(m.group(1)))
        if not nxt or nxt == p:
            break
        hops.append(shown)
        p = nxt
    return p, hops

def page_text(path):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", t)
    return norm(t)

def hit(probe, txt):
    """Is this row on the page?

    A long probe is distinctive enough to match as a substring. A short one —
    Skoko, Bembo, Corva — is not: it would match inside a longer word and pass
    for the wrong reason. It is matched on a word boundary instead. What it is
    NOT is skipped, which is how forty of these rows went unexamined for as
    long as this script has existed."""
    if len(probe) >= 8:
        return probe[:60] in txt
    return re.search(r"(?<![0-9a-z])%s(?![0-9a-z])" % re.escape(probe), txt) is not None

def main():
    problems = 0
    unchecked = 0
    for fname, key, slug, field in CHECKS:
        path = os.path.join(D, fname)
        if not os.path.exists(path):
            continue
        data = json.load(open(path, encoding="utf-8"))
        rows = data[key] if key else data
        if not isinstance(rows, list):
            continue
        built, hops = locate(slug)
        if built is None:
            print("  ?  %-14s no built page at /%s/" % (fname, slug))
            continue
        txt = page_text(built)
        where = "/%s/%s" % (slug, "".join(" -> %s" % h for h in hops))
        missing, blind = [], []
        for r in rows:
            if not isinstance(r, dict) or field not in r:
                continue
            probe = norm(r[field])
            if not probe:
                blind.append(repr(r.get(field))[:70])
                continue
            if not hit(probe, txt):
                missing.append(str(r[field])[:70])
        mark = "OK " if not missing and not blind else "!! "
        note = ""
        if missing:
            note += "   %d MISSING" % len(missing)
        if blind:
            note += "   %d UNPROBEABLE" % len(blind)
        print("  %s %-16s %3d rows -> %s%s" % (mark, fname, len(rows), where, note))
        for m in missing[:6]:
            print("       missing: %s" % m)
        if len(missing) > 6:
            print("       ... and %d more" % (len(missing) - 6))
        for b in blind[:6]:
            print("       no usable probe in field %r: %s" % (field, b))
        problems += len(missing)
        unchecked += len(blind)
    print("\n  %d row(s) present in data but not on the page." % problems)
    if unchecked:
        print("  %d row(s) carried nothing this check could look for." % unchecked)
    return 0   # advisory only

if __name__ == "__main__":
    sys.exit(main())
