#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The research map: every record book we can name, where it is, and how far we got.

One place, several providers. A parish can sit in FamilySearch's Croatian
collection, in its Italian one, in the Pazin state archive's own register list
and on Antenati, and each of those knows something the others do not — Pazin
alone says who holds the paper and whether it has been digitised at all.

Sources, and where each comes from:

    fs-hr     FamilySearch, Croatia Church Books 2040054. Walked from the
              collection's own waypoint tree in David's Chrome (the in-app
              browser's egress IP is blocked), landed at data/fs-catalogue.json.
    fs-it     FamilySearch, Udine civil registration 1939238 — the Carnia
              comuni, already in site/src/data/carnia-books.json.
    dapa      Državni arhiv u Pazinu's own register list, site/src/data/
              registers.json. Fourteen places, and the only source that says
              «digitised: no».

Coverage was three states until the cataloguing finished and made them useless:
1,219 places gold against three grey is not a picture, it is a wash. So the
shading now carries DEPTH — how much is actually on the shelf — and keeps one
colour for the only number that matters:

    none   nothing catalogued here at all
    thin   one or two volumes
    some   three to nine
    deep   ten or more
    read   the search register names the place as a source, whatever its size

    for c in HR BA SI RS HU IT AT ME; do
      curl -sO https://download.geonames.org/export/dump/$c.zip && unzip -o $c.zip $c.txt
    done
    python3 scripts/build-research-map.py --gaz .

Writes site/src/data/researchmap.json and one Atlas blob per source view.
"""
import sys, os, re, json, collections, itertools, unicodedata, urllib.parse
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gazcheck

NS   = {"k": "http://www.opengis.net/kml/2.2"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PUB  = os.path.join(ROOT, "site", "public")
KML  = os.path.join(ROOT, "data", "genealogy-resources-croatia.kml")
FSC  = os.path.join(ROOT, "data", "fs-catalogue.json")
ANT  = os.path.join(DATA, "antenati-catalogue.json")
ELS  = os.path.join(DATA, "fs-elsewhere.json")
CAT  = os.path.join(DATA, "sweep.json")
RDS  = os.path.join(DATA, "reads.json")

STOP = {"zupa", "jaksic", "velika", "sveti", "grad", "novi", "stari"}
LAYERS = {"Roman Catholic": "rc", "Orthodox": "orth", "Greek Catholic": "gc",
          "Jewish": "jew", "Military": "mil", "Reformed Christian": "ref",
          "Civil": "civil", "Evangelical": "ev"}
LABEL  = {"rc": "Roman Catholic", "orth": "Orthodox", "gc": "Greek Catholic",
          "jew": "Jewish", "mil": "Military", "ref": "Reformed",
          "civil": "Civil", "ev": "Evangelical"}
SOURCES = [
    ("fs-hr",    "FamilySearch — Croatia",  "Croatia, Church Books 1516–1994 (collection 2040054)"),
    ("fs-it",    "FamilySearch — Udine",    "Italy, Udine civil registration (collection 1939238)"),
    ("dapa",     "Pazin State Archive",     "Državni arhiv u Pazinu, its own register list"),
    ("antenati", "Antenati",                "Portale Antenati, Archivio di Stato di Udine — the Carnia civil registers"),
    ("fs-it-pola", "FamilySearch — Pola & Trieste",
     "Italy, Pola and Trieste, Catholic Church Records 1593–1941 (collection 2152685) — Croatian Istrian parishes filed by Italy"),
    ("fs-si-mj",  "FamilySearch — Međimurje",
     "Slovenia, Prekmurje and Međimurje, Civil Registers 1895–1918 (collection 1985107) — Croatian towns under Hungarian county names"),
    ("fs-hr-delnice", "FamilySearch — Delnice",
     "Croatia, Delnice Deanery Catholic Church Books 1571–1926 (collection 1875189) — browsable only by film"),
    ("fs-cat",     "FamilySearch catalogue",
     "The library catalogue rather than the image collections — printed editions, microfilms and transcriptions, swept by place-authority id across 75 places"),
]
DAPA_TYPE = {"MKR": "Births", "MKV": "Marriages", "MKU": "Deaths", "SD": "Church Census"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\(.*?\)", " ", s).split(",")[0]
    return re.sub(r"[^a-z0-9]+", "", s)

def volkey(t):
    """Years and letters only, order-insensitive — the same key the map panel
    uses to recognise that «Births (Rođeni) 1716-1884» and «1716–1884 · Births
    (Rođeni)» are one book. It is what lets the read ledger name a volume in
    the words a reader sees rather than by an ark nobody can check."""
    t = unicodedata.normalize("NFKD", t or "")
    years = "".join(sorted(re.findall(r"1[5-9]\d\d", t)))
    word = re.sub(r"[^a-z]+", "", t.lower())
    return years + "|" + word

def ledger():
    """site/src/data/reads.json — one row per volume somebody has actually
    opened. Empty is the honest starting state: before this file there was no
    place in the archive to record that a particular book had been read, and
    the map said «none read» under a parish it knew had been worked."""
    if not os.path.exists(RDS):
        return {}
    d = json.load(open(RDS, encoding="utf-8"))
    out = {}
    for r in d.get("reads", []):
        st = r.get("state", "read")
        if st not in ("read", "part"):
            continue
        out[(norm(r["place"]), volkey(r["volume"]))] = r
    return out

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)

def gazetteer(d):
    g = {}
    for cc in ("HR", "BA", "SI", "RS", "HU", "IT", "AT", "ME"):
        p = os.path.join(d, cc + ".txt")
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            f = line.rstrip("\n").split("\t")
            if len(f) < 15 or f[6] not in ("P", "A"):
                continue
            try:
                lat, lon, pop = float(f[4]), float(f[5]), int(f[14] or 0)
            except ValueError:
                continue
            rank = (cc == "HR", f[6] == "P", pop)
            alts = [x.strip() for x in (f[3] or "").split(",") if x.strip()]
            names = {f[1], f[2]} | set(alts)
            # GeoNames files a hamlet too small to have its own entry under a
            # COMPOUND name — «Osais-Pesariis», «Tartinis-Colza», «Pieria-Prato
            # Carnico». Four Carnian villages with seventy-five volumes between
            # them had no dot on this map because only the whole string was
            # indexed. The parts go in too, but always at a lower rank than a
            # place that carries the name on its own.
            parts = set()
            for n in list(names):
                if "-" in n:
                    parts |= {x.strip() for x in n.split("-") if len(x.strip()) > 2}
            for n, r in [(x, rank) for x in names] + [(x, (False, False, -1)) for x in parts]:
                k = norm(n)
                if len(k) > 2 and (k not in g or r > g[k][0]):
                    g[k] = (r, round(lat, 5), round(lon, 5), cc, f[1], alts)
                if len(k) > 2:
                    ALL.setdefault(k, []).append((round(lat, 5), round(lon, 5), cc, f[1]))
    return {k: v[1:] for k, v in g.items()}


# Every candidate for an ambiguous name, so a place whose region is known can
# be given the right one of them. Prato Carnico sat on Prato in Tuscany for a
# day — three hundred kilometres away, and the winner purely because Tuscany's
# Prato has a hundred and ninety thousand people in it.
ALL = {}

# The provinces this archive actually reads, as boxes. A place catalogued only
# by a provider that works one valley cannot be in another country.
HINT = {
    "fs-it":    (45.85, 46.75, 12.30, 13.75),   # Friuli — Udine province
    "antenati": (45.85, 46.75, 12.30, 13.75),   # the same registers, other portal
}

def in_box(lat, lon, box):
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]

# FamilySearch labels its Udine comuni with the short name the register clerk
# used. «Prato» is ambiguous even inside Friuli — there is a Prato di Resia —
# and the one this collection means is PRATO CARNICO, the Val Pesarina comune
# whose own frazioni (Pesariis, Osais, Pieria) are listed beside it in the same
# collection. Written down here rather than left to a coordinate lookup to
# guess, because it moved a dot three hundred kilometres once already.
FS_IT_ALIAS = {"Prato": "Prato Carnico"}

# ---- what a place was called before ------------------------------------
# GeoNames ships every name a place has ever been indexed under in one
# comma-separated column, and for this corner of Europe that column is the
# whole history: Rijeka carries Fiume and Sankt Veit am Flaum, Pazin carries
# Mitterburg and Pisino, Gračišće carries Gallignana. The registers are
# written in whichever of those the clerk's empire used, so a reader who
# only knows the Croatian name cannot find the book.
LATIN = re.compile(r"^[A-Za-zÀ-ž' .\-]{5,34}$")
ADMIN = re.compile(r"^(grad|town of|city of|op[cć]ina|comune|municipality|"
                   r"obcina|gemeinde|distretto)\b", re.I)

def loose(s):
    """A key that sees through spelling systems rather than just accents.

    GeoNames carries Fažana as «Fazhana» and Svetvinčenat as «Svetvinchenat» —
    the same name written for a reader who has no hačeks. Those are not older
    names, they are the same name, and listing them makes the panel look like
    a parish had five identities when it had one.
    """
    s = norm(s)
    for a, b in (("cz", "c"), ("ch", "c"), ("sz", "s"), ("sh", "s"),
                 ("zh", "z"), ("tz", "c"), ("y", "i"), ("j", "i"), ("w", "v")):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)

def older_names(name, alts):
    """What else this place has been called, minus everything that is noise.

    The dump is generous: it carries airport codes, romanisations meant for
    Mandarin and Cyrillic readers, and the modern administrative wrapper
    («Grad Vodnjan»). None of those is an older name. What is left — Fiume for
    Rijeka, Gallignana for Gračišće, Pisino for Pazin — is the name the clerk
    who wrote the register would have used, which is the whole point.
    """
    seen, out = {loose(name)}, []
    for a in alts:
        if not LATIN.match(a) or "," in a or ADMIN.match(a):
            continue
        if a == a.lower():          # lowercase entries are transliterations
            continue
        k, n = loose(a), norm(a)
        if k in seen or n.startswith(norm(name)) or norm(name).startswith(n):
            continue
        seen.add(k)
        out.append(a)
    return out[:6]

def progress(n, reads, vread, vknown, vpart=0):
    """How far this archive has got, which is the only question worth a colour.

    The first cut of this map coloured by coverage state and saturated. The
    second coloured by DEPTH — one or two volumes, three to nine, ten or more —
    and that was worse, because it answered a question nobody was asking. A
    parish with forty volumes and a parish with two are equally untouched if
    nobody has opened either, and «one or two volumes» told a reader nothing
    about whether the work had been done.

    So the colour now says: nothing here, never opened, partly read, read
    right through. Depth has not been thrown away — it is in the panel, in
    words, where «114 volumes catalogued» can sit next to «nobody has read
    any of it» without either pretending to be the other.

    «Read right through» can only be claimed where this archive tracks which
    volumes were read, which today is Antenati alone. Everywhere else a read
    is recorded against the PLACE, not the book, so the best that can be
    honestly said is «started».

    And «started» used to say two different things in the same colour, which
    is the fault this docstring exists to record. Twenty-two places were amber
    and twenty of them had not had a single register volume opened: they were
    amber because the search register NAMES them — a local history of Žminj, a
    migration paper that lists Žminj among the places the Carni settled. That
    is real work and it is not the same work. Reading a book about a parish
    and reading the parish's own registers are two different acts, and a map
    whose legend says «how far we have got with the shelf» must not colour the
    first as though it were the second.

    So they are separated. «Worked» is a place this archive has researched
    from print, index or correspondence without opening its registers;
    «started» now means what it says — a volume of this parish's own books has
    been read.
    """
    if n == 0:
        return "none"
    if vknown and vread >= n:
        return "done"
    if vread or vpart:
        return "started"
    if reads:
        return "worked"
    return "untouched"

YEARS = re.compile(r"\b(1[5-9]\d\d)\b")
def span(title):
    ys = [int(y) for y in YEARS.findall(title or "")]
    return (min(ys), max(ys)) if ys else (None, None)


# ---- what kind of book is it? -------------------------------------------
# Every provider names its volumes differently — FamilySearch in English with
# the Croatian in brackets, Pazin in three-letter codes, Antenati in Italian —
# and none of them can be compared with another until the titles are reduced to
# the same three words. Anything that is an index, an allegato or a census is
# deliberately NOT given a kind: an index is not a register, and counting one as
# cover for the other would invent coverage that does not exist.
# Five languages, because five states kept these books. The Hungarian words
# arrived with Međimurje, whose registers are filed under Hungarian county
# names in a collection named for Slovenia — without them, 365 volumes fell
# into «Other» and the coverage timeline for a whole Croatian county said
# nothing at all.
KIND = [
    ("b", r"birth|rodjen|rođen|kr[sš]ten|batti|battesim|\bnati\b|nascit|taufe|szulett|születt|MKR"),
    ("m", r"marri|vjenc|vjenč|matrimon|trauung|hazasult|házasult|MKV"),
    ("d", r"death|umrl|\bmorti\b|sterbe|halottak|MKU"),
]
SKIP = re.compile(r"index|indic|kazalo|allegat|status animarum|confirmation|"
                  r"krizman|census|popis|SD\b", re.I)

def kinds(title):
    t = title or ""
    if SKIP.search(t):
        return set()
    return {k for k, pat in KIND if re.search(pat, t, re.I)}

def overlaps(a, b):
    """Two year spans, either of which may be half-open or missing entirely."""
    if not a[0] or not b[0]:
        return False
    return a[0] <= (b[1] or b[0]) and b[0] <= (a[1] or a[0])


# ---- the coverage timeline ----------------------------------------------
# A parish's panel used to list its volumes in whatever order the providers
# happened to be walked: births, births, births, deaths, births again, and a
# reader had to hold thirteen year-ranges in their head to see that nothing
# survives between 1825 and 1848. This collapses them per record type and
# names the holes, which is the thing anybody actually came to the map for.
KIND_LABEL = [("b", "Births"), ("m", "Marriages"), ("d", "Deaths")]

def vol_years(b):
    return (f'{b["from"]}–{b["to"]}' if b.get("from") and b.get("to") != b.get("from")
            else (str(b.get("from")) if b.get("from") else "—"))

def timeline_label(b):
    """One label for a volume, used by the timeline row AND by the clickable
    list, so the page can recognise that they are the same book and show it
    once. Years are stripped from the title because the row already carries
    them in its own column."""
    # A register's title is «Births (Rođeni) 1716-1816» and the years belong in
    # their own column. A catalogue entry's title is a book's title, and
    # cutting years out of it mangles the name of the book.
    t = (b["t"] if b.get("catalogue")
         else re.sub(r"\s*\b1[5-9]\d\d\b[,\s\-–]*", " ", b["t"]).strip(" ,-–") or b["t"])
    if b.get("how") == "read":
        t += " — READ"
    elif b.get("how") == "part":
        t += " — PART READ" + (f": {b['readWhat']}" if b.get("readWhat") else "")
    if not b.get("digitised", True):
        t += (" — Pazin holds the paper; filmed elsewhere" if b.get("alsoFilmed")
              else " — NOT FILMED ANYWHERE: the book exists, nobody has photographed it")
    return t



def merge(spans):
    """Union of [lo, hi] ranges, touching or overlapping ones joined."""
    out = []
    for lo, hi in sorted(spans):
        if out and lo <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out

def timeline(books):
    """[[when, what]] rows: covered stretches and the gaps between them.

    Only births, marriages and deaths get a timeline. An index is not a
    register and an allegato is not a register, so counting either as cover
    would draw a line across a hole — the same rule the cross-provider gap
    test uses. Everything the rule will not classify is counted at the end
    rather than dropped, because a volume this archive cannot read the title
    of is still a volume on a shelf.
    """
    def vol_row(b):
        return ["    " + vol_years(b), timeline_label(b)]

    rows, other, undated = [], [], 0
    place_tracked = any(b.get("how") for b in books)
    for kind, label in KIND_LABEL:
        mine = [b for b in books if kind in kinds(b["t"]) and b.get("from")]
        got = [(b["from"], b["to"] or b["from"]) for b in mine]
        if not got:
            continue
        n = len(got)
        runs = merge(got)
        # Where every volume of this kind covers exactly ONE year — the
        # Napoleonic comuni are all like this — a missing year is a missing
        # book, full stop, and softening it would have hidden Mione's lost
        # 1807, which this archive has proved is a real hole.
        single = all(lo == hi for lo, hi in got)
        first, last = runs[0][0], runs[-1][1]
        head = f"{first}–{last}" if first != last else f"{first}"
        # How much of THIS record type has been read. The panel colours the
        # heading on it: green when the kind is finished, amber when it is
        # started, nothing when nobody has opened a page of it.
        # «None read» is a statement about the LEDGER, and under a parish the
        # search register says has been worked it reads as a statement about
        # the work. Where not one volume of this kind carries a read flag at
        # all, the honest word is that nobody has written it down yet.
        nread = sum(1 for b in mine if b.get("how") == "read")
        npart = sum(1 for b in mine if b.get("how") == "part")
        # Tracking is a property of the PLACE, not of one record type in it.
        # This asked whether any volume OF THIS KIND carried a read flag, so
        # Gračišće — where the 1667–1745 baptism book is recorded as read right
        # through — announced «not tracked per volume» over its marriages. The
        # marks beside those same rows said «never opened», because the panel
        # script has always asked the question of the place. Heading and marks
        # contradicted each other on one screen.
        #
        # They ask the same question now: if this archive keeps a per-volume
        # record for this parish at all, then a volume with no flag has not
        # been opened, and the panel says so.
        done = (" · not tracked per volume" if not place_tracked
                else " · ALL READ" if nread >= n
                else f" · {nread} read, {npart} part read, {n - nread - npart} unopened"
                if nread or npart
                else f" · none read, {n} never opened")
        rows.append([label, (f"{n} volumes, covering {head}"
                             + ("" if len(runs) == 1 else f", in {len(runs)} stretches")
                             if n > 1 else "1 volume") + done])
        if len(runs) == 1:
            # An unbroken run needs no span row: the heading gives the span and
            # the volumes below give it again. Meljani was showing one volume
            # four times over — heading, span, volume, link — which is three
            # times more than anybody needs.
            rows += [vol_row(b) for b in sorted(mine, key=lambda b: (b["from"], b["t"]))]
            continue
        for i, (lo, hi) in enumerate(runs):
            rows.append(["  " + (f"{lo}–{hi}" if lo != hi else f"{lo}"), "held"])
            if i + 1 < len(runs):
                g0, g1 = hi + 1, runs[i + 1][0] - 1
                yrs = g1 - g0 + 1
                when = "  " + (f"{g0}–{g1}" if g0 != g1 else f"{g0}")
                # A one- or two-year hole is usually how a clerk wrote a title,
                # not a book that burned: a volume labelled «1716-1816» sitting
                # beside one that ends 1714 leaves 1715 uncovered on paper and
                # almost certainly not in fact. Calling that a GAP would cry
                # wolf on every parish and bury the ones that matter.
                if yrs <= 2 and not single:
                    rows.append([when, f"not covered by any title — probably how the "
                                       f"volumes were labelled, not a missing book"])
                else:
                    # «filmed» was the wrong word and it made a GAP look like
                    # the same thing as a volume marked NOT FILMED ANYWHERE.
                    # They are opposites: a gap is a stretch with no book of
                    # this kind in ANY provider's list, filmed or not; a book
                    # marked not filmed is one that exists and has not been
                    # photographed.
                    rows.append([when, f"GAP — no {label.lower()} register listed anywhere, "
                                       f"{yrs} year{'' if yrs == 1 else 's'}"])
        rows += [vol_row(b) for b in sorted(mine, key=lambda b: (b["from"], b["t"]))]
    for b in books:
        if not any(k in kinds(b["t"]) for k, _ in KIND_LABEL):
            other.append(b)
        elif not b.get("from"):
            undated += 1
    if other:
        rows.append(["Other", f"{len(other)} volume{'' if len(other) == 1 else 's'} "
                              f"— indexes, allegati, censuses and titles this archive "
                              f"cannot classify. Not counted as cover."])
        rows += [vol_row(b) for b in sorted(other, key=lambda b: (b.get("from") or 0, b["t"]))]
    if undated:
        rows.append(["Undated", f"{undated} volume{'' if undated == 1 else 's'} whose "
                                f"title carries no year. Not counted as cover."])
    return rows

def main():
    gdir = sys.argv[sys.argv.index("--gaz") + 1] if "--gaz" in sys.argv else None
    # Eight country dumps hold well over a hundred thousand names between
    # them. Anything under fifty thousand means the path is wrong.
    gaz  = gazcheck.require(gazetteer(gdir) if gdir else {}, gdir, 50000)
    prev = {}
    out_path = os.path.join(DATA, "researchmap.json")
    if os.path.exists(out_path):
        for p in load("researchmap.json")["places"]:
            if p.get("lat"):
                prev[p["key"]] = (p["lat"], p["lon"], p.get("geo"))

    places = {}
    def P(name, key=None):
        k = key or norm(name)
        return places.setdefault(k, {"key": k, "name": name.replace(", Croatia", "").strip(),
                                     "alt": set(), "layers": set(), "c": None, "geo_alt": None,
                                     "src": {}})

    # ---- 1. the KML: coordinates, confessions, and the places FS has dropped
    doc = ET.parse(KML).getroot().find("k:Document", NS)
    researchers = []
    for folder in doc.findall("k:Folder", NS):
        head = (folder.find("k:name", NS).text or "").split(" (")[0]
        for pm in folder.findall("k:Placemark", NS):
            nm   = (pm.find("k:name", NS).text or "").strip()
            data = {D.get("name"): (D.find("k:value", NS).text or "")
                    for D in pm.findall(".//k:Data", NS)}
            crd  = pm.find(".//k:coordinates", NS)
            c    = None
            if crd is not None and (crd.text or "").strip():
                lon, lat, *_ = crd.text.strip().split(",")
                c = [round(float(lat), 5), round(float(lon), 5)]
            if head == "Other Research Sites":
                researchers.append({"place": nm, "id": data.get("Oznaka istraživača"),
                                    "zupa": data.get("Župa"), "vjera": data.get("Vjera"),
                                    "prezimena": data.get("Prezimena"),
                                    "izvori": data.get("Izvori podataka"),
                                    "since": data.get("Od kada se bavite rodoslovljem?"),
                                    "drzava": data.get("Država"), "c": c})
                continue
            if head not in LAYERS or not norm(nm):
                continue
            p = P(nm); p["alt"].add(nm); p["layers"].add(LAYERS[head])
            p["c"] = p["c"] or c

    # ---- 2. FamilySearch Croatia, from the walk
    fsc = json.load(open(FSC, encoding="utf-8")) if os.path.exists(FSC) else {"p": [], "b": {}, "f": []}
    for lay, name, wp in fsc["p"]:
        p = P(name); p["alt"].add(name); p["layers"].add(lay)
        sh = p["src"].setdefault("fs-hr", {"shelves": {}})
        books = fsc["b"].get(lay + "|" + name)
        tail = wp.split(":")[1]
        vols = None
        if books is not None:
            vols = []
            for rec in books:
                t, bid, extra = rec[0], rec[1], rec[2]
                ark = rec[3] if len(rec) > 3 else None
                lo, hi = span(t)
                wpf = f"{bid}:{tail},{extra}" if extra else f"{bid}:{tail}"
                v = {"t": t, "wp": wpf, "from": lo, "to": hi}
                if ark:
                    # the ark is what makes a title clickable: the Atlas builds
                    # familysearch.org/ark:/61903/<ark>?cc=<cc>&wc=<waypoint>
                    v.update({"ark": ark, "cc": "2040054", "wc": wpf})
                vols.append(v)
        sh["shelves"][lay] = {"wp": wp, "books": vols}   # None = not walked yet

    # ---- 3. FamilySearch Udine — the Carnia comuni
    for r in load("carnia-books.json")["comuni"]:
        p = P(r["name"])
        if r["name"] in FS_IT_ALIAS:
            p["alt"].add(FS_IT_ALIAS[r["name"]])
        vols = [{"t": f["t"], "ark": f["ark"], "wc": f.get("wc"), "cc": "1939238",
                 "from": span(f["t"])[0], "to": span(f["t"])[1]} for f in r.get("films", [])]
        p["src"]["fs-it"] = {"shelves": {"civil": {"wp": None, "books": vols}}}

    # ---- 4. Pazin's own list — the only source that admits what is not digitised
    dapa = collections.defaultdict(list)
    # Pazin's list writes a town under both its names at once — «Vodnjan /
    # Dignano», «Umag / Umago», «Motovun / Montona». Keyed on the whole string
    # that is a THIRD place, so Vodnjan stood on this map twice: one dot with
    # nine volumes and, a few pixels away, another with a hundred and
    # thirty-three. Three towns and 383 volumes were split that way. The town
    # is the first name; the second is what it is also written as, which is a
    # thing this panel already knows how to say.
    for r in load("registers.json"):
        nm = r["place"]
        head = nm.split("/")[0].strip() if "/" in nm else nm
        dapa[norm(head)].append(r)
    for k, rows in dapa.items():
        nm = rows[0]["place"]
        head = nm.split("/")[0].strip() if "/" in nm else nm
        p = P(head, key=k)
        for other in [x.strip() for x in nm.split("/")[1:] if x.strip()]:
            p["alt"].add(other)
        vols = []
        for r in rows:
            lo, hi = span((r.get("period") or "").replace("/", " "))
            vols.append({"t": f"{DAPA_TYPE.get(r['type'], r['type'])} {r.get('period','')}".strip(),
                         "held": r.get("held_at"), "digitised": r.get("digitised") == "yes",
                         "no": r.get("dapa_no"), "from": lo, "to": hi})
        p["src"]["dapa"] = {"shelves": {"all": {"wp": None, "books": vols}},
                            "notDigitised": sum(1 for v in vols if not v["digitised"])}

    # ---- 4b. Antenati — the Carnia comuni, in the Italian state archive's own portal
    # Antenati has no name index at all, so a volume here is a book to be turned
    # page by page. The ark is the whole address: it opens the register at image one.
    if os.path.exists(ANT):
        ant = json.load(open(ANT, encoding="utf-8"))
        for com in ant["comuni"]:
            p = P(com["name"])
            for a in com.get("alt", []):
                p["alt"].add(a)
            if com.get("lat") and not p["c"]:
                p["c"] = [com["lat"], com["lon"]]
            vols = []
            for v in com["volumes"]:
                t = (f"{v['series']} {v['year']}" if v["series"]
                     else "Listed in the range, identity unconfirmed")
                vols.append({"t": t, "ark": v["ark"], "antenati": True,
                             "how": v["how"], "from": v["from"], "to": v["to"]})
            p["src"]["antenati"] = {"shelves": {"civil": {"wp": None, "books": vols}}}

    # ---- 4c. the collections that file Croatia under another country ----
    # A town's registers are filed by whichever state kept them, under the name
    # that state used. Čakovec is «Csáktornya», in a Hungarian county, inside a
    # collection named for Slovenia; Buje is «Buie», filed by Italy. None of it
    # can be found by walking a collection named for Croatia — which is exactly
    # why the map could not see any of it until 15 September 2026.
    if os.path.exists(ELS):
        els = json.load(open(ELS, encoding="utf-8"))
        for rec in els["places"].values():
            key = els["collections"][rec["cc"]]["key"]
            p = P(rec["today"])
            # The catalogue's own spelling goes into «also written», because it
            # is the name the book is filed under and the one a reader has to
            # search for.
            if norm(rec["catalogue"]) != norm(rec["today"]):
                p["alt"].add(rec["catalogue"])
            p["layers"].add("rc" if rec["cc"] == "2152685" else "civil")
            vols = []
            for b in rec["books"]:
                lo, hi = span(b["t"])
                v = {"t": b["t"], "wp": b["wp"], "from": lo, "to": hi,
                     "cc": rec["cc"], "filedIn": rec["country"]}
                # The walk that found these recorded the waypoint and stopped,
                # so for a year they were filmed volumes with no address. The
                # ark is fetched separately, one call a book, and it is what
                # turns the title into a link: ark + collection + waypoint.
                if b.get("ark"):
                    v.update({"ark": b["ark"], "wc": b["wp"]})
                vols.append(v)
            p["src"][key] = {"shelves": {"all": {"wp": None, "books": vols}}}
        # Delnice browses by film, not by parish: six reels and no place tree,
        # so they hang on the deanery town itself rather than pretending to a
        # precision the collection does not have.
        if els.get("films"):
            p = P("Delnice")
            p["layers"].add("rc")
            p["src"]["fs-hr-delnice"] = {"shelves": {"all": {"books": [
                {"t": f"Film {f['film']} — {f.get('images', '')} images".strip(),
                 "ark": f["ark"], "cc": "1875189", "from": 1571, "to": 1926}
                for f in els["films"]], "wp": None}}}

    # ---- 4d. the FamilySearch CATALOGUE, as distinct from its film -------
    # The image collections are one thing; the library catalogue is another,
    # and it holds printed editions, transcriptions and microfilms that no
    # collection walk will ever surface. This archive swept it by
    # place-authority id across seventy-five places and the result sat in its
    # own file for weeks without ever reaching the map.
    #
    # Its «no holdings» list is the more valuable half: fourteen places where
    # somebody looked and found nothing. A negative that has been checked is
    # worth more than a blank.
    if os.path.exists(CAT):
        cat = json.load(open(CAT, encoding="utf-8"))
        byplace = collections.defaultdict(list)
        for it in cat.get("items", []):
            byplace[it["place"]].append(it)
        for nm, items in byplace.items():
            p = P(nm)
            if items and items[0].get("fsPlace"):
                p["alt"].add(items[0]["fsPlace"].split(",")[0])
            vols = []
            for it in items:
                lo, hi = span(it["title"])
                vols.append({"t": it["title"][:120], "from": it.get("start") or lo,
                             "to": hi or it.get("start"), "catalogue": True})
            p["src"]["fs-cat"] = {"shelves": {"all": {"wp": None, "books": vols}}}
        for nm in cat.get("noHoldings", []):
            p = P(nm)
            # Walked and empty — not «unknown». The distinction is the point.
            p["src"].setdefault("fs-cat", {"shelves": {"all": {"wp": None, "books": []}}})

    # ---- 5. what has actually been read
    rows = load("searched.json")["rows"]
    where = [" ".join(str(r.get(x, "")) for x in ("src", "dest")) for r in rows]
    reads = collections.Counter()
    # «Researched, books unopened» was a count and nothing else: five things
    # read about Žminj, and the reader had to go and look for themselves what
    # the five were. The titles are right here; the map should say them.
    readrows = collections.defaultdict(list)
    for k, p in places.items():
        if k in STOP or len(p["name"]) < 4:
            continue
        pat = re.compile(r"\b" + re.escape(p["name"]) + r"\b", re.I)
        for t, r in zip(where, rows):
            if not pat.search(t):
                continue
            reads[k] += 1
            readrows[k].append({"t": (r.get("src") or "").strip(),
                                "w": (r.get("when") or "").strip(),
                                "o": (r.get("outcome") or "").strip()})

    # ---- 6. coordinates
    atlas = {norm(p["name"]): p for p in load("atlas.json")["places"]}
    for p in load("places.json"):
        if p.get("coords"):
            atlas.setdefault(norm(p["name"]), {"lat": p["coords"][0], "lon": p["coords"][1]})
    def gaz_row(p):
        """The gazetteer entry for a place, however its coordinates were found.

        Coordinates come from the KML or from the previous build's cache long
        before the gazetteer is consulted, so hanging the alternate names off
        the coordinate lookup found them for almost nobody. This asks the
        question on its own, with the same widening the coordinate search uses.
        """
        for cand in [p["key"]] + [norm(x) for x in p["alt"]]:
            if len(cand) > 2 and cand in gaz:
                return gaz[cand]
        raw = p["name"]
        parts = []
        m = re.search(r"\(([^)]+)\)", raw)
        if m:
            parts.append(m.group(1))
        parts += [x.strip() for x in re.split(r"[-–/]", re.sub(r"\(.*?\)", "", raw)) if x.strip()]
        for x in parts:
            kk = norm(x)
            if len(kk) > 2 and kk in gaz:
                return gaz[kk]
        return None

    def box_for(p):
        """Where a place can possibly be, if only one provider knows it.
        A comune catalogued by nobody but the Udine sources is in Friuli."""
        srcs = {sn for sn, blk in p["src"].items()
                if any(sh.get("books") for sh in blk["shelves"].values())}
        boxes = {HINT[sn] for sn in srcs if sn in HINT}
        return boxes.pop() if len(boxes) == 1 and srcs <= set(HINT) else None

    def resolve(p):
        k = p["key"]
        if p["c"]:   return p["c"], "kml"
        box = box_for(p)
        if box:
            # Name first, region second: take the candidate that is where the
            # provider works. Without this, Prato Carnico is Prato in Tuscany
            # and Priola in the Val Pesarina is Priola in Piedmont, because
            # both of those are bigger and the index keeps one row per name.
            # The alias first, then the name, then its parts: a name this
            # archive has written down beats one a lookup guessed at.
            tries = (list(p["alt"]) + [p["name"]]
                     + [y.strip() for y in re.split(r"[-–/]", p["name"]) if y.strip()])
            for x in tries:
                for cand in ALL.get(norm(x), []):
                    if in_box(cand[0], cand[1], box):
                        return [cand[0], cand[1]], "geonames-region"
        if k in prev: return list(prev[k][:2]), prev[k][2]
        if k in atlas and atlas[k].get("lat"):
            return [atlas[k]["lat"], atlas[k]["lon"]], "atlas"
        if k in gaz: return list(gaz[k][:2]), "geonames"
        raw, cand = p["name"], []
        m = re.search(r"\(([^)]+)\)", raw)
        if m: cand.append(m.group(1))
        cand += [x.strip() for x in re.split(r"[-–/]", re.sub(r"\(.*?\)", "", raw)) if x.strip()]
        cand.append(re.sub(r"^(sv\.?|sveti|sveta)\s+", "", raw, flags=re.I))
        for x in cand:
            kk = norm(x)
            if len(kk) > 2 and kk in gaz:
                return list(gaz[kk][:2]), "geonames-part"
        return None, None

    # ---- the read ledger, stamped onto the books it names ------------------
    # Antenati's own catalogue already carries a per-volume flag and needs
    # nothing from here. Every other provider hands over a shelf with no
    # notion of whether anybody has opened it, and this is where that is
    # supplied — by place and volume title, in the words the panel prints,
    # so the row can be written by a person reading the map.
    LEDG = ledger()
    ledg_hit, ledg_miss = 0, set(LEDG)
    for k, p in places.items():
        for blk in p["src"].values():
            for sh in blk["shelves"].values():
                for b in (sh["books"] or []):
                    r = LEDG.get((k, volkey(b["t"])))
                    if not r:
                        continue
                    b["how"] = r.get("state", "read")
                    if r.get("what"):
                        b["readWhat"] = r["what"]
                    ledg_hit += 1
                    ledg_miss.discard((k, volkey(b["t"])))
    if ledg_miss:
        sys.stderr.write("read ledger: %d row(s) match no volume: %s\n"
                         % (len(ledg_miss), sorted(ledg_miss)[:6]))

    out, src_count = [], collections.Counter()
    for k, p in sorted(places.items(), key=lambda kv: kv[1]["name"]):
        c, how = resolve(p)
        gr = gaz_row(p)
        # gaz rows are (lat, lon, cc, canonical name, alternates)
        older = older_names(p["name"], gr[4]) if gr and len(gr) > 4 else []
        vols = {}
        for s, blk in p["src"].items():
            n = sum(len(sh["books"]) for sh in blk["shelves"].values() if sh["books"] is not None)
            walked = any(sh["books"] is not None for sh in blk["shelves"].values())
            vols[s] = {"n": n, "walked": walked}
        total = sum(v["n"] for v in vols.values())
        # How many of this place's volumes are known, one by one, to have been
        # read. Only Antenati carries that flag today; FamilySearch reads are
        # recorded against the place, not the book.
        vread = sum(1 for blk in p["src"].values() for sh in blk["shelves"].values()
                    for b in (sh["books"] or []) if b.get("how") == "read")
        # A volume somebody has read part of is a volume somebody has opened,
        # which is the whole distinction «started» exists to draw. It is not
        # counted as read — that is what «done» is for — but it is not nothing.
        vpart = sum(1 for blk in p["src"].values() for sh in blk["shelves"].values()
                    for b in (sh["books"] or []) if b.get("how") == "part")
        vknown = any(b.get("how") for blk in p["src"].values()
                     for sh in blk["shelves"].values() for b in (sh["books"] or []))
        state = progress(total, reads.get(k), vread, vknown, vpart)

        # ---- 6b. where the providers disagree ---------------------------
        # A place catalogued by two providers is the only place a gap can be
        # SEEN. Pazin lists a marriage register for 1815–1830 and FamilySearch
        # has no marriage film touching those years: that book exists, on paper,
        # and nobody has photographed it. The reverse happens too, and matters
        # less — but it is the same test run the other way.
        # ---- who is allowed to accuse whom of a hole ----------------------
        # The cross-provider test compares SHELVES: one holder says a register
        # for these years exists, another has not filmed it. «fs-cat» is not a
        # shelf. It is the library catalogue, and one of its records is a
        # bibliographic line that can span three centuries — «Matična knjiga,
        # 1568-1917» is one row covering a parish's whole holdings. Letting it
        # into the comparison turned a test of 460 volumes across six places
        # into 1,572 across seventy-eight, and almost all of the difference was
        # a catalogue record being read as a statement about a particular year.
        CROSS = {"fs-hr", "fs-it", "dapa", "antenati", "fs-it-pola", "fs-si-mj",
                 "fs-hr-delnice"}
        shelf = {}
        for sname, blk in p["src"].items():
            if sname not in CROSS:
                continue
            rows = []
            for sh in blk["shelves"].values():
                for b in (sh["books"] or []):
                    for kd in kinds(b["t"]):
                        rows.append((kd, (b.get("from"), b.get("to")), b))
            shelf[sname] = rows
        gaps = []
        for sname, rows in shelf.items():
            for other, orows in shelf.items():
                if other == sname:
                    continue
                for kd, yr, b in rows:
                    if not yr[0]:
                        continue
                    if not any(okd == kd and overlaps(yr, oyr) for okd, oyr, _ in orows):
                        gaps.append({"have": sname, "missing": other, "kind": kd,
                                     "t": b["t"], "from": yr[0], "to": yr[1],
                                     "digitised": b.get("digitised", True)})
        gaps.sort(key=lambda g: (g["missing"], g["kind"], g["from"]))

        # ---- 6c. is a «not digitised» volume really unreachable? ----------
        # Pazin's digitised column is the only one in the estate that admits
        # an absence, and this archive published it as «books that exist on a
        # shelf in Istria and cannot be read from anywhere else». That is only
        # true where nobody ELSE has filmed them, and mostly somebody has.
        filmed = [b for sname, blk in p["src"].items() if sname != "dapa"
                  for sh in blk["shelves"].values() for b in (sh["books"] or [])]
        for sh in p["src"].get("dapa", {}).get("shelves", {}).values():
            for b in (sh["books"] or []):
                if b.get("digitised", True):
                    continue
                kk, yy = kinds(b["t"]), (b.get("from"), b.get("to") or b.get("from"))
                b["alsoFilmed"] = any(
                    (kinds(f["t"]) & kk) and overlaps(yy, (f.get("from"), f.get("to") or f.get("from")))
                    for f in filmed)
        # Ninety-odd single volumes is a list nobody reads. Merged into the
        # stretches of years they cover, the same information is four lines.
        spans = []
        for key, grp in itertools.groupby(gaps, key=lambda g: (g["have"], g["missing"], g["kind"])):
            cur = None
            for g in grp:
                lo, hi = g["from"], g["to"] or g["from"]
                if cur and lo <= cur[1] + 1:
                    cur[1] = max(cur[1], hi)
                    cur[2] += 1
                else:
                    if cur:
                        spans.append({"have": key[0], "missing": key[1], "kind": key[2],
                                      "from": cur[0], "to": cur[1], "n": cur[2]})
                    cur = [lo, hi, 1]
            if cur:
                spans.append({"have": key[0], "missing": key[1], "kind": key[2],
                              "from": cur[0], "to": cur[1], "n": cur[2]})
        for s in p["src"]: src_count[s] += 1
        out.append({"key": k, "name": p["name"],
                    "alt": sorted(x for x in p["alt"]
                                  if norm(x) != norm(p["name"])
                                  and not norm(x).startswith(norm(p["name"]))),
                    "older": older,
                    "lat": c[0] if c else None, "lon": c[1] if c else None, "geo": how,
                    "cat": state, "layers": sorted(p["layers"]),
                    "sources": p["src"], "counts": vols, "volumes": total,
                    "reads": reads.get(k, 0), "readrows": readrows.get(k, [])[:12],
                    "vread": vread, "vpart": vpart, "vknown": vknown,
                    "gaps": gaps, "ngaps": len(gaps), "gapSpans": spans})

    stats = {"places": len(out), "placed": sum(1 for o in out if o["lat"]),
             "volumes": sum(o["volumes"] for o in out),
             # «Read» now means a register volume of this parish's own books has
             # been opened. Places we have only researched from print are
             # counted separately, because conflating the two is what made
             # twenty places amber that had never had a book opened.
             "read": sum(1 for o in out if o["cat"] in ("started", "done")),
             "worked": sum(1 for o in out if o["cat"] == "worked"),
             "listed": sum(1 for o in out if o["cat"] == "untouched"),
             "untouched": sum(1 for o in out if o["cat"] == "untouched"),
             "byProgress": {x: sum(1 for o in out if o["cat"] == x)
                            for x in ("none", "untouched", "worked", "started", "done")},
             "volumesRead": sum(o["vread"] for o in out),
             "researchers": len(researchers),
             "bySource": {s: {"places": src_count[s],
                              "volumes": sum(o["counts"].get(s, {}).get("n", 0) for o in out),
                              "walked": sum(1 for o in out if o["counts"].get(s, {}).get("walked"))}
                          for s, _, _ in SOURCES},
             "byLayer": dict(collections.Counter(l for o in out for l in o["layers"])),
             "notDigitised": sum(o["sources"].get("dapa", {}).get("notDigitised", 0) for o in out),
             "notDigitisedAnywhere": sum(
                 1 for o in out for sh in o["sources"].get("dapa", {}).get("shelves", {}).values()
                 for b in (sh["books"] or [])
                 if not b.get("digitised", True) and not b.get("alsoFilmed")),
             # The page that lists these joins on Pazin's own shelfmark, which is
             # unique, rather than on the place name — the two catalogues spell
             # «Poreč (Poreč)» and «Vodnjan / Dignano» differently and a name
             # join silently lost a third of the rows.
             "filmedElsewhere": sorted(
                 b["no"] for o in out for sh in o["sources"].get("dapa", {}).get("shelves", {}).values()
                 for b in (sh["books"] or [])
                 if not b.get("digitised", True) and b.get("alsoFilmed") and b.get("no")),
             "notDigitisedButFilmed": sum(
                 1 for o in out for sh in o["sources"].get("dapa", {}).get("shelves", {}).values()
                 for b in (sh["books"] or [])
                 if not b.get("digitised", True) and b.get("alsoFilmed")),
             "fsPending": len(fsc.get("f", [])),
             # Places two real shelves both describe — the only places a hole
             # can be seen at all. The library catalogue is not a shelf.
             "crossChecked": sum(1 for o in out if len(
                 [x for x in o["counts"] if x != "fs-cat"]) > 1),
             "timelineGaps": None,   # filled once the blobs are built
             "gaps": sum(o["ngaps"] for o in out),
             "gapsBy": dict(collections.Counter(
                 f'{g["have"]}>{g["missing"]}' for o in out for g in o["gaps"])),
             "linked": sum(1 for o in out for b in o.get("sources", {}).get("fs-hr", {}).get("shelves", {}).values()
                           for b in (b["books"] or []) if b.get("ark"))}

    researchmap_note = "Every record book this archive can name, by place and by provider."
    json.dump({"note": researchmap_note,
               "sources": [{"key": k, "label": l, "what": w} for k, l, w in SOURCES],
               "kml": "data/genealogy-resources-croatia.kml",
               "stats": stats, "places": out, "researchers": researchers},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 7. one Atlas blob per view -------------------------------------
    allk = {k for k, _, _ in SOURCES}

    def blob(keys, path):
        pubs = []
        for o in out:
            if not o["lat"]:
                continue
            got = {s: b for s, b in o["sources"].items() if s in keys}
            # A place with NO provider block at all is the one thing the «nothing
            # filmed here» colour exists to show — it came off David's map and not
            # one of the four catalogues knows it. Dropping it for having no source
            # made that filter permanently empty. It belongs on the all-providers
            # view only: a provider's own page should show that provider's places.
            if not got and keys != allk:
                continue
            n = sum(o["counts"][s]["n"] for s in got)
            walked = any(o["counts"][s]["walked"] for s in got)
            state = progress(n, o["reads"], o["vread"], o["vknown"], o.get("vpart", 0))
            who = " · ".join(LABEL.get(l, l) for l in o["layers"]) or "Civil"
            prov = " · ".join(dict((k, l) for k, l, _ in SOURCES)[s] for s in got)
            if not got:
                # Two of these three are Evangelical, and that is not the same
                # thing as unfilmed: this archive never found the Evangelical
                # root in FamilySearch's waypoint tree, so the shelf was never
                # walked. Saying «nothing is filmed here» would blame the
                # collection for a hole of our own making.
                if o["layers"] == ["ev"]:
                    what = (f"{who}. In no catalogue here — and the fault is ours. This archive "
                            f"never found the Evangelical root in FamilySearch's waypoint tree, "
                            f"so the shelf has not been walked. It is not known to be empty.")
                else:
                    what = (f"{who}. On the map and in no catalogue. Neither FamilySearch, nor "
                            f"Pazin, nor Antenati holds a register book for this place — it is "
                            f"here because David's own map marks it.")
            elif not walked:
                what = f"{who}. Not walked yet — we hold the waypoint and nothing more."
            elif n == 0:
                what = f"{who}. Walked, and the shelf is empty — this collection films nothing here."
            else:
                shelf = f"{who}. {n} volume{'' if n == 1 else 's'} catalogued, from {prov}. "
                if o["vknown"] and o["vread"] >= n:
                    tail = (f"All {n} have been read. This is the only state on the map that "
                            f"means the work here is finished.")
                elif o["vread"] or o.get("vpart"):
                    bits = []
                    if o["vread"]: bits.append(f"{o['vread']} read right through")
                    if o.get("vpart"): bits.append(f"{o['vpart']} read in part")
                    rest = n - o["vread"] - o.get("vpart", 0)
                    tail = ("Of the %d: %s%s." % (n, " and ".join(bits),
                            f", and {rest} never opened" if rest > 0 else ""))
                elif o["reads"]:
                    # The Atlas panel escapes its text — it renders no markup at
                    # all — so this sentence carries its weight in words.
                    tail = (f"Not one of them has been opened. What has been read here is "
                            f"{o['reads']} thing{'' if o['reads'] == 1 else 's'} ABOUT this "
                            f"place — named below — which is research, and is not the same as "
                            f"reading the parish's own books.")
                else:
                    tail = ("Nobody has opened any of it. The number of volumes is the size of "
                            "the shelf, not a measure of what has been done.")
                what = shelf + tail
            nd = sum(b.get("notDigitised", 0) for b in got.values())
            if nd:
                what += (f" {nd} of them is not digitised anywhere." if nd == 1
                         else f" {nd} of them are not digitised anywhere.")
            # The timeline is built from EVERY volume — linked or not, and from
            # every provider — because coverage is a fact about the shelf, not
            # about which of its books happen to have an ark yet. The films list
            # below is the separate question of what you can click.
            allb, films, nolink = [], [], None
            for s, blk in sorted(got.items()):
                for sh in blk["shelves"].values():
                    for b in (sh["books"] or []):
                        allb.append(b)
                        if b.get("ark") and not b.get("antenati"):
                            # The title here is built to match the volume row in
                            # the timeline exactly, so the page can move this
                            # link into that row and drop the duplicate list.
                            vr = timeline_label(b)
                            films.append({"t": vr, "ark": b["ark"],
                                          "cc": b.get("cc"), "wc": b.get("wc")})
            # Why the «open at page one» list is missing, when it is missing.
            # Silence there reads as an oversight; for Gračišće it is a fact
            # about the record, and the reader should be told which.
            if n and not films:
                # Which providers actually PUT A BOOK on this shelf. Asking
                # set(got) counted providers that catalogued the place and
                # contributed nothing, so Gračišće — thirty-two volumes, every
                # one of them Pazin's, and an empty FamilySearch-catalogue
                # shelf beside them — was told «no image address has been
                # harvested yet», which reads as an errand nobody has run. It
                # is not. Pazin publishes a register list and no images, and
                # FamilySearch's Croatian collection does not hold the parish.
                # There is nothing to harvest, and the panel should say which
                # of the two kinds of silence this is.
                with_books = {s for s, blk in got.items()
                              if any(sh.get("books") for sh in blk["shelves"].values())}
                paperonly = {"dapa", "fs-cat"}
                # Antenati's arks are deliberately kept out of the films list —
                # they live on a different host and open in the portal's own
                # viewer — so a comune with nothing but Antenati volumes is not
                # unlinked, it is linked from a different page.
                if with_books and with_books <= {"antenati", "fs-cat"}:
                    why = ("they are Antenati's, and Antenati is opened from "
                           "its own page rather than from this panel.")
                elif with_books and with_books <= paperonly:
                    why = ("every volume above is a catalogue entry: Pazin publishes a "
                           "register list, not images, and FamilySearch's Croatian "
                           "collection does not hold this parish. They are read on "
                           "microfilm at Pazin, or by ordering a copy.")
                else:
                    why = "no image address has been harvested for any of them yet."
                what += " Not one of them is openable from here — " + why
                # And say it AGAIN at the foot of the volume list. The sentence
                # above sits at the top of a panel that can run seventeen
                # hundred pixels; by the time a reader is looking at a row with
                # no link on it, the explanation is off the screen, and the
                # only thing visible is thirty-two titles that do not click.
                nolink = why
            ev = timeline(allb)
            # Name them. A reader who is told «five things about this place»
            # and not which five has been given a number, not a finding.
            if o.get("readrows") and not o["vread"]:
                one = o["reads"] == 1
                ev.append(["Read about it",
                           f"{o['reads']} row{'' if one else 's'} of the search register "
                           f"{'names' if one else 'name'} this place as a source or a "
                           f"destination. Not one of them is a volume from the shelf above."])
                for rr in o["readrows"]:
                    ev.append(["    " + (rr["w"] or "—"),
                               rr["t"] + (f" — {rr['o']}" if rr["o"] else "")])
                if o["reads"] > len(o["readrows"]):
                    ev.append(["    and more",
                               f"{o['reads'] - len(o['readrows'])} further rows, listed in full "
                               f"on the search register."])
            if len(allb) > 2 and ev and not any(t.startswith(("GAP", "not covered"))
                                                for _, t in ev):
                ev.append(["No gaps", "Every year between the first volume and the last is "
                                      "covered by some register, for each kind above."])
            if nolink:
                ev.append(["No links", "Nothing above opens from this panel — " + nolink])
            nd = [b for b in allb if not b.get("digitised", True)]
            if nd:
                ev.append(["Not digitised",
                           (f"One of the volumes above exists on paper and nowhere else."
                            if len(nd) == 1 else
                            f"{len(nd)} of the volumes above exist on paper and nowhere else.")
                           + " Pazin says so; no other provider admits it."])
            pubs.append({"name": o["name"], "lat": o["lat"], "lon": o["lon"], "cat": state,
                         "n": 0,
                         # The panel's «also written» line is the only place a
                         # reader meets the name the register is actually filed
                         # under. Catalogue spellings and historic exonyms both
                         # belong in it — Gračišće is Gallignana in every
                         # Austrian book, and a reader who only knows the
                         # Croatian name will never find it.
                         "also": sorted(set(o["alt"]) | set(o.get("older") or []),
                                        key=lambda x: (x.lower() != x.lower(), x)),
                         "what": what,
                         "when": None,
                         # Antenati's arks live on a different host, and the Atlas panel
                         # builds FamilySearch addresses. Rather than reach into the shared
                         # component, these places point at the archive's own page, where
                         # all 59 volumes are listed and every one of them is a link.
                         "href": ("/antenati/" if "antenati" in got
                                  else ("/searched/" if o["reads"] else None)),
                         "events": ev[:260], "films": films, "nfilms": len(films)})
        json.dump({"places": pubs, "stats": stats}, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False)
        return len(pubs)

    n = blob(allk, os.path.join(PUB, "research-map-data.json"))
    # Count the real holes off the all-providers blob, which is where the
    # timeline is actually computed, and fold the figure back into the stats
    # every page reads.
    _all = json.load(open(os.path.join(PUB, "research-map-data.json"), encoding="utf-8"))
    _rows = [t for p in _all["places"] for _, t in p["events"] if t.startswith("GAP")]
    stats["timelineGaps"] = {
        "rows": len(_rows),
        "places": sum(1 for p in _all["places"]
                      if any(t.startswith("GAP") for _, t in p["events"])),
        "clean": sum(1 for p in _all["places"]
                     if any(w == "No gaps" for w, _ in p["events"]))}
    # The towns of the people were injected here for one afternoon, while the
    # research map, the atlas and the graves map were still three pages. They
    # are merged properly now in scripts/build-map.py, which folds all three
    # onto one set of places and keeps each question's category separately.
    # Doing it twice put a second Fužine on the all-providers blob.
    _all["stats"] = stats
    json.dump(_all, open(os.path.join(PUB, "research-map-data.json"), "w",
                         encoding="utf-8"), ensure_ascii=False)
    gazcheck.guard(out_path, "stats.placed", stats["placed"], "placed record-book places")
    json.dump({"note": researchmap_note, "sources": [{"key": k, "label": l, "what": w}
                                                     for k, l, w in SOURCES],
               "kml": "data/genealogy-resources-croatia.kml",
               "stats": stats, "places": out, "researchers": researchers},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    per = {}
    for k, _, _ in SOURCES:
        per[k] = blob({k}, os.path.join(PUB, f"research-map-{k}.json"))
    print(json.dumps({"stats": stats, "blobAll": n, "blobPer": per}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
