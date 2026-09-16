#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the people this archive has and the live tree does not, as a GEDCOM.

The reconciliation runs both ways, and the second direction is the one worth
being pleased about: **780 people in this archive's roster are in David's live
tree under no spelling.** They came out of the registers, the headstones and
the indexes one at a time — 111 out of households read off the page, 79 off a
headstone, 72 out of burial registers.

This is the archive paying the tree back. It writes a GEDCOM rather than
typing into the tree, because a GEDCOM is a file David can look at before he
imports it, and an import he can undo.

    python3 scripts/export-to-tree.py

Writes data/to-the-tree.ged.

**No living person is in it.** The rule everywhere else on this site is name
and town and never a date; here the rule is stricter still, because a tree
entry is a date by construction. Anybody the roster marks living, and anybody
with no death and a birth after 1930, is left out entirely.
"""
import json, io, os, re, sys, unicodedata, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(ROOT, "data", "to-the-tree.ged")

SRC = {
    "myheritage": "the July 2018 family file",
    "household": "a household read out of a parish register",
    "record": "an indexed record",
    "burial": "a burial register",
    "read": "a register volume read page by page",
    "grave": "a headstone",
    "golo": "the Gologorica registers",
    "index": "a name index",
    "namesake": "a namesake, not joined to this family",
    "life": "a life written up in the archive",
    "line": "a line drawn in the archive",
    "chart": "the published Omiš chart",
    "eleven": "the Gračišće eleven",
    "paper": "a newspaper",
}

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def given(name):
    """Given names only — the join the reconciliation uses."""
    s = strip(name).lower()
    s = re.sub(r"[\"“”'’(),/]", " ", s)
    toks = [t for t in s.split() if t not in ("de", "di", "da", "the", "nee", "n", "von")]
    toks = [t for t in toks
            if not re.match(r"^franc?es+c?h?i\w*$|^francesk\w*$|^defranc\w*$|^defranesk\w*$", t)]
    return " ".join(sorted(set(toks)))

def esc(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

def main():
    ros = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]
    rec = json.load(io.open(os.path.join(DATA, "reconcile.json"), encoding="utf-8"))
    gedj = sys.argv[1] if len(sys.argv) > 1 else None
    if not gedj:
        print("Pass the parsed gedcom.json so the tree side can be matched.\n"
              "   python3 scripts/export-to-tree.py <dir>/gedcom.json")
        return 2
    g = json.load(io.open(gedj, encoding="utf-8"))
    SUR = re.compile(r"de\s*franc?es+c?h?i|de\s*francesk|defrancesk|defraneski|defrancesch", re.I)
    tree = {given(p["name"]) for p in g["people"].values() if SUR.search(p["name"] or "")}

    out, skipped = [], collections.Counter()
    for r in ros:
        if given(r["name"]) in tree:
            skipped["already in the tree"] += 1
            continue
        if r.get("living"):
            skipped["living — never exported"] += 1
            continue
        if not r.get("d") and (r.get("b") or 0) > 1930:
            skipped["no death, born after 1930 — treated as living"] += 1
            continue
        out.append(r)

    lines = ["0 HEAD", "1 SOUR TheDefranceschiArchive",
             "2 NAME The Defranceschi Archive", "2 CORP https://daviddef.github.io/TheDefranceski/",
             "1 DATE " + datetime.date.today().strftime("%d %b %Y").upper(),
             "1 CHAR UTF-8", "1 GEDC", "2 VERS 5.5.1", "2 FORM LINEAGE-LINKED",
             "1 NOTE " + esc("People this archive holds that tree 4 does not. Every one came out of a "
                             "register, a headstone or an index; the source of each is in its own NOTE. "
                             "No living person is in this file.")]
    for i, r in enumerate(out, 1):
        # The surname is the word the family is actually called, not the last
        # word in the string: «Alessandro de Franceschi OP» ends in the Order
        # of Preachers, and splitting on the last space made OP a surname.
        nm = esc(r["name"])
        # «Francesco» and «Francesca» are GIVEN names and begin with the same
        # six letters as the surname; matching «Franc\w*» turned Tommaso-
        # Francesco de Franceschi into a man surnamed Francesco.
        m = re.search(r"((?:de\s+|di\s+|dei\s+)?"
                      r"(?:Frances?ch\w*|Francesk\w*|Defrance?sc?h?\w*|Defranesk\w*))", nm, re.I)
        if m:
            sur = m.group(1)
            fore = (nm[:m.start()] + " " + nm[m.end():]).strip()
        else:
            bits = nm.rsplit(" ", 1)
            sur, fore = bits[-1], (bits[0] if len(bits) > 1 else "")
        lines += ["0 @I%d@ INDI" % i,
                  "1 NAME %s /%s/" % (esc(fore), esc(sur))]
        if r.get("b"):
            lines += ["1 BIRT", "2 DATE %s" % r["b"]]
            if r.get("place"): lines += ["2 PLAC %s" % esc(r["place"])]
        if r.get("d"):
            lines += ["1 DEAT", "2 DATE %s" % r["d"]]
            if r.get("place"): lines += ["2 PLAC %s" % esc(r["place"])]
        why = SRC.get(r.get("src"), r.get("src") or "the archive")
        note = "From the Defranceschi Archive — %s." % why
        if r.get("ark"):
            note += " FamilySearch ark:/61903/%s." % r["ark"]
        if r.get("who"):
            note += " https://daviddef.github.io/TheDefranceski%s" % r["who"]
        lines += ["1 NOTE " + esc(note)]
    lines.append("0 TRLR")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(json.dumps({"written": len(out), "file": os.path.relpath(OUT, ROOT),
                      "skipped": dict(skipped),
                      "bySource": dict(collections.Counter(x.get("src") for x in out))},
                     ensure_ascii=False, indent=1))

if __name__ == "__main__":
    sys.exit(main() or 0)
