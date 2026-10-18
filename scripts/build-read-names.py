#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Names read from records get an entry (the linking standard, L2: kit/docs/linking-standard.md). Written 18 October 2026.

    python3 scripts/build-read-names.py            report only
    python3 scripts/build-read-names.py --write    write site/src/data/read-names.json and add the missing /who/ pages to dossiers.json
    python3 scripts/build-read-names.py --check    write nothing; exit 1 if either file differs from what the data gives

THE PROBLEM. The narrative pages quote people from parish registers, and the names index (scripts/build-names-index.py) is made from
the ROSTER, so a person the archive only READ has no entry for the build-time linker to link to. The parish-book readings themselves
exist only as prose (no table of «persons read from act X»); this round does NOT extract names from prose. It uses the names the
archive already holds in STRUCTURED files, where the name sits in a field of its own:

  register.json    the FamilySearch persona index: the persona's own name (n) and the relatives named on the entry (o)
  fsrecords.json   the FamilySearch records the archive resolved (name)
  households.json  the Fiume / Medulin households: father, mother and children by name

WHO QUALIFIES (every rule is a refusal; a name that cannot be shown to pass all of them is held out and listed in the editorial table):
  1. the name is a plain «Given Surname» (two words or more; no comma, bracket, «née» or title), its first word a given name the ROSTER
     itself uses (so a Latin genitive such as «Francæ», an abbreviation such as «Ant» or a register-order form is held out), its last word
     a SURNAME the archive holds (a roster surname or a register `sp`) and not a forename (so «Jacobum Vincentium», «Martina Antonia»,
     a Latin accusative or a pair of given names, are not names);
  2. the name appears, whole and spelt so, in the prose of the twelve narrative pages' data files (it is a name the narratives use);
  3. no roster row bears it (in any of the roster's labels), and no index entry already holds it: this is for names the roster does not
     have; a name with a roster bearer is the roster's to decide;
  4. EVERY structured entry that bears the name shows the bearer dead by the archive's own rule: a death or burial recorded, or a birth
     in or before 1900 for the persona itself; for a relative named on someone's entry, the persona's birth in or before 1850 (a parent,
     spouse or child of a person born by 1850 was born by 1895); for a household's parent or child, a child born in or before 1900. A
     name with one entry that cannot be shown dead is held out whole: nobody is guessed dead;
  5. the name is not on the living list (built by build-names-index.py) and not borne by anyone of David's tree (build-names-index.py
     refuses the run if it is).
An entry is a NAME entry, as every /who/ page is («Identity here is by name, not by resolved individual»): it says what the structured
files hold under that exact spelling and links nobody to anybody. Aliases are added only where a file states the other form: none is.

