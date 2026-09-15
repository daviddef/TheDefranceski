#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One rule, shared by every builder that puts a dot on a map.

On 15 September 2026 `build-graves-map.py` was run with `--gaz` pointing at a
directory that had been created by a different session and held none of the
GeoNames dumps. The loader returned an empty dictionary, every place failed to
resolve, and the map was rebuilt with **twenty-three of its sixty-four places**
instead of sixty-four. Nothing complained. The page rendered, every link
resolved, and the archive's own audit passed, because a place with no
coordinate is a perfectly valid record — it just means «we could not place
this», which is a claim about the PLACE and was in fact a claim about the path.

So: a gazetteer that loads nothing is a broken run, not an empty one, and a
builder that places fewer places than it did last time says so before it
writes anything.
"""
import json, os, sys

def require(gaz, gdir, want):
    """Die rather than publish a map built on an empty gazetteer."""
    if len(gaz) >= want:
        return gaz
    sys.stderr.write(
        "\nGAZETTEER EMPTY OR SHORT\n"
        "  --gaz %s\n"
        "  loaded %d entries, expected at least %d.\n"
        "  %s\n"
        "  Nothing has been written. Point --gaz at the directory holding\n"
        "  cities500.txt and the GeoNames country dumps and run it again.\n\n"
        % (gdir or "(not given)", len(gaz), want,
           "That directory does not exist." if gdir and not os.path.isdir(gdir)
           else "The files are not in that directory."))
    raise SystemExit(2)

def guard(path, key, n, label="places"):
    """Compare a count against the last run's and refuse to go backwards.

    `path` is the file the builder is about to overwrite; `key` the dotted path
    to the number inside it. A fall is a hard stop rather than a warning,
    because the whole failure mode here is a number quietly going down while
    everything downstream carries on looking healthy.
    """
    if not os.path.exists(path):
        return
    try:
        d = json.load(open(path, encoding="utf-8"))
        for k in key.split("."):
            d = d[k]
        was = int(d)
    except Exception:
        return
    if n < was:
        sys.stderr.write(
            "\nCOUNT WENT BACKWARDS\n"
            "  %s\n"
            "  %s: was %d, now %d — %d fewer.\n"
            "  Nothing has been written. If the fall is real and intended,\n"
            "  pass --allow-shrink.\n\n" % (path, label, was, n, was - n))
        if "--allow-shrink" not in sys.argv:
            raise SystemExit(3)
    elif n > was:
        sys.stderr.write("  %s: %d -> %d\n" % (label, was, n))
