#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate for the two files the build-time name linker reads (private/autolink/names-index.json and living.json).

    python3 scripts/check-names-index.py                 judge the files against the committed roster
    python3 scripts/check-names-index.py --dist DIST     and the built, linked site
    python3 scripts/check-names-index.py --self-test     plant the faults below in a made-up archive; each must be caught

Written 18 October 2026, with scripts/build-names-index.py, when the kit's autolink.py replaced the browser linker
(site/public/wholink.js and whoindex.json, whose own gate this file took over). The kit's own checks stop the run on
a living name or a stale link; what only THIS archive can say is who the names are, so this reads the roster again
with code of its own (it shares only the two small predicates `known_dead` and `is_name` with the builder) and
refuses what the builder must never write.

WHAT IT REFUSES (counts are printed, a name never is)
  living     an entry for a person the roster calls living, by mark or by the living rule, or a name that a living
             person bears, or a living person's address; or a roster living person MISSING from living.json
  dead       a /person/ entry for a person the roster does not show to be dead (a death, a burial or headstone, a
             birth in or before 1900, or an undated person from an old register)
  bearers    a /person/ entry whose name is borne by anyone else, in this spelling or in the other orthography
             (de Franceschi / Defranceschi), counting the labels the roster wrote for itself
  forename   a name that ends in a forename (two forenames, no surname)
  junk       a name that is not a name: a page title, a placeholder, a label with a comma or a bracket
  ambiguous  a name with fewer than two bearers sent to a name page or a search; a name sent to a name page that
             lists fewer than two people, or a living one; a search address that is not the search for the name
  address    an address that is neither /person/<pid>/ of a roster pid, /who/<slug>/ of a name page, nor /search/?q=
  alias      a name or alias that none of the person's own rows holds (a guess, not the archive's spelling)
  shape      an entry that is not {name, aliases, url}; a name listed twice
  empty      nothing listed. A gate that examined no names has not passed.
  stale      the files differ from what build-names-index.py writes from the roster now
and, with --dist (the linked site):
  page       an indexed address whose page is missing, is noindex, or (a name page) does not list two people
  excluded   a data-autolink link on a page that asked not to be linked (Base's noautolink: a person's own page, a name page, the
             people index)
"""
import os, re, sys, json, copy, glob, importlib.util
from urllib.parse import quote, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "private", "autolink")


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load("build_names_index", "build-names-index.py")
L2 = B._living_v2()


def nz(s):
    """A spelling as the builder's case_forms leaves it, folded for comparison."""
    return s.replace("DeFranceschi", "Defranceschi").replace("DeFranceski", "Defranceski").casefold()


def key_exact(name):
    return B.slugify(B.base_name(name))


def key_pooled(name):
    return key_exact(name).replace("de-franceschi", "defranceschi")


