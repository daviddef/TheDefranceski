#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The records table: site/src/data/records.json, made from the data the archive already holds. Nothing is composed from a guess.

    python3 scripts/build-records.py            write site/src/data/records.json
    python3 scripts/build-records.py --check    write nothing; exit 1 if the committed file differs from what the data gives

WHAT IT HOLDS (the linking standard, L3: kit/docs/linking-standard.md; the Rec link: src/lib/md.js `[words](rec:ID)`):
  antenati-<ark>   every volume of site/src/data/antenati-catalogue.json (the Carnia civil registers at the Archivio di Stato di
                   Udine, 74 volumes): its address is the catalogue's own `base` + the ark, exactly as /antenati/ links it.
  fs-<ark>         a FamilySearch IMAGE ark that a research narrative writes in the form `3:1:XXXX-XXXX-XXXX`: its address is
                   https://www.familysearch.org/ark:/61903/3:1:<ark>, the pattern every FamilySearch link in this archive uses.
                   Only arks that appear in the prose of the twelve narrative pages' own data files are listed (SOURCES below).
No plate is in this table: a plate is linked by its own anchor on the page that shows it (rec:plate-<id>, components/Plates.astro).
There is no row for a DAPA image id (M0xxxxxxx), a film or a frame: the archive holds no public address for them, and none is made up.

Antenati and FamilySearch images are LINK-ONLY: no row carries `plate` or `show` (David's rulings of 18 October 2026: FamilySearch
frames and Antenati scans are never drawn beside a passage unless the archive already shows them). A row about a person who is or
may be living would be flagged `living` and never drawn; there is none, because these rows name volumes and images, not people.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(DATA, "records.json")

# the data files whose prose the narrative pages render (FamilySearch arks are read from these)
SOURCES = ["gologorica.json", "corrections.json", "carnia.json", "liznjan.json", "fiume.json", "valentino.json",
           "jbaptista.json", "lines.json", "seget.json", "pfullingen.json", "carlo.json", "crikvenica.json"]
FS_ARK = re.compile(r"`3:1:([A-Z0-9]{4}-[A-Z0-9]{3,4}-[A-Z0-9]{3,4})`")
FS_BASE = "https://www.familysearch.org/ark:/61903/3:1:"


def rows():
    with open(os.path.join(DATA, "antenati-catalogue.json"), encoding="utf-8") as f:
        cat = json.load(f)
    base = cat["base"]
    out = []
    for c in cat["comuni"]:
        for v in c["volumes"]:
            ark = v["ark"]
            label = "Antenati: %s, %s %s" % (c["name"], v.get("series") or "volume", v.get("year") or "")
            out.append({"id": "antenati-" + ark, "kind": "ark", "label": label.strip(), "url": base + ark, "key": [ark]})
    seen = set()
    for fn in SOURCES:
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            text = f.read()
        for m in FS_ARK.finditer(text):
            a = m.group(1)
            if a not in seen:
                seen.add(a)
                out.append({"id": "fs-" + a, "kind": "ark", "label": "FamilySearch image 3:1:" + a, "url": FS_BASE + a,
                            "key": ["3:1:" + a]})
    out.sort(key=lambda r: r["id"])
    ids = [r["id"] for r in out]
    assert len(ids) == len(set(ids)), "a record id is used twice"
    return out


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    doc = {"note": "The records the narrative pages cite, made by scripts/build-records.py from the archive's own data. Link-only: no scan is drawn "
                   "from this table. Do not edit by hand.", "records": rows()}
    s = dumps(doc)
    if "--check" in argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != s:
            print("build-records: site/src/data/records.json differs from what the data gives (run scripts/build-records.py)")
            return 1
        print("build-records: ok, %d records" % len(doc["records"]))
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(s)
    print("build-records: %d records (%d Antenati volumes, %d FamilySearch image arks)" % (
        len(doc["records"]), sum(1 for r in doc["records"] if r["id"].startswith("antenati-")),
        sum(1 for r in doc["records"] if r["id"].startswith("fs-"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
