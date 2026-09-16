#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find the dots that are in the wrong country.

Checking Carnia by eye turned up six wrong or missing places in thirty, and
checking Istria turned up three more: Prato Carnico on Prato in Tuscany,
Priola in Piedmont, Ledenice in South Bohemia, Ragusa in Sicily. Every one was
found because David asked about a panel. Nobody has looked at the other twelve
hundred.

Two tests, both mechanical, both already used by the builders:

    provider   a place catalogued ONLY by a provider that works one region
               cannot be outside that region
    string     a place whose own name or «also written» carries a country
               cannot be in a different one

Prints what fails. It changes nothing: a wrong coordinate is fixed by naming
the right place, not by a script guessing again.

    python3 scripts/place-audit.py
"""
import json, io, os, re, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

def load(n, d=None):
    p = os.path.join(DATA, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d

# Where each provider actually works, as a generous box. Generous because the
# point is to catch a dot in the wrong COUNTRY, not to quarrel about a valley.
BOX = {
    "fs-it":        (45.4, 47.0, 12.0, 14.0,  "Friuli — the Udine civil registers"),
    "antenati":     (45.4, 47.0, 12.0, 14.0,  "Friuli — the Udine state archive"),
    "dapa":         (44.4, 45.8, 13.2, 14.6,  "Istria — the Pazin state archive"),
    "fs-it-pola":   (44.6, 46.0, 13.2, 14.6,  "Istria, Pola and Trieste"),
    "fs-si-mj":     (46.0, 47.1, 15.8, 16.9,  "Prekmurje and Međimurje"),
    "fs-hr":        (41.8, 46.8, 13.2, 19.6,  "Croatia"),
    "fs-hr-delnice": (45.0, 45.8, 14.2, 15.2, "the Delnice deanery"),
}
# A country named in a place string, and the box it puts the place in.
CTRY = {
    "croatia": (41.8, 46.8, 13.2, 19.6), "hrvatska": (41.8, 46.8, 13.2, 19.6),
    "italia": (35.4, 47.1, 6.5, 18.6),   "italy": (35.4, 47.1, 6.5, 18.6),
    "slovenia": (45.4, 46.9, 13.3, 16.7), "slovenija": (45.4, 46.9, 13.3, 16.7),
    "austria": (46.3, 49.1, 9.5, 17.2),  "osterreich": (46.3, 49.1, 9.5, 17.2),
    "magyarorszag": (45.7, 48.6, 16.1, 22.9), "hungary": (45.7, 48.6, 16.1, 22.9),
    "madarska": (45.7, 48.6, 16.1, 22.9),
    "bosna": (42.5, 45.3, 15.7, 19.6),   "srbija": (42.2, 46.2, 18.8, 23.0),
    "serbia": (42.2, 46.2, 18.8, 23.0),  "serbien": (42.2, 46.2, 18.8, 23.0),
}

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")
def norm(s): return re.sub(r"[^a-z0-9]+", " ", strip(s).lower()).strip()

def inbox(la, lo, b):
    return b[0] <= la <= b[1] and b[2] <= lo <= b[3]

def main():
    rm = load("researchmap.json", {"places": []})
    bad, nocoord = [], []
    for p in rm["places"]:
        la, lo = p.get("lat"), p.get("lon")
        vols = sum(len(sh["books"] or []) for v in p["sources"].values()
                   for sh in v["shelves"].values())
        if la is None:
            if vols:
                nocoord.append((p["name"], vols, sorted(p["sources"])))
            continue
        srcs = {s for s, v in p["sources"].items()
                if any(sh.get("books") for sh in v["shelves"].values())}
        # A place that names its own country has said where it is, and that
        # beats the provider's usual ground: Zemun and Stara Pazova are
        # Serbian parishes in a Croatian collection and are not faults.
        said = " ".join([p["name"]] + list(p.get("alt") or []) + list(p.get("older") or []))
        owncc = [b for w, b in CTRY.items() if re.search(r"\b" + w + r"\b", norm(said))]
        # --- test one: the provider's own ground
        boxes = [BOX[s] for s in srcs if s in BOX]
        if owncc:
            boxes = []
        if boxes and all(s in BOX for s in srcs) and not any(inbox(la, lo, b) for b in boxes):
            bad.append((p["name"], la, lo, vols, "outside " + " / ".join(
                sorted({b[4] for b in boxes})), p.get("geo")))
            continue
        # --- test two: a country the place names itself
        for word, b in CTRY.items():
            if re.search(r"\b" + word + r"\b", norm(said)) and not inbox(la, lo, b):
                bad.append((p["name"], la, lo, vols, "its own name says " + word, p.get("geo")))
                break

    print("PLACES IN THE WRONG PLACE: %d" % len(bad))
    for r in sorted(bad, key=lambda x: -x[3]):
        print("  %-26s %8.3f,%8.3f  %4d vols  %-46s [%s]" % (
            r[0][:26], r[1], r[2], r[3], r[4], r[5]))
    print("\nPLACES WITH VOLUMES AND NO COORDINATES: %d places, %d volumes"
          % (len(nocoord), sum(n for _, n, _ in nocoord)))
    byprov = collections.Counter()
    for _, n, s in nocoord:
        byprov[",".join(s)] += n
    for k, v in byprov.most_common():
        print("   %-24s %4d volumes" % (k, v))
    print()
    for nm, n, s in sorted(nocoord, key=lambda x: -x[1])[:20]:
        print("   %-26s %3d  %s" % (nm[:26], n, ",".join(s)))

if __name__ == "__main__":
    main()
