#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the kit's linking-standard gate (checkstandard.py) over the built site. The archive's one place that knows where the
config, the names index, the living list and the floor are. Written 18 October 2026.

    python3 ../scripts/standard-run.py                run from site/: the gate, with the committed ratchet (.standardfloor.json)
    python3 ../scripts/standard-run.py --table        the same, printing every page's five counts
    python3 ../scripts/standard-run.py --write-floor  after an improvement, lock the gain in (refuses while anything rose)

It reads site/<ARCHIVE_OUT or dist>, AFTER `npm run autolink` (it counts the links that step wrote) and after every other step that
changes or reads the built HTML, so it is the last step of `npm run build`. It is also what a person runs by hand.

WHAT IT CHECKS (kit/docs/linking-standard.md). For the narrative pages named in site/standard.json, per page:
  L1 names with an entry that are still not linked     L2 people read from records that have no entry
  L3 passages citing a record with no link to it       L4 held DAPA scans not beside the passage that relies on them
  L5 bare given names and forms nobody has written in full     EX exemptions (each carries its reason in the page or the config)
and a ratchet: a page's count may only go down; a page not yet in the floor may start at 0. Counts only are ever printed.

IN CI (no GEDCOM, no David's tree): nothing here reads a file CI does not have. The names index and the living list are the ones
`npm run autolink` has just written from the COMMITTED roster (build-names-index.py; the tree only ever ADDS names to living.json
and CI has none), the given-name vocabulary and the plate keys are rebuilt from committed data by build-standard-inputs.py,
the config and the floor are committed, and the counts do not depend on the tree. --strict-config makes a scan key that matches nothing a
failure. The kit's own self-test of the gate (checkstandard_selftest.py) is a separate step of the workflow.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "site")
KIT = os.path.join(SITE, "node_modules", "@daviddef", "archive-kit", "kit", "tools")
INDEX = os.path.join("..", "private", "autolink", "names-index.json")
LIVING = os.path.join("..", "private", "autolink", "living.json")


def main(argv):
    py = sys.executable
    # the inputs the config names (rebuilt every run, from committed data)
    if subprocess.call([py, os.path.join(HERE, "build-standard-inputs.py")]):
        return 2
    if not (os.path.exists(os.path.join(SITE, INDEX)) and os.path.exists(os.path.join(SITE, LIVING))):
        # the names index and the living list are what `npm run autolink` writes; written here the same way if it has not run
        if subprocess.call([py, os.path.join(HERE, "build-names-index.py")]):
            return 2
    dist = os.environ.get("ARCHIVE_OUT") or "dist"
    cmd = [py, os.path.join(KIT, "checkstandard.py"), "--dist", dist, "--index", INDEX, "--config", "standard.json",
           "--living", LIVING, "--floor", ".standardfloor.json", "--strict-config"]
    if "--table" in argv:
        cmd.append("--table")
    if "--write-floor" in argv:
        cmd.append("--write-floor")
    return subprocess.call(cmd, cwd=SITE)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
