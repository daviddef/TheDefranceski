#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check David's MyHeritage GEDCOM against this archive's people and links.

    python3 scripts/check-gedcom-vs-archive.py <export.ged> [--out private/gedcom-check-YYYY-MM-DD]

THE SET. Every person who carries the Defranceschi name in any of its forms (the Record Atlas catalogue's `same`, `attested`
and typo-`lead` forms, typography folded: De Franceschi = Defranceschi = DeFranceschi), plus every spouse of such a person, plus
every child of such a person.  A bare «Franceschi» is not the name and is not in the set.

THE QUESTIONS.
  1. Does the archive hold this person at all?  (roster row, by MyHeritage id first, then by name and years.)
  2. Where the archive holds the person, does it hold the same parents, spouses and children?  (Archive links are those the person
     page draws: dossiers.json ptree, plus tree.json father/mother/spouse/kids.)
  3. Is every FamilySearch record the tree cites for these people cited anywhere in the archive's data?
  4. What is in the archive about this surname that the tree does not hold?

THE LIVING RULE. The GEDCOM carries the dates of living people, and this archive publishes a living person's name and town and
nothing else.  Everything is written under private/ (git-ignored); the GEDCOM itself is never copied.  A living person is
counted, and listed by name and the relation that matters, with no date.
"""
import sys, os, io, re, json, csv, glob, unicodedata, argparse, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
THIS_YEAR = datetime.date.today().year
LIVING_FROM = THIS_YEAR - 80          # the archive's cutoff: no death recorded and born after this = living
PRESUMED_DEAD_BEFORE = THIS_YEAR - 119

def fold(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)

def foldsp(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

# the name: catalogue forms 'same' + 'attested' + typo-looking leads, typography folded (spaces, case, hyphen, apostrophe)
FORMS = ["Defranceschi", "Defranceski", "Defrančeski", "Deffranceschi", "Defranca", "Defrancaschi", "Defranceschy", "Defrancesci",
         "Defrancheski", "Defranci", "Defranzeschi", "Defranzesi", "di Franceschi", "Franceski", "Francetchi", "Franchessi",
         "Dafranceschi", "Deframeschi", "Defrancejchi", "Defranceshi", "Defrancesshi", "Defrancischi", "Defrancoschi", "Defrancschi",
         "Dofranceschi", "Sefranceschi", "Defranceschi", "de Franceski", "Defranceskij", "Defranceski's"]
FORMSET = {fold(f) for f in FORMS}
def is_carrier_surname(s):
    f = fold(s)
    if not f: return False
    if f in FORMSET: return True
    # tolerate a trailing parenthetical / second surname fragment in the field
    for part in re.split(r"[ ,/]+", str(s or "")):
        if fold(part) in FORMSET: return True
    return False

# ---------------------------------------------------------------- GEDCOM
def read_lines(path):
    for rawb in io.open(path, "rb"):
        try: line = rawb.decode("utf-8")
        except UnicodeDecodeError: line = rawb.decode("cp1252", "replace")
        yield line.rstrip("\r\n").lstrip("﻿")

def parse(path):
    """-> (indi, fam).  indi[id] = dict(names[], sex, bdate,bplace,ddate,dplace, dead, famc[], fams[], rin, text)"""
    indi, fam = {}, {}
    cur = None; kind = None; ctx = None; ctx_tag = None
    for line in read_lines(path):
        m = re.match(r"^(\d+) (@[^@]+@ )?(\S+)(?: (.*))?$", line)
        if not m: continue
        lvl, xref, tag, val = int(m.group(1)), (m.group(2) or "").strip(), m.group(3), (m.group(4) or "")
        if lvl == 0:
            cur = None; kind = None
            if xref and tag == "INDI":
                cur = indi.setdefault(xref, dict(id=xref, names=[], sex="", b="", bp="", d="", dp="", dead=False, famc=[], fams=[],
                                                 rin="", text=[], marnm=[], upd=""))
                kind = "I"
            elif xref and tag == "FAM":
                cur = fam.setdefault(xref, dict(id=xref, husb="", wife="", chil=[], mdate="", mplace="", div=False, text=[]))
                kind = "F"
            ctx = None
            continue
        if cur is None: continue
        if lvl == 1:
            ctx = tag; ctx_tag = tag
            if kind == "I":
                if tag == "NAME": cur["names"].append(dict(full=val, given="", sur="", marn=False))
                elif tag == "SEX": cur["sex"] = val.strip()
                elif tag == "DEAT": cur["dead"] = True
                elif tag == "FAMC": cur["famc"].append(val.strip())
                elif tag == "FAMS": cur["fams"].append(val.strip())
                elif tag == "RIN": cur["rin"] = val.strip()
                elif tag == "_UPD": cur["upd"] = val.strip()
            else:
                if tag == "HUSB": cur["husb"] = val.strip()
                elif tag == "WIFE": cur["wife"] = val.strip()
                elif tag == "CHIL": cur["chil"].append(val.strip())
                elif tag == "DIV": cur["div"] = True
            if tag in ("NOTE", "SOUR", "OBJE", "EVEN") or True:
                cur["text"].append(val)
        else:
            cur["text"].append(val)
            if kind == "I":
                if lvl == 2 and ctx == "NAME" and cur["names"]:
                    if tag == "GIVN": cur["names"][-1]["given"] = val
                    elif tag == "SURN": cur["names"][-1]["sur"] = val
                    elif tag == "_MARNM": cur["names"][-1]["marn"] = True
                if lvl == 2 and tag == "_MARNM": cur["marnm"].append(val)
                if lvl == 2 and ctx == "BIRT":
                    if tag == "DATE" and not cur["b"]: cur["b"] = val
                    if tag == "PLAC" and not cur["bp"]: cur["bp"] = val
                if lvl == 2 and ctx == "DEAT":
                    if tag == "DATE" and not cur["d"]: cur["d"] = val
                    if tag == "PLAC" and not cur["dp"]: cur["dp"] = val
            else:
                if lvl == 2 and ctx == "MARR":
                    if tag == "DATE" and not cur["mdate"]: cur["mdate"] = val
                    if tag == "PLAC" and not cur["mplace"]: cur["mplace"] = val
    return indi, fam

def year_of(s):
    m = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", str(s or ""))
    return int(m[0]) if m else None

PLACEWORDS = set()
def kind_of(p):
    """real | bucket (a place or country standing in for a person) | unnamed (Unknown ...) | stub (name only, no year, no place)"""
    g = p["given"]; gf = foldsp(g)
    if (not g and not p["sur"]) or not g or "unknown" in gf.split() or foldsp(p["sur"]) == "unknown":
        return "unnamed"
    if re.search(r"[:,]|PLACEHOLDER|\bnot real\b", g, re.I) or re.search(r"\b[A-Z]{4,}\b", g):
        return "bucket"
    if gf in PLACEWORDS or (gf.split() and gf.split()[0] in PLACEWORDS and len(gf.split()) <= 3 and not p["by"] and not p["dy"]):
        return "bucket"
    if not p["by"] and not p["dy"] and not p["bp"] and not p["dp"]: return "stub"
    return "real"

# the GEDCOM's person, reduced
def prep(p):
    names = p["names"] or [dict(full="", given="", sur="")]
    n0 = names[0]
    sur = n0["sur"] or re.sub(r".*/(.*?)/.*", r"\1", n0["full"]) if "/" in n0["full"] or n0["sur"] else n0["sur"]
    given = n0["given"] or re.sub(r"/.*", "", n0["full"]).strip()
    allsur = set()
    for n in names:
        s = n["sur"] or (re.search(r"/(.*?)/", n["full"]) or [None, ""])[1]
        if s: allsur.add(s)
    for s in p["marnm"]: allsur.add(s)
    p["given"] = given.strip(); p["sur"] = (sur or "").strip(); p["allsur"] = allsur
    p["by"] = year_of(p["b"]); p["dy"] = year_of(p["d"])
    p["carrier"] = any(is_carrier_surname(s) for s in allsur) or any(is_carrier_surname(n["full"]) for n in names)
    if p["dead"] or p["dy"]: p["life"] = "dead"
    elif p["by"] and p["by"] <= PRESUMED_DEAD_BEFORE: p["life"] = "presumed-dead"
    else: p["life"] = "living-or-unknown"
    p["kind"] = kind_of(p)
    p["display"] = (p["given"] + " " + (p["sur"] or "")).strip() or n0["full"]
    return p

# ---------------------------------------------------------------- the archive
def load_archive():
    r = json.load(open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]
    people = {}
    for x in r:
        pid = x.get("pid")
        if not pid: continue
        name = x.get("name", "")
        main = re.sub(r"\s*\(.*?\)", "", name).strip()
        paren = re.findall(r"\((.*?)\)", name)
        people[pid] = dict(pid=pid, name=name, main=main, paren=paren, b=year_of(x.get("b")), d=year_of(x.get("d")), place=x.get("place", ""),
                           mh=str(x.get("mh") or ""), line=x.get("line", ""), who=x.get("who", ""), href=x.get("href", ""),
                           ark=x.get("ark", ""), src=x.get("src", ""))
    return people

def archive_links():
    """pid -> dict(parents:set, spouse:set, kids:set)  from the dossiers' ptree and the tree page"""
    L = collections.defaultdict(lambda: dict(parents=set(), spouse=set(), kids=set()))
    d = json.load(open(os.path.join(DATA, "dossiers.json"), encoding="utf-8"))["persons"]
    for pid, v in d.items():
        pt = v.get("ptree") or {}
        for q in pt.get("parents") or []:
            if isinstance(q, dict) and q.get("pid"): L[pid]["parents"].add(q["pid"])
        sp = pt.get("spouse")
        for q in ([sp] if isinstance(sp, dict) else (sp or [])):
            if isinstance(q, dict) and q.get("pid"): L[pid]["spouse"].add(q["pid"])
        for q in pt.get("children") or []:
            if isinstance(q, dict) and q.get("pid"): L[pid]["kids"].add(q["pid"])
    tp = os.path.join(ROOT, "data", "tree-page", "tree.json")
    if os.path.exists(tp):
        for q in json.load(open(tp, encoding="utf-8"))["people"]:
            i = q["id"]
            for k in ("father", "mother"):
                if q.get(k): L[i]["parents"].add(q[k])
            for s in q.get("spouse") or []:
                L[i]["spouse"].add(s if isinstance(s, str) else (s.get("id") if isinstance(s, dict) else None))
            for s in q.get("kids") or []:
                L[i]["kids"].add(s if isinstance(s, str) else (s.get("id") if isinstance(s, dict) else None))
    for i in L:
        for k in L[i]: L[i][k].discard(None)
    # make links symmetric: a parent link on the child is a kids link on the parent, and spouses are mutual
    for i in list(L):
        for p in list(L[i]["parents"]): L[p]["kids"].add(i)
        for k in list(L[i]["kids"]): L[k]["parents"].add(i)
        for s in list(L[i]["spouse"]): L[s]["spouse"].add(i)
    return L

