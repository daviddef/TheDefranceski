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
import json, io, os, re, sys, datetime

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

    # ---- THE LIVING NAMES IN data/tree-page/tree.json (David, 17 Nov 2026: "Dead and living, as asked"; policy meta.living = "names").
    # A row with living:true is a NAME and RELATIONSHIP LINKS and nothing else, for the Record Atlas Tree Canvas. This file is embedded in /roots/ (indexed), so the
    # committed file is judged here, not only at generation: only keys of the whitelist; only a roster row that is living; never a held-out id, a possible minor or
    # a person whose status the committed row cannot decide; no dead row points at one; no living name stands in the not-drawn list.
    TREE = os.path.join(ROOT, "data", "tree-page", "tree.json")
    if os.path.exists(TREE):
        t = json.load(io.open(TREE, encoding="utf-8"))
        KEYS = {"id", "sex", "given", "sur", "father", "mother", "spouse", "kids", "living", "surAlso"}
        by_pid = {r["pid"]: r for r in rows if r.get("pid")}
        led = L2.load_ledger(); held_u = set(led.get("held") or []); held_p = {p_ for p_, u_ in (led.get("people") or {}).items() if u_ in held_u}
        lv = {p["id"]: p for p in t.get("people", []) if p.get("living") is True}
        if lv and (t.get("meta") or {}).get("living") != "names":
            fails.append("tree.json carries %d living rows but meta.living is %r, not 'names'." % (len(lv), (t.get("meta") or {}).get("living")))
        for pid_, p in lv.items():
            r = by_pid.get(pid_)
            if set(p) - KEYS: fails.append("tree.json: living row %s carries more than a name and links (%s)." % (pid_, sorted(set(p) - KEYS)))
            # a name-only row is a roster row with no death YEAR recorded: living by the rule, by its own flag, by the floor (no death within 110 years), or one whose birth year is only
            # an estimate (withheld as possibly living by the builder; David named them 17 Nov 2026). Never one with a death year, and never a held-out or possible-minor row (below).
            if r is None or r.get("d"): fails.append("tree.json: %s is a living row but the roster has no such person, or records a death year." % pid_)
            if pid_ in held_p: fails.append("tree.json: %s is a held-out person (the ledger) and is named." % pid_)
            if r is not None and isinstance(r.get("b"), int) and r["b"] >= L2.MINOR_BORN_FROM and not L2.row_recorded_dead(r): fails.append("tree.json: %s is a possible minor and is named." % pid_)
        PHK = {"id", "sex", "given", "sur", "father", "mother", "spouse", "kids", "placeholder"}
        phs = {p["id"]: p for p in t.get("people", []) if p.get("placeholder") is True}
        for pid_, p in phs.items():
            if set(p) - PHK: fails.append("tree.json: stand-in %s carries more than a name and links (%s)." % (pid_, sorted(set(p) - PHK)))
            if pid_ in lv or pid_ in by_pid: fails.append("tree.json: stand-in %s is also a living row or a roster person." % pid_)
            for k in [p.get("father"), p.get("mother")] + list(p.get("spouse") or []) + list(p.get("kids") or []):
                if k in lv: fails.append("tree.json: stand-in %s points at the living row %s." % (pid_, k))
        for p in t.get("people", []):
            if p.get("living") is True or p.get("placeholder") is True: continue
            for k in [p.get("father"), p.get("mother")] + list(p.get("spouse") or []) + list(p.get("kids") or []):
                if k in lv or k in phs: fails.append("tree.json: the dead person %s points at the living or stand-in row %s." % (p.get("id"), k))
        for u in t.get("undrawn", []):
            if u.get("id") in lv or (by_pid.get(u.get("id")) or {}).get("living") or any(k in lv for k in [u.get("father"), u.get("mother")] + list(u.get("spouse") or []) + list(u.get("kids") or [])):
                fails.append("tree.json: the not-drawn entry %s is a living person or points at one." % u.get("id"))
            if isinstance(u.get("by"), int) and u["by"] >= L2.CUTOFF or isinstance(u.get("b"), int) and u["b"] >= L2.CUTOFF: fails.append("tree.json: the not-drawn entry %s carries a birth year at or after the cutoff." % u.get("id"))

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
