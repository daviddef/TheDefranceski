#!/usr/bin/env python3
"""Rebuild site/src/data/dossiers.json — one page per person.

The roster is the authoritative list of people. For each of them this walks
every data file the site actually renders, finds every mention of the name,
and records it with a link back to the page it appears on. Roster facts
(place, years, source, line, what the archive knows) are carried onto the
page so a person's dossier opens with the finding, not just the quotations.

Entries already in dossiers.json that are not roster people are kept as they
are, so no existing /who/ link breaks.

    python3 scripts/build-dossiers.py
"""
import json, os, re, glob, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PAGES = os.path.join(ROOT, "site", "src", "pages")

def slugify(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def plain(s):
    s = str(s)
    s = s.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"')
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`#>]", "", s)
    # strip the JSON scaffolding a raw blob drags in
    s = re.sub(r'"\s*[,:]\s*(true|false|null|\d+)\s*[,}\]]*', " ", s)
    s = re.sub(r'"\s*[},\]]+\s*[{\[]?\s*"?', " ", s)
    s = re.sub(r'"[a-z][a-zA-Z_]{1,12}"\s*:\s*"?', " ", s)
    s = re.sub(r'[{}\[\]"]', " ", s)
    s = re.sub(r"\s+([·,;.])", r"\1", s)
    s = re.sub(r"(?<![A-Za-z])[a-z][a-zA-Z_]{0,14}\s+:\s*", " ", s)  # JSON keys, once the quotes are gone
    s = re.sub(r"(?<![A-Za-z])(key|true|false|null)(?![A-Za-z])", " ", s)
    s = re.sub(r"\s+([·,;.])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip(" ·,;:-")

# ---- which data file is rendered by which page -------------------------
route_of = {}
for f in glob.glob(os.path.join(PAGES, "**", "*.astro"), recursive=True):
    rel = os.path.relpath(f, PAGES)
    if "[" in rel:          # dynamic routes have no single href
        continue
    href = "/" + rel[:-6].replace(os.sep, "/")
    href = href.replace("/index", "") or "/"
    if not href.endswith("/"): href += "/"
    src = open(f, encoding="utf-8").read()
    m = re.search(r'title=\{?["\`]([^"\`]{2,80})["\`]', src)
    title = m.group(1) if m else href.strip("/").replace("-", " ").title() or "Home"
    for dm in re.finditer(r'from\s+["\'][^"\']*data/([a-z0-9_-]+)\.json["\']', src):
        route_of.setdefault(dm.group(1), (href, title))

roster = json.load(open(os.path.join(DATA, "roster.json")))
srclabel = roster.get("srclabel", {})
legend = dict(roster.get("legend") or [])

# ---- load every data file once ----------------------------------------
SKIP = {"dossiers", "searchindex"}
# Structured record files: they get a page link, but their rows are field/value
# data and make unreadable quotations, so no snippets are taken from them.
TABULAR = {"households", "explorer", "roster", "fsrecords", "registers", "sweep",
           "istriasweep", "marriages", "burials", "graves", "plates", "art-src",
           "tree", "names", "givennames", "atlas", "searched", "eleven", "arrivals",
           "lineages", "onename", "parishmap", "parishbooks", "library", "sources"}
blobs = {}
for f in sorted(glob.glob(os.path.join(DATA, "*.json"))):
    name = os.path.basename(f)[:-5]
    if name in SKIP or name not in route_of:
        continue
    try:
        blobs[name] = json.dumps(json.load(open(f, encoding="utf-8")), ensure_ascii=False)
    except Exception:
        pass


# ---- structured records, so an index-only person's page shows the record ----
def _load(name):
    fp = os.path.join(DATA, name + ".json")
    if not os.path.exists(fp): return []
    try: d = json.load(open(fp, encoding="utf-8"))
    except Exception: return []
    r = d.get("rows", d) if isinstance(d, dict) else d
    return r if isinstance(r, list) else []

def _key(n):
    n = re.sub(r"\s*\(.*?\)\s*", " ", str(n or ""))
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = n.replace("defranceschi", "de franceschi").replace("defranceski", "de franceschi")
    return re.sub(r"[^a-z ]+", " ", n).split()

RECORDS = {}
def _add(name, kind, bits, href, extra=None):
    k = " ".join(_key(name))
    if not k: return
    RECORDS.setdefault(k, []).append({"kind": kind, "text": " · ".join([b for b in bits if b]),
                                      "href": href, "url": extra})

for r in _load("fsrecords"):
    bits = []
    for lab in ("birth", "christening", "marriage", "death", "burial"):
        if r.get(lab): bits.append(f"{lab.capitalize()} {r[lab]}")
    # An indexer's place string can carry the right country and the wrong
    # province: FamilySearch geocodes Istrian «Fasana» to Pont Canavese in
    # Piedmont, five hundred kilometres away, and eight people were being
    # shown as born there. Where this archive has resolved one, show the
    # resolution and keep the index's own words beside it - the string is the
    # provenance and the correction is the finding.
    if r.get("place"):
        bits.append("%s - indexed as \u00ab%s\u00bb" % (r["placeFixed"], r["place"])
                    if r.get("placeFixed") else r["place"])
    if r.get("parents"): bits.append("parents: " + r["parents"])
    if r.get("spouses"): bits.append("spouse: " + r["spouses"])
    _add(r.get("name"), "FamilySearch record", bits, "/archive/")

for r in _load("burials"):
    bits = [f"Buried {r['buried']}" if r.get("buried") else "", r.get("place"),
            f"aged {r['age']}" if r.get("age") else "", r.get("kin")]
    _add(r.get("name"), "Parish burial", bits, "/burials/")

for r in _load("graves"):
    bits = [r.get("span"), r.get("cem"), r.get("place"), r.get("plot")]
    _add(r.get("name"), "Headstone", bits, "/graves/", r.get("url"))


# ---- evidence files keyed to a person by SLUG -------------------------------
# Everything above is matched on the name, which only works where the evidence
# file and the roster spell a person the same way. valentino.json does not: it
# writes the fourteen children of Fiume in the nominative — «Josepha Catharina»
# — while the archive has them in the accusative the register clerk used,
# «Josepham Catharinam Defranceschi». No name match was ever going to join
# those, and none did. The file sat in site/src/data for eleven days and was
# read by no script and no page, while five of the people in it had /who/ pages
# saying «born about 1749 — estimated, not recorded» and four had no page at
# all. The dates were on disk the whole time.
#
# So a person-keyed evidence file now declares its own slug and is loaded here.
# BY_SLUG carries the record card; YEAR_FROM carries the recorded date, which
# overrides the roster's estimate in the facts strip. Neither touches the
# household chart: that still draws households.json exactly as it stands, and
# says so.
BY_SLUG, YEAR_FROM = {}, {}

def _slug_evidence(file, kind, href, label):
    d = _raw_early(file)
    of = d.get("of") or {}
    for c in d.get("children") or []:
        slug, says = c.get("who"), c.get("says")
        if not slug or not says: continue
        if c.get("covered") and c["covered"] != file:
            continue                      # already reaches the page another way
        bits = [says, of.get("place"), "child of " + of.get("father", "") if of.get("father") else ""]
        BY_SLUG.setdefault(slug, []).append(
            {"kind": kind, "text": " \u00b7 ".join([b for b in bits if b]), "href": href, "url": None})
        if c.get("year"):
            YEAR_FROM[slug] = {"says": says, "href": href, "src": label}

def _raw_early(name):
    fp = os.path.join(DATA, name + ".json")
    if not os.path.exists(fp): return {}
    try: return json.load(open(fp, encoding="utf-8"))
    except Exception: return {}

_slug_evidence("valentino", "Parish baptism, Fiume", "/fiume-1626/#valentino",
               "Liber Baptizatorum, St Vitus, Fiume")


# ---- MyHeritage key rows, and provenance for tree-only people ----
MH = {}
kr = os.path.join(ROOT, "notes", "myheritage-key-rows.md")
if os.path.exists(kr):
    for line in open(kr, encoding="utf-8"):
        if not re.match(r"^\d{6,8}\|", line): continue
        f = [x.strip() for x in line.rstrip("\n").split("|")]
        f += [""] * (8 - len(f))
        MH[f[0]] = {"name": f[1], "b": f[2], "bp": f[3], "d": f[4], "dp": f[5], "rel": f[6], "arks": f[7]}

def mh_record(r):
    """A provenance card for a person the archive knows only from the family tree."""
    k = MH.get(str(r.get("mh") or ""))
    bits = []
    if k:
        if k["b"]: bits.append("Born " + k["b"] + (" at " + k["bp"] if k["bp"] else ""))
        if k["d"]: bits.append("Died " + k["d"] + (" at " + k["dp"] if k["dp"] else ""))
        if k["rel"]: bits.append("relationship in the tree: " + k["rel"])
        if k["arks"]: bits.append("cited to " + str(len(k["arks"].split(","))) + " FamilySearch record(s)")
    if not bits:
        yrs = "–".join([str(r["b"]) if r.get("b") else "", str(r["d"]) if r.get("d") else ""]).strip("–")
        bits = [x for x in (yrs, r.get("place") or "") if x]
    bits.append("MyHeritage tree 4, individual " + str(r.get("mh")))
    return {"kind": "Family tree entry — not yet checked against a register",
            "text": " · ".join(bits), "href": "/people/", "url": None}


# ---- the mini-tree: parents, siblings, spouse, children, from households.json ----
HH = _load("households")

def _nm(x):
    """Normalise a register name to something matchable: drop the patronymic tail."""
    x = re.sub(r"\s*\(.*?\)\s*", " ", str(x or ""))
    x = re.split(r"\b(?:q\.?m|fu|di|del|dei|della)\b", x, 1)[0]
    x = unicodedata.normalize("NFD", x)
    x = "".join(c for c in x if unicodedata.category(c) != "Mn").lower()
    x = x.replace("defranceschi", "de franceschi").replace("defranceski", "de franceschi")
    return " ".join(re.sub(r"[^a-z ]+", " ", x).split())

PARENT_OF, CHILD_IN = {}, {}
for hh in HH:
    for role in ("father", "mother"):
        k = _nm(hh.get(role))
        if k: PARENT_OF.setdefault(k, []).append(hh)
    for c in hh.get("children") or []:
        k = _nm(c.get("name"))
        if k: CHILD_IN.setdefault(k, []).append((hh, c))

def mini_tree(name):
    k = _nm(name)
    if not k: return None
    up, down = CHILD_IN.get(k, []), PARENT_OF.get(k, [])
    if not up and not down: return None
    t = {"ambiguous": len(up) > 1 or len(down) > 1}
    if up:
        hh, me = up[0]
        t["parents"] = [hh.get("father") or "—", hh.get("mother") or "—"]
        t["parentsPlace"] = hh.get("place") or ""
        t["siblings"] = [c["name"] for c in (hh.get("children") or []) if _nm(c.get("name")) != k]
        t["asChild"] = me.get("birth") or ""
    if down:
        hh = down[0]
        mine = _nm(hh.get("father")) == k
        t["spouse"] = (hh.get("mother") if mine else hh.get("father")) or "—"
        t["children"] = [{"n": c["name"], "d": c.get("birth") or ""} for c in (hh.get("children") or [])]
        t["span"] = f"{hh.get('from','')}–{hh.get('to','')}".strip("–")
        t["childrenPlace"] = hh.get("place") or ""
    t["upN"], t["downN"] = len(up), len(down)
    return t



# ---- the record itself: for people with no household, show the index entry ----
REGROWS = {}
try:
    _rg = json.load(open(os.path.join(DATA, "register.json"), encoding="utf-8"))
    for _r in _rg.get("rows", []): REGROWS[_r["id"]] = _r
except Exception:
    pass

# a person can have parents named in a register row and still have no household object.
# 99 people were in that state: the row exists, nobody had built a family from it.
# Two guards, both learned the hard way:
#   - the key must be at least two words. _nm strips a patronymic tail, so "Andrea dei
#     Franceschi" collapses to "andrea", which matches every Andrea in the register.
#   - the row must be a BIRTH. On a marriage row the other names are in-laws and a
#     spouse, not parents, and drawing them as parents invents a family.
REG_BY_NAME = {}
for _r in REGROWS.values():
    if not _r.get("o"): continue
    if not str(_r.get("says") or "").strip().startswith("b."): continue
    _k = _nm(_r.get("n"))
    if len(_k.split()) < 2: continue
    REG_BY_NAME.setdefault(_k, []).append(_r)

def record_strip(rows):
    """The indexed entry a person appears in — the record, not a reconstructed family."""
    ids = []
    for r in rows:
        m = re.search(r"([0-9A-Z]{4}-[0-9A-Z]{3,4})", str(r.get("ark") or ""))
        if m: ids.append(m.group(1))
        ids += r.get("arks") or []
    for i in ids:
        e = REGROWS.get(i)
        if not e: continue
        others = []
        for nm in (e.get("o") or []):
            row = ROW_BY_NAME.get(_nm(nm))
            o = {"n": nm}
            if row: o["slug"] = slugify(row["name"])
            others.append(o)
        return {"id": i, "says": e.get("says") or "", "place": e.get("p") or "",
                "sp": e.get("sp") or "", "others": others,
                "url": "https://www.familysearch.org/ark:/61903/1:1:" + i}
    return None


# ---- the pedigree chart: parents / self+spouse / children / siblings, with provenance ----
# Provenance tiers, strongest first. They are NOT interchangeable and the page says so.
#   line     the archive's own descent, argued on /direct-line/
#   read     a register this archive has read with its own eyes
#   index    a FamilySearch index entry — a transcription, not the page
#   tree     David's MyHeritage tree, unverified here
VIA_RANK = {"line": 0, "read": 1, "index": 2, "tree": 3, "": 4}

ROW_BY_NAME = {}
# AND EVERY ROW OF THAT NAME, NOT ONLY THE FIRST. `setdefault` below means the
# first roster row of a name wins, which is what put «Ivan Defranceski, 1829 –
# 1895» on his great-great-grandson's page as his father. A node inside a
# household can be resolved against the household's own dates instead.
ROWS_BY_NAME = {}
for _r in roster["rows"]:
    ROW_BY_NAME.setdefault(_nm(_r["name"]), _r)
    ROW_BY_NAME.setdefault(_nm(re.sub(r"\s*\(.*?\)\s*", "", _r["name"])), _r)
    for _kk in {_nm(_r["name"]), _nm(re.sub(r"\s*\(.*?\)\s*", "", _r["name"]))}:
        if _kk: ROWS_BY_NAME.setdefault(_kk, []).append(_r)


# THE DIRECT LINE KNOWS EXACTLY WHO ITS PEOPLE ARE, so it is asked first.
# A household whose father and mother are a direct-line generation and that
# generation's own spouse identifies the father beyond doubt — which is how
# David's father stops being «ambiguous, 6 of this name» on David's page.
try:
    _DL = json.load(open(os.path.join(DATA, "directline.json"), encoding="utf-8"))["generations"]
    _DLP = json.load(open(os.path.join(DATA, "directline-pids.json"), encoding="utf-8"))["generations"]
except Exception:
    _DL, _DLP = [], []
_FILLER = {"born", "nee", "n", "the", "of", "and"}


def _wifekey(x):
    """A wife's name reduced to the words that identify her.

    The two files write her differently and both are right. The household
    says «Hedviga Blažević (Defranceski)»; the direct line says «Hedviga,
    born Blažević». The married surname, the maiden surname and the word
    «born» all move about, so the comparison is on the set of real words and
    a match is one set containing the other — «cheryl lerena» inside «cheryl
    anne defranceski nee lerena».
    """
    return frozenset(w for w in _nm(x or "").split() if w and w not in _FILLER)


_DL_BY_HUSBAND = {}
for _g, _gp in zip(_DL, _DLP):
    _sp = _g.get("spouse")
    _spn = _sp.get("name") if isinstance(_sp, dict) else _sp
    if _spn and _gp.get("pid"):
        _DL_BY_HUSBAND.setdefault(_nm(_g["name"]), []).append((_wifekey(_spn), _gp["pid"]))
_ROW_BY_PID = {r["pid"]: r for r in roster["rows"] if r.get("pid")}


def _direct_line_row(name, hh):
    """The roster row this name is, when the household is a direct-line one."""
    if not hh: return None
    f = _nm(hh.get("father") or "")
    k = _nm(name)
    if k != f: return None
    wife = _wifekey(hh.get("mother"))
    if not wife: return None
    hits = [pid for wk, pid in _DL_BY_HUSBAND.get(f, [])
            if wk and (wk <= wife or wife <= wk)]
    return _ROW_BY_PID.get(hits[0]) if len(hits) == 1 else None


def _row_fitting(name, hh=None, child=None):
    """The roster row of this name that fits where the name is standing.

    A parent in a household begun in `from` was born twelve to sixty years
    before it and had not died before it. A child has its own birth year in
    the household record. Where the candidates cannot be told apart the first
    is returned, exactly as before — this narrows the guess, it does not
    invent certainty.
    """
    k = _nm(name)
    cands = ROWS_BY_NAME.get(k) or []
    if len(cands) <= 1:
        return ROW_BY_NAME.get(k)
    _dl = _direct_line_row(name, hh)
    if _dl is not None: return _dl
    if child and (_yr(child.get("birth")) or _yr(child.get("death"))):
        cy = _yr(child.get("birth")) or _yr(child.get("death"))
        fit = [r for r in cands
               if (isinstance(r.get("b"), int) and abs(r["b"] - cy) <= 6)
               or (isinstance(r.get("d"), int) and abs(r["d"] - cy) <= 6)]
        if len(fit) == 1: return fit[0]
    f = hh.get("from") if hh else None
    if isinstance(f, int):
        fit = []
        for r in cands:
            b, d = r.get("b"), r.get("d")
            if not isinstance(b, int): continue
            if not (12 <= f - b <= 60): continue
            if isinstance(d, int) and d < f: continue
            fit.append(r)
        if len(fit) == 1: return fit[0]
        if len(fit) > 1:
            # TWO PEOPLE OF THIS NAME BOTH FIT, so this node does not know who
            # it is. Returning the first — which is what `ROW_BY_NAME` does —
            # is how «Ivan Defranceski, 1829 – 1895» came to be printed as the
            # father of a man born in 1951: both the 1894 and the 1925 Ivan fit
            # a household begun in 1948, and the fallback reached past them
            # both to the oldest man of the name.
            #
            # NOT A BROKEN LINK, A WORKING LINK TO THE WRONG MAN, which is the
            # failure this estate found twice tonight and the harder one to
            # notice. So the name is drawn with no dates and no link, and the
            # reader is sent to the name index to choose.
            return None
    return ROW_BY_NAME.get(k) if len(cands) <= 1 else None

def _dates(row, child=None):
    if row and row.get("living"): return ""
    if child and (child.get("birth") or child.get("death")):
        b, d = child.get("birth") or "", child.get("death") or ""
        return f"{b} – {d}" if b and d else (f"b. {b}" if b else f"d. {d}")
    if not row: return ""
    b, d = row.get("b"), row.get("d")
    if b and d: return f"{b} – {d}"
    if b: return f"b. {b}"
    if d: return f"d. {d}"
    return ""

# Read from a register page · read off an index · off the family tree.
# The band under every name on a person page says which, and it used to say
# «the archive's own line» for anybody flagged as the compiler's kin — which is
# a statement about KINSHIP and was being printed in the place where the reader
# looks for PROVENANCE. Ninety-four rows whose only source is David's family
# tree were wearing the strongest band on the page, including every person the
# Australian and Crikvenica branches brought in on 15 and 16 September.
#
# The evidence now wins, and «line» is kept for the drawn descent and for the
# kin who have no other source at all:
READ_SRC = {"read", "golo", "eleven"}      # all three came off register pages

def _via(row, hh=None, child=None):
    if hh and hh.get("src") == "read": return "read"
    if child and child.get("id"): return "index"
    if row:
        if row.get("direct"): return "line"
        if row.get("src") in READ_SRC: return "read"
        if row.get("ark"): return "index"
        if row.get("mh"): return "tree"
        if row.get("mine"): return "line"
        if hh: return "index" if hh.get("src") == "index" else ""
    if hh and hh.get("src") == "index": return "index"
    return ""

def node(name, hh=None, child=None, small=False):
    if not name or name == "—": return None
    row = _row_fitting(name, hh, child)
    sl = slugify(row["name"]) if row else None
    n = {"n": name, "dt": _dates(row, child), "via": _via(row, hh, child)}
    if sl: n["slug"] = sl
    # AND THE PID, so a person page can link person-to-person. `slug` is the
    # NAME page and stays, because /who/ needs it; this is the address of the
    # individual the node resolved to, and it is only ever set when the node
    # knows which individual that is.
    if row and row.get("pid"): n["pid"] = row["pid"]
    elif len(ROWS_BY_NAME.get(_nm(name)) or []) > 1:
        # Several people of this archive carry this name and the household
        # cannot say which one this is. Said out loud rather than guessed.
        n["ambiguous"] = len(ROWS_BY_NAME[_nm(name)])
    if small: n["small"] = True
    # Does this person head a household of their own? A sister listed as a bare
    # name looks like the end of a line, and Petrica Defranceski is not: she
    # married and had two daughters. Say so on the box rather than making the
    # reader click to find out.
    own = PARENT_OF.get(_nm(name)) or []
    kids = max((len(h.get("children") or []) for h in own), default=0)
    if kids: n["own"] = kids
    return n

VIA_WORD = {"line": "the archive's own line", "read": "a register this archive has read",
            "index": "a FamilySearch index entry", "tree": "the family tree, unverified"}


def _yr(x):
    m = re.search(r"\b(1[3-9]\d\d|20\d\d)\b", str(x or ""))
    return int(m.group()) if m else None

def _fits_child(myY, me, hh, t, estY=None):
    """Is the person plausibly THIS household's child? A name is not enough."""
    cY = _yr(me.get("birth")) or _yr(me.get("death"))
    if myY is None and estY is not None and cY is not None:
        # only an estimate to test against, so the window is deliberately loose
        if abs(estY - cY) <= 25: return True
        t["gate"].append(["estimate", hh.get("father") or "", hh.get("mother") or "", str(cY)])
        return False
    if myY is None or cY is None:
        t["gate"].append(["unchecked", hh.get("father") or "", hh.get("mother") or "", ""])
        return True
    if abs(myY - cY) <= 6: return True
    t["gate"].append(["dropped", hh.get("father") or "", hh.get("mother") or "", f"{cY}"])
    return False

def _fits_parent(myY, hh, t, estY=None, dieY=None):
    """Is the person plausibly a PARENT in this household?

    A DEATH YEAR ENDS THE QUESTION and this did not ask for one. Ivan
    Defranceski of 1943 died in 1945, aged two, and was handed Cheryl Lerena
    as a wife and David as a son — because the only test was that the
    household began between twelve and sixty years after his birth, and a
    household of 1980 does sit in that window for a boy born in 1943. He was
    thirty-five years dead. Nothing but a death date can refuse that, so a
    death date is now asked for.
    """
    f, to = hh.get("from"), hh.get("to")
    if dieY is not None and isinstance(f, int) and f > dieY:
        t["gate"].append(["dead", hh.get("father") or "", hh.get("mother") or "",
                          f"died {dieY}, household from {f}"])
        return False
    if myY is None and estY is not None and isinstance(f, int):
        if 5 <= f - estY <= 75: return True
        t["gate"].append(["estimate", hh.get("father") or "", hh.get("mother") or "", str(f)])
        return False
    if myY is None or not isinstance(f, int):
        t["gate"].append(["unchecked", hh.get("father") or "", hh.get("mother") or "", ""])
        return True
    gap = f - myY
    if 12 <= gap <= 60: return True
    t["gate"].append(["dropped", hh.get("father") or "", hh.get("mother") or "",
                      f"{f}\u2013{to}" if to else str(f)])
    return False

def ptree(name, row=None):
    """The family, for ONE PERSON.

    `row` is that person's roster row. Pass it and the year gates below —
    `_fits_child`, `_fits_parent` — test the households against THIS person's
    dates. Leave it out and the function falls back to ROW_BY_NAME, which
    keeps a name page working and is the reason this needed fixing:
    `ROW_BY_NAME.setdefault` means THE FIRST ROSTER ROW OF A NAME WINS, so
    every later person of that name was gated against a stranger's year.

    /who/ivan-defranceski/ is what that produces. Three Ivan Defranceski
    share the name-slug — 1925, 1943, 1951 — the first row is the one who
    died in 1895, and the tree came out as «Ivan Defranceski, 1829 – 1895»
    with CHERYL LERENA as his wife and DAVID as his son. One man's dates,
    another man's wife, a third man's child, on one page.

    Nothing new is asserted here. The gates were always person-level; they
    were simply handed the wrong person.
    """
    k = _nm(name)
    if not k: return None
    up, down = CHILD_IN.get(k, []), PARENT_OF.get(k, [])
    # no household either way — but one register row may still name this person's parents
    if not up and not down and len(REG_BY_NAME.get(k, [])) != 1: return None
    if row is None: row = ROW_BY_NAME.get(k)
    t = {"self": {"n": name, "dt": _dates(row), "via": _via(row)}}
    myY = estY = None
    if row:
        for _f in ("b", "d"):
            if isinstance(row.get(_f), int): myY = row[_f]; break
        if myY is None and isinstance(row.get("bEst"), int):
            estY = row["bEst"]
            t["est"] = [estY, row.get("bEstRange") or [estY - 11, estY + 9], row.get("yfrom") or ""]
    t["gate"] = []
    if row and row.get("rel"): t["self"]["rel"] = row["rel"]
    if row and row.get("me"): t["self"]["me"] = True
    up = [(hh, me) for hh, me in up if _fits_child(myY, me, hh, t, estY)]
    _dieY = _yr(row.get("d")) if row and row.get("d") else None
    # A CHILD WHO DIED A CHILD IS NOBODY'S PARENT, and the household gates
    # cannot say so on their own: a household with no `from` year falls
    # through `_fits_parent` as «unchecked», which is the right default for a
    # grown man and the wrong one for Ivan Defranceski of 1943, who died in
    # 1945 aged two and was given Cheryl Lerena as a wife and David as a son.
    # Fifteen is deliberately generous; this refuses infants, not marriages.
    if myY is not None and _dieY is not None and _dieY - myY < 15:
        for _hh in down:
            t["gate"].append(["died a child", _hh.get("father") or "",
                              _hh.get("mother") or "", f"{myY}\u2013{_dieY}"])
        down = []
    down = [hh for hh in down if _fits_parent(myY, hh, t, estY, _dieY)]
    if up:
        hh, me = up[0]
        par = [node(hh.get("father"), hh), node(hh.get("mother"), hh)]
        t["parents"] = [x for x in par if x]
        t["parentsPlace"] = hh.get("place") or ""
        t["parentsHref"] = "/households/"
        sibs = [node(c["name"], hh, c, small=True) for c in (hh.get("children") or [])
                if _nm(c.get("name")) != k]
        t["siblings"] = [x for x in sibs if x]
        if me.get("birth"): t["self"]["dt"] = t["self"]["dt"] or f"b. {me['birth']}"
    if down:
        hh = down[0]
        mine = _nm(hh.get("father")) == k
        t["spouse"] = node(hh.get("mother") if mine else hh.get("father"), hh)
        kids = [node(c["name"], hh, c) for c in (hh.get("children") or [])]
        t["children"] = [x for x in kids if x]
        t["span"] = f"{hh.get('from','')}–{hh.get('to','')}".strip("–")
        t["childrenPlace"] = hh.get("place") or ""
    t["upN"], t["downN"] = len(up), len(down)
    t["dropped"] = [g for g in t["gate"] if g[0] == "dropped"]
    t["unchecked"] = [g for g in t["gate"] if g[0] == "unchecked"]
    t["estRej"] = [g for g in t["gate"] if g[0] == "estimate"]
    t.pop("gate", None)
    # No household could be matched. But the index row that names this person may
    # name their parents too — draw that, clearly marked as a single index entry.
    if not t.get("parents"):
        cand = REG_BY_NAME.get(k) or []
        # the same date gate the household path uses. Without it a Domenico de' Franceschi
        # of the 1560s collects the parents of a Domenico baptised at Svetvinčenat in the 1800s.
        if len(cand) == 1 and myY is not None:
            rY = _yr(cand[0].get("y")) or _yr(cand[0].get("says"))
            if rY is not None and abs(rY - myY) > 6:
                t.setdefault("dropped", []).append(
                    ["dropped", cand[0].get("o", [""])[0] if cand[0].get("o") else "", "", str(rY)])
                cand = []
        if len(cand) == 1:
            e = cand[0]
            ps = [o for o in (e.get("o") or []) if o and o != "—"][:2]
            if ps:
                t["parents"] = [x for x in (node(p) for p in ps) if x]
                for x in t["parents"]: x["via"] = "index"
                t["parentsPlace"] = (e.get("pl") or "").strip()
                t["parentsHref"] = "/register/"
                t["parentsFromRow"] = True
                t["parentsCaveat"] = ("Drawn from the one indexed entry that names this person, not from a "
                                      "household this archive has built. The entry names these people together; "
                                      "it does not prove the relationship it implies.")

    if not t.get("parents") and not t.get("children") and not t.get("spouse"):
        return {"none": True, "dropped": t["dropped"], "self": t["self"]} if t["dropped"] else None

    # every relationship drawn, counted by how it is known
    rel = (t.get("parents") or []) + (t.get("siblings") or []) + (t.get("children") or [])
    if t.get("spouse"): rel = rel + [t["spouse"]]
    tally = {}
    for x in rel: tally[x["via"]] = tally.get(x["via"], 0) + 1
    t["tally"] = sorted(tally.items(), key=lambda kv: VIA_RANK.get(kv[0], 9))
    t["nrel"] = len(rel)
    t["nread"] = tally.get("read", 0) + tally.get("line", 0)
    # a repeated forename among the children is the classic false join
    seen, dup = {}, set()
    for x in (t.get("children") or []):
        g = " ".join(_given(x["n"])) if _given(x["n"]) else x["n"]
        if g in seen: dup.add(g)
        seen[g] = 1
    t["dupNames"] = sorted(dup)
    return t


# ---- the name, and what only collides with it ---------------------------
# This archive studies a NAME, so it collects on the name rather than on the
# bloodline. A study of a name still has to say where the name stops, and on
# 17 September 2026 David ruled that it stops before the diminutive:
# De Franceschi is a genitive plural, «of the Franceschi»; Franceschini and
# its kin are diminutives of Francesco, formed separately. They are held —
# thirty-five of them have pages here, swept up by an Austrian harvest — and
# they are marked, because deleting a person over a surname ruling would be
# its own dishonesty and the next researcher needs to see they were set aside.
#
# The test is on the SURNAME. «Franceschina De Franceschi» is a Franceschina
# whose surname is ours, and must not be caught by it.
_nms = _raw_early("names").get("scope") or {}
ADJACENT = [a["form"] for a in _nms.get("adjacent") or []]
_adj_re = re.compile("|".join(re.escape(a) for a in ADJACENT), re.I) if ADJACENT else None
_ours_re = re.compile(r"\bde\s*franceschi|defranceschi|defranceski|de\s*franceski|franceschich", re.I)

def adjacent_name(name):
    """A surname that collides with this one and is not it."""
    if not _adj_re: return None
    n = str(name or "")
    if _ours_re.search(n): return None          # the surname here is ours
    m = _adj_re.search(n)
    return m.group(0) if m else None


# ---- the same name, written in another language ------------------------
# /your-name/ reconciles 645 forms of 73 given names across seven languages,
# and until 17 September 2026 NOTHING read it. Both normalisers in this
# archive — _nm here and norm() in lib/people.js — fold the SURNAME and stop,
# so «Josephus», «Giuseppe» and «Josip» were three strangers to every join on
# the site, and /name/ said in as many words that a normaliser carried the
# whole table. It did not.
#
# This does NOT merge them. Identity here is by name, deliberately, and
# collapsing Ivan into Giovanni by machine would be the same mistake this
# archive keeps correcting other people for. It cross-references: a page now
# says which other pages hold its own name in another language, and the reader
# decides. 327 of 1,122 pages turn out to be in such a group.
_gn = _raw_early("givennames")
CANON = {}
for _r in _gn.get("rows", []):
    for _k in _gn.get("langs", []):
        for _f in (_r.get(_k) or "").split(","):
            _f = _f.strip()
            if _f and _f != "\u2014":
                CANON.setdefault(_nm(_f), _r["canon"])
for _sl in _gn.get("slips", []):
    CANON.setdefault(_nm(_sl["form"]), _sl["canon"])

def fold_given(name):
    """The name with every given name replaced by its canonical form."""
    out = []
    for w in _nm(name).split():
        out.append(w if w in ("de", "franceschi") else CANON.get(w, w))
    return " ".join(out)

# ---- linear pedigrees: the Omis chart and the direct line, as chains ----
CHAINS = []
def _raw(name):
    fp = os.path.join(DATA, name + ".json")
    if not os.path.exists(fp): return {}
    try: return json.load(open(fp, encoding="utf-8"))
    except Exception: return {}

_om = _raw("omis")
if isinstance(_om, dict) and isinstance(_om.get("line"), list):
    CHAINS.append({"label": "The Omiš chart — twenty generations, 1318 to 1992",
                   "href": "/omis-line/", "caveat": "A made family chart, not a register.",
                   "people": [{"n": r[0], "d": " · ".join(x for x in r[1:] if x)} for r in _om["line"] if r and r[0]]})
_dl = _raw("directline")
if isinstance(_dl, dict) and isinstance(_dl.get("generations"), list):
    CHAINS.append({"label": "The direct line — Gologorica to Brisbane",
                   "href": "/direct-line/", "caveat": "",
                   "people": [{"n": g.get("name") or "", "d": " · ".join(str(x) for x in (g.get("born"), g.get("died"), g.get("place")) if x)}
                              for g in _dl["generations"] if g.get("name")]})

CHAIN_AT = {}
for ci, ch in enumerate(CHAINS):
    for i, pr in enumerate(ch["people"]):
        k = _nm(pr["n"])
        if k: CHAIN_AT.setdefault(k, []).append((ci, i))

def _given(x):
    """The person's own name with the surname stripped, so it matches a chart's bare forename."""
    k = _nm(x)
    return re.sub(r"\s*de franceschi\s*$", "", k).strip()

def chain_tree(name):
    g = _given(name)
    if not g: return None
    out = []
    for ci, ch in enumerate(CHAINS):
        for i, pr in enumerate(ch["people"]):
            if _given(pr["n"]) != g: continue
            out.append({"label": ch["label"], "href": ch["href"], "caveat": ch["caveat"],
                        "above": ch["people"][i-1] if i > 0 else None,
                        "self": ch["people"][i],
                        "below": ch["people"][i+1] if i + 1 < len(ch["people"]) else None,
                        "pos": i + 1, "of": len(ch["people"])})
    return out or None

old = json.load(open(os.path.join(DATA, "dossiers.json"), encoding="utf-8"))
people = {}

# people the roster names
by_slug = {}
for r in roster["rows"]:
    by_slug.setdefault(slugify(r["name"]), []).append(r)

for slug, rows in by_slug.items():
    name = rows[0]["name"]
    needle = re.sub(r"\s*\(.*?\)\s*", "", name).strip()
    if len(needle) < 5:
        continue
    hits, pages = [], []
    for dataname, blob in blobs.items():
        href, title = route_of[dataname]
        if dataname in TABULAR:
            if needle in blob and not any(pp["h"] == href for pp in pages):
                pages.append({"h": href, "t": title})
            continue
        for m in re.finditer(re.escape(needle), blob):
            a, b = max(0, m.start() - 260), min(len(blob), m.end() + 260)
            snip = plain(blob[a:b])
            snip = " ".join(snip.split(" ")[1:-1]) if len(snip.split(" ")) > 6 else snip
            hits.append({"page": href, "title": title, "text": snip})
            if len(hits) >= 24: break
        if any(h["page"] == href for h in hits) and not any(p["h"] == href for p in pages):
            pages.append({"h": href, "t": title})
    facts = []
    r0 = rows[0]
    yrs = "–".join([str(r0["b"]) if r0.get("b") else "", str(r0["d"]) if r0.get("d") else ""]).strip("–")
    if r0.get("place"):
        facts.append(["Place", r0["place"]] + ([f"/places/{r0['placeSlug']}/"] if r0.get("placeSlug") else []))
    if yrs: facts.append(["Years", yrs + (f" \u00b7 from {r0['yfrom']}" if r0.get("yfrom") else "")])
    elif YEAR_FROM.get(slug):
        # the roster has no year, but a register this archive read does. The
        # page said «estimated, not recorded» over the top of a date that was
        # sitting in the repository. It says the date now.
        _y = YEAR_FROM[slug]
        facts.append(["Years", f"{_y['says']} \u2014 read in the register, not estimated"])
    elif r0.get("bEst"):
        _rg = r0.get("bEstRange") or []
        facts.append(["Years", f"born about {r0['bEst']}" + (f" (somewhere {_rg[0]}\u2013{_rg[1]})" if len(_rg) == 2 else "") + " \u2014 estimated, not recorded"])
    if r0.get("parish"): facts.append(["Parish", r0["parish"]])
    if r0.get("line") and legend.get(r0["line"]): facts.append(["Line", legend[r0["line"]].split("—")[0].strip()])
    if r0.get("me"): facts.append(["Who this is", "David — the compiler of this archive"])
    elif r0.get("rel"): facts.append(["Relationship to David", r0["rel"]])
    if r0.get("living"): facts.append(["Living", "named only — no dates, no places, no photograph"])
    if r0.get("img"): facts.append(["Read from", r0["img"]])
    srcs = sorted({srclabel.get(r["src"], r["src"]) for r in rows})
    if srcs: facts.append(["Found in", " · ".join(srcs)])
    notes = [r["note"] for r in rows if r.get("note")]
    people[slug] = {
        "name": name, "slug": slug, "n": len(hits) or len(rows),
        "pages": pages or [{"h": r0.get("href") or "/people/", "t": "Everyone"}],
        "hits": hits,
        "facts": facts,
        "known": notes[0] if notes else "",
        "more": notes[1:],
        "records": (BY_SLUG.get(slug, []) + RECORDS.get(" ".join(_key(name)), []))[:12]
                    or [mh_record(r) for r in rows if r.get("mh") and r["src"] == "myheritage"][:2],
        "tree": mini_tree(name),
        "ptree": ptree(name),
        "rec": record_strip(rows),
        "chain": chain_tree(name),
        "recyear": YEAR_FROM.get(slug),
        "adjacent": adjacent_name(name),
        "roster": True,
    }

# ONE ENTRY PER PERSON, keyed on the pid, beside the name-keyed `people`.
#
# The name map stays exactly as it was: /who/ is an index of everybody sharing
# a name and needs it. This is what a PERSON page reads, and the only
# difference is that each person's tree is computed against their own roster
# row rather than against the first row that happened to carry their name.
persons = {}
for _r in roster["rows"]:
    _pid = _r.get("pid")
    if not _pid: continue
    _t = ptree(_r["name"], _r)
    if not _t: continue
    persons[_pid] = {"pid": _pid, "name": _r["name"], "ptree": _t}
print(f"  persons with a tree of their own: {len(persons)} of "
      f"{sum(1 for r in roster['rows'] if r.get('pid'))}")

# group the pages that are one name in more than one language, and say so on
# each of them — sorted, and capped, because a page is a page and not a list.
_by_fold = {}
for _slug, _p in people.items():
    _by_fold.setdefault(fold_given(_p["name"]), []).append(_slug)
for _fk, _slugs in _by_fold.items():
    if len(_slugs) < 2: continue
    for _slug in _slugs:
        people[_slug]["alsoWritten"] = sorted(
            ({"slug": s2, "name": people[s2]["name"]} for s2 in _slugs if s2 != _slug),
            key=lambda x: x["name"])[:24]

# The fold above keeps the WHOLE name, so it never joins a long baptismal name
# to its own short form. Fiume christened children «Franciscum Josephum
# Aloysium Joannem Nepomuc» and the index then carried that at four different
# lengths — four pages, one boy, and not a link between them. Camillo Romano
# never reached Camillo either.
#
# So: a second pass on FIRST given name plus BIRTH YEAR, which is specific
# enough to mean something and is exactly the case the first pass misses.
# It only ever adds to alsoWritten; it never replaces what the fold found.
_born = {}
for _r in roster["rows"]:
    if _r.get("b"):
        _born.setdefault(slugify(_r["name"]), _r["b"])

def _first_given(n):
    _t = re.sub(r"\(.*?\)", " ", n or "")
    _t = re.sub(r"(?i)\b(de\s*)?fran[czs]{1,2}[eh]?sch?i\w*|defranceski\w*|franceschich\w*|franceschin\w*", " ", _t)
    _t = unicodedata.normalize("NFD", _t)
    _t = "".join(c for c in _t if unicodedata.category(c) != "Mn")
    _t = re.sub(r"[^A-Za-z ]", " ", _t).lower()
    for _w in _t.split():
        if _w in ("de", "di", "del", "della", "dei", "da", "von", "van", "in", "croatian", "the", "or"):
            continue
        return CANON.get(_w, _w)
    return ""

_by_year = {}
for _slug, _p in people.items():
    _b = _born.get(_slug)
    _fg = _first_given(_p["name"])
    if _b and _fg:
        _by_year.setdefault((_fg, _b), []).append(_slug)
for _k, _slugs in _by_year.items():
    if len(_slugs) < 2: continue
    for _slug in _slugs:
        _have = {x["slug"] for x in (people[_slug].get("alsoWritten") or [])}
        _add = [{"slug": s2, "name": people[s2]["name"]}
                for s2 in _slugs if s2 != _slug and s2 not in _have]
        if not _add: continue
        people[_slug]["alsoWritten"] = sorted(
            (people[_slug].get("alsoWritten") or []) + _add,
            key=lambda x: x["name"])[:24]

# keep anything that already had a page and is not a roster person
kept = 0
for slug, p in old.get("people", {}).items():
    if slug not in people:
        # A page carried over from an earlier build is still a person, and the
        # record files still have records for them. This branch used to
        # setdefault("records", []) and stop, so Nicolaa De Franceschi's page
        # said nothing had been read while fsrecords.json held her birth.
        p.setdefault("facts", []); p.setdefault("known", ""); p.setdefault("more", [])
        p["records"] = (p.get("records") or []) or (BY_SLUG.get(slug, []) + RECORDS.get(" ".join(_key(p.get("name"))), []))[:12]
        if BY_SLUG.get(slug) and not p.get("recyear"): p["recyear"] = YEAR_FROM.get(slug)
        p.setdefault("tree", mini_tree(p.get("name"))); p.setdefault("chain", chain_tree(p.get("name")))
        p["adjacent"] = adjacent_name(p.get("name"))
        p["roster"] = False
        people[slug] = p
        kept += 1

out = {"note": old.get("note", ""), "people": people}
out["note"] = ("A dossier is every mention of a name anywhere in this archive's data, gathered automatically and "
  "linked back to the page it appears on, with what the archive knows about the person set out at the top. "
  "**Identity here is by NAME, not by resolved individual**: where two people share a name they share a dossier, "
  "and the archive says so rather than guessing. Rebuilt from the roster, so every person the archive can name "
  "has a page — including the ones read straight off a register that no index anywhere contains.")
out["persons"] = dict(sorted(persons.items()))
json.dump(out, open(os.path.join(DATA, "dossiers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"roster people {len(by_slug)} · pages written {len(people)} · non-roster kept {kept}")

_orph = orphan_report(ROOT, set(by_slug), set(people)) if "orphan_report" in dir() else []
if _orph:
    print("ORPHANED BY A RENAME: %d — %s" % (len(_orph), ", ".join(_orph)))
    print("  (a page whose slug was a roster row in a recent commit and is not one now)")

# --- orphan check (renames) ---
# This builder is additive and never prunes, which is right for the 200-odd
# pages that come from somewhere other than the roster. It is wrong for a page
# left behind when a roster row is RENAMED: the old slug keeps its page, the
# page keeps whatever the person used to be called, and nothing ever notices.
# One was found on 22 September 2026, an hour after the rename that made it.
#
# A rename orphan is distinguishable from a legitimate non-roster page by its
# history: it was a roster slug in a recent commit and is not one now. This
# prints them; it does not delete, because deciding what a stale page should
# become is a person's job.
def orphan_report(root, current_slugs, page_slugs, depth=12):
    import subprocess, json as _json
    try:
        heads = subprocess.run(["git", "log", "--format=%H", "-%d" % depth, "--",
                                "site/src/data/roster.json"],
                               cwd=root, capture_output=True, text=True).stdout.split()
    except Exception:
        return []
    ever = set()
    for h in heads:
        try:
            t = subprocess.run(["git", "show", h + ":site/src/data/roster.json"],
                               cwd=root, capture_output=True, text=True).stdout
            for r in _json.loads(t)["rows"]:
                ever.add(slugify(r["name"]))
        except Exception:
            pass
    return sorted((ever - current_slugs) & page_slugs)
