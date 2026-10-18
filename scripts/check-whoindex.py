#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate for site/public/whoindex.json, the name list the client-side linker (wholink.js) turns into links.

    python3 scripts/check-whoindex.py              check the committed file against the roster
    python3 scripts/check-whoindex.py --self-test  plant the faults below in a made-up archive; each must be caught

Written 18 October 2026. The file was committed once, on 7 September 2026, with no generator behind it. By the
18th it listed 631 names of the archive's 1,535 deceased roster names, and 175 of the 631 were page titles. A
file nobody regenerates and nothing reads drifts; this makes the build read it. Run scripts/build-whoindex.py
to write it again.

WHAT IT REFUSES (counts are printed, a name never is)
  stale     the file is not what build-whoindex.py would write from the committed roster and dossiers
  junk      an entry whose name is not a roster name (a page title, a heading, a phrase)
  living    an entry whose person is living: a row marked living, or one the estate rule calls living, or a
            name that contains a living person's name
  ambiguous a name borne by two or more people
  page      an entry whose /who/<slug>/ page does not exist, or whose slug is not the name's slug
  order     the list is not longest-name-first (wholink.js joins the names into one alternation and a
            JavaScript alternation takes the first match: a shorter name ahead of a longer one wins)
  shape     an entry that is not [name, slug, count], or a name listed twice
  empty     nothing listed. A gate that examined no names has not passed.

