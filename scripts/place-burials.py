#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give a parish to the burials whose place-string is only «Croatia».

Work-list #80 said these forty could not be placed from anything in this
repository, and that the per-record output of the Istrian sweep — the thing
that would place them — «was never written to disk». Both halves were wrong.

It IS on disk, as data/parish-by-record-2026-09.txt: ninety-three parishes,
each with the FamilySearch persona ids the sweep read under it, 952 in all.
Joining the burial rows to it on name and date places most of them outright.

THE TWIN RULE. The rest fail for one reason: FamilySearch mints a persona per
ROLE, so the same burial is indexed twice, and the sweep kept one id while the
name-search kept the other. The two ids differ in the LAST CHARACTER only
(6B47-SK44 / 6B47-SK4W) and every other field — name, sex, all five dates,
place, spouses, parents — is identical. That is not a guess about which film a
record came from; it is the same record under its other id, so its parish is
the parish.

What is left after that is not this surname: ten Franceschini and one
Franceschinelli, an Istrian family of a different name that the wide search
swept up.

    python3 scripts/place-burials.py          # report
    python3 scripts/place-burials.py --write  # rewrite site/src/data/burials.json
"""
import csv, json, re, sys, collections

ROOT = "."
VAGUE = "Croatia, parish not named"

def norm(s): return re.sub(r"\s+", " ", (s or "").strip()).lower()

def load():
    rows = list(csv.DictReader(open(f"{ROOT}/data/familysearch-croatia.csv")))
    pm = {}
    for line in open(f"{ROOT}/data/parish-by-record-2026-09.txt"):
        if "::" not in line: continue
        par, ids = line.rstrip("\n").split("::", 1)
        for i in ids.split(","): pm[i.strip()] = par
    return rows, pm

FIELDS = ("name","sex","birth","christening","marriage","death","burial","place","spouses","parents")

def resolver(rows, pm):
    twin = {}
    for r in rows:
        if r["id"] in pm:
            twin[(r["id"][:-1], tuple(r[k] for k in FIELDS))] = pm[r["id"]]
    def parish(r):
        if r["id"] in pm: return pm[r["id"]], "index"
        t = twin.get((r["id"][:-1], tuple(r[k] for k in FIELDS)))
        return (t, "twin") if t else (None, None)
    return parish

def main():
    rows, pm = load()
    parish = resolver(rows, pm)

    # A burial row is keyed on the name plus whichever date the tsv carried:
    # «3 May 1890 @ Croazia, Austria» is the burial date, and a bare
    # «Regnum Croatiae» means the tsv had only the death date to go on.
    byname = collections.defaultdict(list)
    for r in rows: byname[norm(r["name"])].append(r)

    b = json.load(open(f"{ROOT}/site/src/data/burials.json"))
    placed, unplaced = [], []
    for row in b["rows"]:
        if row.get("place") != VAGUE: continue
        date, _, where = (row["buried"] or "").partition(" @ ")
        if not where: date, where = "", row["buried"]
        cands = []
        for c in byname.get(norm(row["name"]), []):
            if norm(c["place"]) != norm(where): continue
            if date and norm(c["burial"]) != norm(date) and norm(c["death"]) != norm(date): continue
            cands.append(c)
        found = {parish(c)[0]: parish(c)[1] for c in cands if parish(c)[0]}
        if len(found) == 1:
            p, how = next(iter(found.items()))
            row["place"], row["how"] = p, how
            row["pid"] = next(c["id"] for c in cands if parish(c)[0] == p)
            placed.append((row["name"], p, how))
        else:
            unplaced.append((row["name"], row["buried"], sorted(found)))

    counts = collections.Counter(p for _, p, _ in placed)
    print(f"  placed {len(placed)} · still unplaced {len(unplaced)}")
    for p, n in counts.most_common(): print(f"     {p:<18} {n}")
    for n, w, f in unplaced: print(f"     unplaced  {n}  ({w})  {f or ''}")

    if "--write" in sys.argv:
        pl = collections.Counter(r["place"] for r in b["rows"])
        b["summary"]["places"] = [[p, n] for p, n in pl.most_common()]
        json.dump(b, open(f"{ROOT}/site/src/data/burials.json", "w"), ensure_ascii=False, indent=1)
        print("  written")

main()
