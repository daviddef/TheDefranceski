#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Does every person's page list exactly the other people of their name?

    python3 ../tools/checknamesakes.py --dist "${ARCHIVE_OUT:-dist}"        # from site/; `npm run check:namesakes`
    python3 ../tools/checknamesakes.py --selftest                           # plants one fault per rule

WHY (23 November 2026). This archive's /who/<name>/ pages are research dossiers on a NAME (what the archive knows under it,
the households drawn from it, every mention across the site) and they stay. What David asked for is that a person's own page
also lead to the other people who carry the same name, so that nobody has to go through the name page to find them. A person
page has done that since 23 September ("Others of the same name"), but it grouped rows by the raw name, not by the rule the name
page uses, so 316 pages did not list everyone the name page lists, and a page with nobody to list said so in a section of its own.
The kit's checknamepages.py judges a name page that SAYS "N people" and was never wired in this archive.

This gate reads the BUILD, not the generator. Both sides come from the built HTML:

  expected   the people each built /who/<name>/ page lists under its heading (<ul class="who-bearers">, one /person/<pid>/ link per
             bearer). A person's expected others are every bearer of the name page(s) that list them, less themselves.
  listed     the links inside the person page's #others-of-this-name block (the kit's #namesakes section).

Findings:
  missing   a person page leaves out a person its name page lists.
  extra     it lists a person its name page does not list as a bearer of the same name, or itself, or a page that is not built.
  twice     it lists one person twice.
  absent    a name has other bearers and the page has no #others-of-this-name block (a living person's page is exempt: the kit
            draws no namesakes there, and the name page is where they are found).
  spurious  the page has the block and nobody shares the name.
  count     the sentence "N other people" does not match the links beside it.
  dead      a name page lists a person with no built page.