THE HELD-OUT. People the rule holds out (an undated person with a living parent) are not in the roster, so no
roster-built file can name them; check-living-v2.py --require-tree reads site/public/*.json for their full
names with David's tree, and this file is among those it reads.
"""
import os, re, sys, json, importlib.util, copy

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


W = _load("build_whoindex", "build-whoindex.py")
L2 = _load("living_v2", "living_v2.py")


def problems(text, rows, people):
    """-> {kind: count} for a file's text, judged against the roster rows and the dossiers `people`."""
    P = {}

    def bad(kind):
        P[kind] = P.get(kind, 0) + 1

    try:
        entries = json.loads(text)
    except ValueError:
        return {"shape": 1}
    if not isinstance(entries, list) or not entries:
        return {"empty": 1}

    # who bears each name: slug of the base name -> {person: [rows]}
    bearers = {}
    for r in rows:
        nm = W.base_name(r.get("name"))
        if nm:
            pid = r.get("pid") or ("anon:" + nm)
            bearers.setdefault(W.slugify(nm), {}).setdefault(r.get("sameAs") or pid, []).append(r)
    living_keys = []
    for r in rows:
        if r.get("living") or L2.row_is_living(r):
            nm = W.base_name(r.get("name"))
            if len(nm.split()) >= 2:
                living_keys.append(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(nm), re.I))

    seen = set()
    for e in entries:
        if not (isinstance(e, list) and len(e) == 3 and isinstance(e[0], str) and isinstance(e[1], str)
                and isinstance(e[2], int)):
            bad("shape")
            continue
        name, slug, _n = e
        if name.lower() in seen:
            bad("shape")
        seen.add(name.lower())
        who = bearers.get(W.slugify(name))
        if not who:
            bad("junk")                      # not a roster name at all
            continue
        if len(who) > 1:
            bad("ambiguous")
        rs = [r for g in who.values() for r in g]
        if any(not W.deceased_with_page(r, L2) for r in rs) or any(k.search(name) for k in living_keys):
            bad("living")
        if slug not in people or slug not in {W.slugify(r["name"]) for r in rs}:
            bad("page")
        if not W.is_name(name):
            bad("junk")
    names = [e[0] for e in entries if isinstance(e, list) and e and isinstance(e[0], str)]
    if any(len(a) < len(b) for a, b in zip(names, names[1:])):
        bad("order")
    expected = W.dumps(W.generate(rows, people, L2))
    if text.strip() != expected:
        bad("stale")
    return P


# ---- self-test -------------------------------------------------------------

def _fixture():
    def row(name, pid, **kw):
        r = {"name": name, "pid": pid, "b": None, "d": None, "src": "record", "ark": "", "mh": "", "note": "",
             "notable": False, "line": "x", "place": "Testville, Testland", "href": "/x/"}
        r.update(kw)
        return r
    rows = [
        row("Aa Bbbb", "aa-bbbb", d=1750),                               # deceased, one bearer: listed
        row("Aa Bbbb Cccc", "aa-bbbb-cccc", d=1760),                     # a longer name that begins with it
        row("Cc Dddd", "cc-dddd", living=True, b=None),                  # living, marked
        row("Ee Ffff", "ee-ffff-1", d=1800),                             # deceased ...
        row("Ee Ffff", "ee-ffff-2", living=True),                        # ... sharing a name with a living person
        row("Gg Hhhh", "gg-hhhh-1", d=1700),                             # two dead people, one name
        row("Gg Hhhh", "gg-hhhh-2", d=1710),
        row("Ii Jjjj", "ii-jjjj-1", d=1690),                             # one person read twice
        row("Ii Jjjj", "ii-jjjj-2", d=1690, sameAs="ii-jjjj-1"),
        row("Kk Llll (Mmmm)", "kk-llll", d=1650),                        # nickname in brackets: listed without it
        row("Nn Oooo", "nn-oooo", b=1990),                               # the rule says living, row not marked
        row("Pp", "pp", d=1600),                                         # one word: never listed
    ]
    people = {W.slugify(r["name"]): {"n": 3, "name": r["name"]} for r in rows}
    return rows, people


def self_test():
    rows, people = _fixture()
    fails = []
    planted = [0]

    def expect(label, cond):
        if not cond:
            fails.append(label)

    gen = W.generate(rows, people, L2)
    names = [e[0] for e in gen]
    expect("generator lists the deceased single-bearer name", "Aa Bbbb" in names)
    expect("generator strips a bracketed nickname", "Kk Llll" in names)
    expect("generator lists a read-twice person once", names.count("Ii Jjjj") == 1)
    expect("generator omits a living person", "Cc Dddd" not in names)
    expect("generator omits a name with a living bearer", "Ee Ffff" not in names)
    expect("generator omits a name two dead people bear", "Gg Hhhh" not in names)
    expect("generator omits a person the rule calls living but the row does not", "Nn Oooo" not in names)
    expect("generator omits a one-word name", "Pp" not in names)
    expect("generator is longest first", names.index("Aa Bbbb Cccc") < names.index("Aa Bbbb"))

    good = W.dumps(gen)
    expect("control: the clean file passes", problems(good, rows, people) == {})

    def with_(mutate):
        e = copy.deepcopy(gen)
        mutate(e)
        return W.dumps(e)

    def caught(label, text, kind):
        got = problems(text, rows, people)
        planted[0] += 1
        expect("%s -> %s" % (label, kind), kind in got)

    caught("a living person planted", with_(lambda e: e.append(["Cc Dddd", "cc-dddd", 1])), "living")
    caught("a living person planted (in front)", with_(lambda e: e.insert(0, ["Nn Oooo", "nn-oooo", 1])), "living")
    caught("a name with a living bearer planted", with_(lambda e: e.append(["Ee Ffff", "ee-ffff", 1])), "living")
    caught("a duplicate name planted", with_(lambda e: e.append(["Gg Hhhh", "gg-hhhh", 1])), "ambiguous")
    caught("a junk page-title phrase planted", with_(lambda e: e.insert(0, ["a hundred thousand ducats", "a-hundred-thousand-ducats", 1])), "junk")
    caught("a heading planted", with_(lambda e: e.append(["What it is", "what-it-is", 5])), "junk")
    caught("an entry with no page", with_(lambda e: e[-1].__setitem__(1, "no-such-page")), "page")
    caught("a stale file (a name missing)", with_(lambda e: e.pop()), "stale")
    caught("a stale file (a count out of date)", with_(lambda e: e[0].__setitem__(2, 99)), "stale")
    caught("a shorter name ahead of a longer", with_(lambda e: e.reverse()), "order")
    caught("a name listed twice", with_(lambda e: e.append(copy.deepcopy(e[0]))), "shape")
    caught("a malformed entry", with_(lambda e: e.append(["only a name"])), "shape")
    caught("an empty list", "[]", "empty")
    caught("not json", "{", "shape")
    # a living person's name inside a longer, otherwise legitimate deceased name
    rows2 = rows + [{"name": "Qq Rrrr, son of Cc Dddd", "pid": "qq-rrrr", "d": 1900, "b": None}]
    people2 = dict(people, **{W.slugify("Qq Rrrr, son of Cc Dddd"): {"n": 1}})
    t2 = W.dumps(W.generate(rows2, people2, L2))
    planted[0] += 1
    expect("a deceased name that contains a living person's name is caught", "living" in problems(t2, rows2, people2))

    if fails:
        for f in fails:
            print("  FAIL  whoindex self-test: not caught: %s" % f)
        return 1
    print("  ok    whoindex self-test  %d faults planted, every one caught; the clean control passes" % planted[0])
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    path = W.OUT
    if not os.path.exists(path):
        print("  FAIL  whoindex  no file at %s; run scripts/build-whoindex.py" % os.path.relpath(path, W.ROOT))
        return 1
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows, people = W.load()
    P = problems(text, rows, people)
    if P:
        print("  FAIL  whoindex  %s" % ", ".join("%s: %d" % kv for kv in sorted(P.items())))
        print("            site/public/whoindex.json is built from the roster by scripts/build-whoindex.py; "
              "run it and commit the result")
        return 1
    n = len(json.loads(text))
    print("  ok    whoindex  %d names, all deceased single-bearer roster names with a page, longest first, "
          "equal to what build-whoindex.py writes (roster %d rows)" % (n, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
