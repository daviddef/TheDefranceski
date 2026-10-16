#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The prose gate for living people: run the kit's checkprose.py over what this archive's authors type.

    python3 ../scripts/check-prose.py                  # from site/ (what `npm run check:prose` and the build run)
    python3 ../scripts/check-prose.py --require-tree   # a run without the tree is a FAILURE, even in CI

checkprose.py (kit/tools) fails when a hand-written page, a hand-edited data file or a note puts a year, a date or
a life-event word beside a living person's name, or when a JSON record naming a living person carries a field
beyond the standard (name, relationships, full town and country). check-living-v2.py guards the BUILT pages and
the generated data; this guards what somebody typed.

THE FEED. Who is living is the archive's question, answered by scripts/build-checkprose-feed.py with the kit's
living_rule.py over David's MyHeritage tree. The feed holds names, so it lives in private/ (gitignored) or at
$CHECKPROSE_FEED, and is rebuilt on every run so it is never stale.

EXIT CODES. 0 passed. 1 failed. 2 NOT RUN: the tree is not on this machine, so nobody can say who is living,
and "cannot say" is not "nobody is". On David's machine that stops the build. In CI (the environment variable CI
is set: GitHub Actions sets it) the build goes on and the log says, in capitals, that this gate did not run;
--require-tree turns that into a failure there too, as it does for check-living-v2.py.

WHICH FILES (see HAND_EDITED and GENERATED below). The kit reads, by default, site/src/pages, site/src/content,
notes/, docs/ and the top-level markdown; this adds the hand-EDITED data files and the components and layouts
(a sentence can be typed there). A data file that is in neither list FAILS the gate, so that a new file has to be
classified by someone who knows whether a person edits it or a script writes it.

