#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read a MyHeritage GEDCOM into something this archive can reason about.

The roster's family file was the export of **July 2018** — 8,286 people — and
the live tree has 15,643. A structural walk of the live tree through the
browser found 798 individuals of the surname where the old name-query method
found 459, and then could not get them out: MyHeritage blocks a POST to a
local receiver and the browser tool channel truncates at about a thousand
characters, which is ten people a call.

David exported the tree on 16 September 2026. This reads it.

    python3 scripts/read-gedcom.py <file.ged> [--out <dir>]

The GEDCOM itself is NOT committed. It carries dates of birth for living
people, and this archive publishes a living person's name and town and nothing
else. What is written here is a derived, rule-checked summary.
"""
import sys, os, io, json, re, collections

def parse(path):
    """One pass. GEDCOM is a flat list of levelled lines; records start at 0."""
    recs, cur, stack = [], None, {}
    # The file declares UTF-8 and is UTF-8 for 425,574 of its 425,636 lines.
    # Sixty-two are not, and one bad byte at offset 3,571 stops a strict
    # decoder dead. Decoding line by line keeps every Croatian diacritic in the
    # 99.98% that is clean and rescues the rest as cp1252 rather than throwing
    # the tree away or replacement-charactering the whole thing.
    for rawb in io.open(path, "rb"):
        try:
            raw = rawb.decode("utf-8-sig")
        except UnicodeDecodeError:
            raw = rawb.decode("cp1252", errors="replace")
        line = raw.rstrip("\r\n").lstrip("\ufeff")
        if not line.strip():
            continue
        m = re.match(r"^(\d+)\s+(?:(@[^@]+@)\s+)?(\S+)(?:\s(.*))?$", line)
        if not m:
            continue
        lvl, xref, tag, val = int(m.group(1)), m.group(2), m.group(3), m.group(4) or ""
        node = {"tag": tag, "val": val, "id": xref, "sub": []}
        if lvl == 0:
            cur = node
            recs.append(node)
            stack = {0: node}
        else:
            parent = stack.get(lvl - 1)
            if parent is None:
                continue
            if tag == "CONC":
                if parent["sub"]:
                    parent["sub"][-1]["val"] += val
                else:
                    parent["val"] += val
                continue
            if tag == "CONT":
                if parent["sub"]:
                    parent["sub"][-1]["val"] += "\n" + val
                else:
                    parent["val"] += "\n" + val
                continue
            parent["sub"].append(node)
            stack[lvl] = node
    return recs

def sub(node, *tags):
    """First descendant down a tag path."""
    cur = node
    for t in tags:
        nxt = None
        for c in cur["sub"]:
            if c["tag"] == t:
                nxt = c
                break
        if nxt is None:
            return None
        cur = nxt
    return cur

def val(node, *tags):
    n = sub(node, *tags)
    return (n["val"] if n else "").strip()

def allsub(node, tag):
    return [c for c in node["sub"] if c["tag"] == tag]

YEAR = re.compile(r"\b(1[0-9]\d\d|20\d\d)\b")

def main():
    path = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.dirname(path)
    recs = parse(path)
    indi = [r for r in recs if r["tag"] == "INDI"]
    fam  = [r for r in recs if r["tag"] == "FAM"]
    people = {}
    for r in indi:
        name = val(r, "NAME").replace("/", "").strip()
        giv, sur = val(r, "NAME", "GIVN"), val(r, "NAME", "SURN")
        b, d = sub(r, "BIRT"), sub(r, "DEAT")
        bd = val(b, "DATE") if b else ""
        dd = val(d, "DATE") if d else ""
        bp = val(b, "PLAC") if b else ""
        dp = val(d, "PLAC") if d else ""
        # MyHeritage marks the living with _MARNM/_UID variously; the reliable
        # test is the one this archive already uses: no death, and a birth
        # inside the last hundred years.
        by = YEAR.search(bd)
        dy = YEAR.search(dd)
        living = (not dd) and (not d) and (by is None or int(by.group()) > 1926)
        # The citations David types by hand are NOTES, not SOUR records.
        # SOUR here is MyHeritage's own Smart-Match plumbing — «Meyer Family
        # Site», «Geni World Family Tree» — and reading only those found 272
        # citations and two arks in a file that contains **3,746 of them**.
        # The hand-written ones hang off the events: a full FamilySearch
        # citation with the ark, the image number and the date read.
        cites = []
        for n in allsub(r, "NOTE"):
            if n["val"].strip():
                cites.append(n["val"].strip()[:600])
        for tag in ("BIRT", "DEAT", "BAPM", "BURI", "MARR", "RESI", "IMMI",
                    "OCCU", "CHR", "CENS", "EVEN"):
            for ev in allsub(r, tag):
                for n in allsub(ev, "NOTE"):
                    if n["val"].strip():
                        cites.append(tag + ": " + n["val"].strip()[:600])
        for s in allsub(r, "SOUR"):
            t = " ".join(x for x in (s["val"], val(s, "PAGE"), val(s, "DATA", "TEXT")) if x)
            if t.strip():
                cites.append(t.strip()[:400])
        for tag in ("BIRT", "DEAT", "BAPM", "BURI", "MARR", "RESI", "IMMI", "OCCU"):
            for ev in allsub(r, tag):
                for s in allsub(ev, "SOUR"):
                    t = " ".join(x for x in (s["val"], val(s, "PAGE"), val(s, "DATA", "TEXT")) if x)
                    if t.strip():
                        cites.append(tag + ": " + t.strip()[:400])
        people[r["id"]] = {
            "id": r["id"], "name": name, "giv": giv, "sur": sur,
            "sex": val(r, "SEX"), "b": bd, "d": dd, "bp": bp, "dp": dp,
            "by": int(by.group()) if by else None, "dy": int(dy.group()) if dy else None,
            "living": bool(living), "cites": cites,
            "famс": [], "fams": [],
        }
    fams = {}
    for f in fam:
        kids = [c["val"] for c in allsub(f, "CHIL")]
        fams[f["id"]] = {"id": f["id"], "husb": val(f, "HUSB"), "wife": val(f, "WIFE"),
                         "chil": kids, "marr": val(sub(f, "MARR") or {"sub": []}, "DATE") if sub(f, "MARR") else "",
                         "place": val(sub(f, "MARR") or {"sub": []}, "PLAC") if sub(f, "MARR") else ""}
    json.dump({"people": people, "families": fams},
              io.open(os.path.join(out, "gedcom.json"), "w", encoding="utf-8"), ensure_ascii=False)
    NAME = re.compile(r"de\s*franc?es+c?h?i|de\s*francesk|defrancesk|defraneski|defrancesch", re.I)
    ours = [p for p in people.values() if NAME.search(p["name"] or "")]
    print(json.dumps({
        "individuals": len(people), "families": len(fams),
        "of_the_surname": len(ours),
        "surname_living": sum(1 for p in ours if p["living"]),
        "surname_with_citations": sum(1 for p in ours if p["cites"]),
        "citations_total": sum(len(p["cites"]) for p in ours),
        "all_with_citations": sum(1 for p in people.values() if p["cites"]),
        "surnames_top": collections.Counter(p["sur"] for p in people.values() if p["sur"]).most_common(12),
    }, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
