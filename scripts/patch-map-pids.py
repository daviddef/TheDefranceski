#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give each person on /map/ the id of their own page: `pid`, so the map can say «open in Roots & Routes» for THEM and not for a namesake.

    python3 scripts/patch-map-pids.py            # add `pid` to the people of site/src/data/atlas.json and site/public/map-data.json
    python3 scripts/patch-map-pids.py --check    # exit 1 if either file differs from what the roster gives

WHY IT IS A PATCH AND NOT A BUILDER CHANGE. build-atlas.py also carries LIVING people to the map (a name and a town, never a date), and a pid is a
person-page address that, for a living person, ends in a birth year. So the id is added here, after the builders, under the same rule as
scripts/build-tree-page.py: nobody the roster shows living (living_v2.row_is_living, or born within 110 years with no death recorded) ever gets one.
Order: build-atlas.py, build-map.py, THIS, build-place-crosswalk.py, build-tree-page.py.

A person gets a pid only on a UNIQUE match of name + birth year + death year against the roster. Two rows that fit, or none, leave the entry as it was
(the map's `w` link to the name page is untouched); a stale pid is removed.
"""
import datetime, io, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import living_v2 as L2
FILES = [os.path.join(ROOT, "site", "src", "data", "atlas.json"), os.path.join(ROOT, "site", "public", "map-data.json")]
ROSTER = os.path.join(ROOT, "site", "src", "data", "roster.json")
NOW = datetime.date.today().year


def jl(p):
    return json.load(io.open(p, encoding="utf-8"))


def yr(v):
    try: return int(str(v)[:4])
    except Exception: return None


def living(r):
    if L2.row_is_living(r): return True
    b = yr(r.get("b")); dead = bool(r.get("d") or r.get("deathRecorded") or r.get("deceased") or r.get("deathSource"))
    return (not dead) and b is not None and b > NOW - 110


def index():
    ix = collections.defaultdict(list)
    for r in jl(ROSTER)["rows"]:
        if r.get("pid") and not living(r):
            ix[(r["name"], yr(r.get("b")), yr(r.get("d")))].append(r["pid"])
    return ix


def patch(path, ix):
    d = jl(path); n = gone = 0; unmatched = 0
    for p in d["places"]:
        for q in p.get("people") or []:
            ids = set(ix.get((q.get("n"), yr(q.get("y")), yr(q.get("d"))), []))
            if len(ids) == 1:
                q["pid"] = next(iter(ids)); n += 1
            else:
                if "pid" in q: del q["pid"]; gone += 1
                unmatched += 1
    return d, n, gone, unmatched


def main():
    check = "--check" in sys.argv
    ix = index(); bad = 0
    for f in FILES:
        d, n, gone, un = patch(f, ix)
        text = json.dumps(d, ensure_ascii=False, indent=1 if f.endswith("atlas.json") else None)   # each file keeps its builder's own formatting
        have = io.open(f, encoding="utf-8").read()
        rel = os.path.relpath(f, ROOT)
        if check:
            if have.rstrip("\n") != text.rstrip("\n"): print("%s: STALE (pids)" % rel); bad = 1
            else: print("%s: current, %d people carry a pid" % (rel, n))
        else:
            io.open(f, "w", encoding="utf-8").write(text + ("\n" if have.endswith("\n") else ""))
            print("%s: %d people carry a pid, %d without (living, namesakes, no match), %d stale removed" % (rel, n, un, gone))
    sys.exit(bad)


if __name__ == "__main__":
    main()
