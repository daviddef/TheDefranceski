#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the feed the kit's prose gate (kit/tools/checkprose.py) reads: who is living, and who is dead.

    python3 scripts/build-checkprose-feed.py                # writes private/checkprose-feed.json
    python3 scripts/build-checkprose-feed.py --out PATH     # or $CHECKPROSE_FEED
    python3 scripts/build-checkprose-feed.py --counts       # counts only, writes nothing

The feed holds living people's NAMES, so it is never committed: it is written under private/ (gitignored),
or wherever $CHECKPROSE_FEED / --out says, and the file is created readable by its owner only. This script
prints COUNTS only, never a name.

    {"living":    [{"id": "<opaque tree id>", "names": ["Given Family", ...]}, ...],
     "deadNames": ["Given Family", ...]}

WHO IS LIVING is not decided here. It is the archive's one definition, scripts/living_v2.py over the kit's
living_rule.py, applied to David's MyHeritage tree (the only place a living person's birth year exists):

  * every person in the tree the rule calls living (80 or younger, no death or burial recorded, no public
    source; no birth year is NOT living);
  * every possible minor (an undated person with a living parent). They are held out of the archive
    altogether, so any date or detail beside such a name in a hand-written page is as wrong as for a living one;
  * every roster row the archive publishes as living (the roster's `living` flag), whatever spelling the roster
    uses, for the day the tree cannot match a row.

Every recorded spelling of a living person goes in: the GEDCOM name, given names with the surname, with the
married name (_MARNM), with a nickname, a former name, an alias.

WHO IS DEAD is decided by IDENTITY, never by "every name that is not a living name" (a living person and an
ancestor who share a name would then cancel each other out of the corpus; the kit skips and counts a name both
have, it does not guess). Dead names come from the archive's own dead rows:

  * every roster row that is not flagged living (name);
  * the dossier record of each such row (dossiers.json "persons", keyed by the row's pid): its name, and the
    names in its family tree strip that carry a pid of another dead row;
  * the spellings the archive records for a dead row's name page (dossiers.json "people", alsoWritten), taken
    only when no living row sits under the same name page.

Without the tree this script writes nothing and exits 2: "cannot say who is living" is not "nobody is".
"""
import os, sys, re, io, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_v2 as L2                       # the archive's adapter to the kit's living_rule.py

ROOT = L2.ROOT
DATA = os.path.join(ROOT, "site", "src", "data")
DEFAULT_FEED = os.path.join(ROOT, "private", "checkprose-feed.json")


def feed_path(explicit=None):
    return explicit or os.environ.get("CHECKPROSE_FEED") or DEFAULT_FEED


def _json(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _clean(n):
    n = re.sub(r"\s+", " ", str(n or "").replace("/", " ")).strip()
    return n


def tree_names(rec, g):
    """Every recorded spelling of one tree person, as plain 'Given Family' strings."""
    out = set()
    for nm in (x for x in rec["sub"] if x["tag"] == "NAME"):
        out.add(_clean(nm["val"]))
        sub = {}
        for y in nm["sub"]:
            sub.setdefault(y["tag"], []).append(_clean(y["val"]))
        given = (sub.get("GIVN") or [""])[0]
        surnames = (sub.get("SURN") or []) + sub.get("_MARNM", []) + sub.get("_FORMERNAME", []) \
            + sub.get("_AKA", []) + sub.get("_RNAME", [])
        for s in surnames:
            if given and s:
                out.add(given + " " + s)
        for nick in sub.get("NICK", []):
            for s in (sub.get("SURN") or []) + sub.get("_MARNM", []):
                if nick and s:
                    out.add(nick + " " + s)
        for alias in sub.get("_AKA", []) + sub.get("_FORMERNAME", []) + sub.get("_RNAME", []):
            if " " in alias:
                out.add(alias)
    return sorted(n for n in out if " " in n)


def who_slug(href):
    m = re.search(r"/who/([^/]+)/?", href or "")
    return m.group(1) if m else None


def build(gedcom=None, year=None):
    """Return (feed, stats), or (None, reason) when the tree is not on this machine."""
    path = L2.gedcom_path(gedcom)
    if not path:
        return None, "the MyHeritage tree is not on this machine (set ARCHIVE_GEDCOM)"
    year = year or L2.THIS_YEAR
    g = L2._gedcom_module()
    tree = L2.load_tree(path)
    if len(tree.people) < 1000:
        return None, "the tree has %d people; refusing to decide who is living from that" % len(tree.people)
    recs = {}
    for r in g.parse(path):
        if r["tag"] == "INDI":
            recs[g.val(r, "_UID") or r["id"]] = r

    roster = _json("roster.json")["rows"]
    ledger = L2.load_ledger()
    uid_of_pid = ledger.get("people", {})

    living = {}                                     # uid or pid -> set of names
    stats = {"tree living": 0, "tree possible minors": 0, "roster living rows": 0,
             "roster living rows with no tree person": 0}
    for uid, p in tree.people.items():
        is_l, is_minor = tree.verdict(uid, year)
        if is_l or is_minor:
            stats["tree living" if is_l else "tree possible minors"] += 1
            living.setdefault(uid, set()).update(tree_names(recs[uid], g) if uid in recs else [])
            living[uid].add(_clean(p["name"]))
    for r in roster:
        if not r.get("living"):
            continue
        stats["roster living rows"] += 1
        uid = uid_of_pid.get(r.get("pid"))
        key = uid if uid in tree.people else "roster:" + str(r.get("pid"))
        if key.startswith("roster:"):
            stats["roster living rows with no tree person"] += 1
        living.setdefault(key, set()).add(_clean(r.get("name")))
    living_rows = [r for r in roster if r.get("living")]
    living_who = {who_slug(r.get("who") or r.get("href")) for r in living_rows} - {None}

    # ---- the dead, by identity ----
    dead_rows = [r for r in roster if not r.get("living")]
    dead_pids = {r["pid"] for r in dead_rows if r.get("pid")}
    dead = {_clean(r.get("name")) for r in dead_rows}
    stats["roster dead rows"] = len(dead_rows)
    dos = _json("dossiers.json")
    persons = dos.get("persons", {})

    def strip_names(node):
        if isinstance(node, dict):
            if node.get("pid") in dead_pids and node.get("n"):
                yield node["n"]
            for v in node.values():
                yield from strip_names(v)
        elif isinstance(node, list):
            for v in node:
                yield from strip_names(v)

    for pid in dead_pids:
        d = persons.get(pid)
        if not d:
            continue
        dead.add(_clean(d.get("name")))
        pt = d.get("ptree")
        if isinstance(pt, str):
            try:
                pt = json.loads(pt)
            except ValueError:
                pt = None
        dead.update(_clean(n) for n in strip_names(pt))
    named_pages = dos.get("people", {})
    for r in dead_rows:
        slug = who_slug(r.get("who"))
        if not slug or slug in living_who:
            continue
        for a in (named_pages.get(slug) or {}).get("alsoWritten", []) or []:
            dead.add(_clean(a.get("name")))
    dead = sorted(n for n in dead if n)

    feed = {"living": [{"id": k, "names": sorted(v)} for k, v in sorted(living.items()) if v],
            "deadNames": dead}
    stats.update({"living people in the feed": len(feed["living"]),
                  "living names": sum(len(x["names"]) for x in feed["living"]),
                  "dead names": len(dead)})
    sys.path.insert(0, os.path.join(ROOT, "site", "node_modules", "@daviddef", "archive-kit", "kit", "tools"))
    try:
        import checkprose as cp
        lp, dp = set(), set()
        for x in feed["living"]:
            lp |= cp.phrases(x["names"])
        for n in dead:
            dp |= cp.phrases([n])
        stats["living phrases"] = len(lp)
        stats["living phrases shared with a dead person (skipped by the gate)"] = len(lp & dp)
    except ImportError:
        pass
    return feed, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the living / dead name feed for checkprose.py (counts only are printed).")
    ap.add_argument("--out")
    ap.add_argument("--gedcom")
    ap.add_argument("--counts", action="store_true", help="print counts, write nothing")
    ap.add_argument("--year", type=int, default=L2.THIS_YEAR)
    a = ap.parse_args(argv)
    feed, stats = build(a.gedcom, a.year)
    if feed is None:
        print("build-checkprose-feed: not run: %s" % stats)
        return 2
    if not feed["living"] or not feed["deadNames"]:
        print("build-checkprose-feed: FAIL, %d living, %d dead names; refusing to write a feed that could pass on nothing" % (
            len(feed["living"]), len(feed["deadNames"])))
        return 1
    for k, v in stats.items():
        print("  %-62s %d" % (k, v))
    if a.counts:
        return 0
    out = feed_path(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False)
    print("build-checkprose-feed: wrote %s (names inside; not for commit)" % os.path.relpath(out, ROOT)
          if out.startswith(ROOT) else "build-checkprose-feed: wrote the feed outside the repo (names inside)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
