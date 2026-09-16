#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check the built site against the rule for living people.

The rule is **name and town, never a date**. Every builder applies it itself
rather than trusting the pages — the reconciliation writes an empty year for a
living person, the Findmypast builder drops the electoral registers and the
death indexes entirely — but in one day this archive grew a GEDCOM
reconciliation, a DNA page, a Findmypast sweep and a fourth map layer, and
nobody has checked that every page agrees.

This reads the BUILT HTML, which is the only thing a reader ever sees, and
looks for a four-digit year standing near the name of somebody the archive
holds as living. It changes nothing.

    python3 scripts/living-audit.py [dist-dir]
"""
import json, io, os, re, sys, glob, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

def load(n, d=None):
    p = os.path.join(DATA, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def living_names():
    """Everybody this archive has reason to think is alive."""
    out = {}
    for r in (load("roster.json") or {}).get("rows", []):
        if r.get("living"):
            out[r["name"]] = "roster"
    # The reconciliation publishes tree people with an empty year when living.
    for p in (load("reconcile.json") or {}).get("new", []):
        if p.get("living"):
            out[p["n"]] = "live tree"
    # Households marked as coming from the tree carry modern people.
    _hh = load("households.json") or []
    _hh = _hh if isinstance(_hh, list) else (_hh.get("rows") or _hh.get("households") or [])
    for h in _hh:
        if not isinstance(h, dict):
            continue
        if h.get("src") == "tree":
            for k in (h.get("kids") or []):
                if isinstance(k, dict) and not k.get("died") and not k.get("y"):
                    out[k.get("name", "")] = "household (tree)"
    out.pop("", None)
    return out

def main():
    dist = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site", "dist")
    names = living_names()
    print("%d people held as living\n" % len(names))
    # A name is looked for as its own run of words, and a year has to be
    # within a short distance of it — far enough to catch «Name, 1979» and a
    # table cell, near enough not to flag the century in the next paragraph.
    pats = {}
    for n in names:
        core = re.sub(r"\s*\(.*?\)\s*", " ", n).strip()
        if len(core) < 6:
            continue
        # No tag may stand between the name and the year. Without that, the
        # audit reported the menu link «Cheryl Lerena — the poems» followed by
        # a href containing «1948», and a households row where the year 1951
        # belonged to the NEXT person in the next span. A date that is really
        # attached to a name sits in the same run of text as the name.
        # And no sentence may end between them either: «David Defranceski. The
        # 1584 plaque…» is prose about a plaque, not a date against a name.
        pats[n] = re.compile(re.escape(core) + r"[^<>.;!?]{0,60}?\b(1[89]\d\d|20[0-2]\d)\b", re.I)
    hits = collections.defaultdict(list)
    files = sorted(glob.glob(os.path.join(dist, "**", "*.html"), recursive=True))
    for fp in files:
        try:
            h = io.open(fp, encoding="utf-8").read()
        except Exception:
            continue
        # Everything before the first heading is site chrome — the menu lists
        # every page title on every page, and several of them are names.
        body = re.split(r"<h1\b", h, maxsplit=1)[-1]
        body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
        for n, rx in pats.items():
            m = rx.search(body)
            # A credit line — «David Defranceski, 10 September 2026» — is the
            # archive signing its own work, not dating a living person.
            if m and not re.search(r",?\s*\d{0,2}\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*$",
                                   m.group(0)[:m.group(0).rfind(m.group(1))], re.I):
                page = os.path.relpath(fp, dist)
                hits[n].append((page, re.sub(r"\s+", " ", m.group(0))[:120]))
    print("PAGES THAT PUT A YEAR NEAR A LIVING NAME: %d name%s\n"
          % (len(hits), "" if len(hits) == 1 else "s"))
    for n in sorted(hits):
        print("  %s  — %s" % (n, names[n]))
        for page, frag in hits[n][:4]:
            print("      %-34s %s" % (page, frag))
    if not hits:
        print("  none.")
    print("\n%d pages read." % len(files))

if __name__ == "__main__":
    main()
