#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This archive's adapter to the estate's one definition of who is living.

David's ruling of 16 October 2026 (the living-people standard, version 2):

    LIVING  =  80 or younger (this year minus the birth year) with NO death or
               burial recorded, and no citation from a public record source.
    A person with no birth year is NOT living: nothing shows they are 80 or younger.
    HELD OUT = a possible minor (under 18 by year, or no birth year and a living
               parent). Not published at all.

The test itself is not written here. It is `living_rule.py`, in the shared kit,
read through the installed copy so that this archive cannot drift from the others:

    is_living(birth_year, recorded_dead, citations, today_year)
    possible_minor(birth_year, recorded_dead, citations, parent_living, today_year)
    public_source(citations)

What this file adds is the part that is the archive's own: WHERE the facts come
from. A living person's birth year is never committed (the generator scrubs at the
source), so the only place it exists is David's MyHeritage tree, exported as a
GEDCOM that lives outside the repository. `load_tree()` reads it and produces,
for every person, the four facts the rule needs: birth year, whether a death or
burial is recorded, the citations that count, and who the parents are.

WHAT COUNTS AS A CITATION. The kit's `public_source` looks at strings. A MyHeritage
export carries three kinds of source and only some are public records:

  * a NOTE that names FamilySearch (David pastes the citation by hand)      -> counts
  * a «Collection» source: a census, a register, a death index, a cemetery
    transcription, FamilySearch Family Tree                                -> counts
  * a «Collection» that is itself somebody's TREE (Geni World Family Tree,
    WikiTree, Filae, GenealogieOnline), and every «Smart Matching» and
    «Discovery» source (another member's family site)                      -> does NOT
    count. The kit's own list says so: a private family-tree entry is not a public
    source. Their URLs begin myheritage.com/research, which the kit would match as a
    record collection, so they are not handed to it.

The committed repository holds only what the rule lets it hold. Nothing here writes
a living person's date anywhere.
"""
import os, re, sys, glob, io, json, unicodedata, importlib.util, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_TOOLS = os.path.join(ROOT, "site", "node_modules", "@daviddef", "archive-kit", "kit", "tools")
if KIT_TOOLS not in sys.path:
    sys.path.insert(0, KIT_TOOLS)
import living_rule as lr          # noqa: E402  (the shared definition; never copied)

LEDGER = os.path.join(ROOT, "data", "living-ledger.json")
THIS_YEAR = datetime.date.today().year

# Collections that are somebody's tree, not a record. Matched as a prefix, lowercase.
TREE_COLLECTIONS = ("geni world family tree", "wikitree", "genealogieonline family tree",
                    "filae family trees", "compilation of", "biographical summaries",
                    "famous people")


def _fold_table():
    """Accented Latin letters -> their plain letter, for str.translate (fast on a hundred megabytes of
    built pages, where a per-character Python loop is not)."""
    t = {}
    for cp in list(range(0xC0, 0x250)) + list(range(0x1E00, 0x1F00)):
        ch = chr(cp)
        a = "".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn")
        if a != ch and a.isascii():
            t[cp] = a.lower()
    t.update({0x111: "d", 0x110: "d", 0x142: "l", 0x141: "l", 0xF8: "o", 0xD8: "o", 0xDF: "ss", 0xE6: "ae", 0xC6: "ae"})
    return t


_FOLD = _fold_table()


def fold(s):
    s = str(s or "").lower().translate(_FOLD)
    return " ".join(re.sub(r"[^a-z ]+", " ", s).split())


def name_key(n):
    """A roster name reduced to the letters a GEDCOM name has: brackets and nicknames gone."""
    n = re.sub(r"\(.*?\)", " ", str(n or ""))
    n = n.replace("“", " ").replace("”", " ")
    return fold(n)


# ---- the tree -------------------------------------------------------------

def _gedcom_module():
    spec = importlib.util.spec_from_file_location("read_gedcom", os.path.join(ROOT, "scripts", "read-gedcom.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def gedcom_path(explicit=None):
    """The tree export: explicit argument, else $ARCHIVE_GEDCOM, else the newest MyHeritage
    export in ~/Downloads. None when there is none, which callers must treat as 'cannot say'."""
    for p in (explicit, os.environ.get("ARCHIVE_GEDCOM")):
        if p:
            return p if os.path.exists(p) else None
    cands = sorted(glob.glob(os.path.expanduser("~/Downloads/*.ged")), key=os.path.getmtime, reverse=True)
    for c in cands:
        with open(c, "rb") as f:
            if b"MYHERITAGE" in f.read(600).upper():
                return c
    return None


class Tree:
    """People of the export, keyed by their stable MyHeritage _UID."""

    def __init__(self, people, by_xref):
        self.people, self.by_xref = people, by_xref
        self._memo = {}

    def verdict(self, uid, year=None):
        """(living, possible_minor) for one person, by the shared rule."""
        year = year or THIS_YEAR
        k = (uid, year)
        if k in self._memo:
            return self._memo[k]
        p = self.people[uid]
        self._memo[k] = (False, False)          # break cycles in a malformed tree
        living = lr.is_living(p["by"], p["dead"], p["cites"], year)
        pl = any(self.verdict(q, year)[0] for q in p["parents"] if q in self.people)
        minor = lr.possible_minor(p["by"], p["dead"], p["cites"], pl, year)
        self._memo[k] = (living, minor)
        return self._memo[k]


def load_tree(path):
    g = _gedcom_module()
    recs = g.parse(path)
    srcs = {r["id"]: r for r in recs if r["tag"] == "SOUR"}
    fams = {r["id"]: r for r in recs if r["tag"] == "FAM"}
    parents_of = {}
    for f in fams.values():
        pa = [c["val"] for c in f["sub"] if c["tag"] in ("HUSB", "WIFE")]
        for c in f["sub"]:
            if c["tag"] == "CHIL":
                parents_of.setdefault(c["val"], []).extend(pa)
    people, by_xref = {}, {}
    for r in recs:
        if r["tag"] != "INDI":
            continue
        uid = g.val(r, "_UID") or r["id"]
        b = g.sub(r, "BIRT")
        m = re.search(r"\b(1[0-9]\d\d|20\d\d)\b", g.val(b, "DATE") if b else "")
        d = g.sub(r, "DEAT")
        dm = re.search(r"\b(1[0-9]\d\d|20\d\d)\b", g.val(d, "DATE") if d else "")
        dead = any(g.sub(r, t) is not None for t in ("DEAT", "BURI", "CREM"))
        people[uid] = {
            "uid": uid, "xref": r["id"], "name": g.val(r, "NAME").replace("/", " ").strip(),
            "by": int(m.group()) if m else None, "dy": int(dm.group()) if dm else None,
            "dead": dead, "place": g.val(b, "PLAC") if b else "",
            "cites": _citations(r, srcs, g), "parents": parents_of.get(r["id"], []),
        }
        by_xref[r["id"]] = uid
    for p in people.values():
        p["parents"] = [by_xref[q] for q in p["parents"] if q in by_xref]
    return Tree(people, by_xref)


def _citations(rec, srcs, g):
    out = []

    def walk(n):
        for c in n["sub"]:
            if c["tag"] == "SOUR":
                s = srcs.get(c["val"])
                if s is not None and g.val(s, "_TYPE") == "Collection":
                    t = g.val(s, "TITL")
                    if "familysearch" in t.lower():
                        out.append("FamilySearch: " + t)
                    elif not t.lower().startswith(TREE_COLLECTIONS):
                        out.append("myheritage.com/research record collection: " + t)
            elif c["tag"] == "NOTE" and "familysearch" in c["val"].lower():
                out.append("FamilySearch: " + c["val"][:80])
            walk(c)
    walk(rec)
    return out


# ---- the roster, from committed data alone ---------------------------------

def row_recorded_dead(r):
    """A death or burial the ROSTER records: a death year, the 'deceased' mark, or a burial
    register / headstone as the source."""
    return bool(r.get("d")) or bool(r.get("deceased")) or r.get("src") in ("burial", "grave")


def row_citations(r):
    """Citations a roster row carries that the kit counts: a FamilySearch ark."""
    c = []
    if r.get("ark") or r.get("arks"):
        c.append("FamilySearch ark")
    if r.get("cited"):                      # the tree cites a public source for this person (see apply-living-rule)
        c.append(str(r["cited"]))
    return c


def row_is_living(r, year=None):
    """The rule over a roster row's COMMITTED fields. A row already scrubbed (living flag, no
    birth year) cannot be re-derived here: it needs the tree. See Tree.verdict."""
    return lr.is_living(r.get("b"), row_recorded_dead(r), row_citations(r), year or THIS_YEAR)


# ---- place: the full town and the country, never a street or an institution ----

_COUNTRY_ONLY = {"australia", "south africa", "germany", "croatia", "italy", "austria", "france",
                 "united states", "usa", "canada", "brazil", "argentina", "slovenia", "serbia",
                 "switzerland", "united kingdom", "england", "new zealand", "uruguay", "chile",
                 "bosnia and herzegovina", "hungary", "montenegro", "greece", "spain",
                 "yugoslavia", "mexico", "venezuela"}
_INSTITUTION = re.compile(
    r"\b(hospital|clinic|infirmary|sanatorium|nursing|care home|hospice|aged care|retirement|"
    r"krankenhaus|bolnica|bolnic|ospedale|klinik|spital|maternity|medical cent|health cent|"
    r"cemetery|church|school|university|prison)\b|\d", re.I)
_STREET = re.compile(r"\b(street|st\.?|road|rd\.?|avenue|ave\.?|lane|drive|strasse|straße|"
                     r"ulica|via|viale|piazza|platz|weg)\b", re.I)
_US_STATES = {"alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
              "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
              "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
              "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
              "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
              "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
              "virginia", "washington", "west virginia", "wisconsin", "wyoming",
              "ny", "pa", "nj", "ca", "tx", "fl", "il", "oh", "ma", "ct", "mi", "wa"}
_COUNTRY_ALIAS = {"usa": "United States", "united states of america": "United States",
                  "u.s.a.": "United States", "uk": "United Kingdom"}


def town_country(place):
    """'Johannesburg, City of Johannesburg Metropolitan Municipality, Gauteng, South Africa'
    -> ('Johannesburg', 'South Africa').  Returns (town, country); either may be ''.
    A leading street or institution component is dropped and the town taken from what follows."""
    parts = [p.strip() for p in str(place or "").split(",") if p.strip()]
    if not parts:
        return "", ""
    country = ""
    if len(parts) > 1 and parts[-1].lower() in _US_STATES:
        country, parts = "United States", parts[:-1]
    elif len(parts) > 1 or parts[0].lower() in _COUNTRY_ONLY:
        last = parts[-1]
        if last.lower() in _COUNTRY_ONLY or last.lower() in _COUNTRY_ALIAS or len(parts) > 1:
            country = _COUNTRY_ALIAS.get(last.lower(), last)
            parts = parts[:-1]
    parts = [p for p in parts if not (_INSTITUTION.search(p) or _STREET.search(p))]
    town = parts[0] if parts else ""
    if town and town.lower() in _COUNTRY_ONLY and not country:
        return "", _COUNTRY_ALIAS.get(town.lower(), town)
    return town, country


def place_line(place):
    t, c = town_country(place)
    return ", ".join(x for x in (t, c) if x)


# ---- the ledger ------------------------------------------------------------

def load_ledger():
    if not os.path.exists(LEDGER):
        return {"people": {}, "held": []}
    with io.open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def save_ledger(led):
    with io.open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
