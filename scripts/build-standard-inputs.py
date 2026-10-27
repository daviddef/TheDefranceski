#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write the two files the linking standard's gate needs besides site/standard.json (kit/docs/linking-standard.md).

    python3 scripts/build-standard-inputs.py            write private/standard/given.json and private/standard/plate-aliases.json
    python3 scripts/build-standard-inputs.py --check    write nothing; exit 1 if either file differs from what the data gives

Both are made from COMMITTED data only (site/src/data/roster.json and plates.json), so a CI runner builds exactly what David's
machine does; both go to private/standard/, which is gitignored, and are rebuilt on every run (the same way the names index is).

given.json        the first word of every roster name of two words or more: the given-name vocabulary L2 and L5 need
                  (the kit takes every word but the last of an INDEX name as a given name; the roster has many more).
plate-aliases.json  {thumbnail file stem: [scan keys]}: the plates' file names carry no locator (DAPA image id, FamilySearch waypoint and
                  frame, FamilySearch image ark), so the key of each plate is read from the holder line and the caption of its
                  entry in plates.json, in the same words the narrative pages cite it by. The keys are the ones the
                  citation patterns of standard.json build (`dapa m0...`, `wp 9R.. fN`, `ark ....-...-...`). A plate that
                  carries no locator (a photograph, a headstone, a card) has no alias and no key.
"""
import json
import os
import re
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(ROOT, "private", "standard")

DAPA = re.compile(r"\b(M0\d{7})\b")
WPF = re.compile(r"\b(9R[0-9A-Z]{2}-[0-9A-Z]{3})\b[^.;]{0,60}?\b(?:frame|image)\s+(\d+)", re.I)
ARK = re.compile(r"\b3:1:([A-Z0-9]{4}-[A-Z0-9]{3,4}-[A-Z0-9]{3,4}(?:-[A-Z0-9]{1,4})?)")


def _bni():
    spec = importlib.util.spec_from_file_location("bni", os.path.join(HERE, "build-names-index.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def given_names():
    bni = _bni()
    with open(os.path.join(DATA, "roster.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    out = set()
    for r in rows:
        w = bni.base_name(r.get("name")).split()
        if len(w) >= 2:
            out.add(w[0])
    return sorted(out)


def plate_aliases():
    with open(os.path.join(DATA, "plates.json"), encoding="utf-8") as f:
        plates = json.load(f)
    out = {}
    for p in plates:
        t = "%s %s" % (p.get("holder") or "", p.get("caption") or "")
        hits = []
        for m in DAPA.finditer(t):
            hits.append((m.start(), "dapa %s" % m.group(1).lower()))
        for m in WPF.finditer(t):
            hits.append((m.start(), "wp %s f%s" % (m.group(1).lower(), m.group(2))))
        for m in ARK.finditer(t):
            hits.append((m.start(), "ark %s" % m.group(1).lower()))
        hits.sort()
        if not hits:
            continue
        # the FIRST locator the entry quotes keys the plate (a plate that also mentions a second image for comparison is the
        # first one's); an ark and a waypoint-and-frame in the same entry name one image, so both are kept when they sit together
        keys = []
        first = hits[0][0]
        for pos, k in hits:
            if pos == first or (k.startswith(("ark", "wp")) and hits[0][1].startswith(("ark", "wp"))):
                if k not in keys:
                    keys.append(k)
        # the pages show a plate by its THUMBNAIL (<plate id>-t.webp), and the gate looks a plate up by the file name it finds
        out[os.path.splitext(os.path.basename(p["thumb"]))[0]] = keys
    return out


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv):
    files = {"given.json": dumps(given_names()), "plate-aliases.json": dumps(plate_aliases())}
    if "--check" in argv:
        bad = 0
        for n, s in files.items():
            p = os.path.join(OUT, n)
            if not os.path.exists(p) or open(p, encoding="utf-8").read() != s:
                print("build-standard-inputs: %s is missing or stale" % n)
                bad = 1
        return bad
    os.makedirs(OUT, exist_ok=True)
    for n, s in files.items():
        with open(os.path.join(OUT, n), "w", encoding="utf-8") as f:
            f.write(s)
    print("build-standard-inputs: %d given names, %d plates keyed" % (len(json.loads(files["given.json"])),
                                                                    len(json.loads(files["plate-aliases.json"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
