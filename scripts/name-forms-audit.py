#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check «Say Your Name» against the records, and refuse the build when it drifts.

WHAT THE PAGE CLAIMS. /your-name/ says of its own table: «Every name below was
reconciled by hand from the forms that actually appear in these registers — not
from a dictionary.»

WHAT WAS TRUE. On 17 September 2026, 130 of its 415 forms — thirty-one per cent
— appeared in no record this archive holds. The Croatian column was the worst,
31 of 48. And dozens were filed under the wrong language outright: «Antal» and
«Ilona» are Hungarian and sat in the Italian column, along with «Božo»,
«Tomislav», «Jerolim» and a dozen more Croatian forms, and «Steven», «Jasper»,
«Noel» and «Dominic», which are English. There was **no Hungarian column at
all**, in an archive whose own place-strings read «Modrus-Fiume, Magyarország».

THE ANSWER IS NOT TO DELETE THEM. A form nobody here has met is still the right
thing to type into a Hungarian or German index tomorrow. It is only not
evidence. So the table now keeps both kinds and this script decides which is
which, mechanically, by looking every form up in the names this archive
actually holds — roster, register, households, burials, graves, the
FamilySearch record sets and the four raw harvests. A form found there is
attested. A form not found is a lookup aid and the page says so.

    python3 scripts/name-forms-audit.py            # report
    python3 scripts/name-forms-audit.py --write    # store the attestation
    python3 scripts/name-forms-audit.py --check    # refuse if it has drifted
"""
import json, csv, os, re, sys, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
LANGS = ["latin", "italian", "venetian", "croatian", "german", "hungarian", "english"]

# The surname in every spelling it takes, so it is never counted as a forename.
SUR = re.compile(r"(de\s*)?franc?[eh]sch?i\w*|franceski\w*|defranceski\w*|franceschin\w*", re.I)
STOP = {"or", "and", "born", "the", "nee", "née", "surname", "not", "indexed",
        "withheld", "private", "unknown", "wife", "husband", "son", "daughter",
        "de", "di", "del", "della", "dei", "von", "van"}

def fold(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace("æ", "ae").replace("ÿ", "y")

def tokens(name):
    n = re.sub(r"\s*\(.*?\)\s*", " ", str(name or ""))
    n = SUR.sub(" ", n)
    n = re.sub(r"[^\wÀ-ɏ'\-]+", " ", n)
    return [w for w in n.split() if len(w) > 1 and w.lower() not in STOP]

def corpus():
    """Every forename token that occurs in a record this archive holds."""
    c = collections.Counter()
    def eat(names):
        for n in names:
            for t in tokens(n): c[fold(t)] += 1
    def load(f):
        d = json.load(open(os.path.join(DATA, f), encoding="utf-8"))
        return d.get("rows", d) if isinstance(d, dict) else d
    for f, keys in [("roster.json", ("name",)), ("burials.json", ("name", "kin")),
                    ("graves.json", ("name",)),
                    ("fsrecords.json", ("name", "spouses", "parents"))]:
        eat([r.get(k) for r in load(f) for k in keys if r.get(k)])
    rg = load("register.json")
    eat([r.get("n") for r in rg] + [r.get("sp") for r in rg]
        + [x for r in rg for x in (r.get("o") or [])])
    hh = load("households.json")
    eat([h.get(k) for h in hh for k in ("father", "mother")]
        + [ch.get("name") for h in hh for ch in (h.get("children") or [])])
    for name in ("familysearch-croatia", "familysearch-inlaws",
                 "familysearch-migration", "familysearch-austria"):
        fp = os.path.join(ROOT, "data", name + ".csv")
        if not os.path.exists(fp): continue
        for r in csv.DictReader(open(fp, encoding="utf-8")):
            eat([r.get("name"), r.get("parents"), r.get("spouses")])
    return c

def forms(g):
    for r in g["rows"]:
        for k in LANGS:
            for f in (r.get(k) or "").split(","):
                f = f.strip()
                if f and f != "—":
                    yield r["canon"], k, f

def main():
    g = json.load(open(os.path.join(DATA, "givennames.json"), encoding="utf-8"))
    c = corpus()
    seen, tot, att = {}, collections.Counter(), collections.Counter()
    miss = collections.defaultdict(list)
    for canon, k, f in forms(g):
        tot[k] += 1
        n = c.get(fold(f), 0)
        if n:
            att[k] += 1
            seen[f] = n
        else:
            miss[k].append((canon, f))

    if "--check" in sys.argv:
        stored = g.get("seen") or {}
        bad = []
        for f, n in stored.items():
            if not c.get(fold(f)):
                bad.append(f"«{f}» is stored as attested and appears in no record")
        for f in seen:
            if f not in stored:
                bad.append(f"«{f}» appears in the records and is not stored as attested")
        if bad:
            print(f"  FAIL  names       {len(bad)} — the name table's attestation no longer matches the records")
            for b in bad[:25]: print(f"          {b}")
            if len(bad) > 25: print(f"          … and {len(bad)-25} more")
            print("          run: python3 scripts/name-forms-audit.py --write")
            return 1
        print(f"  ok    names      {sum(att.values())} of {sum(tot.values())} cells attested in the records "
              f"({len(stored)} distinct forms), {sum(tot.values())-sum(att.values())} marked as lookup aids")
        return 0

    print(f"{'column':11} {'forms':>6} {'attested':>9} {'lookup aid':>11}")
    for k in LANGS:
        print(f"{k:11} {tot[k]:6} {att[k]:9} {tot[k]-att[k]:11}")
    print(f"{'TOTAL':11} {sum(tot.values()):6} {sum(att.values()):9} {sum(tot.values())-sum(att.values()):11}")
    if "--verbose" in sys.argv:
        for k in LANGS:
            if miss[k]:
                print(f"\n-- {k}: no record here uses these ({len(miss[k])})")
                print("   " + " · ".join(f"{f} ({canon})" for canon, f in miss[k]))
    if "--write" in sys.argv:
        g["seen"] = dict(sorted(seen.items()))
        g["totalForms"] = sum(tot.values())
        g["attested"] = sum(att.values())
        json.dump(g, open(os.path.join(DATA, "givennames.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\nwritten: {g['attested']} attested of {g['totalForms']}")
    return 0

sys.exit(main())
