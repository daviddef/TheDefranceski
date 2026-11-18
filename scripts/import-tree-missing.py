#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add to roster.json the people the GEDCOM check (scripts/check-gedcom-vs-archive.py) found in David's tree and not in this archive.

    python3 scripts/import-tree-missing.py <tree.ged> <missing-from-archive.csv> [--write] [--report FILE]

Same rule as scripts/import-placeholder-branch.py, which this follows row for row: a person is living if 80 or younger with no death
recorded (L2.CUTOFF). Dead and born before the cutoff (or no birth year) is added; no death recorded and born before the cutoff is added
without a death year; everyone else is NOT added and is written to the report as «held back» (a possible minor is never published).
Only the rows the check calls `real` (a name, and a year or a place) are read; stubs, «Unknown …» and place buckets stay out.
Every row says it is the tree's word (`lore`) and that no kinship is claimed. The GEDCOM is never committed.
"""
import sys, re, io, json, os, csv, importlib.util, collections, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import living_v2 as L2
spec = importlib.util.spec_from_file_location("ipp", os.path.join(ROOT, "scripts", "import-placeholder-people.py"))
ipp = importlib.util.module_from_spec(spec); spec.loader.exec_module(ipp)
parse, f1, sub, yr, slug = ipp.parse, ipp.f1, ipp.sub, ipp.yr, ipp.slug
def dslug(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
FSRX = re.compile(r"(?:https?://)?(?:www\.)?familysearch\.org/(ark:/61903/[0-9:A-Za-z\-]+)(\?[^\s\"']*)?")

def main():
    ged, csvp = sys.argv[1], sys.argv[2]; write = "--write" in sys.argv
    rep = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    ids = [r["gedcom_id"] for r in csv.DictReader(open(csvp, encoding="utf-8")) if r["kind"] == "real"]
    recs = parse(ged)
    def name(p): return " ".join(((f1(recs[p], "NAME") or [""])[0]).replace("/", " ").split())
    roster = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))
    pids = {r["pid"] for r in roster["rows"] if r.get("pid")}
    have_mh = {str(r["mh"]) for r in roster["rows"] if r.get("mh")}
    def norm(x):
        x = unicodedata.normalize("NFKD", re.sub(r"\(.*?\)", "", x)).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z]", "", x.replace("de franceschi", "defranceschi").replace("de franceski", "defranceski"))
    have_nb = collections.defaultdict(list)
    for r in roster["rows"]: have_nb[norm(r["name"])].append(r.get("b"))
    out, held, dups = [], [], []
    for p in ids:
        r = recs[p]; nm = name(p)
        mh = str(4000000 + int(p.strip("@I")))
        if mh in have_mh: continue
        b = yr((sub(r, "BIRT", "DATE") or [""])[0]); d = yr((sub(r, "DEAT", "DATE") or [""])[0]); dead = bool(f1(r, "DEAT"))
        dnote = ""
        if b is not None and d is not None and d < b: dnote = " The tree gives a death year (%d) earlier than the birth year (%d); neither can be right, so no death year is shown here." % (d, b); d = None
        if len(nm.split()) < 2:   # a given name alone (the tree has no surname for this spouse or child): no page, no link, nothing to search on
            held.append((nm, "the tree gives a given name only, no surname")); continue
        bs = have_nb.get(norm(nm), [])
        if bs and (b in bs): dups.append((nm, b)); continue
        if not dead and (b is None or b >= L2.CUTOFF): held.append((nm, "no death recorded and %s" % ("no birth year" if b is None else "born in the living window"))); continue
        if dead and b is not None and b >= L2.CUTOFF: held.append((nm, "born in the living window; the tree's death flag is not a death record")); continue
        pl0 = ((sub(r, "BIRT", "PLAC") or sub(r, "CHR", "PLAC") or sub(r, "DEAT", "PLAC") or sub(r, "RESI", "PLAC") or [""])[0]).strip()
        parts = [x.strip() for x in pl0.split(",") if x.strip()]
        if len(parts) > 1 and re.search(r"Maria|Santissim|^San |^Santa |Immacolata|Catedral|Nuestra|Visitazione|Assunzione|Parroquia|Chiesa", parts[0]): parts = parts[1:]
        pl = ", ".join(parts[:3])
        links = []
        for ln in r["l"]:
            for m in FSRX.finditer(ln[1]):
                u = "https://www.familysearch.org/" + m.group(1) + (m.group(2) or "")
                if u not in links: links.append(u)
        ark = next((re.search(r"ark:/61903/(1:1:[0-9A-Z\-]+)", u).group(1) for u in links if "/1:1:" in u), "")
        base = slug(nm) + ("-%d" % b if b else ""); pid, n = base, 2
        while pid in pids: pid = "%s-%d" % (base, n); n += 1
        pids.add(pid)
        note = ("**From David's MyHeritage tree, a spouse or child of a person who carries the name.** "
                "**Tree only (`lore`):** the name, years and place are the tree's word; no register or index record has been read here, and **no kinship to this archive's lines is claimed**. "
                "Added on 18 November 2026 by the check of the tree against this archive.")
        note += dnote
        if links:
            note += " The tree cites FamilySearch: " + "; ".join("[%s](%s)" % (re.search(r"ark:/61903/([0-9:A-Za-z\-]+)", u).group(1), u) for u in links) + "."
        row = {"name": nm, "b": b, "d": d if dead else None, "place": pl, "src": "myheritage", "href": "/people/", "note": note, "notable": False,
               "ark": ark, "mh": mh, "line": "unplaced", "pid": pid}
        if len(re.sub(r"\s*\(.*?\)\s*", "", nm)) >= 5: row["who"] = "/who/%s/" % dslug(nm)
        out.append(row)
    print("to add %d; held back %d; already on the roster by name and year %d" % (len(out), len(held), len(dups)))
    if rep:
        io.open(rep, "w", encoding="utf-8").write(json.dumps({"added": [{"pid": r["pid"], "place": r["place"]} for r in out], "held": held, "dups": dups}, ensure_ascii=False, indent=1))
    if write:
        roster["rows"].extend(out)
        io.open(os.path.join(DATA, "roster.json"), "w", encoding="utf-8").write(json.dumps(roster, ensure_ascii=False, indent=1) + "\n")
        print("written")

if __name__ == "__main__": main()
