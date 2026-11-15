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

LIVING_NODES = os.path.join(ROOT, "data/tree-page/living-nodes.json")
TREE_JSON = os.path.join(ROOT, "data/tree-page/tree.json")
LEDGER = os.path.join(ROOT, "data/living-ledger.json")
PUBLIC = os.path.join(ROOT, "site", "public")
NODE_KEYS = {"id", "sex", "given", "sur", "surAlso", "father", "mother", "spouse", "kids", "page"}
YEARISH = re.compile(r"\b(1[0-9]\d\d|20\d\d)\b")


def check_living_nodes():
    """`data/tree-page/living-nodes.json` — the living people the tree canvas may draw.

    It carries a name and relationship links and NOTHING else, it is not served, and nothing
    in the built site reads it. Each rule below is a way that could stop being true quietly.
    """
    out = []
    if not os.path.exists(LIVING_NODES):
        return out                                   # the file is optional; its absence is not a fault
    doc = json.load(io.open(LIVING_NODES, encoding="utf-8"))
    people = doc.get("people") or []

    # 1. the shape: no key but the seven, and no year anywhere in any value
    for p in people:
        extra = sorted(set(p) - NODE_KEYS)
        if extra:
            out.append("living-nodes: %s carries %s — this file is a name and relationship links, nothing else."
                       % (p.get("id", "?"), ", ".join(extra)))
        if not (str(p.get("given") or "").strip() or str(p.get("sur") or "").strip()):
            out.append("living-nodes: %s has neither a given name nor a surname; the canvas cannot draw it."
                       % p.get("id", "?"))
        if p.get("sex") not in ("m", "f", "u"):
            out.append("living-nodes: %s has sex %r; the canvas takes m, f or u." % (p.get("id", "?"), p.get("sex")))
        for k in ("fg", "mg", "grade", "conf"):
            if k in p:
                out.append("living-nodes: %s carries `%s`. A living person's parent link is ungraded, which is the "
                           "truthful state: this archive publishes no evidence for it." % (p.get("id", "?"), k))
        for k, v in p.items():
            if k in ("spouse", "kids", "spouses", "children"):
                continue                                   # lists of relatives' pids; judged by rule 3, not by shape
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append("living-nodes: %s has a number in `%s`; no year or count belongs on a living node."
                           % (p.get("id", "?"), k))
            # father/mother/spouse/kids hold the pids of DEAD relatives, and a dead person's pid
            # legitimately carries their year. The living person's own id and page never may.
            if isinstance(v, str) and k not in ("page", "father", "mother") and YEARISH.search(v):
                out.append("living-nodes: %s has what reads as a year in `%s`. The canvas's own living filter "
                           "keys off a birth year: a year here drops the person it is meant to draw."
                           % (p.get("id", "?"), k))

    # 1b. the sex a node carries must agree with the role the file itself gives it (the coordinator's
    #     fourteenth fault: thirteen planted faults all passed while a «mother» slot held sex «m»)
    sexes = {p.get("id"): p.get("sex") for p in people}
    for p in people:
        for slot, wrong in (("father", "f"), ("mother", "m")):
            q = p.get(slot)
            if q and sexes.get(q) == wrong:
                out.append("living-nodes: %s is in %s's `%s` slot with sex %r. The role is sourced; the sex is "
                           "the field to doubt." % (q, p.get("id"), slot, wrong))

    # 2. nobody held out, and nobody the archive does not publish as living
    roster = {r.get("pid"): r for r in json.load(io.open(ROSTER, encoding="utf-8"))["rows"] if r.get("pid")}
    ledger = json.load(io.open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    held = {pid for pid, uid in (ledger.get("people") or {}).items() if uid in set(ledger.get("held") or [])}
    for p in people:
        pid = p.get("id")
        if pid in held:
            out.append("living-nodes: %s is held out by the ledger and must be absent, not blanked." % pid)
        r = roster.get(pid)
        if r is None:
            out.append("living-nodes: %s is in no roster row." % pid)
            continue
        if not (r.get("living") or L2.row_is_living(r)):
            out.append("living-nodes: %s is not a living person by the rule; this file is only for the living." % pid)
        if r.get("b") or r.get("d"):
            out.append("living-nodes: %s has a year in the roster — scrub the row before drawing them." % pid)

    # 3. nobody is in both this file and the tree page's own data
    if os.path.exists(TREE_JSON):
        t = json.load(io.open(TREE_JSON, encoding="utf-8"))
        ids = {q.get("id") for q in (t.get("people") or t.get("nodes") or []) if isinstance(q, dict)}
        for p in people:
            if p.get("id") in ids:
                out.append("living-nodes: %s is in tree.json as well. tree.json omits the living and goes on "
                           "omitting them." % p.get("id"))

    # 4. it is not served and no built page reads it
    for probe in (os.path.join(PUBLIC, "tree-page", "living-nodes.json"), os.path.join(PUBLIC, "living-nodes.json")):
        if os.path.exists(probe):
            out.append("living-nodes: a copy is at %s — /roots/ is in the sitemap and has no robots meta, so that "
                       "would make every name on it indexable." % os.path.relpath(probe, ROOT))
    for base, _dirs, files in os.walk(os.path.join(ROOT, "site", "src")):
        for f in files:
            if not f.endswith((".astro", ".js", ".ts", ".jsx", ".tsx", ".json", ".md")):
                continue
            try:
                s = io.open(os.path.join(base, f), encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if "living-nodes" in s:
                out.append("living-nodes: %s names the file. Nothing built may read it."
                           % os.path.relpath(os.path.join(base, f), ROOT))
    # 5. and the name does not reach a BUILT artefact — a copy step or a glob is how this would really happen,
    #    and it would not look like an import
    dist = os.environ.get("ARCHIVE_OUT") or os.path.join(ROOT, "site", "dist")
    if os.path.isdir(dist):
        for base, _dirs, files in os.walk(dist):
            for f in files:
                if f == "living-nodes.json" or "living-nodes" in f:
                    out.append("living-nodes: %s is in the built site." % os.path.relpath(os.path.join(base, f), ROOT))
                    continue
                if not f.endswith((".html", ".js", ".json", ".xml", ".txt")):
                    continue
                try:
                    if "living-nodes" in io.open(os.path.join(base, f), encoding="utf-8", errors="ignore").read():
                        out.append("living-nodes: the built file %s names it."
                                   % os.path.relpath(os.path.join(base, f), ROOT))
                except OSError:
                    continue
    return out


def main():
    rows = json.load(io.open(ROSTER, encoding="utf-8"))["rows"]
    year = datetime.date.today().year
    fails, review = [], []
    fails.extend(check_living_nodes())

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
