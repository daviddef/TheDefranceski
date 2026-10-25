#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate for the living-people standard, version 2 (David, 16 October 2026).

    python3 scripts/check-living-v2.py --dist dist            # what CI can run: committed data and the built site
    python3 scripts/check-living-v2.py --dist dist --require-tree   # and David's tree, which only his machine has

THE RULE (one definition, in the kit: kit/tools/living_rule.py, read through scripts/living_v2.py):
living is 80 or younger by year with no death recorded; no birth year is not living; an UNDATED person with a
living parent (a possible minor) is held out and not published at all. A public-source citation does NOT make a
person with a birth year "not living" (the kit's rule says it does; scripts/living_v2.py withholds the citations
from it, and this gate does the same: 25 October 2026, after a woman born in 1946 was published with her year on
the strength of a FamilySearch ark).

WHY THIS READS THE DATA AND NOT THE GENERATOR. scripts/apply-living-rule.py decides who is living and
writes the roster. This file decides again, from the committed roster and from the built pages, and
compares. A generator that is wrong cannot make its own output pass.

WHAT IT REFUSES.
  rule       a row the rule calls living that is published with a birth year, a death year, or no living mark
  scrub      a living row that carries anything beyond name, page address, relationship, and a full town and
             country: a date, a citation, a note, a parish, a tree id, an estimate, an image
  place      a living row whose place is not 'Town, Country' (a street, a number, a hospital, a care home)
  child      (with David's tree) a child with a KNOWN birth year under 18 whom the archive names but has no
             page for, or whom the ledger wrongly holds out. Known children follow the standard: a page,
             noindex, no dates (kit 6cefc79, David, 16 October 2026). Only an UNDATED person with a living
             parent is held out.
  page       a living person's page that is missing, is not noindex, carries structured data, a table, an
             image, or a four-digit year
  name page  a /who/ page whose every bearer is living and is not noindex or names a canonical elsewhere
  sitemap    a living page in the sitemap
  search     a living person in this archive's own search index
  pages      a roster row with no person page
  links      MORE unlinked relatives on living pages than the recorded count (see the ledger)
  tree       (with David's tree) a ledger entry the rule now disagrees with, a possible minor in the roster,
             and any held-out person's FULL NAME anywhere the archive publishes: data, pages, built site
  year       (25 October 2026) A BIRTH YEAR THAT MAKES SOMEONE 80 OR YOUNGER (>= L2.CUTOFF, 1946 in 2026), with no
             death beside it, anywhere: in any data row (source or built), in any built page, in JSON-LD, in a title,
             after a living person's name, or as a `b. YYYY` / `born YYYY`. Nothing starts from the `living` flag or
             from a citation: the year and the absence of a death decide, alone. See rule7_years().
  cutoff     a page, component or script that spells the 80-year boundary out itself (`NOW - by < 80`) instead of
             reading src/lib/living.js / scripts/living_v2.py, or a kit whose 80 disagrees with ours.
  empty      nothing to examine. A gate that examined zero people has not passed.

Counts only are printed; a name never is.
"""
import os, sys, re, io, json, glob, collections, argparse, html

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



# ============================================================================================================
# RULE 7 (25 October 2026): no birth year of someone 80 or younger is published without a death beside it.
#
# The fault this closes: a woman born in 1946 was published as "not living", with her year in the title, the
# heading, the JSON-LD, the search index, the timeline, the people lists and four name-cluster pages, because her
# row carried a FamilySearch ark and the kit's rule takes a public source for a death. Every other living check
# here started from the `living` flag, so none of them looked. This one starts from nothing: it reads every data
# row and every built page for a year at or after the cutoff and asks whether a death is beside it.
#
#   7a  a data row that names a living person by pid / slug / who-address carries no birth or death field
#   7b  a data row with a birth-ish field in the window, no death field, whose person the roster does not record
#       as dead (by pid, by name page and the same year, or by name and the same year), and not flagged living
#   7c  a built page or data file with `b. YYYY`, `born YYYY`, or JSON-LD birthDate YYYY in the window and no death
#       marker within 80 characters; a reviewed exception goes in data/living-year-allow.json, each a decision
#   7d  a living person's NAME followed (within a few characters) by a year in the window, or, with David's tree,
#       a person the tree gives as 80 or younger with no death followed by their own birth year
# ============================================================================================================
BIRTHISH = {"b", "by", "born", "birth", "birthyear", "bornyear", "birthdate", "dob", "yob"}
DEATHISH = {"d", "dy", "died", "death", "deathyear", "deathdate", "deceased", "dead", "buried", "dod"}
YEAR_ONE = re.compile(r"(?<!\d)(1[0-9]\d\d|20\d\d)(?!\d)")
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DEATH_NEAR = re.compile(r"(died|death|dead|deceased|buried|burial|killed|drown|funeral|obituar|†|✝|\bd\.|\bd\s*\d|"
                        r"[–-]\s*(?:\d{1,2}\s+" + MONTH + r"\s+)?(?:19|20)\d\d)", re.I)
RX_B = re.compile(r"\bb\.\s*(?:\d{1,2}\s+" + MONTH + r"\s+)?(1[0-9]\d\d|20\d\d)\b", re.I)
_Y = r"(?:1[0-9]\d\d|20\d\d)"
# «born 1942, 1946 and 1947» (every year in the run), «born at Adelaide in 1967», «born — Dean in 1967 and Lisa in 1968»
RX_BORN = re.compile(r"\b(?:born|geb\.)\s*(?:in|on|at|about|circa|c\.)?\s*(?:\d{1,2}\s+" + MONTH + r"\s+)?(?:" + MONTH + r"\s+)?"
                     + _Y + r"(?:\s*(?:,|and|&)\s*(?:" + MONTH + r"\s+)?" + _Y + r")*\b", re.I)
RX_BORN_IN = re.compile(r"\bborn\b[^.;\d]{0,30}?\bin\s+" + _Y + r"(?:[^.;\d]{0,24}\bin\s+" + _Y + r")*\b", re.I)
RX_LD = re.compile(r'birthDate"\s*:\s*"([^"]*)"')


def _birth_year(v):
    """A single plain year out of a birth-ish value, else None. Two years (a span with an end) is not a bare birth."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v if 1000 <= v <= 2100 else None
    if isinstance(v, str):
        ys = YEAR_ONE.findall(v)
        if len(ys) == 1:
            return int(ys[0])
        if ys and re.search(r"[–-]\s*(\?|$)", v.strip()):
            return int(ys[0])
    return None


def _slug_of(v):
    if not isinstance(v, str):
        return None
    m = re.match(r"^/(?:who|person)/([^/]+)/?$", v.strip())
    return m.group(1) if m else None


def _walk_nodes(o):
    stack = [o]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            yield x
            stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
        elif isinstance(x, list):
            stack.extend(v for v in x if isinstance(v, (dict, list)))


def _allow(root):
    ap = os.path.join(root, "data", "living-year-allow.json")
    if not os.path.exists(ap):
        return []
    return [a["text"] for a in _load_json(ap, {}).get("allow", []) if a.get("text")]


def _name_norm(n):
    return L2.name_key(n)


def rule7_years(root, dist, rows, tree, year, P, S):
    cut = L2.cutoff(year)
    win = lambda y: isinstance(y, int) and cut <= y <= year
    live_pids = {r["pid"] for r in rows if r.get("living") and r.get("pid")}
    live_who = {(r.get("who") or "").strip("/").split("/")[-1] for r in rows if r.get("living") and r.get("who")}
    live_who.discard("")
    dead_pid, dead_who, dead_name = set(), collections.defaultdict(set), collections.defaultdict(set)
    dead_win = []          # (name tokens, birth year) of roster people recorded dead who were born in the window
    for r in rows:
        if r.get("living") or not L2.row_recorded_dead(r):
            continue
        if r.get("pid"):
            dead_pid.add(r["pid"])
        w = (r.get("who") or "").strip("/").split("/")[-1]
        for yy in (r.get("b"), r.get("d")):
            if isinstance(yy, int):
                if w:
                    dead_who[w].add(yy)
                dead_name[_name_norm(r.get("name"))].add(yy)
        if isinstance(r.get("b"), int) and win(r["b"]):
            toks = {t for t in _name_norm(r.get("name")).split() if len(t) > 1}
            if toks:
                dead_win.append((toks, r["b"]))
    # the files: every JSON in the source data and the public folder, and every JSON in the built site
    jfiles = []
    for base in (os.path.join(root, "site", "src", "data"), os.path.join(root, "site", "public"), dist):
        for dp, _, fs in os.walk(base):
            for f in fs:
                if f.endswith(".json") and f not in ("roster.json",):
                    jfiles.append(os.path.join(dp, f))
    n_rows = n_nodes = 0
    bad_a, bad_b = [], []
    for path in jfiles:
        try:
            doc = json.loads(rd(path))
        except Exception:
            continue
        rel = os.path.relpath(path, root)
        for d in _walk_nodes(doc):
            n_nodes += 1
            ids = [v for k, v in d.items() if k in ("pid", "slug", "id") and isinstance(v, str)]
            who = [_slug_of(v) for k, v in d.items() if k in ("w", "who", "h", "href", "page") and _slug_of(v)]
            is_live_flag = d.get("living") is True
            names_live = bool((set(ids) & live_pids) or (set(who) & live_who) or (set(ids) & live_who))
            life_vals = [(k, v) for k, v in d.items()
                         if (k.lower() in BIRTHISH or k.lower() in DEATHISH
                             or (k == "y" and ("d" in d or "n" in d or "name" in d) and "p" not in d and "living" not in d)
                             or (k in ("y",) and "living" in d)
                             or k == "dt")
                         and v not in (None, "", [], {}, False, 0)]
            if names_live and not is_live_flag:
                n_rows += 1
                if life_vals:
                    bad_a.append("%s: a row that names a living person carries %s" % (rel, sorted({k for k, _ in life_vals})[:3]))
                continue
            if is_live_flag:
                continue
            # 7b
            has_death = any(k.lower() in DEATHISH and v not in (None, "", [], {}, False, 0) for k, v in d.items())
            for k, v in d.items():
                kl = k.lower()
                birthish = (kl in BIRTHISH or kl == "dt"
                            or (k == "y" and ("d" in d) and ("n" in d or "name" in d))
                            or (k == "y" and "living" in d))
                if not birthish:
                    continue
                y = _birth_year(v)
                if not win(y) or has_death:
                    continue
                nm = d.get("n") or d.get("name") or d.get("t") or ""
                dead_ok = (set(ids) & dead_pid or any(y in dead_who.get(w, ()) for w in who)
                           or y in dead_name.get(_name_norm(nm), ()))
                if dead_ok:
                    continue
                bad_b.append("%s: a row with a birth year in the 80-year window, no death and no living flag (%s)" % (
                    rel, (ids or who or [nm or "unnamed"])[0]))
    S["rows naming a living person (rule 7a)"] = n_rows
    S["data nodes read (rule 7)"] = n_nodes
    for m in sorted(set(bad_a))[:8]:
        P.append("year: " + m)
    for m in sorted(set(bad_b))[:8]:
        P.append("year: " + m)
    if len(set(bad_a)) + len(set(bad_b)) > 16:
        P.append("year: ... and %d more data rows" % (len(set(bad_a)) + len(set(bad_b)) - 16))

    # 7c / 7d: the built site
    allow = _allow(root)
    live_names = sorted({re.sub(r"\s+", " ", re.sub(r"[“”\"]", "", re.sub(r"\(.*?\)", "", r["name"]))).strip()
                         for r in rows if r.get("living") and len(r.get("name", "").split()) >= 2}, key=len, reverse=True)
    name_rx = None
    if live_names:
        name_rx = re.compile("(?:" + "|".join(r"\s+".join(re.escape(t) for t in n.split()) for n in live_names) + r")\)?\s*[,(–—-]?\s*(?:b\.|born|geb\.)?\s*(?:in\s+)?(1[0-9]\d\d|20\d\d)(?![\d–-])", re.I)
    win_names = {}
    if tree is not None:
        for p in tree.people.values():
            if p["by"] is not None and not p["dead"] and L2.in_window(p["by"], year) and len(p["name"].split()) >= 2:
                win_names.setdefault(re.sub(r"\s+", " ", p["name"]), set()).add(p["by"])
    win_rx = None
    if win_names:
        win_rx = re.compile("|".join(r"\s+".join(re.escape(t) for t in n.split()) for n in sorted(win_names, key=len, reverse=True)))
    hits = collections.Counter()
    groups = collections.OrderedDict()           # (kind, year, snippet) -> [files]

    def explained(y, near):
        """A year in the window beside the NAME of a roster person recorded dead who was born that year."""
        words = set(_name_norm(near).split())
        return any(by == y and toks <= words for toks, by in dead_win)

    def note(kind, y, rel, msg, snippet):
        k = (kind, msg, re.sub(r"\s+", " ", snippet.lower()))
        groups.setdefault(k, []).append(rel)
    n_files = 0
    for base, dp_ in ((dist, None),):
        for dp, _, fs in os.walk(base):
            for f in fs:
                if not f.endswith((".html", ".json", ".xml", ".txt")):
                    continue
                path = os.path.join(dp, f)
                n_files += 1
                t = rd(path)
                rel = os.path.relpath(path, dist)
                ld = " ".join(RX_LD.findall(t)) if f.endswith(".html") else ""
                if f.endswith(".html"):
                    meta = " ".join(re.findall(r'<(?:title)[^>]*>[^<]*|content="[^"]*"', t))
                    plain = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", t, flags=re.S)
                    plain = TAGS.sub(" ", plain)
                else:
                    meta, plain = "", t
                plain = re.sub(r"\s+", " ", html.unescape(plain))
                for a in allow:
                    plain = re.sub(re.escape(a), " ", plain, flags=re.I)
                # JSON-LD: a Person's birthDate in the window with no deathDate in the same block
                if f.endswith(".html"):
                    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
                        try:
                            doc = json.loads(blk)
                        except ValueError:
                            doc = None
                        for d in (_walk_nodes(doc) if doc is not None else ()):
                            y = _birth_year(d.get("birthDate"))
                            if win(y) and not d.get("deathDate"):
                                nmv = str(d.get("name") or "")
                                if y in dead_name.get(_name_norm(nmv), ()):
                                    continue
                                hits["jsonld"] += 1
                                note("jsonld", y, rel, "a Person's birthDate (%d) is in the 80-year window with no deathDate" % y, nmv)
                                break
                for kind, rx in (("b.", RX_B), ("born", RX_BORN), ("born in", RX_BORN_IN)):
                    for m in rx.finditer(plain):
                        for y in sorted({int(v) for v in YEAR_ONE.findall(m.group(0))}):
                            if not win(y):
                                continue
                            near = plain[max(0, m.start() - 80): m.end() + 80]
                            if DEATH_NEAR.search(near) or explained(y, plain[max(0, m.start() - 400): m.end() + 200]):
                                continue
                            hits[kind] += 1
                            note(kind, y, rel, "«%s %d» is a birth year in the 80-year window with no death shown" % (kind, y), plain[max(0, m.start() - 40): m.end() + 30])
                if name_rx:
                    for m in name_rx.finditer(plain):
                        y = int(m.group(1))
                        if win(y):
                            hits["name+year"] += 1
                            note("name+year", y, rel, "a living person's name is followed by the year %d (80-year window)" % y, plain[max(0, m.start() - 10): m.end() + 10])
                            break
                if win_rx:
                    for m in win_rx.finditer(plain):
                        nm = re.sub(r"\s+", " ", m.group(0))
                        tail = plain[m.end(): m.end() + 100]
                        fm = YEAR_ONE.search(tail)
                        if fm and re.fullmatch(r"[^\d]*", tail[:fm.start()]) and int(fm.group(0)) in win_names.get(nm, ()):
                            hits["tree name+year"] += 1
                            note("tree", int(fm.group(0)), rel, "a person the tree gives as 80 or younger with no death is followed by their own birth year", nm)
                            break
    S["built files read for years (rule 7)"] = n_files
    S["year hits"] = sum(len(v) for v in groups.values())
    for (kind, msg, snip), files in list(groups.items())[:12]:
        P.append("year: %s (%d file%s, first %s; «…%s…»)" % (msg, len(files), "" if len(files) == 1 else "s", files[0], snip[:60]))
    if len(groups) > 12:
        P.append("year: ... and %d more distinct hits" % (len(groups) - 12))


# RULE 8: the boundary is spelled once.
LITERAL_BOUNDARY = [
    re.compile(r"(?:getFullYear\(\)|\bNOW\b|\bYEAR\b|\bTHIS_YEAR\b|\bthisYear\b|\bnowYear\b|today(?:_year|Year)?\b)\s*-\s*[\w.\[\]]+\)?\s*(?:<|<=|>|>=)\s*(?:79|80|81)\b"),
    re.compile(r"[\w.\[\]]+\s*(?:<|<=|>|>=)\s*(?:79|80|81)\b\s*(?:#.*)?$(?<=\S)"),   # placeholder, refined below
    re.compile(r"\b(?:PRESUME\w*|PRESUMED?_?DEAD\w*|LIVING_YEARS|ALIVE_WITHIN|WINDOW|LIVING_AGE)\s*=\s*(?:79|80|81)\b"),
    re.compile(r"\b(?:year|today\.year|YEAR|THIS_YEAR)\s*-\s*[\w.\[\]\"']+\)?\s*(?:<|<=|>|>=)\s*(?:79|80|81)\b"),
]
LITERAL_BOUNDARY = [LITERAL_BOUNDARY[0], LITERAL_BOUNDARY[2], LITERAL_BOUNDARY[3]]


def rule8_cutoff_literals(root, P, S):
    n = 0
    for base, exts in (("site/src/pages", (".astro", ".js", ".ts")), ("site/src/components", (".astro", ".js", ".ts")),
                       ("site/src/layouts", (".astro", ".js", ".ts")), ("site/src/lib", (".js", ".mjs", ".ts")),
                       ("scripts", (".py", ".mjs", ".js")), ("tools", (".py", ".mjs", ".js"))):
        for dp, _, fs in os.walk(os.path.join(root, base)):
            for f in fs:
                if not f.endswith(exts) or f in ("living.js", "living_v2.py", "check-living-v2.py", "test-living-v2.py"):
                    continue
                path = os.path.join(dp, f)
                n += 1
                for i, line in enumerate(rd(path).splitlines(), 1):
                    code = line.split("//")[0] if path.endswith((".js", ".astro", ".ts", ".mjs")) else line.split("#")[0]
                    if any(rx.search(code) for rx in LITERAL_BOUNDARY):
                        P.append("cutoff: %s:%d spells the 80-year boundary out (use src/lib/living.js or scripts/living_v2.py)" % (
                            os.path.relpath(path, root), i))
    S["files read for a literal boundary (rule 8)"] = n
    # the two copies of the number must agree: the kit's JS and the kit's Python
    kit = os.path.join(root, "site", "node_modules", "@daviddef", "archive-kit", "kit")
    pj = os.path.join(kit, "lib", "person.js")
    if os.path.exists(pj):
        m = re.search(r"export const LIVING_YEARS = (\d+);", rd(pj))
        if not m or int(m.group(1)) != L2.LIVING_YEARS:
            P.append("cutoff: the kit's JavaScript LIVING_YEARS (%s) is not the kit's Python LIVING_YEARS (%d)" % (
                m.group(1) if m else "missing", L2.LIVING_YEARS))
    lj = os.path.join(root, "site", "src", "lib", "living.js")
    if os.path.exists(lj):
        src = rd(lj)
        if "LIVING_CUTOFF = THIS_YEAR - LIVING_YEARS" not in src or "archive-kit/lib/person.js" not in src:
            P.append("cutoff: site/src/lib/living.js does not derive the cutoff from the kit's LIVING_YEARS")
    elif os.path.isdir(os.path.join(root, "site", "src", "lib")):
        P.append("cutoff: site/src/lib/living.js is missing: the pages have no single cutoff")


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
            if L2.is_living(r.get("b"), L2.row_recorded_dead(r), L2.row_citations(r), year,
                            undated_dead=L2.row_undated_dead(r)):
                P.append("rule: the rule calls this person living and the row carries a birth year and no living mark (%s)" % pid)
            elif isinstance(r.get("b"), int) and L2.in_window(r["b"], year) and not L2.row_recorded_dead(r):
                # belt and braces, written without the kit: a year at or after the cutoff and no death field
                P.append("rule: a row carries a birth year of someone 80 or younger, no death, and no living mark (%s)" % pid)
    S["pids"] = len({r.get("pid") for r in rows if r.get("pid")})
    # A person born in the window who is published as dead on a death RECORD with no date (a `deathSource`, no death
    # year) is accepted: a recorded, sourced death frees them (kit 341af33). A bare `deceased` mark does NOT (the line
    # above calls that row living and fails). The gate counts the undated records and prints their source, because if
    # the source is wrong the year is a living person's.
    shaky = [r.get("pid") for r in rows if not r.get("living") and isinstance(r.get("b"), int) and L2.in_window(r["b"], year)
             and L2.row_recorded_dead(r) and not r.get("d") and r.get("src") not in ("burial", "grave")]
    S["born in the window, death recorded without a date"] = len(shaky)
    for r in rows:
        if r.get("pid") in shaky and not (r.get("deathSource") and r.get("deathGrade")):
            P.append("rule: a person born in the window is dead on a record with no date but the row carries no deathSource and deathGrade (%s)" % r.get("pid"))
    if shaky:
        N.append("%d person(s) born in the 80-year window are published as dead on a source with no date (%s): %s" % (
            len(shaky), ", ".join(sorted(shaky)),
            "; ".join(sorted({"%s (%s)" % (r["deathSource"], r.get("deathGrade", "?")) for r in rows if r.get("pid") in shaky and r.get("deathSource")}))))

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
            if L2.row_recorded_dead(r) and not r.get("living"):
                living, minor = False, False      # a death the tree does not hold, recorded on the row (family confirmation)
            S["ledger entries checked"] += 1
            if minor:
                P.append("tree: a possible minor is published (%s)" % pid)
            elif bool(r.get("living")) != living:
                P.append("tree: the rule says %s and the roster says %s (%s)" % (
                    "living" if living else "not living", "living" if r.get("living") else "not living", pid))
        for uid in led.get("held", []):
            if uid in tree.people and not tree.verdict(uid, year)[1]:
                P.append("child: a person is held out and the rule does not hold them out (a known child, or no "
                         "longer undated, follows the standard and gets a page)")
        # unmatched rows that the tree would call living
        by_key = collections.defaultdict(list)
        for u_, p in tree.people.items():
            by_key[L2.name_key(p["name"])].append(u_)
        ledger_pids = set(led.get("people", {}))
        for r in rows:
            if r.get("pid") in ledger_pids or r.get("living"):
                continue
            if r.get("b") or r.get("d") or r.get("deceased") or L2.row_recorded_dead(r):
                continue
            c = [u_ for u_ in by_key.get(L2.name_key(r["name"]), []) if tree.verdict(u_, year)[0]]
            if c:
                S["undated rows sharing a name with a living tree person"] += 1
        # the held-out: no held-out person's full name anywhere; and every KNOWN child the archive names has a page
        minors = [p for u_, p in tree.people.items() if tree.verdict(u_, year)[1]]
        known_children = [p for u_, p in tree.people.items()
                          if p["by"] is not None and (year - p["by"]) < 18 and not p["dead"]
                          and not tree.verdict(u_, year)[1]]
        rkeys = {L2.name_key(r["name"]) for r in rows}
        keys = sorted({L2.name_key(p["name"]) for p in minors if len(L2.name_key(p["name"]).split()) >= 2})
        ckeys = sorted({L2.name_key(p["name"]) for p in known_children
                        if len(L2.name_key(p["name"]).split()) >= 2} - rkeys)
        S["possible minors in the tree"] = len(minors)
        S["known children in the tree"] = len(known_children)
        if keys or ckeys:
            # A name shared with someone who is not the person (a man of 1870 with the same name as a child
            # of 2012) cannot be told apart by the name, so a hit on it is read, not refused.
            adults = collections.Counter()
            for u_, p in tree.people.items():
                if not tree.verdict(u_, year)[1]:
                    adults[L2.name_key(p["name"])] += 1
            shared = {k for k in keys if adults.get(k)} | {k for k in ckeys if sum(
                1 for p in tree.people.values() if L2.name_key(p["name"]) == k) > 1}
            hit_files, child_files, soft = collections.Counter(), collections.Counter(), 0
            allk = [(k, " %s " % k, "held") for k in keys] + [(k, " %s " % k, "child") for k in ckeys]
            for f in corpus_files(root, dist):
                try:
                    t = rd(f)
                except OSError:
                    continue
                if f.endswith(".html"):
                    t = TAGS.sub(" ", t)
                ft = " %s " % L2.fold(t)
                seen = set()
                for k, pk, kind in allk:
                    if pk in ft and (kind, f) not in seen:
                        if k in shared:
                            soft += 1
                            continue
                        seen.add((kind, f))
                        (hit_files if kind == "held" else child_files)[os.path.relpath(f, root)] += 1
            S["name hits shared with someone else in the tree (read, not refused)"] = soft
            if soft:
                N.append("%d place(s) name someone who shares a name with a held-out person or a child and with another person in the tree; read them" % soft)
            S["files naming a held-out person"] = len(hit_files)
            for f in sorted(hit_files)[:6]:
                P.append("held out: a person who is held out is named in %s" % f)
            if len(hit_files) > 6:
                P.append("held out: ... and %d more files" % (len(hit_files) - 6))
            S["files naming a child with no page"] = len(child_files)
            for f in sorted(child_files)[:6]:
                P.append("pages: a child with a known birth year is named in %s and has no person page" % f)
            if len(child_files) > 6:
                P.append("pages: ... and %d more files naming a child with no page" % (len(child_files) - 6))

    # ---------------- a year in the window, with no death, anywhere (25 October 2026) ----------------
    rule7_years(root, dist, rows, tree, year, P, S)
    rule8_cutoff_literals(root, P, S)

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
        S["person pages built"], "; tree checked: %d ledger entries agree, %d held out by rule (named in %d files), %d known children (%d named with no page)" % (
            S["ledger entries checked"], S["possible minors in the tree"], S["files naming a held-out person"],
            S["known children in the tree"], S["files naming a child with no page"]) if tree else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
