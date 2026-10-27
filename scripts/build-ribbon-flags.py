#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The mini flags on the ribbon cards: the story's ribbon and the family ribbons (kit/docs/ribbon-flags.md; David, 27 October 2026).

    python3 scripts/build-ribbon-flags.py              # write site/src/data/story-flags.json and family-flags.json
    python3 scripts/build-ribbon-flags.py --check      # fail if either is not what the ribbons, the snapshot and the kit make (CI)
    python3 scripts/build-ribbon-flags.py --report     # every place line of every ribbon: what it draws and, where nothing, why

WHY A FILE OF ITS OWN. The kit's generator (kit/tools/ribbonflags.py) writes `flags` onto a kit story's ribbon cards. This archive's
story is its own (src/pages/story.astro over src/data/story-book.json), so its ribbon is first put in the kit's card shape by the
same function that feeds the direct-line gates (scripts/build-direct-line.py, kit_story), and the KIT's generator then writes the
flags onto those cards: site/src/data/story-flags.json, committed, never typed. story.astro draws card n's flags with the kit's own
FlagMini (the same markup and classes as the kit's StoryRibbon) and stops the build if the two ribbons ever disagree.

WHY THE FAMILY RIBBONS' FLAGS ARE NOT IN family-lines.json. The kit's generator would write them there, but the kit's own family
ribbon gate (checkfamilyribbon.py F0, kit 1fa6b54) holds family-lines.json to kit/data/family-ribbon-schema.json, which does not
know a card's `flags` and fails every flagged card. So family-lines.json stays exactly what scripts/build-family-lines.py makes,
and the flags go to site/src/data/family-flags.json: the same families and cards (the kit's family-lines shape, so the kit's
checkribbonflags.py reads it as it is) with the kit generator's `flags`. src/components/FamilyBand.astro hands the kit's
FamilyRibbon each card with its flags, and stops the build if the two files ever disagree on a card.

THE ARCHIVE'S OWN ANSWERS, each with its evidence in the file:
  site/src/data/flag-countries.json   today's country of a place the kit's table cannot place (--countries); null: two countries
  site/src/data/flag-places.json      a card's place text -> the place as the era table prints it (--alias)
Nothing else is decided here: the era flag, today's flag and every silence are the kit's (era snapshot, regime table, place table).
"""
import argparse, importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "src", "data")
KIT_TOOLS = os.path.join(SITE, "node_modules", "@daviddef", "archive-kit", "kit", "tools")
GENERATOR = os.path.join(KIT_TOOLS, "ribbonflags.py")
SNAPSHOT = os.path.join(DATA, "era-snapshot.json")
COUNTRIES = os.path.join(DATA, "flag-countries.json")
ALIAS = os.path.join(DATA, "flag-places.json")
OUT = os.path.join(DATA, "story-flags.json")
OUT_FAMILY = os.path.join(DATA, "family-flags.json")
FAMILY_LINES = os.path.join(DATA, "family-lines.json")
NOTE = ("Made by scripts/build-ribbon-flags.py: the story's ribbon (story-book.json) in the kit's card shape, with the flags the kit's "
        "ribbonflags.py gives each card (kit/docs/ribbon-flags.md). Drawn by src/pages/story.astro with the kit's FlagMini. Do not edit by hand.")
NOTE_FAMILY = ("Made by scripts/build-ribbon-flags.py: the families and cards of family-lines.json with the flags the kit's ribbonflags.py "
               "gives each card (kit/docs/ribbon-flags.md); kept apart because the kit's family-ribbon schema does not know `flags`. "
               "Drawn by src/components/FamilyBand.astro through the kit's FamilyRibbon. Do not edit by hand.")


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def with_flags(story=None, families=None, report=None):
    """Run the kit's generator (--write) on copies of the documents; -> (story, families) with each card's `flags` set or removed."""
    if not os.path.exists(GENERATOR):
        sys.exit("build-ribbon-flags: the kit's ribbonflags.py is not installed (npm install in site/)")
    with tempfile.TemporaryDirectory() as tmp:
        args = [sys.executable, GENERATOR, "--snapshot", SNAPSHOT, "--countries", COUNTRIES, "--alias", ALIAS, "--write"]
        paths = {}
        for key, doc in (("story", story), ("family-lines", families)):
            if doc is None:
                continue
            paths[key] = os.path.join(tmp, key + ".json")
            open(paths[key], "w", encoding="utf-8").write(dump(doc))
            args += ["--" + key, paths[key]]
        if report:
            args += ["--report", report]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            sys.exit("build-ribbon-flags: the kit's ribbonflags.py failed (exit %d)" % r.returncode)
        out = {k: json.load(open(p, encoding="utf-8")) for k, p in paths.items()}
        return out.get("story"), out.get("family-lines"), r.stdout


def story_cards():
    dl = _module(os.path.join(ROOT, "scripts", "build-direct-line.py"), "build_direct_line")
    book = json.load(open(os.path.join(DATA, "story-book.json"), encoding="utf-8"))
    story = dl.kit_story(book)
    story["_note"] = NOTE
    return story


def family_cards():
    fl = json.load(open(FAMILY_LINES, encoding="utf-8"))
    return {"_note": NOTE_FAMILY, "families": [{"id": f["id"], "cards": f.get("cards") or []} for f in fl["families"]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true", help="print every place line of the story and the family ribbons")
    a = ap.parse_args()
    story, fams, text = with_flags(story_cards(), family_cards())
    if a.report:
        print(text, end="")
        return 0
    ns = sum(len(c.get("flags") or []) for c in story["ribbon"]["cards"])
    nf = sum(len(c.get("flags") or []) for f in fams["families"] for c in f["cards"])
    said = "story-flags.json (%d cards, %d flags) and family-flags.json (%d families, %d flags)" % (len(story["ribbon"]["cards"]), ns, len(fams["families"]), nf)
    if a.check:
        bad = 0
        for path, doc in ((OUT, story), (OUT_FAMILY, fams)):
            have = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if have != dump(doc):
                print("build-ribbon-flags: %s is not what the ribbons, the era snapshot and the kit make; run scripts/build-ribbon-flags.py"
                      % os.path.relpath(path, ROOT))
                bad += 1
        if bad:
            return 1
        print("build-ribbon-flags: " + said + " are the ribbons with the kit's flags")
        return 0
    open(OUT, "w", encoding="utf-8").write(dump(story))
    open(OUT_FAMILY, "w", encoding="utf-8").write(dump(fams))
    print("build-ribbon-flags: wrote " + said)
    return 0


if __name__ == "__main__":
    sys.exit(main())
