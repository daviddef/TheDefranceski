#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The records table: site/src/data/records.json, made from the data the archive already holds. Nothing is composed from a guess.

    python3 scripts/build-records.py            write site/src/data/records.json
    python3 scripts/build-records.py --check    write nothing; exit 1 if the committed file differs from what the data gives, or a passage
                                                names an image beside an ark that opens the volume's first image
    python3 scripts/build-records.py --self-test plant that fault in a made-up folder; it must be caught

WHAT IT HOLDS (the linking standard, L3: kit/docs/linking-standard.md; the Rec link: src/lib/md.js `[words](rec:ID)`):
  antenati-<ark>   every volume of site/src/data/antenati-catalogue.json (the Carnia civil registers at the Archivio di Stato di
                   Udine, 74 volumes): its address is the catalogue's own `base` + the ark, exactly as /antenati/ links it.
  fs-<ark>         a FamilySearch IMAGE ark that a research narrative writes in the form `3:1:XXXX-XXXX-XXXX`: its address is
                   https://www.familysearch.org/ark:/61903/3:1:<ark>, the pattern every FamilySearch link in this archive uses.
                   Only arks that appear in the prose of the twelve narrative pages' own data files are listed (SOURCES below).
Each fs- row says WHICH image its address opens ("image 159 of 174, waypoint 9R2X-BZD"), from site/src/data/fs-images.json, and the
build REFUSES a passage that names image N next to an ark that opens the volume's FIRST image (18 November 2026: seventeen citations
of the corrections page linked "the volume" because the ark copied from a volume's address bar is its first image, and a bare ark ignores
`?i=`; a reader clicked "image 159" and landed on the roll's filming slate). The fix is the per-image ark of the image the passage names.
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
FS_ARK = re.compile(r"`3:1:([A-Z0-9]{4}-[A-Z0-9]{3,4}-[A-Z0-9]{3,4}(?:-[A-Z0-9]{1,4})?)`")  # a fourth segment exists on some volumes (Crikvenica births: ...-R9M9-1)
FS_BASE = "https://www.familysearch.org/ark:/61903/3:1:"
IMAGES = os.path.join(DATA, "fs-images.json")          # ark -> [image number (1-based, as FamilySearch labels it), images in the volume, waypoint]
CLAIM = re.compile(r"\b(?:images?|frames?)\s+((?:\d{1,4}(?:\s*(?:,|and|&|–|-)\s*)?)+)", re.I)   # "image 159", "images 11 and 12", "frames 86–90"


def fs_images():
    if not os.path.exists(IMAGES):
        return {}
    with open(IMAGES, encoding="utf-8") as f:
        return json.load(f)["images"]


def fs_label(ark, images):
    m = images.get(ark)
    if not m:
        return "FamilySearch image 3:1:" + ark
    return "FamilySearch image %d of %d (waypoint %s), 3:1:%s" % (m[0], m[1], m[2], ark)


def volume_links(images):
    """Every passage that names image/frame N beside an ark that opens image 1 of its volume. Returns [(file, ark, claimed, words)]."""
    bad = []
    for fn in SOURCES:
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            text = f.read()
        for m in FS_ARK.finditer(text):
            ark = m.group(1)
            if ark not in images or images[ark][0] != 1:
                continue
            before = text[max(0, m.start() - 170):m.start()].split("\n")[-1]
            after = text[m.end():m.end() + 120].split("\n")[0]
            claimed = sorted({int(n) for c in CLAIM.finditer(before + " " + after) for n in re.findall(r"\d+", c.group(1))} - {1})
            if claimed:
                bad.append((fn, ark, claimed, (before[-70:] + "`" + ark + "`" + after[:50]).strip()))
    return bad


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
    images = fs_images()
    seen = set()
    for fn in SOURCES:
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            text = f.read()
        for m in FS_ARK.finditer(text):
            a = m.group(1)
            if a not in seen:
                seen.add(a)
                out.append({"id": "fs-" + a, "kind": "ark", "label": fs_label(a, images), "url": FS_BASE + a,
                            "key": ["3:1:" + a]})
    out.sort(key=lambda r: r["id"])
    ids = [r["id"] for r in out]
    assert len(ids) == len(set(ids)), "a record id is used twice"
    return out


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1) + "\n"


def self_test():
    """Plant the fault the gate exists for in a made-up data folder and check it is caught, and that the right link passes."""
    import tempfile
    global DATA, SOURCES
    keep = (DATA, SOURCES)
    images = {"AAAA-BBBB-CCCC": [1, 90, "9R00-AAA"], "DDDD-EEEE-FFFF": [12, 90, "9R00-AAA"]}
    cases = [("volume ark beside image 12", "(9R00-AAA, volume [`3:1:AAAA-BBBB-CCCC`](rec:fs-AAAA-BBBB-CCCC), image 12 left)", 1),
             ("volume ark beside frames 86-90", "frames 86-90 of [`3:1:AAAA-BBBB-CCCC`](rec:fs-AAAA-BBBB-CCCC)", 1),
             ("the image's own ark", "(9R00-AAA, image 12 [`3:1:DDDD-EEEE-FFFF`](rec:fs-DDDD-EEEE-FFFF) left)", 0),
             ("the volume cited as a volume", "the volume [`3:1:AAAA-BBBB-CCCC`](rec:fs-AAAA-BBBB-CCCC), 90 images", 0),
             ("the first image named as image 1", "image 1 [`3:1:AAAA-BBBB-CCCC`](rec:fs-AAAA-BBBB-CCCC)", 0)]
    ok = True
    with tempfile.TemporaryDirectory() as d:
        DATA, SOURCES = d, ["t.json"]
        for name, prose, want in cases:
            with open(os.path.join(d, "t.json"), "w", encoding="utf-8") as f:
                json.dump({"x": prose}, f, ensure_ascii=False, indent=1)
            got = len(volume_links(images))
            if got != want:
                print("self-test: %s: wanted %d finding(s), got %d" % (name, want, got)); ok = False
    DATA, SOURCES = keep
    print("build-records self-test: %d cases, %s" % (len(cases), "all as expected" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    doc = {"note": "The records the narrative pages cite, made by scripts/build-records.py from the archive's own data. Link-only: no scan is drawn "
                   "from this table. Do not edit by hand.", "records": rows()}
    s = dumps(doc)
    images = fs_images()
    bad = volume_links(images)
    for fn, ark, claimed, words in bad:
        print("  FAIL  %s: names image %s but 3:1:%s opens image 1 of its volume: ...%s..." % (fn, ", ".join(map(str, claimed)), ark, words))
    if bad:
        print("build-records: %d passage(s) link the VOLUME where they name an image. Link the image's own ark: open the volume at that image in the "
              "viewer, copy the address, read the ark, then record it in site/src/data/fs-images.json." % len(bad))
        return 1
    cited = {r["id"][3:] for r in doc["records"] if r["id"].startswith("fs-")}
    unchecked = sorted(cited - set(images))
    if "--check" in argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != s:
            print("build-records: site/src/data/records.json differs from what the data gives (run scripts/build-records.py)")
            return 1
        print("build-records: ok, %d records; %d of %d FamilySearch arks have a recorded image number%s" % (
            len(doc["records"]), len(cited) - len(unchecked), len(cited), "" if not unchecked else " (the other %d are not checked for the image they open)" % len(unchecked)))
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(s)
    print("build-records: %d records (%d Antenati volumes, %d FamilySearch image arks, %d with a recorded image number)" % (
        len(doc["records"]), sum(1 for r in doc["records"] if r["id"].startswith("antenati-")),
        len(cited), len(cited) - len(unchecked)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
