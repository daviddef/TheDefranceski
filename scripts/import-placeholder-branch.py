#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add to roster.json EVERY person of David's MyHeritage branch «PLACEHOLDERS Defranceschi's for Investigation (not real)» (children of the
country nodes, and their spouses) that the archive does not hold yet. The first pass (scripts/import-placeholder-people.py, 16 Nov 2026) took only
those who carried a FamilySearch citation; David asked on 18 Nov 2026 for the whole branch, to be researched country by country.

    python3 scripts/import-placeholder-branch.py <tree.ged> [--write] [--report FILE]

Rule of the archive (CLAUDE.md), unchanged: a person is living if 80 or younger with no death recorded (L2.CUTOFF). A person the tree shows dead
and born before the cutoff is added; someone born before the cutoff with no death recorded is added without a death year; everyone else (born in
the window, or no birth year and no death) is NOT added and is written to the report as «held back». A bare death flag is not a death record for
someone born in the window. Structural stubs of the tree (a state name, «Unknown Defranceschi», «QLD Defranceschi (Deceased)») are skipped and
listed. Every row says that it is the tree's word (lore), that no record has been read here, and that no kinship is claimed. Nothing about a
person goes to the Record Atlas. The GEDCOM is never committed.
"""
import sys, re, io, json, os, importlib.util, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import living_v2 as L2
spec = importlib.util.spec_from_file_location("ipp", os.path.join(ROOT, "scripts", "import-placeholder-people.py"))
ipp = importlib.util.module_from_spec(spec); spec.loader.exec_module(ipp)
parse, f1, sub, yr, slug = ipp.parse, ipp.f1, ipp.sub, ipp.yr, ipp.slug
BRANCH = "PLACEHOLDERS Defranceschi's for Investigation (not real)"
FSRX = re.compile(r"(?:https?://)?(?:www\.)?familysearch\.org/(ark:/61903/[0-9:A-Za-z\-]+)(\?[^\s\"']*)?")


def main():
    ged = sys.argv[1]; write = "--write" in sys.argv
    rep = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    recs = parse(ged)
    fams = [r for r in recs.values() if r["t"] == "FAM"]
    def kids(p):
        out = []
        for f in fams:
            if p in f1(f, "HUSB") + f1(f, "WIFE"): out += f1(f, "CHIL")
        return out
    def spouses(p):
        out = []
        for f in fams:
            h, w = f1(f, "HUSB"), f1(f, "WIFE")
            if p in h: out += w
            if p in w: out += h
        return out
    def name(p): return " ".join(((f1(recs[p], "NAME") or [""])[0]).replace("/", " ").split())
    root = next(k for k, r in recs.items() if r["t"] == "INDI" and name(k) == BRANCH)
    country_of, order = {}, []
    for s in kids(root):
        label = re.match(r"[A-Z][A-Z \-]+", name(s)); label = (label.group(0).strip() if label else name(s)).title()
        stack = [s]
        while stack:
            p = stack.pop()
            if p in country_of: continue
            country_of[p] = (s, label); order.append(p)
            stack += kids(p) + spouses(p)
    roster = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))
    pids = {r["pid"] for r in roster["rows"] if r.get("pid")}
    have_mh = {str(r["mh"]) for r in roster["rows"] if r.get("mh")}
    import unicodedata
    def norm(x):
        x = unicodedata.normalize("NFKD", re.sub(r"\(.*?\)", "", x)).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z]", "", x.replace("de franceschi", "defranceschi").replace("de franceski", "defranceski"))
    have_nb = collections.defaultdict(list)
    for r in roster["rows"]: have_nb[norm(r["name"])].append(r.get("b"))
    out, held, skipped, dups = [], [], [], []
    for p in order:
        s, label = country_of[p]
        if p == s: continue                                    # the country node itself
        if name(s).upper().startswith("PLACEHOLDER: FRANCE"): continue   # the French cluster was added on 18 Nov 2026 (d01f902b), told on /namesakes/
        if name(s).upper().startswith("PLACEHOLDER:"): label = "Others"
        r = recs[p]; nm = name(p)
        mh = str(4000000 + int(p.strip("@I")))
        if mh in have_mh: continue
        b = yr((sub(r, "BIRT", "DATE") or [""])[0]); d = yr((sub(r, "DEAT", "DATE") or [""])[0]); dead = bool(f1(r, "DEAT"))
        dnote = ""
        if b is not None and d is not None and d < b: dnote = " The tree gives a death year (%d) earlier than the birth year (%d); neither can be right, so no death year is shown here." % (d, b); d = None
        pl0 = ((sub(r, "BIRT", "PLAC") or sub(r, "CHR", "PLAC") or sub(r, "DEAT", "PLAC") or sub(r, "RESI", "PLAC") or [""])[0]).strip()
        stub = (not nm) or nm.isupper() or re.search(r"\bUnknown\b|\(Deceased\)|^PLACEHOLDER|^N\s", nm, re.I) or len(re.sub(r"[^A-Za-zÀ-ÿ]", "", nm)) < 4
        bs = have_nb.get(norm(nm), [])
        if bs and (b in bs):   # same name and the same birth year (both None counts as the same)
            dups.append((label, nm, b)); continue
        if stub and b is None and d is None and not pl0: skipped.append((label, nm or "(no name)")); continue
        if not nm: skipped.append((label, "(no name)")); continue
        if not dead and (b is None or b >= L2.CUTOFF): held.append((label, nm, "no death recorded and %s" % ("no birth year" if b is None else "born %d" % b))); continue
        if dead and b is not None and b >= L2.CUTOFF: held.append((label, nm, "born %d; the tree's death flag is not a death record" % b)); continue
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
        note = ("**From David's MyHeritage tree** (filed under the investigation branch «%s»; the tree itself calls that node not real). "
                "**Tree only (`lore`):** the name, years and place are the tree's word; no register or index record has been read here, and **no kinship to this archive's lines is claimed**. "
                "Added on 18 November 2026 so that the country can be searched; what a search finds will be told here." % label)
        note += dnote
        if links:
            note += " The tree cites FamilySearch: " + "; ".join("[%s](%s)" % (re.search(r"ark:/61903/([0-9:A-Za-z\-]+)", u).group(1), u) for u in links) + "."
        row = {"name": nm, "b": b, "d": d if dead else None, "place": pl, "src": "myheritage", "href": "/people/", "note": note, "notable": False,
               "ark": ark, "mh": mh, "line": "unplaced", "pid": pid}
        if len(re.sub(r"\s*\(.*?\)\s*", "", nm)) >= 5: row["who"] = "/who/%s/" % slug(nm)
        out.append((label, row))
    by = collections.Counter(l for l, _ in out)
    print("to add %d; held back %d; skipped stubs %d; already on the roster by name and year %d" % (len(out), len(held), len(skipped), len(dups)))
    for k, v in sorted(by.items()): print("  %-28s %d" % (k, v))
    if rep:
        io.open(rep, "w", encoding="utf-8").write(json.dumps({"added": [{"country": l, "pid": r["pid"], "place": r["place"]} for l, r in out],
                                                              "held": held, "skipped": skipped, "dups": dups}, ensure_ascii=False, indent=1))
    if write:
        roster["rows"].extend(r for _, r in out)
        io.open(os.path.join(DATA, "roster.json"), "w", encoding="utf-8").write(json.dumps(roster, ensure_ascii=False, indent=1) + "\n")
        print("written")


if __name__ == "__main__": main()
