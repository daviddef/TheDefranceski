#!/usr/bin/env python3
"""A living person's date of birth, in ANY data file — not just the roster.

`checkliving` asks whether a living person's NAME reached the built pages, and
`check-living-data.py` looks for contradictions in roster.json. Neither reads
the other twenty data files, and that is where the leak was.

WHAT THIS WAS WRITTEN FOR. `pfullingen.json` printed full dates of birth for
two women aged 86 and 81 for months, four clicks from a caption promising the
archive would not. No gate saw it: they were never flagged living, and the
household list writes them as bare forenames under a dash — «— Ursula» — with
the surname carried by the heading above, so no name-phrase check could match
them. They were found by grepping for a string while checking something else.

AND ON THIS GATE'S FIRST RUN IT FOUND THE SAME LEAK AGAIN, in the same file,
surviving the fix. The full dates had been redacted; an entry headed «Two
daughters of Petar» still carried `born: "1940 and 1945"`, and a counselling
card note repeated the years in prose. **The page had deliberately withheld
their NAMES and published their YEARS — the rule kept exactly backwards.**
Meanwhile the roster now names them and withholds the dates, correctly. So
between two pages, each following half the rule, a reader had both halves.

*A rule obeyed in opposite directions on two pages is not obeyed.*

WHAT IT DOES. Walks every JSON under site/src/data, finds nodes carrying both
a name-ish key and a birth-ish value, extracts a year, and fails when that
year falls inside the living window with nothing recording a death.

WHAT IT DELIBERATELY DOES NOT FAIL ON.
  * `d`, `died`, `death`, `dy`, or `deceased: true` — a death the archive
    knows about, dated or not.
  * «fl. 1943–1945» and the like. A floruit is not a birth.
  * The ALLOW list: people found in public indexes who are not this family.
    David's rule is «family only, as written» — a stranger in an Italian IRO
    file keeps their dates, and three of them do.
  * Two-digit years, which are genuinely ambiguous: «20.1.90» in this register
    is 1890, not 1990. They are REPORTED for a human, never failed on.
"""
import json, io, os, re, sys, glob, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
WINDOW = 95
NAMEK = {"name", "who", "person", "child", "fullname"}
DATEK = {"born", "birth", "b", "dob", "birthdate"}
DEADK = {"d", "died", "death", "dy", "deathdate", "deceased"}

# A death can be recorded in three places and only one of them is a field.
#   * a death KEY on the node — the easy case;
#   * PROSE in the same node: this file's Anton carries his date of birth in
#     `born` and «He died on 28 June 1999 and is buried at Warrill Park» in
#     `role`. The node knows he is dead; no key says so.
#   * ANOTHER FILE: Robbie appears in households.json with a birth year and
#     nothing else, while roster.json carries `deceased: true` for him. The
#     archive knows; this file does not.
# Missing any of the three turns a correct record into a false alarm, and a
# gate that cries wolf on the healthy case stops being read — which is the
# fault this whole week has been about.
DEADWORDS = re.compile(r"\b(died|death|buried|headstone|grave|d\.\s*1[89]\d\d|"
                       r"no longer living|posthum)", re.I)

# Found in public indexes, not this family. «Family only, as written.»
ALLOW = {
    ("roster.json", "Giordana Defranceschi"),
    ("roster.json", "Maria Defranceschi"),
    ("roster.json", "Claudio Defranceschi"),
}

def year_of(s):
    """Returns (year, certain). A two-digit year is never certain."""
    s = str(s)
    if re.search(r"\bfl\.", s):           # a floruit is not a birth
        return None, True
    m = re.search(r"\b(1[6-9]\d\d|20\d\d)\b", s)
    if m:
        return int(m.group(1)), True
    m = re.search(r"\b\d{1,2}\.\d{1,2}\.(\d{2})\b", s)
    if m:
        return 1900 + int(m.group(1)), False
    return None, True

def _norm(n):
    return re.sub(r"[^a-z]", "", (n or "").lower())

def _dead_names():
    """Everyone roster.json records as dead, however the death is expressed."""
    out = set()
    try:
        rows = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]
    except Exception:
        return out
    for r in rows:
        if r.get("d") or r.get("deceased"):
            out.add(_norm(r.get("name")))
    return out

DEAD_NAMES = _dead_names()

def main():
    year = datetime.date.today().year
    fails, review = [], []

    def walk(o, fn):
        if isinstance(o, dict):
            nm = next((str(o[k]) for k in o
                       if k.lower() in NAMEK and isinstance(o.get(k), str)), None)
            dead = any(o.get(k) for k in o if k.lower() in DEADK)
            if not dead:
                dead = any(isinstance(v, str) and DEADWORDS.search(v) for v in o.values())
            if not dead and nm and _norm(nm) in DEAD_NAMES:
                dead = True
            for k, v in o.items():
                if k.lower() in DATEK and isinstance(v, (str, int)):
                    y, certain = year_of(v)
                    if y and (year - y) < WINDOW and not dead:
                        row = (fn, nm or "?", str(v)[:34], year - y)
                        if (fn, nm) in ALLOW:
                            continue
                        (fails if certain else review).append(row)
            for v in o.values():
                walk(v, fn)
        elif isinstance(o, list):
            for x in o:
                walk(x, fn)

    for f in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        try:
            walk(json.load(io.open(f, encoding="utf-8")), os.path.basename(f))
        except Exception:
            continue                       # shape is other checks' business

    if review:
        print("  %d entr(y/ies) with an AMBIGUOUS two-digit year — read, do not assume:"
              % len(review))
        for fn, nm, v, age in review:
            print("        %-22s %-30s %-20s (as 19xx: age %s)" % (fn[:22], nm[:30], v, age))
    for fn, nm, v, age in fails:
        print("  FAIL  %s: «%s» carries born=%s — age %s, no death recorded. A living "
              "person gets a name and a town." % (fn, nm, v, age))
    if fails:
        print("check-dates-everywhere: FAIL — %d date(s) of birth for people who may be living"
              % len(fails))
        return 1
    print("check-dates-everywhere: ok — no unexplained birth dates inside the %d-year window "
          "across %d data file(s)" % (WINDOW, len(glob.glob(os.path.join(DATA, "*.json")))))
    return 0

if __name__ == "__main__":
    sys.exit(main())
