#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn 1,153 undifferentiated «leads» into a worklist somebody can act on.

The Register calls every unaccepted row a lead. Read that way the number is
paralysing and useless. Sorted by whether the spelling is this surname at all,
and by whether the row carries the two things that let you open a book — the
parents and the parish — it becomes a short list with a parish at the top of it.
"""
import json, io, os, re, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
def load(n): return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))

def strip(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")
def norm(s): return re.sub(r"[^a-z]+", "", strip(s).lower())

OURS  = re.compile(r"^(de)?franc(e|i)sc?h?[iy]$|^defrances?k|^franceschi$|^francischi$|^franzeschi$|^defranceschi")
OTHER = re.compile(r"francetich|franchini|franceschini|franceskini|franceschina|francovich|francic|francich")
def klass(sp):
    n = norm(sp)
    if not n or "notindexed" in n: return "parent"
    if OTHER.search(n): return "other"
    if OURS.search(n):  return "ours"
    return "unclear"

reg = load("register.json")
rows = reg if isinstance(reg, list) else reg.get("rows", reg)
leads = [r for r in rows if r.get("st") == "lead"]

by = collections.Counter(klass(r.get("sp")) for r in leads)
mine = [r for r in leads if klass(r.get("sp")) in ("ours", "parent")]
work = [r for r in mine if r.get("o") and r.get("pl")]
part = [r for r in mine if r.get("o") and not r.get("pl")]
none = [r for r in mine if not r.get("o")]

films = {}
pb = load("parishbooks.json")
for parish, books in (pb.get("links") or {}).items(): films[parish] = len(books)
for store, key in [("dalmatia-books.json","parishes"), ("kvarner-books.json","parishes")]:
    for p in load(store).get(key, []): films[p["name"]] = len(p.get("films") or [])
def filmFor(pl):
    if pl in films: return films[pl]
    for k, v in films.items():
        if norm(k) == norm(pl) or norm(k).startswith(norm(pl)): return v
    return 0

parishes = []
for pl, n in collections.Counter(r["pl"] for r in work).most_common():
    parishes.append({"parish": pl, "n": n, "films": filmFor(pl),
                     "who": [{"n": r["n"], "y": r.get("y"), "o": r.get("o", [])[:2], "id": r["id"]}
                             for r in work if r["pl"] == pl][:40]})

d = {
 "heading": "The leads, sorted into something a person can act on",
 "lead": ("The Register holds **1,508 indexed records** and calls **1,153** of them leads. Read as one number that is "
          "paralysing and it is also wrong, because **most of those rows are not this surname.**"),
 "counts": {"leads": len(leads), "other": by["other"], "parent": by["parent"],
            "ours": by["ours"], "unclear": by["unclear"],
            "work": len(work), "part": len(part), "none": len(none)},
 "rows": [
  ["another family entirely", by["other"],
   "**Francetich, Franchini, Franceschini, Franceskini.** The archive's own rule has always excluded these; nobody had "
   "counted how much of the lead pile they were. **They are almost half of it.**"],
  ["indexed under the father's surname only", by["parent"],
   "The child is entered by forename and the only surname in the record is the father's. These are real and they are "
   "the way into the early parish books — but they cannot be searched by name, only read."],
  ["this surname, plainly", by["ours"], "Spelled as one of the forms this archive accepts."],
  ["unclear", by["unclear"], "A spelling that is neither obviously ours nor obviously another family's. Each needs an eye."],
 ],
 "parishes": parishes,
 "close": ("**One hundred and forty-five rows carry both the parents and the parish**, which is everything needed to "
           "open a book and look. That is the worklist. **Forty-five of them are at Vodnjan — a parish with no film "
           "at all**, so those forty-five are a letter to Pazin and not an afternoon at a screen."),
 "source_leads": "Computed from register.json by scripts/build-leads.py, 14 September 2026.",
}
json.dump(d, io.open(os.path.join(DATA, "leads.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(d["counts"], indent=1))
print("parishes on the worklist:", len(parishes))
print("top:", [(p["parish"], p["n"], p["films"]) for p in parishes[:8]])