SPEED. The kit's scan is quadratic in the number of living phrases (it folds each block once per phrase), and
this archive's tree has some 900. So the feed is first narrowed to the living people one of whose phrases occurs
at all in the files the kit will read (an exact, sound narrowing: a phrase absent from every file cannot match),
and the kit scans with those. The summary says how many were kept.
"""
import os, sys, re, io, json, glob, html, argparse, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "site")
KIT_TOOLS = os.path.join(SITE, "node_modules", "@daviddef", "archive-kit", "kit", "tools")
CHECKPROSE = os.path.join(KIT_TOOLS, "checkprose.py")
ALLOW = os.path.join(ROOT, "checkprose-allow.json")
DATA = "site/src/data"

# Data files a person edits (or a person's session appends to). Each is read by the gate.
HAND_EDITED = {
    "america.json", "ancestors.json", "antenati-catalogue.json", "arrivals.json", "art-src.json",
    "atlas-seed.json", "atsea.json", "austria.json", "carlo.json", "carnia.json", "carnia-books.json",
    "cheryl.json", "clusters.json", "collections-walk.json", "corrections.json", "corsica.json",
    "crikvenica.json", "dalmatia-books.json", "decrees.json", "diaspora.json", "dna.json", "eleven.json",
    "errands.json", "families.json", "familysearch.json", "famphotos.json", "findmypast.json",
    "findmypast-map.json", "fiume.json", "fsrecords.json", "gaps.json", "giornaletto.json", "gists.json",
    "givennames-forms.json", "gologorica_roots.json", "hda1448.json", "imotski.json", "imperial.json",
    "istria-outline.json", "istriasweep.json", "jbaptista.json", "josip1863.json", "julius.json",
    "kalanj.json", "kobler.json", "kvarner-books.json", "landmarks.json", "library.json", "lines.json",
    "listria.json", "liznjan.json", "marriages.json", "marriedin.json", "maternal.json", "matricula.json",
    "method.json", "migration.json", "mymap-page.json", "namefold.json", "namefold-extra.json",
    "namesakes.json", "notables.json", "oldsite.json", "omis.json", "parishbooks.json", "parishmap.json",
    "people.json", "pfullingen.json", "places.json", "portraits.json", "pressures.json", "provenance.json",
    "questions.json", "reads.json", "regions.json", "register.json", "registers.json", "ribbon.json",
    "rivers.json", "searched.json", "seget.json", "seget-voce.json", "senjline.json", "shots.json",
    "sources.json", "sovereignty.json", "spines.json", "story.json", "sweep.json", "trees.json",
    "trentino.json", "triage.json", "valentino.json", "vodnjan.json", "walk.json", "waypoints.json",
    "worklist.json", "y1948.json",
}

# Data files a script writes. Their generator's own scrub gate (check-living-v2.py, checkliving.py,
# check-evidence.py ...) is the guard; scanning them here would only meet the homonyms of a family that
# reuses its names, and a fix would be undone by the next run of the generator.
GENERATED = {
    "atlas.json", "burials.json", "changes.json", "directline.json", "directline-pids.json",
    "dossiers.json", "elsewhere.json", "explorer.json", "fs-elsewhere.json", "givennames.json",
    "gologorica-toc.json", "gologorica.json", "graves.json", "gravesmap.json", "households.json",
    "leads.json", "lineages.json", "map.json", "movements.json", "mymap.json", "names.json",
    "onename.json", "plates.json", "reconcile.json", "researchmap.json", "roster.json", "searchindex.json",
}

# Prose that is typed outside src/pages and notes/*.md: components and layouts (a sentence can be typed there),
# the letters and requests the archive writes to record offices, and the plain-text outbox.
EXTRA_INCLUDE = ["site/src/components/**/*.astro", "site/src/layouts/**/*.astro", "requests/**/*.md",
                 "out/**/*.md", "notes/**/*.txt", "docs/**/*.html"]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tracked_data_files():
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", DATA], capture_output=True, text=True)
    return sorted(os.path.basename(f) for f in r.stdout.split("\0") if f)


def classify():
    """Return (include list, problems)."""
    names = tracked_data_files()
    problems = []
    unclassified = [n for n in names if n not in HAND_EDITED and n not in GENERATED]
    for n in unclassified:
        problems.append("%s/%s is in neither HAND_EDITED nor GENERATED in scripts/check-prose.py: say whether "
                        "a person edits it or a script writes it" % (DATA, n))
    for n in sorted((HAND_EDITED | GENERATED) - set(names)):
        problems.append("scripts/check-prose.py lists %s/%s, which is not a tracked file" % (DATA, n))
    both = HAND_EDITED & GENERATED
    for n in sorted(both):
        problems.append("%s is listed as both hand-edited and generated" % n)
    return ["%s/%s" % (DATA, n) for n in sorted(HAND_EDITED)], problems


def strings_of(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            strings_of(v, out)
    elif isinstance(node, list):
        for v in node:
            strings_of(v, out)


def narrow(cp, feed, files):
    """Keep only the living people one of whose phrases occurs in the text of `files`. Sound: a phrase that
    occurs in none of the files cannot match in the kit's scan, which reads the same files."""
    corpus = []
    for rel in files:
        try:
            raw = io.open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        text = None
        if rel.endswith(".json"):
            try:
                out = []
                strings_of(json.loads(raw), out)
                text = "\n".join(out)
            except ValueError:
                text = None
        if text is None:
            text = html.unescape(raw)
        corpus.append(re.sub(r"\s+", " ", cp.fold_keep(text)))
    blob = "\n".join(corpus)
    kept = []
    for p in feed["living"]:
        if any(ph in blob for ph in cp.phrases(p.get("names", []))):
            kept.append(p)
    return dict(feed, living=kept)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--require-tree", action="store_true",
                    help="a run without the tree (nobody can say who is living) fails even in CI")
    ap.add_argument("--feed", help="where to write the feed (default: $CHECKPROSE_FEED or private/checkprose-feed.json)")
    ap.add_argument("--gedcom")
    a = ap.parse_args(argv)

    if not os.path.exists(CHECKPROSE):
        print("checkprose: FAIL, the kit has no checkprose.py at %s (pin the kit at 575409a or later)" % CHECKPROSE)
        return 1
    include, problems = classify()
    if problems:
        print("checkprose: FAIL (%d)" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1

    fb = load_module(os.path.join(HERE, "build-checkprose-feed.py"), "build_checkprose_feed")
    feed, stats = fb.build(a.gedcom)
    if feed is None:
        in_ci = bool(os.environ.get("CI")) and not a.require_tree
        print("checkprose: NOT RUN (%s). The prose gate could not say who is living, so it checked nothing; "
              "this is not a pass." % stats)
        if in_ci:
            print("checkprose: not run in CI, as check-living-v2 does not run its tree checks there; it runs "
                  "wherever the tree is (David's machine)")
            return 0
        return 2

    cp = load_module(CHECKPROSE, "kit_checkprose")
    files, untracked = cp.list_files(ROOT, cp.DEFAULT_INCLUDE + include + EXTRA_INCLUDE, cp.DEFAULT_EXCLUDE, True)
    small = narrow(cp, feed, files)
    out = fb.feed_path(a.feed)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    run_feed = os.path.join(os.path.dirname(os.path.abspath(out)), "checkprose-feed.run.json")
    for path, data in ((out, feed), (run_feed, small)):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    print("checkprose: feed has %d living people (%d names) and %d dead names; %d living people have a phrase in "
          "the %d files the kit will read, and the kit scans for those" % (
              len(feed["living"]), sum(len(x["names"]) for x in feed["living"]), len(feed["deadNames"]),
              len(small["living"]), len(files)))
    cmd = [sys.executable, CHECKPROSE, "--root", ROOT, "--feed", run_feed]
    for inc in include + EXTRA_INCLUDE:
        cmd += ["--include", inc]
    if os.path.exists(ALLOW):
        cmd += ["--allow", ALLOW]
    try:
        r = subprocess.run(cmd)
    finally:
        try:
            os.remove(run_feed)
        except OSError:
            pass
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
