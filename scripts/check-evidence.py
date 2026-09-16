#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refuse the build when evidence on disk does not reach the person's page.

WHY THIS EXISTS. On 6 September 2026 this archive read the Liber Baptizatorum
of Fiume and wrote the fourteen children of Valentino Defranceschi to
site/src/data/valentino.json. Nothing ever read that file — no build script, no
page, for eleven days. Nine of those baptism dates exist in no index and in no
other file in this repository, and meanwhile:

  · five of the children had /who/ pages saying «born about 1749 (somewhere
    1742-1757) — estimated, not recorded» and «This person has no recorded
    year», over the top of a date that was sitting in the repository; and
  · four of them had no page at all.

Nothing refused. Every gate this archive had was green: the links resolved, the
anchors resolved, no living person leaked, the work list balanced. A build can
be entirely correct about what it renders and still be silently dropping what
it was given, and no check that looks only at what IS on the page can see it.
This one looks from the other end: from the evidence file to the page.

WHAT IT CHECKS. For every person named in a declared evidence file:

  1. that person has a rendered page at all; and
  2. that page carries a record card, or a record strip, or the person is
     named in corrections.json — so the page never reads as though nothing
     has been read about someone this archive has documented; and
  3. where the evidence file carries a DATE, the page does not also claim
     there is no recorded year.

It reads site/dist, not the data, deliberately. The failure being guarded
against is the build dropping data between the two.

WHAT IT DOES NOT DO. It does not touch the charts. A household chart here
draws households.json as it stands, and a pedigree draws the export as given;
a date recovered from a register does not silently rewrite either. The point
is only to stop a page claiming nothing has been read when something has.

    python3 scripts/check-evidence.py [--dist site/dist] [--quiet]
"""
import argparse, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")

# Person-keyed evidence files, and how a person is named in each.
#   key   "slug"  the row carries the /who/ slug outright — the only safe join
#   key   "name"  the row carries a name, matched the way build-dossiers matches
#   dated  rows carrying a date, so check 3 applies
EVIDENCE = [
    {"file": "valentino", "rows": "children", "key": "slug", "field": "who",
     "date": "says", "label": "the fourteen children of Fiume"},
    {"file": "burials",   "rows": "rows", "key": "name", "field": "name",
     "date": "buried", "label": "the parish burial register"},
    {"file": "graves",    "rows": "rows", "key": "name", "field": "name",
     "date": "span",   "label": "the headstones"},
    {"file": "fsrecords", "rows": "rows", "key": "name", "field": "name",
     "date": None,     "label": "the FamilySearch record index"},
]

# Phrases the page prints when it believes it has nothing. Each is quoted from
# who/[slug].astro; if one is reworded there it must be reworded here, and the
# gate failing loudly is the right way to find that out.
#
# THEY ARE LOOKED FOR ONLY WHERE THE PAGE ITSELF SPEAKS. A /who/ page also
# quotes every mention of the person from every data file, and on 17 September
# the correction retracting the «no record stands behind it» banner quoted both
# the banner AND a person's name — so her own page carried the sentence as a
# quotation of a thing the archive had stopped saying, and this gate failed her
# for it. A gate that cannot tell a claim from a quotation of a claim will be
# switched off within the week.
NO_RECORD = "no record stands behind it"
NO_YEAR   = "This person has no recorded year"
NO_YEAR_2 = "estimated, not recorded"
HAS_RECORD = ('class="rk"', 'class="recstrip"')
SAYS_IT = re.compile(r'class="(?:mt-warn[^"]*|prov|facts)"(.*?)(?=<section|</section)', re.S)

def claims(html_text):
    """Only the parts of the page that state the archive's own position."""
    return " ".join(SAYS_IT.findall(html_text))


def slugify(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def namekey(n):
    n = re.sub(r"\s*\(.*?\)\s*", " ", str(n or ""))
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = n.replace("defranceschi", "de franceschi").replace("defranceski", "de franceschi")
    return " ".join(re.sub(r"[^a-z ]+", " ", n).split())


def load(name):
    fp = os.path.join(DATA, name + ".json")
    if not os.path.exists(fp): return None
    with open(fp, encoding="utf-8") as fh: return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=os.path.join(ROOT, "site", "dist"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    dossiers = (load("dossiers") or {}).get("people", {})
    by_name = {}
    for slug, p in dossiers.items():
        by_name.setdefault(namekey(p.get("name")), slug)

    corr = json.dumps(load("corrections") or {}, ensure_ascii=False)

    pages = {}          # slug -> rendered html, read once
    def html(slug):
        if slug not in pages:
            fp = os.path.join(a.dist, "who", slug, "index.html")
            pages[slug] = open(fp, encoding="utf-8").read() if os.path.exists(fp) else None
        return pages[slug]

    fails, checked = [], 0
    for ev in EVIDENCE:
        d = load(ev["file"])
        if d is None:
            fails.append((ev["file"], "—", "the evidence file itself is missing"))
            continue
        rows = d.get(ev["rows"], d) if isinstance(d, dict) else d
        if not isinstance(rows, list):
            fails.append((ev["file"], "—", f"no «{ev['rows']}» list in the file"))
            continue
        for r in rows:
            if not isinstance(r, dict): continue
            raw = r.get(ev["field"])
            if not raw: continue
            slug = raw if ev["key"] == "slug" else by_name.get(namekey(raw))
            who = raw if ev["key"] == "name" else raw
            checked += 1
            if not slug:
                fails.append((ev["file"], who, "named in the evidence file and has no page in this archive"))
                continue
            h = html(slug)
            if h is None:
                fails.append((ev["file"], who, f"/who/{slug}/ was not rendered"))
                continue
            named_in_correction = (r.get(ev["field"]) or "") in corr
            if not any(m in h for m in HAS_RECORD) and not named_in_correction:
                fails.append((ev["file"], who,
                              f"/who/{slug}/ carries neither a record nor a correction"))
                continue
            own = claims(h)
            if NO_RECORD in own and not named_in_correction:
                fails.append((ev["file"], who, f"/who/{slug}/ says «{NO_RECORD}»"))
                continue
            if ev["date"] and (r.get(ev["date"]) or "").strip():
                if NO_YEAR in own or NO_YEAR_2 in own:
                    fails.append((ev["file"], who,
                                  f"/who/{slug}/ claims no recorded year, and {ev['file']}.json gives "
                                  f"«{r[ev['date']]}»"))

    if fails:
        print(f"  FAIL  evidence    {len(fails)} of {checked} — evidence on disk that does not reach the person")
        for f, who, why in fails[:40]:
            print(f"          {f + '.json':<18} {who[:44]:<46} {why}")
        if len(fails) > 40:
            print(f"          … and {len(fails) - 40} more")
        return 1
    if not a.quiet:
        print(f"  ok    evidence   {checked} people named in {len(EVIDENCE)} evidence file(s) "
              f"— every one reaches a page carrying a record or a correction")
    return 0


sys.exit(main())