ATLAS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(ROOT)))), "Record Atlas") if ".work" in ROOT else os.path.join(os.path.dirname(ROOT), "Record Atlas")
CANON = {}
def load_given_names():
    fp = os.path.join(ATLAS, "data", "given-name-families.json")
    if not os.path.exists(fp):
        fp = os.path.join("/Volumes/DJ - Crucial - 4TB-SSD/Claude Projects/Family Projects/Record Atlas", "data", "given-name-families.json")
    if not os.path.exists(fp): return 0
    for f in json.load(open(fp, encoding="utf-8"))["families"]:
        for m in f.get("members", []):
            if m.get("status") in ("same", "attested", "rule"):
                CANON.setdefault(fold(m["form"]), f["id"])
        CANON.setdefault(fold(f["name"]), f["id"])
    return len(CANON)
def canon(tok): 
    t = fold(tok); return CANON.get(t, t)
def given_alts(given):
    """«Johannes / Giovanni Gian Battista» -> canonical first-name ids of each alternative"""
    alts = set()
    for part in re.split(r"\s*/\s*", str(given or "")):
        w = part.strip().split(" ")
        if w and w[0]: alts.add(canon(w[0]))
    return alts

PARTICLES = {"de", "di", "da", "del", "della", "dei", "degli", "von", "van"}
def split_name(full):
    """«Maria De Franceschi» -> ('Maria', 'DeFranceschi' folded). The particle stays with the surname."""
    toks = str(full or "").split()
    if not toks: return "", ""
    if len(toks) >= 2 and fold(toks[-2]) in PARTICLES: return " ".join(toks[:-2]), fold(toks[-2] + toks[-1])
    return " ".join(toks[:-1]), fold(toks[-1])

