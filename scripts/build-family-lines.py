#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The family pages' ribbons and "how our line connects" blocks, made from the archive's own data (kit/docs/family-ribbon.md).

    python3 scripts/build-family-lines.py                  # write site/src/data/family-lines.json and family-links.json
    python3 scripts/build-family-lines.py --check          # fail if either file is not what the data makes (CI)
    python3 scripts/build-family-lines.py --check --dist site/dist
                                                            # ... and read the blocks-only families back off the built pages

TWO FILES, ONE RULE. A family page gets a RIBBON only where the archive holds that family's own line of generations as
structured data: one person to a generation, each the parent of the next. Where it does not, the page gets no ribbon and
nothing is invented; its "how our line connects" blocks are drawn all the same.
  family-lines.json   the families WITH a ribbon, in the kit's contract (kit/data/family-ribbon-schema.json), drawn by the
                      kit's FamilyRibbon and held by the kit's gate (checkfamilyribbon.py).
  family-links.json   the families with NO ribbon: their connections, or "not connected", only. The kit's component and gate
                      draw and hold a family only when it has cards (its F3: "no ribbon is empty"), so these are drawn by
                      src/components/FamilyBand.astro with the kit's own block markup and classes, and held by this script's
                      --check --dist (the same rules as the kit's C1-C6, B3, B5, O1 and B6, for these families).

WHERE A LINE OF GENERATIONS COMES FROM (never prose):
  * spines.json (the channels /tree/, /imotski/, /omis-line/, /seget/ and /corsica/ draw): `people` by `gen`, each with dates
    (`d`), the stop they stood at (`at`, its place is the card's "from") and a grade (`conf`); a wife from `joins` of the same gen.
    A generation with two or more people is the one the `joins` name a wife for; if that does not settle it, the line stops.
    A group ("Alvise's six children") is not a person and is not a card.
  * carnia.json `muina.chain` (the four generations the Napoleonic acts give at Muina): `who` ("X and Y" is a couple), `conf`.
  * households.json, from the lane's own person node (rivers.json): each generation is the father of a household the archive
    holds, the next is the eldest of his children who heads a household of his own. A father the archive files under one id in
    two households is two men or one, and the line is not drawn through him.
  The card's years are the data's own, with day and month dropped; nothing is estimated.

HOW OUR LINE CONNECTS (the story's ribbon, story-book.json, and its chapter trees; the direct line is src/data/direct-line.json):
  * married    every ribbon card's person and his wife, for the family of her surname (the married-in and maternal-line pages
               of that surname). Grade: the wife's own grade on the card (`spouse.support`), and inferred at best when the
               story's chapter tree draws the couple under another person page than the ribbon's (generation 1: the weaver's
               son of the register is the chart's Giovanni by inference).
  * son of     the next card's person and that wife, for the same family. Grade: the weaker of the son's and the mother's
               outline in the chapter tree that draws them together (where he is the child who carries the line).
  A family the ribbon does not touch is "not connected"; its `why` is the archive's own sentence where it states one (below),
  and nothing where it does not. A spouse with no person page is named and not linked (Francisca Salomon).
"""
import argparse, json, os, re, sys, unicodedata
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OUT_LINES = os.path.join(DATA, "family-lines.json")
OUT_LINKS = os.path.join(DATA, "family-links.json")
STORY = "/story/"
NOTE_LINES = ("Made by scripts/build-family-lines.py from spines.json, carnia.json, households.json, rivers.json, roster.json and the "
              "story's ribbon; the families with a ribbon, in the kit's contract (kit/docs/family-ribbon.md). Do not edit by hand.")
NOTE_LINKS = ("Made by scripts/build-family-lines.py: the family pages with no line of generations in the data, and how our line "
              "connects to each (the story's ribbon and chapter trees). Drawn by src/components/FamilyBand.astro. Do not edit by hand.")


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


def fold(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]+", " ", s)


def first_sentence(text, marker=None):
    t = re.sub(r"\*+|`", "", str(text or "")).strip()
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z«*])", t)
    if marker:
        sents = [s for s in sents if marker in s]
    return sents[0].strip() if sents else ""


def cap(s):
    s = str(s or "").strip()
    return (s[:1].upper() + s[1:]).rstrip(".") + "." if s else ""


def years_of(d):
    d = str(d or "").strip()
    d = re.sub(r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? ", "", d)
    d = re.sub(r"\s*[–-]\s*", "–", d)
    return "" if d in ("—", "-") else d


GRADE = {"doc": "doc", "documented": "doc", "inf": "inf", "inferred": "inf", "lore": "lore", "family": "lore"}
ORDER = {"doc": 0, "inf": 1, "lore": 2}


def weakest(*gs):
    gs = [GRADE.get(g, "lore") for g in gs if g]
    return max(gs, key=lambda g: ORDER[g]) if gs else "lore"


def plain(t, n=220):
    t = re.sub(r"<[^>]+>", "", str(t or ""))
    t = re.sub(r"\*+|`|\[([^\]]+)\]\([^)]*\)", lambda m: m.group(1) or "", t)
    return re.sub(r"\s+", " ", t).strip()[:n]


def empty_card():
    return {"name": "", "years": "", "origin": "", "originGrade": "", "spouse": "", "spouseOrigin": "",
            "atPlace": "", "atYear": "", "living": False}


# ------------------------------------------------------------------------------------------------ the people the cards may link
class Roster:
    def __init__(self):
        self.rows = [r for r in load("roster.json")["rows"] if r.get("pid")]
        self.by = {r["pid"]: r for r in self.rows}

    def match(self, name, years, line):
        """A spine person's page: the roster row of the same line, the same first name and the same birth and death years."""
        ys = re.findall(r"\b(\d{3,4})\b", years or "")
        if len(ys) != 2:
            return None
        first = fold(name).split()[0] if fold(name).split() else ""
        hits = [r for r in self.rows if r.get("line") == line and str(r.get("b")) == ys[0] and str(r.get("d")) == ys[1]
                and fold(r["name"]).split()[:1] == [first] and not r.get("living") and not r.get("sameAs")]
        return hits[0]["pid"] if len(hits) == 1 else None


# ------------------------------------------------------------------------------------------------ the lines of generations
def spine_card(p, sp, roster):
    stops = sp.get("stops") or []
    c = empty_card()
    c["name"] = p["name"]
    c["years"] = years_of(p.get("d"))
    at = p.get("at")
    c["origin"] = stops[at]["place"] if isinstance(at, int) and 0 <= at < len(stops) else ""
    c["originGrade"] = GRADE.get(p.get("conf"), "lore")
    js = [j for j in sp.get("joins") or [] if j.get("gen") == p["gen"]]
    if len(js) == 1:
        c["spouse"] = js[0].get("person", "")
        c["spouseOrigin"] = ("of " + js[0]["from"]) if js[0].get("from") else ""
    what = plain(p.get("what"))
    if what:
        c["title"] = what
    pid = roster.match(p["name"], c["years"], sp["key"])
    if pid:
        c["person"] = pid
    return c


def cards_from_spine(sp, roster):
    """One person to a generation: a generation with more than one person is not a line (see cards_from_keytree)."""
    gens = {}
    for p in sp.get("people") or []:
        gens.setdefault(p["gen"], []).append(p)
    cards, notes = [], []
    for g in sorted(gens):
        ppl = [p for p in gens[g] if not re.search(r"\bchildren\b|\bbrothers\b", p["name"], re.I)]
        if len(ppl) != 1:
            notes.append("gen %s has %d people; the spine alone does not say which carries the line" % (g, len(ppl)))
            break
        cards.append(spine_card(ppl[0], sp, roster))
    return cards, notes


def cards_from_keytree(tree, sp, lane, roster):
    """A page's own drawn household tree (seget.json `tree`): in each generation the person it marks `key` with a page.
    The grade and the stop are the spine's for the person of the same name and generation; a person the spine names
    otherwise ("Zorzi" for Giorgio) takes the lane's tier, as the kit's cardsFromLane does for a node with no evidence."""
    LANE_GRADE = {"documented": "doc", "inferred": "inf", "origin-unknown": "inf", "family-lore": "lore"}
    cards, notes = [], []
    for g in tree["gens"]:
        keys = [p for p in g["people"] if p.get("key") and p.get("pid")]
        if len(keys) != 1:
            notes.append("tree gen %s: %d key people with a page" % (g["n"], len(keys)))
            break
        p = keys[0]
        same = [q for q in sp.get("people") or [] if str(q["gen"]) == str(g["n"]) and fold(q["name"]).split()[:1] == fold(p["name"]).split()[:1]]
        if len(same) == 1:
            c = spine_card(same[0], sp, roster)
        else:
            c = empty_card()
            c["originGrade"] = LANE_GRADE.get(lane.get("status"), "lore")
        c["name"] = p["name"]
        c["years"] = years_of(re.sub(r"\s*·.*$", "", p.get("d") or ""))
        c["person"] = p["pid"]
        if p.get("spouse"):
            c["spouse"] = p["spouse"]
            js = [j for j in sp.get("joins") or [] if fold(j.get("person")) == fold(p["spouse"])]
            c["spouseOrigin"] = ("of " + js[0]["from"]) if len(js) == 1 and js[0].get("from") else ""
            if p.get("spousePid") and p["spousePid"] in roster.by:
                c["spousePerson"] = p["spousePid"]
        else:
            c["spouse"] = c["spouseOrigin"] = ""
        c.pop("title", None)
        if p.get("w"):
            c["title"] = plain(p["w"])
        cards.append(c)
    return cards, notes


def cards_from_muina(carnia):
    cards = []
    for x in carnia["muina"]["chain"]:
        who = x["who"]
        name, _, spouse = who.partition(" and ")
        name = re.sub(r",.*$", "", name).strip()
        spouse = re.sub(r"\s+—.*$", "", spouse).strip()
        c = empty_card()
        c["name"] = name
        c["originGrade"] = GRADE.get(x.get("conf"), "lore")
        c["spouse"] = spouse
        cards.append(c)
    return cards


def cards_from_households(start, roster):
    H = load("households.json")
    as_father = {}
    for h in H:
        if h.get("fatherPid"):
            as_father.setdefault(h["fatherPid"], []).append(h)
    child_of = {}
    for h in H:
        for c in h["children"]:
            if c.get("pid"):
                child_of.setdefault(c["pid"], []).append((h, c))
    strip = lambda s: re.sub(r"\s*\([^)]*\)", "", str(s or "")).strip()
    chain, notes, cur = [], [], start
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        hs = as_father.get(cur) or []
        if len(hs) > 1:
            notes.append("%s is the father of %d households under one id; the line is not drawn through him" % (cur, len(hs)))
            break
        if not hs:
            break
        h = hs[0]
        chain.append(h)
        kids = [c for c in h["children"] if c.get("pid") and len(as_father.get(c["pid"]) or []) == 1]
        kids.sort(key=lambda c: (c.get("by") or c.get("y") or 9999))
        cur = kids[0]["pid"] if kids else None
    SRC = {"read": "doc", "index": "inf", "tree": "lore"}
    cards = []
    for i, h in enumerate(chain):
        pid = h["fatherPid"]
        r = roster.by.get(pid) or {}
        if r.get("living"):
            notes.append("%s is living; the line is not drawn" % pid)
            return [], notes
        c = empty_card()
        c["name"] = strip(h["father"])
        b, d = r.get("b"), r.get("d")
        c["years"] = "%s–%s" % (b, d) if b and d else ("b. %s" % b if b else ("d. %s" % d if d else ""))
        c["origin"] = r.get("parish") or (r.get("place") or "").split(",")[0]
        # the grade of "from": the household that names him as a child (the one above), else his own
        g = SRC.get(chain[i - 1]["src"], "lore") if i > 0 else SRC.get(h["src"], "lore")
        c["originGrade"] = g
        c["spouse"] = strip(h.get("mother"))
        if h.get("motherPid") and h["motherPid"] in roster.by:
            c["spousePerson"] = h["motherPid"]
        c["person"] = pid
        cards.append(c)
    return cards, notes


# ------------------------------------------------------------------------------------------------ how our line connects
def story_connections(book, dl):
    """{surname-key: [connection]} from the story's ribbon and its chapter trees."""
    cards = book["ribbon"]
    dmap = {p["slug"]: p for p in dl["people"] + dl["partners"]}
    trees = [c.get("tree") for c in book["chapters"] + [book.get("closing") or {}] if c.get("tree")]

    def tree_with_couple(wife_pid):
        for t in trees:
            for r in t.get("rows") or []:
                if r.get("role") == "couple" and any(p.get("pid") == wife_pid for p in r["people"]):
                    return t, r
        return None, None

    out = []
    for i, c in enumerate(cards):
        sp = c.get("spouse") or {}
        if not sp.get("name") or not c.get("pid") or sp.get("living") or c.get("living"):
            continue
        gen = i + 1
        ours = c["pid"]
        if ours not in dmap:
            continue
        theirs = sp.get("pid", "")
        t, couple = tree_with_couple(theirs) if theirs else (None, None)
        if t is None:  # Francisca Salomon has no page: find her couple row by her name
            for tt in trees:
                for r in tt.get("rows") or []:
                    if r.get("role") == "couple" and any(p.get("name") == sp["name"] for p in r["people"]):
                        t, couple = tt, r
        husband = couple["people"][0] if couple else {}
        ident = "doc" if husband.get("pid") == ours else "inf"
        out.append({"surname": sp["name"], "ourSlug": ours, "ourGeneration": gen, "ourName": c["name"],
                    "theirSlug": theirs, "theirName": sp["name"], "theirOrigin": sp.get("place", ""),
                    "relation": "married", "grade": weakest(sp.get("support"), ident),
                    "storyHref": "%s#%s" % (STORY, c["link"]), "note": ""})
        if i + 1 < len(cards) and cards[i + 1].get("pid") and not cards[i + 1].get("living") and t is not None:
            nxt = cards[i + 1]
            kid = None
            for r in t.get("rows") or []:
                if r.get("role") == "kids":
                    kid = next((p for p in r["people"] if p.get("pid") == nxt["pid"] and p.get("line")), None) or kid
            if kid is not None and nxt["pid"] in dmap:
                mother = next((p for p in couple["people"] if (p.get("pid") or p.get("name")) == (theirs or sp["name"])), {})
                out.append({"surname": sp["name"], "ourSlug": nxt["pid"], "ourGeneration": i + 2, "ourName": nxt["name"],
                            "theirSlug": theirs, "theirName": sp["name"], "theirOrigin": sp.get("place", ""),
                            "relation": "son of", "grade": weakest(kid.get("g"), mother.get("g")),
                            "storyHref": "%s#%s" % (STORY, c["link"]), "note": ""})
    return out


# ------------------------------------------------------------------------------------------------ the family pages
def families():
    """(id, title, page, kind, surname keys, source) for every family page, in the order of the menu and the book."""
    rivers = {l["key"]: l for l in load("rivers.json")["lanes"]}
    spines = {s["key"]: s for s in load("spines.json")["spines"]}
    mi = load("marriedin.json")
    mat = load("maternal.json")["lines"]
    fam = []
    # the place lines: one for each lane of the lines drawing, on the page that tells it
    PLACE = [("carnia", "Carnia", "/carnia/", {"muina": True}),
             ("svetvincenat", "Svetvinčenat", "/places/svetvincenat/", {}),
             ("liznjan", "Ližnjan", "/liznjan/", {"households": True}),
             ("venice", "The Imotski Franceschi", "/imotski/", {"spine": "venice"}),
             ("venice-omis", "Out of Venice: Omiš", "/omis-line/", {"spine": "venice", "lane": "venice"}),
             ("crete", "Seget, and Crete", "/seget/", {"spine": "crete", "keytree": "seget.json"}),
             ("vodnjan", "Vodnjan", "/vodnjan/", {}),
             ("corsica", "Corsica", "/corsica/", {"spine": "corsica"})]
    for fid, title, page, src in PLACE:
        lane = rivers[src.get("lane", fid)]
        fam.append({"id": fid, "title": title, "page": page, "kind": "place line", "lane": lane, "src": src,
                    "spine": spines.get(src.get("spine")) if src.get("spine") else None, "keys": []})
    # the maternal lines: the menu's five
    for k in ["salomon", "fernasar", "kalanj", "kovacina", "blazevic"]:
        if k in mat:
            fam.append({"id": "maternal-" + k, "title": mat[k]["name"], "page": "/maternal/%s/" % k, "kind": "maternal line", "keys": [k]})
        elif k == "kalanj":
            fam.append({"id": "maternal-kalanj", "title": "Kalanj", "page": "/kalanj/", "kind": "maternal line", "keys": ["kalanj"]})
        elif k == "blazevic":
            fam.append({"id": "maternal-blazevic", "title": "Blažević", "page": "/senj-line/", "kind": "maternal line", "keys": ["blazevic"]})
    # the families that married in: every page /married-in/<slug>/
    rows = {r["slug"]: r for r in mi["rows"]}
    for slug, d in mi["detail"].items():
        title = rows[slug]["name"] if slug in rows else (d.get("title") or slug)
        keys = [fold(x).strip() for x in title.split("/")]
        fam.append({"id": "married-in-" + slug, "title": title, "page": "/married-in/%s/" % slug, "kind": "married in",
                    "keys": [k.replace(" ", "") for k in keys]})
    return fam


def why_for(f):
    """The archive's own sentence on what is missing, where it states one."""
    fid = f["id"]
    lane = f.get("lane") or {}
    if fid in ("venice", "venice-omis"):
        return first_sentence(load("imotski.json")["note"])
    if fid == "crete":
        return first_sentence(load("seget.json")["photographed"]["why"], "two different families of one surname")
    if fid == "corsica":
        s = next(x for x in f["spine"]["strands"] if x["kind"] == "not-joined")
        return first_sentence(s["note"])
    if fid in ("carnia", "liznjan", "vodnjan"):
        return cap(lane.get("statusNote"))
    return ""


def build():
    book = load("story-book.json")
    dl = load("direct-line.json")
    roster = Roster()
    conns = story_connections(book, dl)
    lines, links, report = [], [], []
    carnia = load("carnia.json")
    for f in families():
        cards, notes = [], []
        if f.get("src", {}).get("keytree"):
            cards, notes = cards_from_keytree(load(f["src"]["keytree"])["tree"], f["spine"], f["lane"], roster)
        elif f.get("spine"):
            cards, notes = cards_from_spine(f["spine"], roster)
        elif f.get("src", {}).get("muina"):
            cards = cards_from_muina(carnia)
        elif f.get("src", {}).get("households"):
            start = next((n["person"] for n in f["lane"]["nodes"] if isinstance(n, dict) and n.get("person")), None)
            cards, notes = cards_from_households(start, roster) if start else ([], ["the lane names no person"])
        if len(cards) < 2:
            if cards:
                notes.append("one generation is not a line")
            cards = []
        mine = []
        for c in conns:
            key = fold(c["surname"]).replace(" ", "")
            if any(k and k in key for k in f["keys"]):
                mine.append({k: v for k, v in c.items() if k != "surname"})
        mine.sort(key=lambda c: (c["ourGeneration"], c["relation"] != "married"))
        entry = {"id": f["id"], "title": f["title"], "page": f["page"], "kind": f["kind"]}
        if cards:
            entry.pop("kind")  # the kit's contract has no such field; the families with a ribbon are all place lines
            lane = f["lane"]
            entry.update({"status": lane.get("status", ""), "statusNote": lane.get("statusNote", ""), "span": lane.get("span") or [None, None],
                          "cards": cards})
        if mine:
            entry["connections"] = mine
        else:
            entry["notConnected"] = {"why": why_for(f)}
        (lines if cards else links).append(entry)
        report.append((f["id"], f["page"], len(cards), len(mine), "; ".join(notes)))
    return ({"_note": NOTE_LINES, "families": lines}, {"_note": NOTE_LINKS, "families": links}, report)


def dump(o):
    return json.dumps(o, ensure_ascii=False, indent=1) + "\n"


# ------------------------------------------------------------------------------------------------ the blocks-only families, built
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.nodes = [], []

    def handle_starttag(self, tag, attrs):
        n = {"tag": tag, "a": dict(attrs), "kids": [], "text": []}
        if self.stack:
            self.stack[-1]["kids"].append(n)
        self.nodes.append(n)
        if tag not in ("br", "img", "meta", "link", "input", "hr", "source", "path", "circle", "rect", "line"):
            self.stack.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, d):
        for n in self.stack:
            n["text"].append(d)


def cls(n):
    return set((n["a"].get("class") or "").split())


def walk(n):
    yield n
    for k in n["kids"]:
        yield from walk(k)


def page_html(dist, path):
    p = os.path.join(dist, path.strip("/"), "index.html") if path.endswith("/") else os.path.join(dist, path.strip("/"))
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def check_built(links, dl, dist):
    errs = []
    dm = {p["slug"]: p for p in dl["people"] + dl["partners"]}
    base = ""
    for f in links["families"]:
        html = page_html(dist, f["page"])
        if html is None:
            errs.append("%s: the page %s is not built" % (f["id"], f["page"]))
            continue
        p = P()
        p.feed(html)
        secs = [n for n in p.nodes if n["tag"] == "section" and "fr" in cls(n) and n["a"].get("data-family") == f["id"]]
        if len(secs) != 1:
            errs.append("%s: %d blocks sections on %s (want 1)" % (f["id"], len(secs), f["page"]))
            continue
        sec = secs[0]
        if any("fr-c" in cls(n) for n in walk(sec)):
            errs.append("%s: a family with no line of generations has ribbon cards on the page" % f["id"])
        blocks = [n for n in walk(sec) if n["tag"] == "li" and "fr-b" in cls(n)]
        built = {(b["a"].get("data-our"), b["a"].get("data-their") or "", b["a"].get("data-relation")) for b in blocks}
        want = {(c["ourSlug"], c["theirSlug"], c["relation"]) for c in f.get("connections") or []}
        for k in sorted(want - built):
            errs.append("%s: the connection %s -> %s (%s) is in the data and not on the page" % ((f["id"],) + k))
        for k in sorted(built - want):
            errs.append("%s: a block %s -> %s (%s) is on the page and not in the data" % ((f["id"],) + k))
        nc = [n for n in walk(sec) if "fr-nc" in cls(n)]
        if f.get("notConnected") and len(nc) != 1:
            errs.append("%s: says it is not connected and the page has %d such blocks" % (f["id"], len(nc)))
        if f.get("connections") and nc:
            errs.append("%s: a 'not connected' block beside connections" % f["id"])
        for b in blocks:
            our = [k for k in walk(b) if "fr-b-our" in cls(k)]
            slug = our[0]["a"].get("data-ours") if our else None
            if not our or "is-ours" not in cls(our[0]) or slug not in dm:
                errs.append("%s: a block's our-side is not tinted or names nobody on the line (%r)" % (f["id"], slug))
            elif str(dm[slug]["generation"]) != b["a"].get("data-our-generation"):
                errs.append("%s: block generation %s for %s, direct-line.json says %s" % (f["id"], b["a"].get("data-our-generation"), slug, dm[slug]["generation"]))
        for n in walk(sec):
            if "is-ours" in cls(n) and n["a"].get("data-ours") not in dm:
                errs.append("%s: an is-ours element names %r, who is not on the line" % (f["id"], n["a"].get("data-ours")))
            if n["tag"] == "a" and n["a"].get("href", "").startswith("/"):
                h = n["a"]["href"]
                path, _, frag = h.partition("#")
                target = page_html(dist, path)
                if target is None:
                    errs.append("%s: link %s goes nowhere" % (f["id"], h))
                elif frag and not re.search(r"""\bid=["']%s["']""" % re.escape(frag), target):
                    errs.append("%s: link %s: no #%s in the page" % (f["id"], h, frag))
        if blocks and "tinted = our direct line" not in re.sub(r"\s+", " ", " ".join("".join(n["text"]) for n in walk(sec) if "fr-leg" in cls(n))):
            errs.append("%s: tinted blocks and no legend" % f["id"])
    return errs


def check_data(links, dl):
    errs = []
    dm = {p["slug"]: p for p in dl["people"] + dl["partners"]}
    roster = Roster()
    REL = {"married", "son of", "daughter of", "child of", "father of", "mother of", "parent of", "brother of", "sister of", "sibling of"}
    for f in links["families"]:
        conns = f.get("connections") or []
        if bool(conns) == bool(f.get("notConnected")):
            errs.append("%s: has connections and notConnected, or neither" % f["id"])
        seen = set()
        for c in conns:
            e = dm.get(c["ourSlug"])
            if not e or e["generation"] != c["ourGeneration"]:
                errs.append("%s: %s is not on the line at generation %s" % (f["id"], c["ourSlug"], c["ourGeneration"]))
            if c["relation"] not in REL:
                errs.append("%s: relation %r" % (f["id"], c["relation"]))
            if c["grade"] not in ("doc", "inf", "lore"):
                errs.append("%s: grade %r" % (f["id"], c["grade"]))
            if c["theirSlug"] and c["theirSlug"] not in roster.by:
                errs.append("%s: %s has no person page" % (f["id"], c["theirSlug"]))
            if c["theirSlug"] and roster.by.get(c["theirSlug"], {}).get("living"):
                errs.append("%s: %s is living" % (f["id"], c["theirSlug"]))
            k = (c["ourSlug"], c["theirSlug"] or c["theirName"], c["relation"])
            if k in seen:
                errs.append("%s: the same pair twice" % f["id"])
            seen.add(k)
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dist")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    lines, links, report = build()
    if a.report:
        for r in report:
            print("%-26s %-28s cards %2d  connections %d  %s" % r)
    if not a.check:
        open(OUT_LINES, "w", encoding="utf-8").write(dump(lines))
        open(OUT_LINKS, "w", encoding="utf-8").write(dump(links))
        print("build-family-lines: wrote family-lines.json (%d families with a ribbon) and family-links.json (%d with blocks only)"
              % (len(lines["families"]), len(links["families"])))
        return 0
    bad = []
    for path, want in ((OUT_LINES, lines), (OUT_LINKS, links)):
        have = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if have != dump(want):
            bad.append("%s is not what the data makes; run scripts/build-family-lines.py" % os.path.relpath(path, ROOT))
    dl = load("direct-line.json")
    bad += check_data(links, dl)
    roster = Roster()
    for f in lines["families"]:
        for i, c in enumerate(f["cards"]):
            for k in ("person", "spousePerson"):
                if c.get(k) and roster.by.get(c[k], {}).get("living"):
                    bad.append("%s card %d: %s is living and the card is not a living card" % (f["id"], i + 1, c[k]))
    looked = "the data"
    if a.dist:
        bad += check_built(links, dl, a.dist)
        looked = "the data and the built pages"
    for b in bad:
        print("FAIL build-family-lines: " + b)
    nconn = sum(len(f.get("connections") or []) for f in lines["families"] + links["families"])
    print("build-family-lines: %d error(s); %d families with a ribbon, %d with blocks only, %d connection blocks (looked at %s)"
          % (len(bad), len(lines["families"]), len(links["families"]), nconn, looked))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
