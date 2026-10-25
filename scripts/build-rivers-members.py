#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill the `members` of the holding pens on /lines/ from the roster, so that a pen's count is the people it lists.

    python3 scripts/build-rivers-members.py            # write site/src/data/rivers.json
    python3 scripts/build-rivers-members.py --check    # fail if rivers.json is not what the roster gives (CI)

A pen in `rivers.json` lists households (`items`, the archive's prose about each) and, since the kit's lines contract
(25 October 2026), the PEOPLE the roster holds at those places (`members`, person ids). The members are DERIVED, never typed:
the roster row's place (its first component: «Rijeka, Modrus-Fiume, Hungary» is Rijeka) is matched against the places each
pen names in PENS below; a person who matches two pens stays in the first. Left out, always:
  * a living person (`living`), and a possible minor (not in the roster at all);
  * a row that is another row's twin (`sameAs`): the twin's page is only a pointer;
  * a row without a page address (`pid`).
The roster's own `line` label is NOT read: it is unreconciled with this page (corrections, item A, 18 October 2026), and a
person at Rijeka is a person at Rijeka whatever label the row was given.

A pen of a different stock lists the roster's people of that stock: `trentino` is the roster's own `line: trentino`.
No person is ever listed on two pens (the kit gate's E1), and none who is living (its P3, with private/lines-living.json).
"""
import io, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(ROOT, "site", "src", "data", "roster.json")
RIVERS = os.path.join(ROOT, "site", "src", "data", "rivers.json")

# pen id -> how its members are found: first-component places (folded), or a roster line label
PENS = {
    "unplaced": {"places": {"rijeka", "vitipolis", "fiume",                      # Rijeka - Fiume, Vitipolis
                            "medulin", "medolino",                               # Medulin
                            "kastelir", "tar", "vizinada", "visinada",           # Kastelir and Tar (Vizinada holds the same people)
                            "dubrovnik", "ragusa",                               # Dubrovnik
                            "krbune", "galizana", "labin",                       # the daughters' villages
                            "sovinjak", "bakar", "rovinj"}},
    "pomer": {"places": {"pomer"}},
    "trentino": {"line": "trentino"},
}


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").lower().replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c))


def first_place(r):
    p = r.get("place") or ""
    return fold(re.split(r"[,→(]", p)[0]).strip()


def members_for(rows, rule, taken):
    out = []
    for r in rows:
        pid = r.get("pid")
        if not pid or r.get("living") or r.get("sameAs") or pid in taken:
            continue
        if "places" in rule and first_place(r) in rule["places"]:
            out.append(pid)
        elif "line" in rule and r.get("line") == rule["line"]:
            out.append(pid)
    return out


def build():
    rows = json.load(io.open(ROSTER, encoding="utf-8"))["rows"]
    riv = json.load(io.open(RIVERS, encoding="utf-8"))
    taken = set()
    n = {}
    for pen in riv.get("pens", []):
        rule = PENS.get(pen.get("id"))
        if not rule:
            continue
        m = members_for(rows, rule, taken)
        taken.update(m)
        pen["members"] = m
        pen.pop("count", None)
        n[pen["id"]] = len(m)
    return riv, n


def dump(riv):
    return json.dumps(riv, ensure_ascii=False, indent=1) + "\n"


def main():
    riv, n = build()
    new = dump(riv)
    old = io.open(RIVERS, encoding="utf-8").read()
    print("pen members from the roster: " + ", ".join("%s %d" % kv for kv in sorted(n.items())))
    if "--check" in sys.argv:
        if new != old:
            print("FAIL  rivers.json: the pens' members are not what the roster gives; run scripts/build-rivers-members.py")
            return 1
        print("ok    rivers.json: the pens' members are what the roster gives")
        return 0
    if new != old:
        io.open(RIVERS, "w", encoding="utf-8").write(new)
        print("written: site/src/data/rivers.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
