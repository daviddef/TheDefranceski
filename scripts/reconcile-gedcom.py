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
ARK = re.compile(r"ark:/\d+/[\w:-]+|\bDGS\s*\d+|\bfilm\s*\d+|\b\d{9}\b", re.I)

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
    def gap(d):
        pairs = [(a, b) for a, b in zip(d["tree"], d["archive"]) if a and b and a != b]
        return max((abs(a - b) for a, b in pairs), default=0)
    dis.sort(key=lambda d: -gap(d))

    # --- what only the tree has, and whether it is worth having --------------
    newp = []
    for k in only_tree:
        for p in T[k]:
            if given(p["name"]) in Rg:      # the soft join caught it; it is a disagreement
                continue
            newp.append(p)
    newp.sort(key=lambda p: (p["by"] or p["dy"] or 9999))

    cites = [p for p in tree if p["cites"]]
    arks  = [p for p in tree if any(ARK.search(c) for c in p["cites"])]

    out = {
      "note": __doc__.strip().split("\n\n")[1],
      "when": "16 September 2026",
      "stats": {
        "treeTotal": len(g["people"]), "treeFamilies": len(g["families"]),
        "treeSurname": len(tree), "rosterRows": len(roster),
        "onlyTree": len(newp), "onlyRoster": sum(len(R[k]) for k in only_ros),
        "exactBoth": sum(len(T[k]) for k in both),
        "disagree": len(dis),
        "treeLiving": sum(1 for p in tree if p["living"]),
        "withCitations": len(cites), "withArks": len(arks),
        "gedcom2018": 254,
      },
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
    print("\nfirst disagreements:")
    for d in dis[:10]:
        print("  %-36s tree %s  archive %s" % (d["name"][:36], d["tree"], d["archive"]))

if __name__ == "__main__":
    main()