A living person is never named in a message (their slug can carry a year): their page is reported as "a living person's page"
(any page that says noindex). Exit 0 clean, 1 findings, 2 it could not see what it checks (no build, no person page, no name page).
"""
import argparse
import html
import os
import re
import sys

SECTION = "others-of-this-name"


def read_pages(dist):
    pages = {}
    for root, _dirs, files in os.walk(dist):
        if "index.html" in files:
            rel = os.path.relpath(root, dist).replace(os.sep, "/")
            route = "/" if rel == "." else "/" + rel + "/"
            if route == "/" or route.startswith(("/person/", "/who/")):
                with open(os.path.join(root, "index.html"), encoding="utf-8", errors="replace") as f:
                    pages[route] = f.read()
    return pages


def is_stub(raw):
    return 'http-equiv="refresh"' in raw[:900]


def noindex(raw):
    return bool(re.search(r'<meta name="robots" content="[^"]*noindex', raw[:6000]))


def bearers_of(raw):
    """The person pages a name page lists, in order (empty when the page has no list)."""
    m = re.search(r'<ul class="who-bearers"[^>]*>(.*?)</ul>', raw, re.S)
    return re.findall(r'href="(/person/[^"#?]+/)"', m.group(1)) if m else []


def listed(raw):
    """(has the block, the person pages its list links to, the number its sentence says)"""
    m = re.search(r'id="%s"' % SECTION, raw)
    if not m:
        return False, [], None
    tail = raw[m.end():]
    # the block ends where the next section of the page begins
    end = re.search(r"</section>", tail)
    block = tail[: end.start()] if end else tail
    hrefs = re.findall(r'class="ns-card" href="(/person/[^"#?]+/)"', block)
    s = re.search(r'class="ns-why"[^>]*>\s*(\d+) other', html.unescape(block))
    return True, hrefs, int(s.group(1)) if s else None


def check(pages):
    """(findings, counts) over an in-memory build: route -> html."""
    persons = {r: raw for r, raw in pages.items()
               if r.startswith("/person/") and r != "/person/" and not is_stub(raw)}
    # a page with no data-person-page is a duplicate's pointer ("the same person as another page"): it is built and linked, and
    # the kit draws no sections on it, so it is a bearer on the name pages and has no block of its own
    pointer = {r for r, raw in persons.items() if "data-person-page" not in raw}
    whos = {r: raw for r, raw in pages.items() if r.startswith("/who/") and r != "/who/" and not is_stub(raw)}
    if not persons or not whos or not any(bearers_of(raw) for raw in whos.values()):
        return None, {}
    label = lambda r: "a living person's page" if noindex(persons.get(r, "")) else r
    findings = []

    sets = {}                               # person route -> the other people of the name pages that list them
    for wr, raw in sorted(whos.items()):
        got = bearers_of(raw)
        for b in got:
            if b not in persons:
                findings.append("dead: %s lists %s, which is not a built person page" % (wr, label(b)))
        for b in set(got):
            sets.setdefault(b, set()).update(set(got) - {b})

    shared = 0
    with_block = 0
    for r, raw in sorted(persons.items()):
        living = noindex(raw)
        others = sets.get(r, set())
        if r in pointer:
            if listed(raw)[0]:
                findings.append("spurious: %s is a duplicate's pointer page and has a #%s block" % (label(r), SECTION))
            continue
        if others:
            shared += 1
        has, got, said = listed(raw)
        if has:
            with_block += 1
        if living:
            if has:
                findings.append("spurious: %s has a #%s block, and the kit draws no namesakes on a living page" % (label(r), SECTION))
            continue
        if others and not has:
            findings.append("absent: %s shares its name with %d other person(s) and has no #%s block" % (label(r), len(others), SECTION))
            continue
        if has and not others:
            findings.append("spurious: %s has a #%s block and nobody shares its name" % (label(r), SECTION))
        dupes = sorted({x for x in got if got.count(x) > 1})
        if dupes:
            findings.append("twice: %s lists %d person(s) twice: %s" % (label(r), len(dupes), ", ".join(label(x) for x in dupes)))
        miss = sorted(others - set(got))
        extra = sorted(set(got) - others)
        if miss:
            findings.append("missing: %s does not list %d of its name: %s" % (label(r), len(miss), ", ".join(label(x) for x in miss[:6])))
        if extra:
            findings.append("extra: %s lists %d that do not carry its name: %s" % (label(r), len(extra), ", ".join(label(x) for x in extra[:6])))
        if has and said is not None and said != len(set(got)):
            findings.append("count: %s says %d other people and lists %d" % (label(r), said, len(set(got))))
        if has and said is None:
            findings.append("count: %s has the block and no 'N other people' sentence" % label(r))
    counts = {"person pages": len(persons), "of them duplicates' pointers": len(pointer), "name pages": len(whos),
              "people with others of the name": shared, "pages with the block": with_block}
    return findings, counts


def selftest(pages):
    f0, _c = check(pages)
    ok = True
    print("  control: the untouched build -> %d finding(s)%s" % (len(f0 or []), "" if not f0 else "  <-- SHOULD BE 0"))
    if f0:
        ok = False
    live = {r for r, raw in pages.items() if r.startswith("/person/") and "data-person-page" in raw and noindex(raw)}
    withb = sorted(r for r, raw in pages.items() if r.startswith("/person/") and r not in live and "data-person-page" in raw and listed(raw)[0] and len(listed(raw)[1]) > 1)
    without = sorted(r for r, raw in pages.items() if r.startswith("/person/") and r != "/person/" and r not in live
                     and "data-person-page" in raw and not is_stub(raw) and not listed(raw)[0])
    if not withb or not without or not live:
        print("  no shared name, no unshared person or no living page to plant against: refusing")
        return False
    a = withb[0]
    other = listed(pages[a])[1][0]
    card = lambda href: re.compile(r'<li class="ns-item"[^>]*>(?:(?!</li>).)*?href="%s".*?</li>' % re.escape(href), re.S)

    def planted(name, mutate, want):
        nonlocal ok
        v = dict(pages)
        mutate(v)
        got, _c = check(v)
        hit = any(g.startswith(want) for g in (got or []))
        print("  %-52s %s" % (name, "caught" if hit else "MISSED  <-- the gate cannot see this"))
        ok = ok and hit

    planted("a person of the name left off a list", lambda v: v.__setitem__(a, card(other).sub("", v[a], count=1)), "missing")

    def add_stranger(v):
        i = v[a].index('<ul class="ns-list"')
        v[a] = v[a][:i] + v[a][i:].replace("</ul>", '<li class="ns-item"><a class="ns-card" href="%s">x</a></li></ul>' % without[0], 1)
    planted("a stranger added to a list", add_stranger, "extra")

    def twice(v):
        m = card(other).search(v[a])
        v[a] = v[a][: m.end()] + m.group(0) + v[a][m.end():]
    planted("one person listed twice", twice, "twice")
    planted("a block on a name nobody shares",
            lambda v: v.__setitem__(without[0], v[without[0]].replace("</main>", '<section><div id="%s"><p class="ns-why" data-x="1">1 other person</p><ul class="ns-list"><li class="ns-item"><a class="ns-card" href="%s">x</a></li></ul></div></section></main>' % (SECTION, a), 1)), "spurious")
    planted("a shared name with no block", lambda v: v.__setitem__(a, v[a].replace('id="%s"' % SECTION, 'id="nothing"')), "absent")
    planted("a sentence whose count is wrong", lambda v: v.__setitem__(a, re.sub(r'(class="ns-why"[^>]*>\s*)\d+ other', r"\g<1>99 other", v[a], count=1)), "count")
    planted("a block on a living page",
            lambda v: v.__setitem__(sorted(live)[0], v[sorted(live)[0]].replace("</main>", '<div id="%s"><p class="ns-why" data-x="1">1 other person</p></div></main>' % SECTION, 1)), "spurious")
    w = sorted(r for r, raw in pages.items() if r.startswith("/who/") and r != "/who/" and bearers_of(raw))[0]
    planted("a name page that lists a person who has no page",
            lambda v: v.__setitem__(w, re.sub(r'(<ul class="who-bearers"[^>]*>)', r'\1<li><a href="/person/nobody-here/">x</a></li>', v[w], count=1)), "dead")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.dist):
        print("checknamesakes: %s is not a directory; nothing was checked" % a.dist)
        return 2
    pages = read_pages(a.dist)
    if a.selftest:
        return 0 if selftest(pages) else 1
    findings, counts = check(pages)
    if findings is None:
        print("checknamesakes: no person page, no name page, or no name page that lists its bearers (a who-bearers list), in %s; nothing was checked" % a.dist)
        return 2
    for f in findings:
        print("  FAIL  " + f)
    print("checknamesakes: " + ", ".join("%d %s" % (v, k) for k, v in counts.items()) + "; %d finding%s" % (len(findings), "" if len(findings) == 1 else "s"))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
