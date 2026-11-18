#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parent, spouse and child links from David's MyHeritage tree, for people this archive already holds. Writes site/src/data/tree-links.json.

    python3 scripts/build-tree-links.py <tree.ged> [--report FILE]

READ BY scripts/build-dossiers.py, which draws them on a person's page graded «tree» («the family tree, unverified») ONLY where the build
found nothing better: a parent link from a register, an index household or ptree-add.json always wins, and a tree link never replaces one.

WHAT GOES IN. A pair of people both of whom
  * the archive holds, matched with the GEDCOM check's confident tiers only (the MyHeritage id, or the same name and the same years);
  * are dead by the archive's rule (a death recorded, or born before 1907): a living person never appears here, on either end;
  * are real people (a name and a year or a place), not a placeholder bucket, an «Unknown …» or a name-only stub;
  * fit each other in time: a parent born 12 to 65 years before the child, a parent not dead more than a year before the child's birth.
Spouses are mutual; a child lists the first family the tree gives it.  Nothing about a living person, and no date, is written here.
The GEDCOM is read, never copied.
"""
import sys, os, io, re, json, importlib.util, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
spec = importlib.util.spec_from_file_location("chk", os.path.join(ROOT, "scripts", "check-gedcom-vs-archive.py"))
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)

def main():
    ged = sys.argv[1]
    rep = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    indi, fam = chk.parse(ged)
    for p in indi.values(): chk.prep(p)
    chk.load_given_names()
    people = chk.load_archive()
    for q in people.values():
        t = chk.foldsp(q["place"].split(",")[0]) if q["place"] else ""
        if t and len(t) > 3: chk.PLACEWORDS.add(t)
    for p in indi.values(): p["kind"] = chk.kind_of(p)
    M = chk.Matcher(people)
    mh_count = collections.Counter(a["mh"] for a in people.values() if a["mh"])
    pid_of = {}
    for i, p in indi.items():
        if p["kind"] != "real" or p["life"] == "living-or-unknown": continue
        tier, pids = M.match(p)
        if tier.startswith(("T0", "T1")) and len(pids) == 1:
            pid_of[i] = pids[0]
    seen = collections.Counter(pid_of.values())          # two tree people on one archive row: the row is not unique, leave it out
    pid_of = {i: q for i, q in pid_of.items() if seen[q] == 1}
    links = collections.defaultdict(lambda: {"father": None, "mother": None, "spouse": [], "kids": []})
    skipped = collections.Counter()
    def fits(par, kid):
        pb, kb, pd = indi[par]["by"], indi[kid]["by"], indi[par]["dy"]
        if pb and kb and not (12 <= kb - pb <= 65): return "parent's age"
        if pd and kb and kb - pd > 1: return "parent dead before the birth"
        return ""
    for f in fam.values():
        h, w = f["husb"], f["wife"]
        hp, wp = pid_of.get(h), pid_of.get(w)
        if hp and wp:
            if wp not in links[hp]["spouse"]: links[hp]["spouse"].append(wp)
            if hp not in links[wp]["spouse"]: links[wp]["spouse"].append(hp)
        for c in f["chil"]:
            cp = pid_of.get(c)
            if not cp: continue
            # the first family the tree gives this child
            if indi[c]["famc"] and indi[c]["famc"][0] != f["id"]: skipped["a later family of the same child"] += 1; continue
            for par, role, ppid in ((h, "father", hp), (w, "mother", wp)):
                if not ppid: continue
                why = fits(par, c)
                if why: skipped[why] += 1; continue
                links[cp][role] = ppid
                if cp not in links[ppid]["kids"]: links[ppid]["kids"].append(cp)
    out = {"_note": "Made by scripts/build-tree-links.py from David's MyHeritage tree (17 Nov 2026 export): dead people only, both ends held by this archive, "
                    "matched by MyHeritage id or by name and years. build-dossiers.py draws these graded «tree» (the family tree, unverified) and only "
                    "where no register, index or hand-written link exists. Do not edit by hand.",
           "links": {k: v for k, v in sorted(links.items()) if v["father"] or v["mother"] or v["spouse"] or v["kids"]}}
    io.open(os.path.join(DATA, "tree-links.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    n_par = sum(1 for v in out["links"].values() if v["father"] or v["mother"]); n_sp = sum(len(v["spouse"]) for v in out["links"].values()) // 2
    n_kids = sum(len(v["kids"]) for v in out["links"].values())
    print("people with links %d; with a parent drawn %d; spouse pairs %d; parent-child pairs (listed from the parent) %d; skipped %s" %
          (len(out["links"]), n_par, n_sp, n_kids, dict(skipped)))
    if rep: io.open(rep, "w", encoding="utf-8").write(json.dumps({"skipped": dict(skipped)}, indent=1))

if __name__ == "__main__": main()
