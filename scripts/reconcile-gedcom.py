#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile the roster against David's live family tree.

The roster's family file was the MyHeritage export of **July 2018** — 8,286
people, 254 of them of this surname. The live tree, exported 16 September 2026,
holds **15,643** and **1,413**. Everything in between is a year of David's own
work that this archive has been building beside without reading.

Three counts come out of this, and they are different questions:

    only in the tree      people the archive has never heard of
    only in the archive   people the archive found and the tree does not have
    in both, disagreeing  the same person with two different years

    python3 scripts/read-gedcom.py <file.ged> --out <dir>
    python3 scripts/reconcile-gedcom.py <dir>/gedcom.json

Writes site/src/data/reconcile.json — a derived summary, checked against the
archive's rule on living people: a living person appears by name and town and
never by a date, so no date of a living person is written here.
"""
import sys, os, io, json, re, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
SURNAME = re.compile(r"de\s*franc?es+c?h?i|de\s*francesk|defrancesk|defraneski|defrancesch", re.I)
# A real FamilySearch ark, and nothing else. The first draft of this also
# matched any nine-digit run, which is the shape of a MyHeritage record number
# too, so it counted six people as carrying film references who carry none.
ARK  = re.compile(r"ark:/\d+/([13]:1:[\w-]+)")
# FamilySearch's own citation names the collection in quotes before the word
# FamilySearch. That title is the useful thing: it says which BOOK was read.
COLL = re.compile(r'"([^"]{12,95})",\s*,?\s*FamilySearch')

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def given(name):
    """Given names only, lowercased, with the surname and its spellings gone.
    Two archives spell this family nine ways; the given names are what match."""
    s = strip(name).lower()
    s = re.sub(r"[\"“”'’(),/]", " ", s)
    toks = [t for t in s.split() if t not in ("de", "di", "da", "the", "nee", "n", "von")]
    toks = [t for t in toks
            if not re.match(r"^franc?es+c?h?i\w*$|^francesk\w*$|^defranc\w*$|^defranesk\w*$", t)]
    return " ".join(sorted(set(toks)))

def key(name, by, dy):
    return "%s|%s|%s" % (given(name), by or "", dy or "")

def main():
    g = json.load(io.open(sys.argv[1], encoding="utf-8"))
    tree = [p for p in g["people"].values() if SURNAME.search(p["name"] or "")]
    roster = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]

    T, R = {}, {}
    for p in tree:
        T.setdefault(key(p["name"], p["by"], p["dy"]), []).append(p)
    for r in roster:
        R.setdefault(key(r["name"], r.get("b"), r.get("d")), []).append(r)

    only_tree = [k for k in T if k not in R]
    only_ros  = [k for k in R if k not in T]
    both      = [k for k in T if k in R]

    # A softer join: same given names, ignore the years. Anything that matches
    # here but not above is the SAME PERSON with a different date somewhere, and
    # that is the most useful category on the page.
    Tg = collections.defaultdict(list)
    Rg = collections.defaultdict(list)
    for p in tree:   Tg[given(p["name"])].append(p)
    for r in roster: Rg[given(r["name"])].append(r)
    # A disagreement is the SAME person recorded twice with one field wrong.
    # Matching on given names alone is not that: it paired a Francesco born
    # 1450 in the tree with every Francesco in the roster and called 2,414 of
    # them disagreements, which is a cross-join wearing a finding's clothes.
    # The test is an anchor — the two must agree on one year exactly and
    # differ on the other. Two people of one name and no shared year are two
    # people, which is the thing this archive keeps having to say out loud.
    disagree = []
    for gname, ps in Tg.items():
        if not gname or gname not in Rg:
            continue
        for p in ps:
            for r in Rg[gname]:
                if key(p["name"], p["by"], p["dy"]) == key(r["name"], r.get("b"), r.get("d")):
                    continue
                anchored = ((p["by"] and p["by"] == r.get("b")) or
                            (p["dy"] and p["dy"] == r.get("d")))
                if not anchored:
                    continue
                # An infant and an adult are never the same person, however
                # many years they share. A child born and buried in the same
                # year gives a register row where b == d, and 20 of this
                # archive's burial rows look like that — so an anchor on ONE
                # year paired Antonius of Gologorica, who died in 1893 aged
                # seventy-nine, with an Antonius buried at Pula as an infant
                # in 1893. Three of the fourteen «disagreements» were that.
                def span(b, d):
                    return (d - b) if (b and d) else None
                s1, s2 = span(p["by"], p["dy"]), span(r.get("b"), r.get("d"))
                if s1 is not None and s2 is not None:
                    short, long_ = min(s1, s2), max(s1, s2)
                    if short <= 5 and long_ >= 30:
                        continue
                if (p["by"] and r.get("b") and p["by"] != r["b"]) or \
                   (p["dy"] and r.get("d") and p["dy"] != r["d"]):
                    disagree.append({
                        "name": p["name"], "rosterName": r["name"],
                        "tree": [p["by"], p["dy"]], "archive": [r.get("b"), r.get("d")],
                        "treePlace": p["bp"] or p["dp"], "src": r.get("src")})
    # one row per pair, and the loudest first
    seen, dis = set(), []
    for d in disagree:
        k = (d["name"], d["rosterName"], tuple(d["tree"]), tuple(d["archive"]))
        if k in seen: continue
        seen.add(k); dis.append(d)
    # Two of these are not disagreements. When the reverse pair is also in the
    # list — tree 1786 against archive 1789, and tree 1789 against archive 1786
    # — both sides are holding the same person twice under two years, and each
    # copy is being matched to the other side's other copy. That is a duplicate
    # to merge, not a date to decide, and the page should not call it one.
    pairs = {(d["name"].lower(), tuple(d["tree"]), tuple(d["archive"])) for d in dis}
    for d in dis:
        d["kind"] = ("mirror"
                     if (d["name"].lower(), tuple(d["archive"]), tuple(d["tree"])) in pairs
                     else "date")

    def gap(d):
        pairs = [(a, b) for a, b in zip(d["tree"], d["archive"]) if a and b and a != b]
        return max((abs(a - b) for a, b in pairs), default=0)
    dis.sort(key=lambda d: -gap(d))

    # --- what only the tree has, and whether it is worth having --------------
    # The join was SET EQUALITY on given names, and the live tree stacks every
    # variant it has ever seen into one string. «Johannes Giovanni Gian
    # Battista de Franceschi» against this archive's «Giovanni Defranceschi»
    # is one set of four names against a set of one, so the top of David's own
    # male line was reported as somebody the archive had never heard of. The
    # test is now: the same set of given names, OR one name in common and a
    # year in common.
    tok = lambda n: set(given(n).split())
    byyear = collections.defaultdict(list)
    for r in roster:
        for y in (r.get("b"), r.get("d")):
            if y:
                for dy in (-1, 0, 1):
                    byyear[y + dy].append(r)
    def in_roster(p):
        t = tok(p["name"])
        if not t or given(p["name"]) in Rg:
            return True
        for y in (p["by"], p["dy"]):
            for r in byyear.get(y or 0, []):
                if t & tok(r["name"]):
                    return True
        return False

    # And David's own placeholder pens — a node called «PLACEHOLDERS
    # Defranceschi's for Investigation (not real)», twenty-three country
    # folders with town folders under them. Everybody inside is somebody he
    # has already tested and parked, which is the opposite of untouched work.
    fams = g["families"]
    def childs(pid):
        out = []
        for f in fams.values():
            if f.get("husb") == pid or f.get("wife") == pid:
                out += (f.get("chil") or [])
        return out
    penned, stack = set(), [q["id"] for q in g["people"].values()
                            if re.search(r"PLACEHOLDER", q["name"] or "", re.I)]
    while stack:
        x = stack.pop()
        if x in penned:
            continue
        penned.add(x)
        stack += childs(x)

    newp = [p for p in tree if not in_roster(p)]
    pennedp = [p for p in newp if p["id"] in penned]
    newp = [p for p in newp if p["id"] not in penned]
    newp.sort(key=lambda p: (p["by"] or p["dy"] or 9999))

    cites = [p for p in tree if p["cites"]]
    arks  = [p for p in tree if any(ARK.search(c) for c in p["cites"])]

    # --- what the tree cites that this archive has never read ---------------
    # Every ark already written down anywhere in this repository, so the page
    # can say which of David's own citations are news to the archive.
    seen_arks = set()
    for base, _dirs, files in os.walk(os.path.join(ROOT, "site", "src")):
        for fn in files:
            if fn == "reconcile.json" or not fn.endswith((".json", ".astro", ".md", ".js")):
                continue
            try:
                txt = io.open(os.path.join(base, fn), encoding="utf-8").read()
            except Exception:
                continue
            seen_arks |= set(ARK.findall(txt))
    tree_arks = collections.Counter()
    for p in tree:
        for c in p["cites"]:
            for a in ARK.findall(c):
                tree_arks[a] += 1
    unseen = [a for a in tree_arks if a not in seen_arks]

    # The collections, and whether this archive has ever named them.
    colls, coll_people = collections.Counter(), collections.defaultdict(set)
    for p in tree:
        for c in p["cites"]:
            for t in COLL.findall(c):
                colls[t] += 1
                coll_people[t].add(p["id"])
    byid = {p["id"]: p for p in tree}
    colrows = []
    for t, n in colls.most_common():
        ppl = [byid[i] for i in coll_people[t]]
        colrows.append({"t": t, "c": n, "p": len(ppl),
                        "n": sum(1 for q in ppl if given(q["name"]) not in Rg)})

    # Where the tree goes that the archive does not, and when.
    newplaces = collections.Counter(
        (p["bp"] or p["dp"] or "").split(",")[0].strip() for p in newp)
    newplaces.pop("", None)
    cent = collections.Counter()
    for p in newp:
        y = p["by"] or p["dy"]
        if y: cent[(y // 100) * 100] += 1

    # And what the archive has that the tree does not, by where it came from.
    bysrc = collections.Counter()
    for k in only_ros:
        for r in R[k]:
            bysrc[r.get("src") or "?"] += 1

    out = {
      "note": __doc__.strip().split("\n\n")[1],
      "when": "16 September 2026",
      "stats": {
        "treeTotal": len(g["people"]), "treeFamilies": len(g["families"]),
        "treeSurname": len(tree), "rosterRows": len(roster),
        "onlyTree": len(newp), "onlyTreePenned": len(pennedp), "onlyRoster": sum(len(R[k]) for k in only_ros),
        "exactBoth": sum(len(T[k]) for k in both),
        "disagree": sum(1 for d in dis if d["kind"] == "date"),
        "mirrored": sum(1 for d in dis if d["kind"] == "mirror"),
        "treeLiving": sum(1 for p in tree if p["living"]),
        "withCitations": len(cites), "withArks": len(arks),
        "arksDistinct": len(tree_arks), "arksUnseen": len(unseen),
        "arksImage": sum(1 for a in tree_arks if a.startswith("3:1")),
        "arksRecord": sum(1 for a in tree_arks if a.startswith("1:1")),
        "collections": len(colrows),
        "collectionsNewPeople": sum(c["n"] for c in colrows),
        "gedcom2018": 254,
      },
      "colls": colrows,
      "newPlaces": newplaces.most_common(28),
      "newCentury": sorted(cent.items()),
      "rosterOnlyBySrc": bysrc.most_common(),
      # Living people: name and place, never a date. The rule is applied here
      # rather than trusted to the page.
      "new": [{"n": p["name"],
               "y": ("" if p["living"] else
                     ("%s–%s" % (p["by"] or "", p["dy"] or "")).strip("–")),
               "p": (p["bp"] or p["dp"] or "").split(",")[0],
               "living": p["living"]} for p in newp[:400]],
      "disagree": dis[:120],
      "newCount": len(newp),
    }
    json.dump(out, io.open(os.path.join(DATA, "reconcile.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out["stats"], ensure_ascii=False, indent=1))
    print("\ncollections, and how many of their people are new here:")
    for c in colrows:
        print("  %3d cites / %3d people / %3d new  %s" % (c["c"], c["p"], c["n"], c["t"]))
    print("\nfirst disagreements:")
    for d in dis[:10]:
        print("  %-36s tree %s  archive %s" % (d["name"][:36], d["tree"], d["archive"]))

if __name__ == "__main__":
    main()
