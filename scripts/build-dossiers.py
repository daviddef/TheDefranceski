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
    if r.get("place"): bits.append(r["place"])
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



# ---- the pedigree chart: parents / self+spouse / children / siblings, with provenance ----
# Provenance tiers, strongest first. They are NOT interchangeable and the page says so.
#   line     the archive's own descent, argued on /direct-line/
#   read     a register this archive has read with its own eyes
#   index    a FamilySearch index entry — a transcription, not the page
#   tree     David's MyHeritage tree, unverified here
VIA_RANK = {"line": 0, "read": 1, "index": 2, "tree": 3, "": 4}

ROW_BY_NAME = {}
for _r in roster["rows"]:
    ROW_BY_NAME.setdefault(_nm(_r["name"]), _r)
    ROW_BY_NAME.setdefault(_nm(re.sub(r"\s*\(.*?\)\s*", "", _r["name"])), _r)

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

def _via(row, hh=None, child=None):
    if hh and hh.get("src") == "read": return "read"
    if child and child.get("id"): return "index"
    if row:
        if row.get("direct") or row.get("mine"): return "line"
        if row.get("src") == "read": return "read"
        if row.get("ark"): return "index"
        if row.get("mh"): return "tree"
        if hh: return "index" if hh.get("src") == "index" else ""
    if hh and hh.get("src") == "index": return "index"
    return ""

def node(name, hh=None, child=None, small=False):
    if not name or name == "—": return None
    row = ROW_BY_NAME.get(_nm(name))
    sl = slugify(row["name"]) if row else None
    n = {"n": name, "dt": _dates(row, child), "via": _via(row, hh, child)}
    if sl: n["slug"] = sl
    if small: n["small"] = True
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

def _fits_parent(myY, hh, t, estY=None):
    """Is the person plausibly a PARENT in this household?"""
    f, to = hh.get("from"), hh.get("to")
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

def ptree(name):
    k = _nm(name)
    if not k: return None
    up, down = CHILD_IN.get(k, []), PARENT_OF.get(k, [])
    if not up and not down: return None
    row = ROW_BY_NAME.get(k)
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
    down = [hh for hh in down if _fits_parent(myY, hh, t, estY)]
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
        "records": (RECORDS.get(" ".join(_key(name)), [])[:12]
                    or [mh_record(r) for r in rows if r.get("mh") and r["src"] == "myheritage"][:2]),
        "tree": mini_tree(name),
        "ptree": ptree(name),
        "chain": chain_tree(name),
        "roster": True,
    }

# keep anything that already had a page and is not a roster person
kept = 0
for slug, p in old.get("people", {}).items():
    if slug not in people:
        p.setdefault("facts", []); p.setdefault("known", ""); p.setdefault("more", []); p.setdefault("records", []); p.setdefault("tree", mini_tree(p.get("name"))); p.setdefault("chain", chain_tree(p.get("name")))
        p["roster"] = False
        people[slug] = p
        kept += 1

out = {"note": old.get("note", ""), "people": people}
out["note"] = ("A dossier is every mention of a name anywhere in this archive's data, gathered automatically and "
  "linked back to the page it appears on, with what the archive knows about the person set out at the top. "
  "**Identity here is by NAME, not by resolved individual**: where two people share a name they share a dossier, "
  "and the archive says so rather than guessing. Rebuilt from the roster, so every person the archive can name "
  "has a page — including the ones read straight off a register that no index anywhere contains.")
json.dump(out, open(os.path.join(DATA, "dossiers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"roster people {len(by_slug)} · pages written {len(people)} · non-roster kept {kept}")