def given_variants(given):
    """every way the tree or the archive may write a given-name field: each slash alternative, whole and first word"""
    out_full, out_first = set(), set()
    for part in re.split(r"\s*/\s*", str(given or "")):
        part = part.strip()
        if not part: continue
        out_full.add(foldsp(part))
        out_first.add(canon(part.split(" ")[0]))
    # «Gian / Giovanni / Ivan Battista»: the last alternative carries the tail, so also try each head with the tail
    parts = [x.strip() for x in re.split(r"/", str(given or "")) if x.strip()]
    if len(parts) > 1:
        tail = parts[-1].split(" ")[1:]
        for h in parts[:-1]:
            if len(h.split(" ")) == 1 and tail: out_full.add(foldsp(h + " " + " ".join(tail)))
    return out_full, out_first

def SK(s):
    """surname key: every spelling of the name is one key (the catalogue's same/attested forms); other surnames fold only"""
    return "DFC" if is_carrier_surname(s) else fold(s)

class Matcher:
    def __init__(self, people):
        self.people = people
        self.by_mh = collections.defaultdict(list)
        self.by_full = collections.defaultdict(list)    # (full given, surname) -> pids
        self.by_first = collections.defaultdict(list)   # (canonical first given, surname) -> pids
        self.by_any = collections.defaultdict(list)     # (canonical given word, surname) -> pids
        for pid, a in people.items():
            if a["mh"]: self.by_mh[a["mh"].lstrip("4") if len(a["mh"]) == 7 else a["mh"]].append(pid)
            g, sur = split_name(a["main"])
            surs = {SK(sur)} if sur else set()
            for par in a["paren"]:                      # «Maria Udovicic (Defranceschi)»: the bracket is the other surname
                surs.add(SK(par))
            fulls, firsts = given_variants(g)
            if not g:  # a bare surname row has no given name to match on
                continue
            words = {canon(w) for w in re.split(r"[\s/]+", g) if len(w) > 1}
            for sname in surs:
                for f in fulls: self.by_full[(f, sname)].append(pid)
                for f in firsts: self.by_first[(f, sname)].append(pid)
                for w in words: self.by_any[(w, sname)].append(pid)

    def match(self, g):
        rin = g["rin"].replace("MH:I", "")
        if rin and rin in self.by_mh: return "T0 mh-id", list(self.by_mh[rin])
        surs = {SK(x) for x in g["allsur"]} | {SK(x) for x in g["marnm"]}
        surs.discard("")
        # the full-name surname may sit in NAME as «Given /de Franceschi/»; allsur already has it
        fulls, firsts = given_variants(g["given"])
        cand_full = list(dict.fromkeys(pid for sname in surs for f in fulls for pid in self.by_full.get((f, sname), [])))
        cand_first = list(dict.fromkeys(pid for sname in surs for f in firsts for pid in self.by_first.get((f, sname), [])))
        by, dy = g["by"], g["dy"]
        def years(a, tol):
            ok_b = (by is None or a["b"] is None) or abs(by - a["b"]) <= tol
            ok_d = (dy is None or a["d"] is None) or abs(dy - a["d"]) <= tol
            has = (by is not None and a["b"] is not None) or (dy is not None and a["d"] is not None)
            return ok_b and ok_d, has
        for pool, label in ((cand_full, "name"), (cand_first, "given-name family")):
            for tol, tier in ((0, "T1 %s + years exact"), (2, "T2 %s + years within 2")):
                hit = [pid for pid in pool if all(years(self.people[pid], tol))]
                if hit: return tier % label, hit
        nodate = [pid for pid in cand_full if by is None and dy is None and self.people[pid]["b"] is None and self.people[pid]["d"] is None]
        if len(nodate) == 1: return "T3 unique name, no years on either side", nodate
        # any given name the two share (the tree writes «Justina», the archive «Magdalena Justina»), the name family, the exact birth year
        if by is not None:
            words = {canon(w) for w in re.split(r"[\s/]+", g["given"]) if len(w) > 1}
            cand_any = list(dict.fromkeys(pid for sname in surs for w in words for pid in self.by_any.get((w, sname), [])))
            hit = [pid for pid in cand_any if self.people[pid]["b"] == by and years(self.people[pid], 1)[0]]
            if hit: return "T4 shared given name + surname family + birth year", hit
        pool = cand_full or cand_first
        if pool: return "possible: same name, years differ or missing on one side", pool
        return "none", []

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ged"); ap.add_argument("--out", default="")
    a = ap.parse_args()
    out = a.out or os.path.join(ROOT, "private", "gedcom-check-" + datetime.date.today().isoformat())
    os.makedirs(out, exist_ok=True)
    indi, fam = parse(a.ged)
    for p in indi.values(): prep(p)
    # the set
    carriers = {i for i, p in indi.items() if p["carrier"]}
    spouses, kids = set(), set()
    for i in carriers:
        for f in indi[i]["fams"]:
            F = fam.get(f)
            if not F: continue
            for s in (F["husb"], F["wife"]):
                if s and s != i and s in indi: spouses.add(s)
            for c in F["chil"]:
                if c in indi: kids.add(c)
    theset = carriers | spouses | kids
    def role(i):
        r = []
        if i in carriers: r.append("carries the name")
        if i in spouses: r.append("spouse of a carrier")
        if i in kids: r.append("child of a carrier")
        return "; ".join(r)

    load_given_names()
    people = load_archive()
    for q in people.values():
        t = foldsp(q["place"].split(",")[0]) if q["place"] else ""
        if t and len(t) > 3: PLACEWORDS.add(t)
    for p in indi.values(): p["kind"] = kind_of(p)
    M = Matcher(people)
    links = archive_links()
    # match everyone we need: the set and the parents of the set
    need = set(theset)
    for i in list(theset):
        for f in indi[i]["famc"] + indi[i]["fams"]:
            F = fam.get(f)
            if F:
                for s in [F["husb"], F["wife"]] + F["chil"]:
                    if s in indi: need.add(s)
    matched = {}
    for i in need:
        tier, pids = M.match(indi[i])
        matched[i] = (tier, pids)

    # ---- 1. presence
    tiers = collections.Counter(); rows = []
    for i in sorted(theset, key=lambda x: (indi[x]["sur"], indi[x]["given"], indi[x]["by"] or 0)):
        p = indi[i]; tier, pids = matched[i]
        tiers[(p["life"], tier.split(" ")[0] if not tier.startswith("possible") else "possible")] += 1
    # archive id -> gedcom ids (inverse of the match, only confident tiers)
    inv = collections.defaultdict(set)
    for i, (tier, pids) in matched.items():
        if tier.startswith("T"):
            for pid in pids: inv[pid].add(i)

    def conf(i): return matched[i][0].startswith("T") and bool(matched[i][1])

    # ---- 2. link comparison, over matched people
    gaps = []
    def arch_rel(pids, kind):
        s = set()
        for pid in pids:
            s |= links.get(pid, {}).get(kind, set())
        return s
    def to_g(pidset):
        """archive pids -> set of gedcom ids (via the confident inverse), plus the pids with no gedcom twin"""
        g, no = set(), set()
        for pid in pidset:
            if pid in inv: g |= inv[pid]
            else: no.add(pid)
        return g, no
    def gedcom_rel(i, kind):
        out_ = set()
        p = indi[i]
        if kind == "parents":
            for f in p["famc"]:
                F = fam.get(f)
                if F:
                    for s in (F["husb"], F["wife"]):
                        if s in indi: out_.add(s)
        else:
            for f in p["fams"]:
                F = fam.get(f)
                if not F: continue
                if kind == "spouse":
                    for s in (F["husb"], F["wife"]):
                        if s and s != i and s in indi: out_.add(s)
                else:
                    for c in F["chil"]:
                        if c in indi: out_.add(c)
        return out_
    def nm(i):
        p = indi[i]
        return p["display"] + ("" if p["life"] != "dead" and p["life"] != "presumed-dead" else
                               " (%s–%s)" % (p["by"] or "?", p["dy"] or "?"))
    linkstat = collections.Counter()
    for i in sorted(theset):
        if not conf(i): continue
        p = indi[i]; pids = matched[i][1]
        if p["life"] == "living-or-unknown":
            livingflag = True
        else:
            livingflag = False
        for kind in ("parents", "spouse", "kids"):
            gset = gedcom_rel(i, kind)
            aset_pids = arch_rel(pids, kind)
            ag, ano = to_g(aset_pids)
            for r in sorted(gset - ag):
                q = indi[r]
                linkstat[(kind, "in tree, not on the archive's page")] += 1
                # is the relative at least in the archive?
                have = "in archive" if conf(r) else ("possible" if matched.get(r, ("", []))[0].startswith("possible") else "not in archive")
                gaps.append(dict(person=nm(i), life=p["life"], relation=kind, gap="in tree, not linked in archive", relative=nm(r),
                                 relative_life=q["life"], relative_kind=q["kind"], relative_in_archive=have, person_tier=matched[i][0], relative_tier=matched[r][0], person_gid=i, relative_gid=r, archive_pid=";".join(pids),
                                 relative_pid=";".join(matched[r][1]) if r in matched else ""))
            for r in sorted(ag - gset):
                linkstat[(kind, "on the archive's page, not in tree")] += 1
                gaps.append(dict(person=nm(i), life=p["life"], relation=kind, gap="in archive, not in tree", relative=nm(r),
                                 relative_life=indi[r]["life"], relative_kind=indi[r]["kind"], relative_in_archive="yes", archive_pid=";".join(pids), relative_pid=""))
            for pid in sorted(ano):
                q = people.get(pid)
                linkstat[(kind, "on the archive's page, relative not in tree")] += 1
                gaps.append(dict(person=nm(i), life=p["life"], relation=kind, gap="in archive, relative has no twin in tree",
                                 relative=(q["name"] if q else pid), relative_life="", relative_in_archive="yes", archive_pid=";".join(pids),
                                 relative_pid=pid))
            if gset and gset <= ag and not (ag - gset) and not ano: linkstat[(kind, "agree")] += 1

    # ---- 3. FamilySearch records the tree cites for these people
    corpus = []
    for fp in glob.glob(os.path.join(DATA, "*.json")):
        try: corpus.append(open(fp, encoding="utf-8").read())
        except Exception: pass
    corpus = "\n".join(corpus)
    arkgaps = []; arkcount = 0
    for i in sorted(theset):
        p = indi[i]
        txt = "\n".join(p["text"])
        for ark in set(re.findall(r"ark:/61903/((?:1|3):1:[A-Z0-9-]+)", txt)):
            arkcount += 1
            tail = ark.split(":", 2)[2]
            if tail not in corpus:
                arkgaps.append(dict(person=nm(i), life=p["life"], ark=ark, archive_pid=";".join(matched[i][1]) if i in matched else "", given=p["given"], sur=p["sur"], by=p["by"] or "", dy=p["dy"] or "", gid=i, tier=matched[i][0] if i in matched else ""))

    # ---- 4. archive people with the surname that the tree does not hold
    tree_names = set()
    for p in indi.values():
        for n in p["names"]:
            s = n["sur"] or (re.search(r"/(.*?)/", n["full"]) or [None, ""])[1]
            tree_names.add(foldsp((n["given"] or "") + " " + s))
    in_tree_pids = set(inv)
    arch_only = []
    for pid, q in people.items():
        if not is_carrier_surname(" ".join(q["main"].split()[-1:])) and not any(is_carrier_surname(x) for x in q["paren"]): continue
        if pid in in_tree_pids: continue
        if q["mh"]: continue
        arch_only.append(q)

    # ---- the files
    def w(name, rows_, cols):
        with open(os.path.join(out, name), "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); wr.writeheader()
            for r_ in rows_: wr.writerow(r_)
    missing, possible, present = [], [], []
    for i in sorted(theset, key=lambda x: (indi[x]["sur"], indi[x]["given"], indi[x]["by"] or 0)):
        p = indi[i]; tier, pids = matched[i]
        rec = dict(gedcom_id=i, name=p["display"], role=role(i), kind=p["kind"], life=p["life"], tier=tier, archive_pid=";".join(pids),
                   birth_year=("" if p["life"] == "living-or-unknown" else p["by"] or ""),
                   death_year=("" if p["life"] == "living-or-unknown" else p["dy"] or ""),
                   place=("" if p["life"] == "living-or-unknown" else p["bp"] or p["dp"]),
                   mh_rin=p["rin"], parents=";".join(indi[x]["display"] for x in gedcom_rel(i, "parents")))
        if tier.startswith("T"): present.append(rec)
        elif tier.startswith("possible"): possible.append(rec)
        else: missing.append(rec)
    cols = ["gedcom_id", "name", "role", "kind", "life", "tier", "archive_pid", "birth_year", "death_year", "place", "mh_rin", "parents"]
    w("present-in-archive.csv", present, cols); w("possible-matches.csv", possible, cols); w("missing-from-archive.csv", missing, cols)
    w("link-gaps.csv", gaps, ["person", "life", "relation", "gap", "relative", "relative_life", "relative_kind", "relative_in_archive", "archive_pid", "relative_pid", "person_tier", "relative_tier", "person_gid", "relative_gid"])
    w("record-links-not-in-archive.csv", arkgaps, ["person", "life", "ark", "archive_pid", "given", "sur", "by", "dy", "gid", "tier"])
    w("archive-people-not-in-tree.csv", [dict(pid=q["pid"], name=q["name"], b=q["b"], d=q["d"], place=q["place"], line=q["line"], src=q["src"]) for q in arch_only],
      ["pid", "name", "b", "d", "place", "line", "src"])
    # tallies
    S = collections.OrderedDict()
    S["gedcom_people"] = len(indi); S["gedcom_families"] = len(fam)
    S["carriers"] = len(carriers); S["spouses_only"] = len(spouses - carriers); S["children_only"] = len(kids - carriers - spouses)
    S["set_total"] = len(theset)
    S["set_by_life"] = dict(collections.Counter(indi[i]["life"] for i in theset))
    S["present"] = len(present); S["possible"] = len(possible); S["missing"] = len(missing)
    S["present_by_tier"] = dict(collections.Counter(r["tier"] for r in present))
    for r_ in missing + possible + present: r_["kind"] = indi[r_["gedcom_id"]]["kind"]
    S["missing_by_kind"] = dict(collections.Counter(r["kind"] for r in missing))
    S["missing_real_by_life"] = dict(collections.Counter(r["life"] for r in missing if r["kind"] == "real"))
    S["missing_real_carriers_dead"] = sum(1 for r in missing if r["kind"] == "real" and r["life"] != "living-or-unknown" and "carries" in r["role"])
    S["missing_real_others_dead"] = sum(1 for r in missing if r["kind"] == "real" and r["life"] != "living-or-unknown" and "carries" not in r["role"])
    S["missing_real_living"] = sum(1 for r in missing if r["kind"] == "real" and r["life"] == "living-or-unknown")
    S["present_by_kind"] = dict(collections.Counter(r["kind"] for r in present))
    S["set_by_kind"] = dict(collections.Counter(indi[i]["kind"] for i in theset))
    S["missing_by_life"] = dict(collections.Counter(r["life"] for r in missing))
    S["missing_by_role"] = dict(collections.Counter(r["role"] for r in missing))
    S["possible_by_life"] = dict(collections.Counter(r["life"] for r in possible))
    act = [g for g in gaps if g["gap"] == "in tree, not linked in archive" and g["relative_in_archive"] == "in archive"
           and g["life"] != "living-or-unknown" and g["relative_life"] != "living-or-unknown"]
    S["link_gaps_actionable_both_in_archive_dead"] = dict(collections.Counter(g["relation"] for g in act))
    S["link_gaps_relative_missing_from_archive_dead"] = dict(collections.Counter(
        g["relation"] for g in gaps if g["gap"] == "in tree, not linked in archive" and g["relative_in_archive"] == "not in archive"
        and g.get("relative_kind") == "real" and g["life"] != "living-or-unknown" and g["relative_life"] != "living-or-unknown"))
    S["link_gaps_relative_is_placeholder_or_blank"] = sum(1 for g in gaps if g.get("relative_kind") in ("bucket", "unnamed", "stub"))
    S["link_gaps"] = len(gaps)
    S["link_gaps_by_kind"] = {" / ".join(k): v for k, v in sorted(linkstat.items(), key=lambda kv: (kv[0][0], kv[0][1]))}
    S["ark_cited_in_tree"] = arkcount; S["ark_not_in_archive"] = len(arkgaps)
    S["archive_surname_people_without_tree_twin"] = len(arch_only)
    S["roster_rows_with_mh_id"] = sum(1 for q in people.values() if q["mh"])
    S["archive_matched_by_mh_id_confirmed"] = sum(1 for r in present if r["tier"].startswith("T0"))
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(S, indent=1, ensure_ascii=False))
    print("written to", out)

if __name__ == "__main__":
    main()
