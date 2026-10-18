#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild site/public/whoindex.json — the vocabulary of the client-side name linker.

    python3 scripts/build-whoindex.py            write the file
    python3 scripts/build-whoindex.py --print    print the counts, write nothing

WHY THIS FILE EXISTS (18 October 2026). site/public/wholink.js fetches whoindex.json in the reader's browser
and turns every name it lists into a link to /who/<slug>/. The file was written once, by hand, on 7 September
2026 and nothing regenerated it: it held 631 names against 1,535 deceased roster names, and 175 of the 631
were not names at all but page titles («a hundred thousand ducats», «What it is», «A palazzetto with an
arcaded portico») which the linker faithfully turned into links. The archive's own links audit (18 October
2026) measured it.

WHERE THE NAMES COME FROM. From the roster and nowhere else: site/src/data/roster.json is the authoritative
list of people, and a name appears here only if every one of these holds:

  * it is a roster name (parenthetical nickname or maiden name dropped, as build-dossiers.py does for its
    needle), two words or more, no digits;
  * exactly ONE person bears it. Rows are grouped on the name's slug; a row marked `sameAs` another is the
    same person, any other pair is two people. A name borne by two or more people is not listed: the linker
    would send every reader to one of them, or to a disambiguation page they did not ask for. (Those names
    are still linked, by hand, where the prose says which one is meant.);
  * that person is DECEASED and has a page: the row has a pid (every pid has a /person/ page), is not marked
    living, and is not living by the estate rule either (scripts/living_v2.py -> the kit's living_rule.py,
    read from the committed row alone). A name with ANY living bearer is never listed, because then it has
    two bearers or one living one. People the rule holds out are not in the roster at all, so they cannot
    arrive here; the gate (check-whoindex.py) says so again from the other side;
  * its /who/<slug>/ page exists (a dossier for the slug, built from the roster).

THE ORDER IS LOAD-BEARING. wholink.js joins the names into one regular expression in file order, and a
JavaScript alternation takes the FIRST alternative that matches, not the longest. «Anton Rudolf Defranceski»
beats «Anton Rudolf» only because it comes earlier. So: longest name first, then alphabetical.

FORMAT, unchanged so wholink.js is not touched: [[name, slug, mentions], ...] — `mentions` is the dossier's
count (`n`), shown in the link's tooltip.

check-whoindex.py reads this file against the same data and fails the build when it differs from what this
would write, so a roster or dossier change that is not followed by a run of this script is refused.
"""
import os, re, sys, json, unicodedata, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(ROOT, "site", "public", "whoindex.json")


def slugify(s):
    """The same function as build-dossiers.py, so a slug here is the slug of the /who/ page."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def base_name(name):
    """A roster name as it would be written in running prose: «(Bortolussi)» and «(Petar)» dropped."""
    return " ".join(re.sub(r"\s*\(.*?\)\s*", " ", str(name or "")).split())


def _living_v2():
    spec = importlib.util.spec_from_file_location("living_v2", os.path.join(HERE, "living_v2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def is_name(s):
    """Two words or more, nothing but letters and the marks a name carries, no digits, and it starts a name."""
    if len(s) < 5 or len(s.split()) < 2 or re.search(r"\d", s):
        return False
    return bool(re.match(r"^[^\W\d_]", s)) and s[0].isupper()


def deceased_with_page(row, L2=None):
    """True when the row is a deceased person with a page. Never true for a living row."""
    if not row.get("pid") or row.get("living"):
        return False
    if L2 is not None and L2.row_is_living(row):
        return False
    return True


def generate(rows, people, L2=None):
    """rows: roster rows. people: dossiers `people` (slug -> {n, ...}). -> list of [name, slug, n]."""
    persons = {}                     # name key -> {canonical pid: row}
    for r in rows:
        nm = base_name(r.get("name"))
        if not nm:
            continue
        pid = r.get("pid") or ("anon:" + nm)
        persons.setdefault(slugify(nm), {}).setdefault(r.get("sameAs") or pid, []).append(r)
    out, seen = [], set()
    for key, bearers in persons.items():
        if len(bearers) != 1:        # two or more people bear this name
            continue
        group = next(iter(bearers.values()))
        # the canonical row speaks for the person; a duplicate (sameAs) keeps its own spelling out of the way
        canon = [r for r in group if not r.get("sameAs")] or group
        if not all(deceased_with_page(r, L2) for r in group):
            continue
        row = canon[0]
        nm = base_name(row.get("name"))
        slug = slugify(row["name"])
        if not is_name(nm) or slug not in people or nm.lower() in seen:
            continue
        seen.add(nm.lower())
        out.append([nm, slug, int(people[slug].get("n") or 0)])
    out.sort(key=lambda e: (-len(e[0]), e[0].lower(), e[0]))
    return out


def dumps(entries):
    return json.dumps(entries, ensure_ascii=False)


def load(data=DATA):
    with open(os.path.join(data, "roster.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    with open(os.path.join(data, "dossiers.json"), encoding="utf-8") as f:
        people = json.load(f)["people"]
    return rows, people


def main(argv):
    rows, people = load()
    entries = generate(rows, people, _living_v2())
    if "--print" in argv:
        print("whoindex: %d names from %d roster rows" % (len(entries), len(rows)))
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dumps(entries))
    print("whoindex: wrote %d names to %s" % (len(entries), os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
