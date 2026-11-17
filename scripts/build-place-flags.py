#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The flag table for places named in the corrections' prose (kit/docs/corrections.md, "Places and shared names").

    python3 scripts/build-place-flags.py            # write site/src/data/place-flags.json
    python3 scripts/build-place-flags.py --check    # fail if the committed file is not what the kit makes from places.json (CI)

The kit's placeflags.py works out, for each place this archive has a page for (site/src/data/places.json), the flag of the state that held it in
each year (the era snapshot, the kit's regime table) and today's flag. src/pages/corrections.astro hands the table to the kit's placeIndex(),
which links a place named in a correction to /places/<slug>/ and draws the era flag only where the sentence names ONE year the snapshot assesses.
Nothing is decided here: the era flag, today's flag and every silence are the kit's. The archive's own answers are the two files the ribbon flags
already use: flag-places.json (a place's name as the era table prints it) and flag-countries.json (today's country where the kit's table is silent).
It reads places.json and never writes it. No name index is built here or at render time (David, 18 Nov 2026).
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
TOOL = os.path.join(ROOT, "site", "node_modules", "@daviddef", "archive-kit", "kit", "tools", "placeflags.py")
OUT = os.path.join(DATA, "place-flags.json")


def make():
    if not os.path.exists(TOOL):
        sys.exit("build-place-flags: the kit's placeflags.py is not installed (npm install in site/)")
    places = json.load(open(os.path.join(DATA, "places.json"), encoding="utf-8"))
    rows = [{"name": p["name"], "aliases": list((p.get("alt") or {}).values())} for p in places if p.get("name")]
    with tempfile.TemporaryDirectory() as tmp:
        pf, out = os.path.join(tmp, "place-rows.json"), os.path.join(tmp, "place-flags.json")
        json.dump(rows, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run([sys.executable, TOOL, "--snapshot", os.path.join(DATA, "era-snapshot.json"), "--places", pf,
                            "--alias", os.path.join(DATA, "flag-places.json"), "--countries", os.path.join(DATA, "flag-countries.json"),
                            "--out", out], capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            sys.exit("build-place-flags: the kit's placeflags.py failed (exit %d)" % r.returncode)
        print(r.stdout.strip())
        return open(out, encoding="utf-8").read()


if __name__ == "__main__":
    text = make()
    if "--check" in sys.argv:
        have = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != text:
            sys.exit("build-place-flags: site/src/data/place-flags.json is stale; run scripts/build-place-flags.py")
        print("build-place-flags: place-flags.json is current")
    else:
        open(OUT, "w", encoding="utf-8").write(text)
