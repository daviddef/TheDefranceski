#!/usr/bin/env python3
"""Say what MOVED, and say nothing when nothing did.

The landing-site session found D'Arcy running on a pin nobody had noticed
had changed. The build had printed the correct pin three times that day.
The instrument was not silent — it was unread, "because a line beginning
«ok» does not get read".

This gate prints thirteen «ok» lines and, under them, nine steady numbers:
55 living, 595 people in the evidence files, 425 attested name cells, 136
of 155 sources reachable. Every one is restated identically each build and
every one is therefore invisible. If a living person's flag were dropped
the count would fall from 55 to 54 and the gate would still say «ok» —
a silent regression in the one number in this archive that must never be
wrong.

So the numbers are written to data/gate-witness.json and COMMITTED, and
this check speaks only when one of them moves. Two things follow from
committing it that do not follow from printing it: a number that shifts
inside an unrelated commit shows up as a diff in a file whose only subject
is these numbers, and the history of the file is the history of the
archive's shape.

It does not fail on movement. Nearly every number here moves for good
reasons — a living person dies, duplicates merge, sources get written up
— and a gate that cried at every change would be turned off within a day.
It fails only when it cannot read the archive at all, because a witness
that reports «no change» after failing to look is the exact fault it
exists to catch.
"""
import json, io, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
WITNESS = os.path.join(ROOT, "data", "gate-witness.json")


def _load(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _rows(j):
    return j["rows"] if isinstance(j, dict) and "rows" in j else j


def measure():
    """Every number is read from the data, never from another check's text."""
    m, roster = {}, _rows(_load("roster.json"))
    living = [r for r in roster if r.get("living")]

    # The living numbers are why this file exists, so they are counted the two
    # ways that differ: the kit's harvest keys by NORMALISED name, and norm
    # strips a married surname in parentheses. Rows over-count, keys under-.
    def fold(n):
        return re.sub(r"\s*\(.*?\)", "", str(n or "")).strip().lower()

    m["living_rows"] = len(living)
    m["living_names"] = len({fold(r["name"]) for r in living})
    m["roster_rows"] = len(roster)
    m["roster_pids"] = sum(1 for r in roster if r.get("pid"))
    m["roster_sameas"] = sum(1 for r in roster if r.get("sameAs"))
    m["roster_direct"] = sum(1 for r in roster if r.get("direct"))

    src = _rows(_load("sources.json"))
    m["sources"] = len(src)
    m["sources_no_url"] = sum(1 for s in src if not s.get("url"))

    wl = _rows(_load("worklist.json"))
    for st in ("next", "done", "blocked", "running", "struck"):
        m["worklist_" + st] = sum(1 for r in wl if r.get("state") == st)

    m["method_rows"] = len(_rows(_load("method.json")))

    # A notable flagged living is the case that started this: the string
    # "living" in a date field is invisible to a checker that reads flags.
    m["notables"] = len(_rows(_load("notables.json")))
    m["notables_living"] = sum(1 for r in _rows(_load("notables.json")) if r.get("living"))

    m["data_files"] = len(glob.glob(os.path.join(DATA, "*.json")))

    # The kit's checkliving harvests EVERY data file, not just the roster, so
    # its number and a roster-only number are different measurements. Both are
    # kept: if they ever diverge by something other than the notables count,
    # one of the two is looking in the wrong place, and that is worth seeing.
    allrows, allnames = 0, set()
    for f in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        try:
            j = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue                      # check-repo and the kit both read
        for r in _rows(j) or []:          # these; this one only counts.
            if not isinstance(r, dict):
                continue
            if any(r.get(k) is True for k in ("living", "presumedLiving",
                                              "alive", "isLiving")) or \
               str(r.get("conf", "")).lower() == "living":
                allrows += 1
                allnames.add(fold(r.get("name") or r.get("n") or ""))
    m["living_rows_alldata"] = allrows
    m["living_names_alldata"] = len(allnames)
    return m


def main():
    try:
        now = measure()
    except Exception as e:
        print("  FAIL  witness    could not read the archive: %s" % e)
        return 1
    if not now:
        print("  FAIL  witness    measured nothing, which is not a result")
        return 1

    was = {}
    if os.path.exists(WITNESS):
        try:
            was = json.load(io.open(WITNESS, encoding="utf-8")).get("counts", {})
        except Exception as e:
            print("  FAIL  witness    %s is unreadable: %s" % (WITNESS, e))
            return 1

    moved = [(k, was.get(k), v) for k, v in sorted(now.items()) if was.get(k) != v]
    gone = [k for k in was if k not in now]

    os.makedirs(os.path.dirname(WITNESS), exist_ok=True)
    json.dump({"note": "Written by scripts/check-witness.py. Commit it: the diff "
                       "is the point. A number moving inside an unrelated commit "
                       "should be visible in a file whose only subject is these "
                       "numbers.",
               "counts": now},
              io.open(WITNESS, "w", encoding="utf-8"), ensure_ascii=False,
              indent=1, sort_keys=True)

    if not was:
        print("  ok    witness    first run — %d number(s) recorded" % len(now))
        return 0
    if not moved and not gone:
        print("  ok    witness    %d number(s), none moved" % len(now))
        return 0
    for k in gone:
        print("        witness    %s is no longer measured (was %s)" % (k, was[k]))
    for k, a, b in moved:
        d = ""
        if isinstance(a, int) and isinstance(b, int):
            d = "  %+d" % (b - a)
        print("        witness    %-18s %s -> %s%s" % (k, a, b, d))
    print("  ok    witness    %d number(s) moved — recorded in data/gate-witness.json"
          % (len(moved) + len(gone)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