def problems(index, living, rows, people, tree_names=(), namesakes=None):
    """-> {kind: count} for the two files, judged against the roster rows and the dossiers `people`."""
    P = {}

    def bad(kind):
        P[kind] = P.get(kind, 0) + 1

    if not isinstance(index, dict) or not isinstance(living, dict):
        return {"shape": 1}
    ppl, amb = index.get("people") or [], index.get("ambiguous") or []
    if not ppl and not amb:
        return {"empty": 1}

    groups, canon = B.person_groups(rows)
    row_of = {r["pid"]: r for r in rows if r.get("pid")}

    def is_living_group(pid):
        return any(r.get("living") or L2.row_is_living(r) for r in groups.get(pid, []))

    # who bears each name, counting every label the roster wrote (a comma, a nickname, a slash form)
    bearers = {}
    for r in rows:
        pid = canon.get(r.get("pid")) or ("anon:" + B.base_name(r.get("name")))
        for k, _sp, _u in B.pool_names(r.get("name")):
            bearers.setdefault(k, set()).add(pid)
    exact = {}                                   # the exact spellings (folded) every label holds, and who holds them
    held = {}                                    # canonical pid -> the spellings of its own rows that may be linked
    for r in rows:
        pid = canon.get(r.get("pid")) or ("anon:" + B.base_name(r.get("name")))
        for _k, sp, usable in B.pool_names(r.get("name")):
            exact.setdefault(B.slugify(sp), set()).add(pid)
            if usable:
                held.setdefault(pid, set()).add(nz(sp))
    first, last = B.given_name_counts(rows, canon)

    seen = set()

    def names_of(e):
        return [e.get("name")] + list(e.get("aliases") or [])

    def shape_ok(e):
        return (isinstance(e, dict) and isinstance(e.get("name"), str) and isinstance(e.get("url"), str)
                and isinstance(e.get("aliases", []), list))

    def name_checks(n):
        if not B.is_name(n) or re.search(r"[,/;()«»“”\"]|\b(née|detto|detti|q\.)", n):
            bad("junk")
        if B.ends_in_given_name(n, first, last):
            bad("forename")

    for e in ppl:
        if not shape_ok(e):
            bad("shape")
            continue
        m = re.match(r"^/person/([^/]+)/$", e["url"])
        if not m or m.group(1) not in row_of:
            bad("address")
            continue
        pid = canon[m.group(1)]
        if canon[m.group(1)] != m.group(1):
            bad("address")                                   # a duplicate row's page: the entry belongs on the person's
        if is_living_group(pid):
            bad("living")
            continue
        if not any(B.known_dead(r) for r in groups[pid]):
            bad("dead")
        for n in names_of(e):
            if n.casefold() in seen:
                bad("shape")
            seen.add(n.casefold())
            name_checks(n)
            if bearers.get(key_pooled(n), set()) != {pid} or exact.get(B.slugify(n), set()) != {pid}:
                bad("bearers")
            if nz(n) not in held.get(pid, set()):
                bad("alias")
    for e in amb:
        if not shape_ok(e):
            bad("shape")
            continue
        for n in names_of(e):
            if n.casefold() in seen:
                bad("shape")
            seen.add(n.casefold())
            name_checks(n)
            who = bearers.get(key_pooled(n), set())
            if len(who) < 2:
                bad("ambiguous")
            if any(is_living_group(p) for p in who) or any(p not in groups for p in who):
                bad("living")
        u = e["url"]
        m = re.match(r"^/who/([^/]+)/$", u)
        if m:
            if m.group(1) not in people:
                bad("address")
            else:
                on = {canon.get(r.get("pid")) for r in rows if r.get("who") == u and r.get("pid")}
                if len(on) < 2 or any(is_living_group(p) for p in on):
                    bad("ambiguous")
        elif u.startswith("/search/?q="):
            if unquote(u[len("/search/?q="):]) != e["name"]:
                bad("address")
        else:
            bad("address")

    # living.json must hold every living person the roster marks or the rule finds
    lnames = {" ".join(str(x).split()).casefold() for x in living.get("names", [])}
    lurls = set(living.get("urls", []))
    for r in rows:
        if r.get("living") or L2.row_is_living(r):
            nm = " ".join(str(r.get("name") or "").split())
            if len(nm.split()) >= 2 and nm.casefold() not in lnames:
                bad("living")
            if "/person/%s/" % r["pid"] not in lurls:
                bad("living")
    # no entry may be one the living list holds
    for e in ppl + amb:
        if not shape_ok(e):
            continue
        if any(" ".join(n.split()).casefold() in lnames for n in names_of(e)) or e["url"] in lurls:
            bad("living")
    for n in tree_names:
        if " ".join(n.split()).casefold() in seen:
            bad("living")

    # stale: the files are what the builder writes now
    exp_i, exp_l, _st = B.build(rows, people, L2, tree_names, namesakes)
    if json.loads(B.dumps(index)) != json.loads(B.dumps(exp_i)) or json.loads(B.dumps(living)) != json.loads(B.dumps(exp_l)):
        bad("stale")
    return P


