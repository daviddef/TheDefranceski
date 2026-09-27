#!/usr/bin/env python3
"""Refuse when a DECISION changes. Not a count — a decision.

Third position, and it is the D'Arcy session's, arrived at between a pin
and a witness. A pin has one correct value, so speaking on any move is
right. A count has no correct value, only a history, so failing on movement
would be a gate switched off inside a day. But a few values in an archive
are neither: they are JUDGEMENTS someone made once, and changing one should
require a deliberate act. Editing the declaration in the same commit is
that act.

What this archive declares, and why each one and not another:

  kit_pin        Which kit this build runs against. D'Arcy ran for a day on
                 a pin nobody noticed had moved, carried there inside a
                 commit about something else entirely.

  living_policy  `named-bare`. If this silently became something laxer, the
                 dates of living people could publish and every other check
                 would still pass, because they all read this flag rather
                 than decide it.

  pids           THE ONE THIS ARCHIVE NEEDS MOST, and the one a count cannot
                 give. Person ids are minted once and never derived, because
                 a derived id moves when a birth year is corrected and a
                 moved id is a dead URL. scripts/check-witness.py counts them
                 — 1,446 — and that count is identical whether or not one of
                 them now points at a different human being. A substitution
                 is invisible to every number in this archive.

                 So the mapping is declared, not counted. Adding a pid is
                 free. Changing or removing one refuses, and the diff names
                 the person whose address moved.

Refusing is the point. These are the places where being stopped and made to
edit a file by hand is cheaper than the mistake.
"""
import json, io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
DECL = os.path.join(ROOT, "data", "decisions.json")


def probe():
    d = {}
    pkg = json.load(io.open(os.path.join(ROOT, "site", "package.json"), encoding="utf-8"))
    d["kit_pin"] = pkg.get("dependencies", {}).get("@daviddef/archive-kit", "")

    gate = io.open(os.path.join(ROOT, "scripts", "gate-isolated.sh"), encoding="utf-8").read()
    m = re.search(r"--policy\s+(\S+)", gate)
    d["living_policy"] = m.group(1) if m else "<no --policy found in the gate>"

    roster = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]
    d["pids"] = {r["pid"]: "%s|%s|%s" % (r.get("name", ""), r.get("b") or "", r.get("d") or "")
                 for r in roster if r.get("pid")}
    return d


def main():
    try:
        now = probe()
    except Exception as e:
        print("  FAIL  decisions  could not read a declared decision: %s" % e)
        return 1

    if not os.path.exists(DECL):
        os.makedirs(os.path.dirname(DECL), exist_ok=True)
        json.dump({"note": "Declared decisions. Changing one of these FAILS the "
                           "gate on purpose: edit this file in the same commit, "
                           "deliberately. Adding a pid is free; changing or "
                           "removing one is not.",
                   "decisions": now},
                  io.open(DECL, "w", encoding="utf-8"), ensure_ascii=False,
                  indent=1, sort_keys=True)
        print("  ok    decisions  first run — %d pid(s) and %d scalar(s) declared"
              % (len(now["pids"]), len(now) - 1))
        return 0

    was = json.load(io.open(DECL, encoding="utf-8"))["decisions"]
    bad = []

    for k in ("kit_pin", "living_policy"):
        if was.get(k) != now[k]:
            bad.append("%s changed: %s -> %s" % (k, was.get(k), now[k]))

    old_pids, new_pids = was.get("pids", {}), now["pids"]
    for pid, who in sorted(old_pids.items()):
        if pid not in new_pids:
            bad.append("pid REMOVED, so a published address is now dead: %s (%s)" % (pid, who))
        elif new_pids[pid] != who:
            bad.append("pid REUSED for a different person: %s\n              was  %s\n              now  %s"
                       % (pid, who, new_pids[pid]))

    added = len(set(new_pids) - set(old_pids))

    if bad:
        print("  FAIL  decisions  %d declared decision(s) changed without being re-declared"
              % len(bad))
        for b in bad[:12]:
            print("            %s" % b)
        if len(bad) > 12:
            print("            ... and %d more" % (len(bad) - 12))
        print("            If these changes are intended, edit data/decisions.json "
              "in the same commit.")
        return 1

    if added:
        json.dump({"note": json.load(io.open(DECL, encoding="utf-8")).get("note", ""),
                   "decisions": now},
                  io.open(DECL, "w", encoding="utf-8"), ensure_ascii=False,
                  indent=1, sort_keys=True)
        print("  ok    decisions  %d pid(s) added, nothing changed or removed" % added)
        return 0

    print("  ok    decisions  %d pid(s) and 2 scalar(s), all as declared" % len(new_pids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
