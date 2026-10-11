#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every `outcome` in searched.json must be a word Record Atlas understands.

WHY THIS EXISTS. The atlas's importer maps an archive's `outcome` onto the
seven states its mark UI already uses. A word that is not in that map does not
get forced into the nearest one — by design, so that nobody's vocabulary is
silently reinterpreted. The consequence is that the row gets **no state**, and
with no state it produces **no source mark**: the search is recorded here, and
reaches the shared map as nothing at all.

It is invisible from this side. The row looks complete, the gate passed, the
page reads well. Found on 11 October by running the atlas's importer against
this archive and reading its rejects: of 635 rows, exactly two had fallen out,
and both for this reason —

    «clean»  Vodnjan deaths, image 562 — twelve entries read, no De Franceschi
    «note»   Vodnjan deaths, image 567 — a re-shoot, and how to count the film

Both became «nil», which this archive already uses 36 times and which the atlas
reads as «searched». Nothing about either finding changed; only the word.

THE VOCABULARY IS NOT COPIED HERE IF IT CAN BE READ. A frozen duplicate of
somebody else's list goes stale without anyone noticing, which is the same
class of fault. So this reads OUTCOME out of the importer when the atlas is on
this machine, and falls back to the list as it stood on 11 October 2026 when it
is not — saying which it used, every time, so a stale pass is never silent.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEARCHED = os.path.join(ROOT, "site", "src", "data", "searched.json")

# ⚠ The atlas is NOT at `../Record Atlas`, whatever CLAUDE.md says — it is in
# «Family Projects». Both are tried, and so is RECORD_ATLAS in the environment,
# because a hard-coded home directory is the next thing to rot.
CANDIDATES = [
    os.environ.get("RECORD_ATLAS"),
    os.path.join(os.path.dirname(ROOT), "Family Projects", "Record Atlas"),
    os.path.join(os.path.dirname(ROOT), "Record Atlas"),
]

FROZEN = {
    "yield", "hit", "found", "correction",
    "done", "nothing", "null", "empty", "nil", "miss", "not there",
    "partial", "part", "mixed",
    "blocked",
    "pending", "outstanding",
    "planned", "not-yet",
}


def vocabulary():
    """(set of words, where it came from). Read it if we can; say so if not."""
    for base in CANDIDATES:
        if not base:
            continue
        imp = os.path.join(base, "scripts", "import-research-sessions.py")
        if not os.path.isfile(imp):
            continue
        src = io.open(imp, encoding="utf-8").read()
        m = re.search(r"^OUTCOME\s*=\s*\{(.*?)^\}", src, re.S | re.M)
        if not m:
            continue
        words = set(re.findall(r'"([^"]+)"\s*:', m.group(1)))
        if words:
            return words, "read from %s" % imp
    return set(FROZEN), ("the frozen copy of 11 Oct 2026 — the atlas is not on "
                         "this machine, so this list may be stale")


def main():
    doc = json.load(io.open(SEARCHED, encoding="utf-8"))
    rows = doc if isinstance(doc, list) else doc.get("rows", [])
    words, where = vocabulary()

    bad = {}
    for r in rows:
        v = str(r.get("outcome") or r.get("status") or "").strip().lower()
        if not v:
            continue
        # The importer also accepts a surname-shaped miss: «no Falco».
        if v in words or v.startswith("no "):
            continue
        bad.setdefault(v, []).append(r.get("src") or "(no src)")

    print("check-atlas-outcomes: %d row(s), %d accepted word(s) — %s"
          % (len(rows), len(words), where))
    if not bad:
        print("   every outcome is a word the shared atlas can read")
        return 0

    print("   FAIL — %d outcome(s) the atlas does not map, so the rows below "
          "reach the shared map with no state and no source mark:" % len(bad))
    for v in sorted(bad):
        print("     %-14s %d row(s)" % ("«%s»" % v, len(bad[v])))
        for s in bad[v][:4]:
            print("        %s" % s[:96])
    print("   Use a word from: %s" % ", ".join(sorted(words)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
