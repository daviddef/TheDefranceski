#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate for the living-people standard, version 2 (David, 16 October 2026).

    python3 scripts/check-living-v2.py --dist dist            # what CI can run: committed data and the built site
    python3 scripts/check-living-v2.py --dist dist --require-tree   # and David's tree, which only his machine has

THE RULE (one definition, in the kit: kit/tools/living_rule.py, read through scripts/living_v2.py):
living is 80 or younger by year with no death recorded and no public source; no birth year is not living;
a possible minor is held out and not published at all.

WHY THIS READS THE DATA AND NOT THE GENERATOR. scripts/apply-living-rule.py decides who is living and
writes the roster. This file decides again, from the committed roster and from the built pages, and
compares. A generator that is wrong cannot make its own output pass.

WHAT IT REFUSES.
  rule       a row the rule calls living that is published with a birth year, a death year, or no living mark
  scrub      a living row that carries anything beyond name, page address, relationship, and a full town and
             country: a date, a citation, a note, a parish, a tree id, an estimate, an image
  place      a living row whose place is not 'Town, Country' (a street, a number, a hospital, a care home)
  minor      a row whose birth year makes the person under 18 with no death or public source (a child)
  page       a living person's page that is missing, is not noindex, carries structured data, a table, an
             image, or a four-digit year
  name page  a /who/ page whose every bearer is living and is not noindex or names a canonical elsewhere
  sitemap    a living page in the sitemap
  search     a living person in this archive's own search index
  pages      a roster row with no person page
  links      MORE unlinked relatives on living pages than the recorded count (see the ledger)
  tree       (with David's tree) a ledger entry the rule now disagrees with, a possible minor in the roster,
             and any possible minor's FULL NAME anywhere the archive publishes: data, pages, built site
  empty      nothing to examine. A gate that examined zero people has not passed.

Counts only are printed; a name never is.
"""
import os, sys, re, io, json, glob, collections, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_v2 as L2

lr = L2.lr
YEAR = re.compile(r"\b(1[0-9]\d\d|20\d\d)\b")
ALLOWED_KEYS = {"name", "pid", "who", "line", "place", "places", "rel", "me", "mine", "direct", "notable",
                "living", "src", "href", "sameAs", "b", "d", "note", "ark", "mh"}
MUST_BE_EMPTY = ("b", "d", "note", "ark", "mh", "notable")
TAGS = re.compile(r"<[^>]+>")


def rd(p):
    with io.open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()


def main_of(html):
    m = re.search(r"<main\b.*?</main>", html, re.S)
    t = m.group(0) if m else ""
    return re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", t, flags=re.S)


def head_of(html):
    m = re.search(r"<head\b.*?</head>", html, re.S)
    return m.group(0) if m else ""


def load_tree_if_any(args):
    path = L2.gedcom_path(args.gedcom)
    if not path:
        return None, None
    return L2.load_tree(path), path


def corpus_files(root, dist):
    """Everything the archive publishes or commits that could name a person."""
    out = []
    for base, pats in (("site/src/data", (".json",)), ("site/public", (".json", ".txt", ".xml", ".css")),
                       ("site/src/pages", (".astro",)), ("site/src/components", (".astro",)),
                       ("data", (".json", ".tsv", ".csv", ".txt", ".ged")), ("notes", None), ("out", None),
                       ("requests", None), ("docs", None)):
        for r, _, fs in os.walk(os.path.join(root, base)):
            if "/gaz" in r:
                continue
            for f in fs:
                if f in ("living-ledger.json",):
                    continue
                if pats is None or f.endswith(pats):
                    out.append(os.path.join(r, f))
    for f in ("README.md", "CLAUDE.md"):
        if os.path.exists(os.path.join(root, f)):
            out.append(os.path.join(root, f))
    if dist and os.path.isdir(dist):
        for r, _, fs in os.walk(dist):
            for f in fs:
                if f.endswith((".html", ".json", ".xml", ".txt")):
                    out.append(os.path.join(r, f))
    return out


def run(root, dist, tree, year, require_tree=False, verbose=False):
    P = []                                  # problems
    N = []                                  # notes
    S = collections.Counter()
    data = os.path.join(root, "site", "src", "data")
    ros_p = os.path.join(data, "roster.json")
    if not os.path.exists(ros_p):
        return ["empty: no roster at %s" % ros_p], N, S
    rows = json.loads(rd(ros_p))["rows"]
    led = L2.load_ledger() if root == L2.ROOT else _load_json(os.path.join(root, "data", "living-ledger.json"), {"people": {}, "held": []})
    S["rows"] = len(rows)

    # ---------------- the rule, over the committed roster ----------------
    living_rows = [r for r in rows if r.get("living")]
    S["living rows"] = len(living_rows)
    for r in rows:
        pid = r.get("pid", "?")
        if r.get("living"):
            for k, v in r.items():
                if k not in ALLOWED_KEYS and v not in (None, "", [], False):
                    P.append("scrub: a living row carries '%s' (%s)" % (k, pid))
            for k in MUST_BE_EMPTY:
                if r.get(k) not in (None, "", False):
                    P.append("scrub: a living row carries a value in '%s' (%s)" % (k, pid))
            if r.get("deceased"):
                P.append("rule: a row is marked living AND deceased (%s)" % pid)
            lines = list(r.get("places") or []) or ([r["place"]] if r.get("place") else [])
            for line in lines:
                for part in str(line).split("→"):
                    part = part.strip()
                    if part and (re.search(r"\d", part) or L2.place_line(part) != part):
                        P.append("place: a living row's place is not a town and a country: '%s' (%s)" % (
                            "" if re.search(r"\d", part) else "?", pid))
        else:
            if lr.is_living(r.get("b"), L2.row_recorded_dead(r), L2.row_citations(r), year):
                P.append("rule: the rule calls this person living and the row carries a birth year and no living mark (%s)" % pid)
        b = r.get("b")
        if isinstance(b, int) and (year - b) < lr.MINOR_AGE and not L2.row_recorded_dead(r) and not L2.row_citations(r):
            P.append("minor: a row's birth year makes the person under 18, and they are published (%s)" % pid)
    S["pids"] = len({r.get("pid") for r in rows if r.get("pid")})

    # ---------------- the built site ----------------
    if not dist or not os.path.isdir(dist):
        P.append("empty: no built site at %s. Nothing to examine." % dist)
        return P, N, S
    livepids = [r["pid"] for r in living_rows if r.get("pid")]
    persons = sorted(glob.glob(os.path.join(dist, "person", "*", "index.html")))
    S["person pages built"] = len(persons)
    missing = [r["pid"] for r in rows if r.get("pid") and not os.path.exists(os.path.join(dist, "person", r["pid"], "index.html"))]
    for pid in missing[:8]:
        P.append("pages: a person in the roster has no page (%s)" % pid)
    if len(missing) > 8:
        P.append("pages: ... and %d more people with no page" % (len(missing) - 8))

    unlinked = 0
    for r in living_rows:
        pid = r.get("pid")
        f = os.path.join(dist, "person", str(pid), "index.html")
        if not os.path.exists(f):
            continue
        S["living pages examined"] += 1
        h = rd(f)
        head, main = head_of(h), main_of(h)
        if not re.search(r'<meta name="robots" content="[^"]*noindex', h):
            P.append("page: a living person's page is not noindex (%s)" % pid)
        if re.search(r"application/ld\+json", h) or re.search(r'"@type"\s*:\s*"Person"', h):
            P.append("page: a living person's page carries structured data (%s)" % pid)
        if re.search(r"<table\b", main) or re.search(r'class="[^"]*\brec\b', main):
            P.append("page: a living person's page carries a table of records (%s)" % pid)
        if re.search(r"<img\b", main) or re.search(r'class="[^"]*\b(plate|pgal|shot)\b', main):
            P.append("page: a living person's page carries an image (%s)" % pid)
        text = TAGS.sub(" ", main) + " " + TAGS.sub(" ", re.sub(r"<link[^>]*>|<script.*?</script>", "", head, flags=re.S))
        if YEAR.search(text):
            P.append("page: a living person's page carries a four-digit year (%s)" % pid)
        fig = re.search(r'<figure class="ptree">.*?</figure>', main, re.S)
        if fig:
            for tag, cls, _a, _i in re.findall(r'<(a|div|span) class="node([^"]*)"([^>]*)>(.*?)</\1>', fig.group(0), re.S):
                if tag != "a" and "me" not in cls.split():
                    unlinked += 1
    S["unlinked relatives on living pages"] = unlinked
    base = int((led.get("unlinked_on_living_pages") or 0))
    if unlinked > base:
        P.append("links: %d relatives on living pages are named without a link to their page; the recorded count is %d" % (unlinked, base))

    # name pages whose every bearer is living
    bearers = collections.defaultdict(list)
    for r in rows:
        w = (r.get("who") or "").strip("/").split("/")[-1]
        if w:
            bearers[w].append(r)
    for slug, rs in bearers.items():
        if rs and all(x.get("living") for x in rs):
            f = os.path.join(dist, "who", slug, "index.html")
            if not os.path.exists(f):
                continue
            S["living name pages examined"] += 1
            h = rd(f)
            if not re.search(r'<meta name="robots" content="[^"]*noindex', h):
                P.append("name page: every bearer is living and the page is not noindex (/who/%s/)" % slug)
            c = re.search(r'<link rel="canonical" href="([^"]+)"', h)
            if c and not c.group(1).rstrip("/").endswith("/who/%s" % slug):
                P.append("name page: a living name page names a canonical elsewhere (/who/%s/)" % slug)
            if re.search(r'"@type"\s*:\s*"Person"', h):
                P.append("name page: a living name page carries a Person (/who/%s/)" % slug)
            if YEAR.search(TAGS.sub(" ", main_of(h))):
                P.append("name page: a living name page carries a four-digit year (/who/%s/)" % slug)

    # sitemap
    sm = [p for p in glob.glob(os.path.join(dist, "sitemap*.xml"))]
    if not sm:
        P.append("sitemap: no sitemap in the built site, so none of it can be checked")
    else:
        xml = "".join(rd(p) for p in sm)
        for pid in livepids:
            if "/person/%s/" % pid in xml:
                P.append("sitemap: a living person's page is in the sitemap (%s)" % pid)
        for slug, rs in bearers.items():
            if rs and all(x.get("living") for x in rs) and "/who/%s/" % slug in xml:
                P.append("sitemap: a living name page is in the sitemap (/who/%s/)" % slug)

    # this archive's own search index
    names = {r["name"] for r in living_rows}
    hrefs = {"/person/%s/" % r["pid"] for r in living_rows if r.get("pid")} | {
        r["who"] for r in living_rows if (r.get("who") or "").startswith("/who/")}
    for rel in ("site/src/data/searchindex.json", "site/public/searchindex.json"):
        pth = os.path.join(root, rel)
        if os.path.exists(pth):
            S["search index files read"] += 1
            for e in json.loads(rd(pth)):
                if e.get("t") in names or e.get("h") in hrefs:
                    P.append("search: a living person is in the search index (%s)" % rel)
                    break
    pth = os.path.join(dist, "searchindex.json")
    if os.path.exists(pth):
        for e in json.loads(rd(pth)):
            if e.get("t") in names or e.get("h") in hrefs:
                P.append("search: a living person is in the BUILT search index")
                break

    # ---------------- David's tree ----------------
    if tree is None:
        if require_tree:
            P.append("tree: --require-tree and no MyHeritage export was found; the people the rule holds out cannot be checked")
        else:
            N.append("the tree is not on this machine: the cross-checks against it (ledger agreement, held-out names) did not run")
    else:
        S["tree people"] = len(tree.people)
        by_pid = {r["pid"]: r for r in rows if r.get("pid")}
        for pid, uid in sorted(led.get("people", {}).items()):
            if uid not in tree.people:
                P.append("tree: a ledger entry points at nobody in the tree (%s)" % pid)
                continue
            living, minor = tree.verdict(uid, year)
            r = by_pid.get(pid)
            if r is None:
                continue
            S["ledger entries checked"] += 1
            if minor:
                P.append("tree: a possible minor is published (%s)" % pid)
            elif bool(r.get("living")) != living:
                P.append("tree: the rule says %s and the roster says %s (%s)" % (
                    "living" if living else "not living", "living" if r.get("living") else "not living", pid))
        # unmatched rows that the tree would call living
        by_key = collections.defaultdict(list)
        for u_, p in tree.people.items():
            by_key[L2.name_key(p["name"])].append(u_)
        ledger_pids = set(led.get("people", {}))
        for r in rows:
            if r.get("pid") in ledger_pids or r.get("living"):
                continue
            if r.get("b") or r.get("d") or r.get("deceased") or L2.row_recorded_dead(r) or L2.row_citations(r):
                continue
            c = [u_ for u_ in by_key.get(L2.name_key(r["name"]), []) if tree.verdict(u_, year)[0]]
            if c:
                S["undated rows sharing a name with a living tree person"] += 1
        # the held-out: no possible minor's full name anywhere
        minors = [p for u_, p in tree.people.items() if tree.verdict(u_, year)[1]]
        keys = sorted({L2.name_key(p["name"]) for p in minors if len(L2.name_key(p["name"]).split()) >= 2})
        S["possible minors in the tree"] = len(minors)
        if keys:
            padded = [" %s " % k for k in keys]
            hit_files = collections.Counter()
            # A name a possible minor shares with someone who is not one (a man of 1870 with the same name as a
            # child of 2012) cannot be told apart by the name, so a hit on it is read, not refused.
            adults = collections.Counter()
            for u_, p in tree.people.items():
                if not tree.verdict(u_, year)[1]:
                    adults[L2.name_key(p["name"])] += 1
            shared = {k for k in keys if adults.get(k)}
            soft = 0
            for f in corpus_files(root, dist):
                try:
                    t = rd(f)
                except OSError:
                    continue
                if f.endswith(".html"):
                    t = TAGS.sub(" ", t)
                ft = " %s " % L2.fold(t)
                for k, pk in zip(keys, padded):
                    if pk in ft:
                        if k in shared:
                            soft += 1
                            continue
                        hit_files[os.path.relpath(f, root)] += 1
                        break
            S["name hits shared with an adult of the tree (read, not refused)"] = soft
            if soft:
                N.append("%d place(s) name someone who shares a name with a possible minor and with an adult in the tree; read them" % soft)
            S["files naming a held-out person"] = len(hit_files)
            for f in sorted(hit_files)[:6]:
                P.append("held out: a possible minor is named in %s" % f)
            if len(hit_files) > 6:
                P.append("held out: ... and %d more files" % (len(hit_files) - 6))

    # ---------------- refuse an empty examination ----------------
    if S["living rows"] == 0:
        P.append("empty: no living person in the roster. The gate examined nothing and has not passed.")
    if S["person pages built"] < 100:
        P.append("empty: only %d person pages in the built site. The gate examined too little to pass." % S["person pages built"])
    if S["living rows"] and S["living pages examined"] == 0:
        P.append("empty: no living person's page was read")
    return P, N, S


def _load_json(p, default):
    return json.loads(rd(p)) if os.path.exists(p) else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--root", default=L2.ROOT)
    ap.add_argument("--gedcom", default=None)
    ap.add_argument("--no-tree", action="store_true", help="do not look for David's tree (fixture runs)")
    ap.add_argument("--require-tree", action="store_true")
    ap.add_argument("--year", type=int, default=L2.THIS_YEAR)
    a = ap.parse_args()
    if os.environ.get("ARCHIVE_OUT") and a.dist == "dist":        # the same convention as every other gate here
        a.dist = os.environ["ARCHIVE_OUT"]
        print("  ..    reading %s (ARCHIVE_OUT)" % a.dist)
    dist = a.dist if os.path.isabs(a.dist) else os.path.join(a.root, "site", a.dist)
    tree, tpath = (None, None) if a.no_tree else load_tree_if_any(a)
    P, N, S = run(a.root, dist, tree, a.year, a.require_tree)
    for n in N:
        print("  note  %s" % n)
    if P:
        print("  FAIL  living-v2  %d problem(s)" % len(P))
        for p in P[:25]:
            print("            %s" % p)
        if len(P) > 25:
            print("            ... and %d more" % (len(P) - 25))
        return 1
    print("  ok    living-v2  %d living of %d rows; %d living pages, %d living name pages, %d person pages read%s" % (
        S["living rows"], S["rows"], S["living pages examined"], S["living name pages examined"],
        S["person pages built"], "; tree checked: %d ledger entries agree, %d possible minors, named in %d files" % (
            S["ledger entries checked"], S["possible minors in the tree"], S["files naming a held-out person"]) if tree else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