# ---- the built site -------------------------------------------------------------------------------------------

def rd(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()


def dist_problems(index, dist):
    P = {}

    def bad(kind):
        P[kind] = P.get(kind, 0) + 1

    def page(u):
        u = u.split("?")[0]
        return os.path.join(dist, u.strip("/"), "index.html")

    n_checked = 0
    for e in index.get("people", []) + index.get("ambiguous", []):
        u = e["url"]
        if u.startswith("/search/"):
            continue
        p = page(u)
        n_checked += 1
        if not os.path.exists(p):
            bad("page")
            continue
        h = rd(p)
        if re.search(r'<meta name="robots" content="[^"]*noindex', h):
            bad("page")
        if u.startswith("/who/"):
            m = re.search(r"<main\b.*?</main>", h, re.S)
            if len(set(re.findall(r'href="(/person/[^"/]+/)"', m.group(0) if m else ""))) < 2:
                bad("page")
    if os.path.exists(page("/search/")) is False:
        bad("page")
    # a page that asked not to be linked has no data-autolink in it
    n_excl = 0
    for d, _ds, fs in os.walk(dist):
        for f in fs:
            if f == "index.html":
                h = rd(os.path.join(d, f))
                if 'class="wrap" data-no-autolink' in h:
                    n_excl += 1
                    if "data-autolink" in h:
                        bad("excluded")
    if n_checked == 0:
        bad("empty")
    return P, n_checked, n_excl


# ---- self-test ------------------------------------------------------------------------------------------------

def _fixture():
    def row(name, pid, **kw):
        r = {"name": name, "pid": pid, "b": None, "d": None, "src": "read", "ark": "", "mh": "", "note": "",
             "notable": False, "line": "x", "place": "Testville, Testland", "href": "/x/",
             "who": "/who/%s/" % B.slugify(B.base_name(name))}
        r.update(kw)
        return r
    rows = [
        row("Aa Bbbb", "aa-bbbb", d=1750),                                   # dead, one bearer: listed
        row("Cc Dddd", "cc-dddd", living=True, who=""),                      # living
        row("Ee Ffff", "ee-ffff-1", d=1800),                                 # dead ...
        row("Ee Ffff", "ee-ffff-2", living=True),                            # ... sharing a name with a living one
        row("Gg Hhhh", "gg-hhhh-1", d=1700),                                 # two dead people, one name
        row("Gg Hhhh", "gg-hhhh-2", d=1710),
        row("Ii Jjjj", "ii-jjjj-1", d=1690),                                 # one person read twice
        row("Ii Jjjj", "ii-jjjj-2", d=1690, sameAs="ii-jjjj-1"),
        row("Nn Oooo", "nn-oooo", b=1953, src="record", ark="1:1:AAAA-BBBB"),     # born 1953, a public record: not shown dead
        row("Pp Qqqq", "pp-qqqq", src="myheritage"),                         # undated, family tree: not shown dead
        row("Rr Ssss", "rr-ssss", d=1650),                                   # dead, but a label below names the same plain name
        row("Rr Ssss, daughter of Tttt", "rr-ssss-2", d=1655, who=""),       # a second Rr Ssss in a label
        row("Uu Vvvv", "uu-vvvv", d=1600),                                   # dead, spelled de Franceschi
        row("Uu Vvvv", "uu-vvvv-2", d=1610, who=""),                         # a namesake without a name page of its own
        row("Anna Maria", "anna-maria", d=1700),                             # two forenames
        row("Anna Zzzz", "anna-zzzz", d=1701),
        row("Bb Cccc", "bb-cccc", d=1660),                                   # ordinary dead person
    ]
    # first names that make «Maria» a forename in the fixture
    for i in range(3):
        rows.append(row("Maria Xxxx%d" % i, "maria-x%d" % i, d=1700 + i))
    people = {B.slugify(B.base_name(r["name"])): {"n": 3, "name": r["name"]} for r in rows}
    return rows, people


def self_test():
    rows, people = _fixture()
    fails, planted = [], [0]

    def expect(label, cond):
        if not cond:
            fails.append(label)

    index, living, _st = B.build(rows, people, L2)
    names = [n for e in index["people"] for n in [e["name"]] + e["aliases"]]
    amb = {e["name"]: e["url"] for e in index["ambiguous"]}
    expect("generator lists a dead single-bearer name", "Aa Bbbb" in names)
    expect("generator lists a person read twice once", names.count("Ii Jjjj") == 1)
    expect("generator omits a living person", "Cc Dddd" not in names)
    expect("generator omits a name with a living bearer", "Ee Ffff" not in names and "Ee Ffff" not in amb)
    expect("generator omits a person born 1953 with no death", "Nn Oooo" not in names)
    expect("generator omits an undated person from the family tree", "Pp Qqqq" not in names)
    expect("generator omits a name a label of the roster also bears", "Rr Ssss" not in names)
    expect("generator sends a name two dead people bear to a name page or the search", "Gg Hhhh" in amb)
    expect("generator omits two forenames", "Anna Maria" not in names and "Anna Maria" not in amb)
    expect("living.json holds the living person's name and address",
           "Cc Dddd" in living["names"] and "/person/cc-dddd/" in living["urls"])
    expect("living.json holds a person not shown dead", "Nn Oooo" in living["names"])

    good = (copy.deepcopy(index), copy.deepcopy(living))
    expect("control: the clean files pass", problems(good[0], good[1], rows, people) == {})

    def with_(mutate):
        i, l = copy.deepcopy(good[0]), copy.deepcopy(good[1])
        mutate(i, l)
        return i, l

    def caught(label, files, kind):
        got = problems(files[0], files[1], rows, people)
        planted[0] += 1
        expect("%s -> %s" % (label, kind), kind in got)

    caught("a living person planted", with_(lambda i, l: i["people"].append({"name": "Cc Dddd", "aliases": [], "url": "/person/cc-dddd/"})), "living")
    caught("a name with a living bearer planted", with_(lambda i, l: i["people"].append({"name": "Ee Ffff", "aliases": [], "url": "/person/ee-ffff-1/"})), "living")
    caught("a person born 1953 planted", with_(lambda i, l: i["people"].append({"name": "Nn Oooo", "aliases": [], "url": "/person/nn-oooo/"})), "dead")
    caught("an undated tree person planted", with_(lambda i, l: i["people"].append({"name": "Pp Qqqq", "aliases": [], "url": "/person/pp-qqqq/"})), "dead")
    caught("a name two dead people bear planted as one person", with_(lambda i, l: i["people"].append({"name": "Gg Hhhh", "aliases": [], "url": "/person/gg-hhhh-1/"})), "bearers")
    caught("a name a roster label also bears planted as one person", with_(lambda i, l: i["people"].append({"name": "Rr Ssss", "aliases": [], "url": "/person/rr-ssss/"})), "bearers")
    caught("two forenames planted", with_(lambda i, l: i["people"].append({"name": "Anna Maria", "aliases": [], "url": "/person/anna-maria/"})), "forename")
    caught("an alias no row of the person holds planted", with_(lambda i, l: i["people"][0].__setitem__("aliases", ["Aa Bbbb Zzzz"])), "alias")
    caught("a page title planted", with_(lambda i, l: i["people"].append({"name": "a hundred thousand ducats", "aliases": [], "url": "/person/bb-cccc/"})), "junk")
    caught("a label with a comma planted", with_(lambda i, l: i["people"].append({"name": "Bb Cccc, the elder", "aliases": [], "url": "/person/bb-cccc/"})), "junk")
    caught("a person with no row planted", with_(lambda i, l: i["people"].append({"name": "Zz Yyyy", "aliases": [], "url": "/person/zz-yyyy/"})), "address")
    caught("an address outside the pattern planted", with_(lambda i, l: i["people"][0].__setitem__("url", "/people/aa-bbbb/")), "address")
    caught("a name with one bearer sent to the search", with_(lambda i, l: i["ambiguous"].append({"name": "Bb Cccc", "aliases": [], "url": "/search/?q=Bb%20Cccc"})), "ambiguous")
    caught("a search address that is not the name's", with_(lambda i, l: i["ambiguous"].__setitem__(0, dict(i["ambiguous"][0], url="/search/?q=Other"))), "address")
    caught("a name listed twice", with_(lambda i, l: i["people"].append(copy.deepcopy(i["people"][0]))), "shape")
    caught("a malformed entry", with_(lambda i, l: i["people"].append({"name": "only a name"})), "shape")
    caught("the living person missing from living.json", with_(lambda i, l: l.__setitem__("names", [n for n in l["names"] if n != "Cc Dddd"])), "living")
    caught("the living person's address missing from living.json", with_(lambda i, l: l.__setitem__("urls", [u for u in l["urls"] if u != "/person/cc-dddd/"])), "living")
    caught("a stale file (a person missing)", with_(lambda i, l: i["people"].pop()), "stale")
    caught("empty files", ({"people": [], "ambiguous": []}, {"names": [], "urls": []}), "empty")

    # the tree's namesakes: found on David's machine, and left out wherever data/autolink-namesakes.json is read
    pids, _amb = B.tree_collisions(good[0], ["aa bbbb", "Gg Hhhh"])
    planted[0] += 1
    expect("a tree-living namesake of an index entry is found (and of an ambiguous one)", pids == ["aa-bbbb"] and _amb == ["Gg Hhhh"])
    i2, _l2, _s2 = B.build(rows, people, L2, (), {"pids": ["aa-bbbb"], "names": ["Gg Hhhh"]})
    expect("a listed namesake is left out of the index without the tree",
           all(e["url"] != "/person/aa-bbbb/" for e in i2["people"]) and all(e["name"] != "Gg Hhhh" for e in i2["ambiguous"]))
    # a tree-only living name that is also an index entry is refused (David's machine only)
    got = problems(good[0], good[1], rows, people, tree_names=["Aa Bbbb"])
    planted[0] += 1
    expect("a tree-living namesake of an index entry is caught -> living", "living" in got)

    if fails:
        for f in fails:
            print("  FAIL  names-index self-test: not caught: %s" % f)
        return 1
    print("  ok    names-index self-test  %d faults planted, every one caught; the clean control passes" % planted[0])
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    ip, lp = os.path.join(OUTDIR, "names-index.json"), os.path.join(OUTDIR, "living.json")
    if not (os.path.exists(ip) and os.path.exists(lp)):
        print("  FAIL  names-index  no files at %s; run scripts/build-names-index.py" % os.path.relpath(OUTDIR, ROOT))
        return 1
    index, living = json.loads(rd(ip)), json.loads(rd(lp))
    rows, people = B.load()
    names, _found = ([], False) if "--no-tree" in argv else B.tree_living_names(L2)
    P = problems(index, living, rows, people, names, B.load_namesakes())
    extra = ""
    if "--dist" in argv:
        dist = os.environ.get("ARCHIVE_OUT") or argv[argv.index("--dist") + 1]
        if not os.path.isdir(dist):
            print("  FAIL  names-index  no built site at %s" % dist)
            return 1
        Q, n, ne = dist_problems(index, dist)
        for k, v in Q.items():
            P[k] = P.get(k, 0) + v
        extra = "; %d indexed pages built and indexable, %d pages excluded and unlinked" % (n, ne)
    if P:
        print("  FAIL  names-index  %s" % ", ".join("%s: %d" % kv for kv in sorted(P.items())))
        print("            private/autolink/ is built from the roster by scripts/build-names-index.py; fix the rule there")
        return 1
    print("  ok    names-index  %d people, %d ambiguous names; none living, none a name two people bear, none a forename pair%s"
          % (len(index["people"]), len(index["ambiguous"]), extra))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