WHAT IT WRITES. site/src/data/read-names.json (name, slug, the records, the basis for «dead»), and, for a name with no /who/ page yet, a
page in dossiers.json in the shape of the archive's other non-roster pages (build-dossiers.py keeps them). A name whose /who/ page already
exists (a non-roster page kept from before) keeps that page untouched and only gains its entry in the index. build-names-index.py lists
every entry as a `people` row with the /who/ address; check-names-index.py re-derives the same rules with code of its own.
"""
import glob
import json
import os
import re
import sys
import unicodedata
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
PAGES = os.path.join(ROOT, "site", "src", "pages")
OUT = os.path.join(DATA, "read-names.json")
DOSS = os.path.join(DATA, "dossiers.json")

# the data files whose prose the twelve narrative pages render
PROSE = ["gologorica.json", "corrections.json", "carnia.json", "liznjan.json", "fiume.json", "valentino.json", "jbaptista.json",
         "lines.json", "seget.json", "pfullingen.json", "carlo.json", "crikvenica.json", "kobler.json", "cheryl.json"]
OLDEST_BIRTH = 1900          # the archive's rule (build-names-index.py): born in or before 1900 counts as dead
RELATIVE_OF = 1850           # a relative named on the entry of someone born by this year was born by 1895


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load("build_names_index", "build-names-index.py")


def fold(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("'", "").replace("’", "").replace("-", " ")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def slugify(s):
    return B.slugify(s)


def pooled(s):
    """A name as build-names-index.py pools it: the slug, with «de-franceschi» and «defranceschi» one name."""
    return B.slugify(s).replace("de-franceschi", "defranceschi")


def yr(x):
    m = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", str(x or ""))
    return int(m.group(1)) if m else None


def jl(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def structured():
    """folded name -> [{src, id, text, dead, spelling}]: every bearer the structured files hold, and whether it is shown dead."""
    out = {}

    def add(name, src, rid, text, dead):
        k = fold(name)
        if k:
            out.setdefault(k, []).append({"spelling": " ".join(str(name).split()), "src": src, "id": rid, "text": text, "dead": bool(dead)})

    for r in jl("register.json")["rows"]:
        y, says = r.get("y"), r.get("says") or ""
        own = bool(re.search(r"\b(d|bur)\.", says)) or (isinstance(y, int) and y <= OLDEST_BIRTH)
        add(r["n"], "register", r["id"], says or "an index entry", own)
        for o in r.get("o") or []:
            add(o, "register", r["id"], "named on the index entry of %s (%s)" % (r["n"], says or "undated"),
                isinstance(y, int) and y <= RELATIVE_OF)
    for r in jl("fsrecords.json"):
        by = yr(r.get("birth"))
        dead = bool(r.get("death") or r.get("burial")) or (by is not None and by <= OLDEST_BIRTH)
        bits = [("%s %s" % (k.capitalize(), r[k])) for k in ("birth", "christening", "marriage", "death", "burial") if r.get(k)]
        add(r["name"], "fsrecord", r["id"], " · ".join(bits) or "a resolved FamilySearch record", dead)
    for h in jl("households.json"):
        ys = [yr(c.get("y") or c.get("birth")) for c in h.get("children") or []]
        ys = [y for y in ys if y]
        fy = min(ys) if ys else yr(h.get("from"))
        label = "%s, %s" % (h.get("key") or "household", h.get("place") or "")
        for role in ("father", "mother"):
            if h.get(role):
                add(h[role], "household", h.get("key"), "%s of a household recorded %s–%s at %s" % (role, h.get("from"), h.get("to"), h.get("place") or "?"),
                    fy is not None and fy <= OLDEST_BIRTH)
        for c in h.get("children") or []:
            cy = yr(c.get("y") or c.get("birth"))
            add(c.get("name"), "household", h.get("key"), "child in the household %s" % label,
                bool(c.get("death")) or (cy is not None and cy <= OLDEST_BIRTH))
    return out


def surnames():
    s = {}
    for r in jl("roster.json")["rows"]:
        w = B.base_name(r.get("name")).split()
        if len(w) >= 2:
            s[fold(w[-1])] = s.get(fold(w[-1]), 0) + 1
    for r in jl("register.json")["rows"]:
        if r.get("sp"):
            s[fold(r["sp"])] = s.get(fold(r["sp"]), 0) + 3
    return s


def prose_text():
    t = []
    for fn in PROSE:
        p = os.path.join(DATA, fn)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                t.append(f.read())
    return fold(" ".join(t))


def mentioned(text, k):
    return re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(k), text) is not None


def select():
    """-> (entries, held): entries qualify; held = [(reason, folded name)] for a structured name the narratives use that did not."""
    rows = jl("roster.json")["rows"]
    taken = set()            # the roster's pooled keys (the builder's own: «De Franceschi» and «Defranceschi» are one name)
    for r in rows:
        for k, sp, _u in B.pool_names(r.get("name")):
            taken.add(k)
        taken.add(pooled(B.base_name(r.get("name"))))
    sur = surnames()
    groups, canon = B.person_groups(rows)
    first_n, last_n = B.given_name_counts(rows, canon)
    given = set()
    for r in rows:
        w = B.base_name(r.get("name")).split()
        if len(w) >= 2:
            given.add(fold(w[0]))
    text = prose_text()
    st = structured()
    entries, held = [], []
    doss = jl("dossiers.json")["people"]
    for k, bearers in sorted(st.items()):
        ws = k.split()
        if len(ws) < 2 or not mentioned(text, k):
            continue
        if pooled(k) in taken:
            continue                                   # a roster bearer: the roster's to decide
        spelling = bearers[0]["spelling"]
        if (ws[-1] in B.FORENAMES or sur.get(ws[-1], 0) < 1 or ws[0] not in given or ws[0] in sur
                or any(w in ("di", "da", "fu", "q", "qm", "vidua", "uxor", "filius", "filia", "cives") for w in ws[1:-1])
                or not B.is_plain(spelling) or B.ends_in_given_name(spelling, first_n, last_n)):
            held.append(("not plainly a given name the archive uses and a surname", k)); continue
        if not all(b["dead"] for b in bearers):
            held.append(("a bearer is not shown dead", k)); continue
        slug = slugify(spelling)
        if len(slug) < 5 or not B.is_name(spelling):
            held.append(("not a plain name", k)); continue
        existing = doss.get(slug)
        if existing and (existing.get("roster") is not False):
            held.append(("the /who/ slug belongs to a roster page", k)); continue
        recs, seen = [], set()
        for b in bearers:
            key = (b["src"], b["id"], b["text"])
            if key in seen:
                continue
            seen.add(key)
            kind = {"register": "FamilySearch index entry", "fsrecord": "FamilySearch record", "household": "Household"}[b["src"]]
            ident = (" %s" % b["id"]) if b["src"] != "household" and b["id"] else ""
            recs.append({"kind": kind, "text": ("%s%s · %s" % (kind, ident, b["text"])).strip(), "src": b["src"], "id": b["id"]})
        entries.append({"name": spelling, "slug": slug, "records": recs[:12],
                        "basis": "every structured entry under this spelling shows the bearer dead (a death or burial recorded, a birth in or before %d, "
                                 "or a relative of a person born by %d)" % (OLDEST_BIRTH, RELATIVE_OF)})
    return entries, held


# ---- the pages -------------------------------------------------------------------------------------------------------------------
def routes():
    """data file stem -> (href, title) of the page that renders it (the same reading build-dossiers.py makes)."""
    route = {}
    for f in glob.glob(os.path.join(PAGES, "**", "*.astro"), recursive=True):
        rel = os.path.relpath(f, PAGES)
        if "[" in rel:
            continue
        href = ("/" + rel[:-6].replace(os.sep, "/")).replace("/index", "") or "/"
        if not href.endswith("/"):
            href += "/"
        src = open(f, encoding="utf-8").read()
        m = re.search(r'title=\{?["\`]([^"\`]{2,80})["\`]', src)
        title = m.group(1) if m else href.strip("/").replace("-", " ").title() or "Home"
        for dm in re.finditer(r'from\s+["\'][^"\']*data/([a-z0-9_-]+)\.json["\']', src):
            stem = dm.group(1)
            # a data file read by several pages belongs to the one named for it (corrections.json to /corrections/, not the home page)
            if stem not in route or (stem[:5] in href and stem[:5] not in route[stem][0]):
                route[stem] = (href, title)
    return route


def plain(s):
    s = str(s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`#>|]", " ", s)
    s = re.sub(r'[{}\[\]"]', " ", s)
    s = s.replace("\\n", " ")
    return re.sub(r"\s+", " ", s).strip(" ·,;:-")


_LIVING = []


def living_names():
    """The names of everyone the roster does not show to be dead (what build-names-index.py writes to living.json), folded. A hit
    snippet quoting one of them is dropped from a name page: a new page quotes nobody who may be living."""
    if not _LIVING:
        rows = jl("roster.json")["rows"]
        people = jl("dossiers.json")["people"]
        _i, living, _s = B.build(rows, people, B._living_v2())
        _LIVING.extend(fold(n) for n in living["names"] if len(n.split()) >= 2)
    return _LIVING


def page_for(e, route):
    needle = e["name"]
    lv = living_names()
    hits, pages = [], []
    for fn in PROSE:
        stem = fn[:-5]
        if stem not in route:
            continue
        href, title = route[stem]
        blob = json.dumps(jl(fn), ensure_ascii=False)
        for m in re.finditer(re.escape(needle), blob):
            a, b = max(0, m.start() - 260), min(len(blob), m.end() + 260)
            snip = plain(blob[a:b])
            snip = " ".join(snip.split(" ")[1:-1]) if len(snip.split(" ")) > 6 else snip
            fs = " " + fold(snip) + " "
            if any(" " + n + " " in fs for n in lv):
                continue                                   # it quotes someone who may be living
            hits.append({"page": href, "title": title, "text": snip})
            if len([h for h in hits if h["page"] == href]) >= 3:
                break
        if any(h["page"] == href for h in hits) and not any(p["h"] == href for p in pages):
            pages.append({"h": href, "t": title})
    recs = [{"kind": r["kind"], "text": r["text"], "href": "/register/", "url": None} for r in e["records"]]
    return {
        "name": e["name"], "slug": e["slug"], "n": len(hits) or len(recs),
        "pages": pages or [{"h": "/register/", "t": "Register"}], "hits": hits[:12],
        "facts": [["Found in", "FamilySearch index and the archive's resolved records: a name read, not joined to any household"],
                  ["Dead", "every record under this spelling shows the bearer dead by the archive's rule"]],
        "known": "A name the narrative pages use that the roster does not hold. This page lists what the archive's structured files "
                 "say under this exact spelling and claims nothing beyond it: who the person was, and whether two entries are one man, "
                 "are for the pages that quote the register.",
        "more": [], "records": recs, "tree": None, "ptree": None, "rec": None, "chain": None, "roster": False, "adjacent": None, "read": True,
    }


def dumps(o):
    return json.dumps(o, ensure_ascii=False, indent=1) + "\n"


def main(argv):
    entries, held = select()
    doc = {"note": "Names the narrative pages use that the roster does not hold, from the structured files (register.json, fsrecords.json, "
                   "households.json) where the name has a field of its own. Every one is dead by the archive's rule; a name that could not be "
                   "shown dead, or is not plainly a given name and a surname, is held out. Made by scripts/build-read-names.py. Do not edit by hand.",
           "names": entries}
    new_s = dumps(doc)
    doss = jl("dossiers.json")
    people = doss["people"]
    route = routes()
    # a name whose /who/ page is one of ours (read: true) is rewritten from the data; a non-roster page from before is kept as it is
    want = {e["slug"]: page_for(e, route) for e in entries if people.get(e["slug"]) is None or people[e["slug"]].get("read") is True}
    cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    pages_differ = any(people.get(s) != p for s, p in want.items())
    print("build-read-names: %d names qualify (%d /who/ pages written by this script, %d kept from before); %d structured names the narratives use are held out"
          % (len(entries), len(want), len(entries) - len(want), len(held)))
    if "--check" in argv:
        if cur != new_s or pages_differ:
            print("build-read-names: read-names.json or dossiers.json differs from what the data gives (run scripts/build-read-names.py --write)")
            return 1
        return 0
    if "--write" in argv:
        raw = open(DOSS, encoding="utf-8").read()
        for s, p in want.items():
            people[s] = p
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(new_s)
        out = json.dumps(doss, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else "")
        with open(DOSS, "w", encoding="utf-8") as f:
            f.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
