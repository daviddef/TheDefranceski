#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is what a /who/<name>/ dossier holds for ONE person readable on that person's page, and only there?

    python3 ../tools/checkdossierfold.py --dist "${ARCHIVE_OUT:-dist}"        # from site/; `npm run check:dossierfold`
    python3 ../tools/checkdossierfold.py --dist "${ARCHIVE_OUT:-dist}" --selftest   # plants one fault per rule

WHY (23 November 2026). /who/<name>/ is a research dossier on a NAME and it stays exactly where it is. David's decision was that the
research text that lives only there must also be readable on the bearers' own pages, so that one page per person costs nothing.
Measured on the build, almost all of it already is: the dossier's "What the archive knows" is the roster rows' own notes strung
together, and a person page in story mode tells its row's note in its story cards (the same words under the life's headings, not as
one block). Two things were on /who/ and on no person page: the notes of the 25 duplicate rows whose page is only a pointer ("the
same person as another page"), and the one FamilySearch index entry the name page draws for a name with no household, for the person
whose own row was read from it. Those are shown in a block (<div class="dfold" data-who data-pid>) and this gate judges it.

It reads the BUILD for what a reader sees, and the source data (src/data/roster.json, dossiers.json, register.json) for whose a
paragraph is:

  living      a fold block on a living person's page (noindex, data-living="1", or a roster row that says living).
  who         the block's name page does not exist, or does not list this person among its bearers.
  person      the block's data-pid is not the page's person.
  text        a folded paragraph is not, word for word, a paragraph of THIS person's roster note (so it is about someone else, or
              it was changed), or is not on the name page's "What the archive knows".
  rec         a folded index entry whose id is not the id this person's own row was read from (`ark`), whose register entry is
              about someone of another given name, or which the name page does not draw.
  twice       a folded paragraph whose words are already on the rest of the page, or an entry whose id is already shown there.
  missing     a duplicate's pointer page whose row note is on its name page and not in full in its block.
  untold      a person page in story mode whose row note is not readable on it (less than 70% of its 4-word runs are on the page:
              measured on the build, the least is 80% for any note of four words or more).
  absent      an index entry that belongs on a page (the row was read from it, same given name, no household drawn, id not shown) and
              is not there.

A living person is never named in a message: their page is reported as "a living person's page". Exit 0 clean, 1 findings, 2 it
could not see what it checks (no build, no data, no pointer page with a folded note).
"""
import argparse
import html
import json
import os
import re
import sys
import unicodedata

BLOCK = re.compile(r'<div class="dfold"[^>]*>')
TOLD = 0.70


# ---- reading --------------------------------------------------------------------------------------------------------------------
def read_pages(dist):
    pages = {}
    for root, _dirs, files in os.walk(dist):
        if "index.html" in files:
            rel = os.path.relpath(root, dist).replace(os.sep, "/")
            route = "/" if rel == "." else "/" + rel + "/"
            if route.startswith(("/person/", "/who/")) and route not in ("/person/", "/who/"):
                with open(os.path.join(root, "index.html"), encoding="utf-8", errors="replace") as f:
                    pages[route] = f.read()
    return pages


def read_data(site):
    d = os.path.join(site, "src", "data")
    out = {}
    for k in ("roster", "dossiers", "register"):
        with open(os.path.join(d, k + ".json"), encoding="utf-8") as f:
            out[k] = json.load(f)
    return out


def is_stub(raw):
    return 'http-equiv="refresh"' in raw[:900]


def noindex(raw):
    return bool(re.search(r'<meta name="robots" content="[^"]*noindex', raw[:6000])) or 'data-living="1"' in raw


def balanced(raw, start):
    """The html of the <div> that opens at `start`, to its matching </div>."""
    depth, i = 0, start
    for m in re.finditer(r"<(/?)div\b[^>]*>", raw[start:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return raw[start:start + m.end()]
    return raw[start:]


def text_of(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def sq(s):
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", str(s)).lower())


def mdplain(t):
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    return t.replace("*", "").replace("`", "")


def toks(s):
    return re.findall(r"\w+", unicodedata.normalize("NFKC", s.lower()))


def grams(t, n=4):
    return [" ".join(t[i:i + n]) for i in range(max(1, len(t) - n + 1))]


def coverage(note, page_text):
    words = toks(mdplain(note))
    if len(words) < 4:           # a note of one to three words ("Arms", "Cimitero di Giubiasco") has no 4-word run: it is on the page or it is not
        return 1.0 if sq(mdplain(note)) in sq(page_text) else 0.0
    g = grams(words)
    have = set(grams(toks(page_text)))
    return sum(1 for x in g if x in have) / len(g) if g else 1.0


def name_slug(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = re.sub(r"[̀-ͯ]", "", s)
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-zA-Z0-9]+", "-", s)).lower()[:60]


def who_slug_of(r):
    if r.get("who"):
        m = re.match(r"^/who/([^/]+)/$", r["who"])
        return m.group(1) if m else None
    return name_slug(r.get("name"))


def name_words(s):
    s = unicodedata.normalize("NFD", re.sub(r"\s*\(.*?\)\s*", " ", str(s or "")))
    return re.findall(r"[a-z]+", re.sub(r"[̀-ͯ]", "", s).lower())


def same_given(a, b):
    x, y = (name_words(a) or [None])[0], (name_words(b) or [None])[0]
    if not x or not y:
        return False
    return x == y or (len(x) >= 4 and y.startswith(x)) or (len(y) >= 4 and x.startswith(y))


def ark_id(r):
    m = re.search(r"([0-9A-Z]{4}-[0-9A-Z]{3,4})", str((r or {}).get("ark") or ""))
    return m.group(1) if m else None


def paragraphs(note):
    return [p.strip() for p in re.split(r"\n\n+", str(note or "")) if p.strip()]


def bearers_of(raw):
    m = re.search(r'<ul class="who-bearers"[^>]*>(.*?)</ul>', raw, re.S)
    return re.findall(r'href="(/person/[^"#?]+/)"', m.group(1)) if m else []


def known_text(raw):
    """The squashed words of a name page's 'What the archive knows' box."""
    m = re.search(r'<div class="known"[^>]*>', raw)
    return sq(text_of(balanced(raw, m.start()))) if m else ""


def block_of(raw):
    m = BLOCK.search(raw)
    return balanced(raw, m.start()) if m else None


def label(route, raw):
    return "a living person's page" if noindex(raw) else route


# ---- the judgement --------------------------------------------------------------------------------------------------------------
def check(pages, data):
    """(findings, counts) over an in-memory build (route -> html) and the source data."""
    roster = {r["pid"]: r for r in data["roster"]["rows"] if r.get("pid")}
    people = data["dossiers"]["people"]
    reg = {x["id"]: x for x in data["register"]["rows"]}
    persons = {r: raw for r, raw in pages.items() if r.startswith("/person/") and not is_stub(raw)}
    whos = {r: raw for r, raw in pages.items() if r.startswith("/who/") and not is_stub(raw)}
    if not persons or not whos or not roster:
        return None, {}
    findings, c = [], {"fold blocks": 0, "paragraphs folded": 0, "words folded": 0, "index entries folded": 0,
                       "pointer pages with a note": 0, "story pages measured": 0}
    pid_of = lambda route: route[len("/person/"):-1]
    bearer_routes = {wr: set(bearers_of(raw)) for wr, raw in whos.items()}

    for route, raw in sorted(persons.items()):
        pid = pid_of(route)
        r = roster.get(pid)
        lbl = label(route, raw)
        blk = block_of(raw)
        pointer = "data-person-page" not in raw
        living = noindex(raw) or bool(r and r.get("living"))
        if r is None:
            if blk:
                findings.append("person: %s has a fold block and no roster row" % lbl)
            continue
        slug = who_slug_of(r)
        wroute = "/who/%s/" % slug if slug else None
        wraw = whos.get(wroute) if wroute else None
        d = people.get(slug) if slug else None

        if blk:
            c["fold blocks"] += 1
            if living:
                findings.append("living: %s carries a fold block" % lbl)
                continue
            m = re.search(r'data-who="([^"]*)" data-pid="([^"]*)"', blk[:400])
            bwho, bpid = (m.group(1), m.group(2)) if m else (None, None)
            if bpid != pid:
                findings.append("person: %s has a block for another person (data-pid says %s)" % (lbl, "someone else" if bpid else "nothing"))
            if bwho != slug or wraw is None or route not in bearer_routes.get(wroute, set()):
                findings.append("who: %s has a block from a name page that does not list this person" % lbl)
                continue
            outside = text_of(raw.replace(blk, " ", 1))
            known = known_text(wraw)
            note_paras = [sq(mdplain(p)) for p in paragraphs(r.get("note"))]
            for part in re.finditer(r'<div class="dfold-p" data-fold="note"', blk):
                ptxt = text_of(balanced(blk, part.start()))
                s = sq(ptxt)
                c["paragraphs folded"] += 1
                c["words folded"] += len(ptxt.split())
                if s not in note_paras:
                    findings.append("text: %s folds a paragraph that is not a paragraph of this person's own note" % lbl)
                elif s not in known:
                    findings.append("text: %s folds a paragraph that is not on the name page's 'What the archive knows'" % lbl)
                if sq(ptxt) and grams(toks(ptxt)) and coverage(ptxt, outside) >= 0.9:
                    findings.append("twice: %s folds a paragraph whose words are already on the page" % lbl)
            for part in re.finditer(r'<div class="dfold-rec" data-fold="rec" data-id="([^"]*)"', blk):
                rid = part.group(1)
                c["index entries folded"] += 1
                e = reg.get(rid)
                ok = (ark_id(r) == rid and e is not None and same_given(e.get("n"), r.get("name"))
                      and d is not None and d.get("rec") and d["rec"].get("id") == rid and not d.get("ptree") and not r.get("sameAs"))
                if not ok:
                    findings.append("rec: %s shows an index entry that is not the one this person's own row was read from" % lbl)
                if wraw is not None and rid not in wraw:
                    findings.append("rec: %s shows an index entry its name page does not draw" % lbl)
                if rid in outside:
                    findings.append("twice: %s shows an index entry whose id is already on the page" % lbl)
            # a notes paragraph on a page that tells its note itself is a double telling
            if not pointer and re.search(r'data-fold="note"', blk):
                findings.append("twice: %s folds a note and tells its note in the story too" % lbl)

        if living or d is None or wraw is None or route not in bearer_routes.get(wroute, set()):
            continue
        known = known_text(wraw)
        note = r.get("note") or ""
        holds = bool(note) and (d.get("known") == note or note in (d.get("more") or []))
        if pointer and holds:
            c["pointer pages with a note"] += 1
            have = sq(text_of(blk)) if blk else ""
            main = re.search(r"<main.*?</main>", raw, re.S)
            outside = text_of((main.group(0) if main else raw).replace(blk or "\0", " ", 1))
            # a paragraph is there if the block holds it, or the page already says it (the lede line is the note's first sentence)
            if any(sq(mdplain(p)) not in have and coverage(p, outside) < 0.9 for p in paragraphs(note)):
                findings.append("missing: %s is a duplicate's pointer and does not carry its row's note in full" % lbl)
        elif holds and not pointer:
            c["story pages measured"] += 1
            body = re.search(r"<main.*?</main>", raw, re.S)
            main = text_of(body.group(0).replace(blk, " ", 1) if blk and body else (body.group(0) if body else raw))
            if coverage(note, main) < TOLD:
                findings.append("untold: %s does not tell its row's note (%d%% of its words)" % (lbl, round(100 * coverage(note, main))))
        # an index entry that belongs here
        if not pointer and not r.get("sameAs"):
            rec, rid = d.get("rec"), ark_id(r)
            if rec and not d.get("ptree") and rid and rec.get("id") == rid and rid in reg and same_given(reg[rid].get("n"), r.get("name")):
                body = re.search(r"<main.*?</main>", raw, re.S)
                rest = (body.group(0) if body else raw)
                rest = rest.replace(blk, " ", 1) if blk else rest
                if rid not in rest and not (blk and 'data-fold="rec"' in blk):
                    findings.append("absent: %s lacks the index entry its row was read from" % lbl)
    return findings, c


# ---- the self-test --------------------------------------------------------------------------------------------------------------
def selftest(pages, data):
    f0, c0 = check(pages, data)
    ok = True
    print("  control: the untouched build -> %d finding(s)%s" % (len(f0 or []), "" if not f0 else "  <-- SHOULD BE 0"))
    if f0:
        ok = False
    withnote = sorted(r for r, raw in pages.items() if r.startswith("/person/") and 'data-fold="note"' in raw)
    withrec = sorted(r for r, raw in pages.items() if r.startswith("/person/") and 'data-fold="rec"' in raw)
    living = sorted(r for r, raw in pages.items() if r.startswith("/person/") and r != "/person/" and noindex(raw) and "data-person-page" in raw)
    story = sorted(r for r, raw in pages.items() if r.startswith("/person/") and "data-person-page" in raw and not noindex(raw) and "dfold" not in raw
                   and len(re.sub(r"<[^>]+>", "", raw)) > 3000)
    if not withnote or not withrec or not living or len(story) < 2:
        print("  no pointer page with a folded note, no folded index entry, no living page or no story page to plant against: refusing")
        return False
    def first_para_alone(route):
        raw = pages[route]
        bk = block_of(raw)
        f = re.search(r'<div class="dfold-p" data-fold="note"[^>]*>', bk)
        return bool(f) and coverage(text_of(balanced(bk, f.start())), text_of(raw.replace(bk, " ", 1))) < 0.5
    cand = [r for r in withnote if first_para_alone(r)]
    if not cand:
        print("  no pointer page whose first folded paragraph is not already on the page to plant against: refusing")
        return False
    a, b = cand[0], story[0]
    ra = pages[a]
    blk = block_of(ra)

    def planted(name, mutate, want):
        nonlocal ok
        v = dict(pages)
        mutate(v)
        got, _c = check(v, data)
        hit = any(g.startswith(want) for g in (got or []))
        print("  %-62s %s" % (name, "caught" if hit else "MISSED  <-- the gate cannot see this"))
        ok = ok and hit

    first = re.search(r'<div class="dfold-p" data-fold="note"[^>]*>', blk)
    para = balanced(blk, first.start())
    planted("a folded paragraph with a word changed",
            lambda v: v.__setitem__(a, ra.replace(para, para.replace(" the ", " a ", 1) if " the " in para else para + " extra words", 1)), "text")
    planted("a block on a living person's page",
            lambda v: v.__setitem__(living[0], v[living[0]].replace("</main>", blk + "</main>", 1)), "living")
    planted("one person's block on another person's page",
            lambda v: v.__setitem__(b, v[b].replace("</main>", blk + "</main>", 1)), "person")
    planted("a block whose name page does not list the person",
            lambda v: v.__setitem__(a, ra.replace('data-who="', 'data-who="nobody-', 1)), "who")
    planted("a folded paragraph that is not this person's note",
            lambda v: v.__setitem__(a, ra.replace(para, '<div class="dfold-p" data-fold="note"><p>The archive says something this person\'s note never said at all.</p></div>', 1)), "text")
    planted("a pointer page that lost a paragraph of its note",
            lambda v: v.__setitem__(a, ra.replace(para, "", 1)), "missing")
    inner = text_of(para)
    planted("a folded paragraph also written into the page",
            lambda v: v.__setitem__(a, ra.replace("</main>", "<p>" + html.escape(inner) + "</p></main>", 1)), "twice")
    rr = pages[withrec[0]]
    rblk = block_of(rr)
    rid = re.search(r'data-fold="rec" data-id="([^"]*)"', rblk).group(1)
    planted("an index entry with another id",
            lambda v: v.__setitem__(withrec[0], rr.replace('data-id="%s"' % rid, 'data-id="ZZZZ-ZZZZ"', 1)), "rec")
    planted("an index entry whose id is also on the page",
            lambda v: v.__setitem__(withrec[0], rr.replace("</main>", "<p>FamilySearch %s</p></main>" % rid, 1)), "twice")
    planted("an index entry that belongs on a page and is not there",
            lambda v: v.__setitem__(withrec[0], rr.replace(rblk, "", 1)), "absent")
    planted("a story page that no longer tells its note",
            lambda v: _untell(v, pages, data), "untold")
    return ok


def _untell(v, pages, data):
    """Blank the body of a story page whose row note is on its name page."""
    roster = {r["pid"]: r for r in data["roster"]["rows"] if r.get("pid")}
    people = data["dossiers"]["people"]
    for route, raw in sorted(pages.items()):
        if not route.startswith("/person/") or "data-person-page" not in raw or noindex(raw):
            continue
        r = roster.get(route[len("/person/"):-1])
        d = people.get(who_slug_of(r)) if r else None
        note = (r or {}).get("note") or ""
        listed = any(route in bearers_of(raw2) for wr, raw2 in pages.items() if wr == "/who/%s/" % who_slug_of(r)) if r else False
        if d and listed and len(note.split()) > 40 and (d.get("known") == note or note in (d.get("more") or [])):
            body = re.search(r"<main.*?</main>", raw, re.S)
            v[route] = raw.replace(body.group(0), '<main><article data-person-page="1" data-mode="story" data-living="0"><p>Nothing here.</p></article></main>', 1)
            return
    raise SystemExit("selftest: no story page with a long note to plant against")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--site", default=".", help="the site folder that holds src/data (default: the current directory)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.dist):
        print("checkdossierfold: %s is not a directory; nothing was checked" % a.dist)
        return 2
    try:
        data = read_data(a.site)
    except OSError as e:
        print("checkdossierfold: cannot read the source data (%s); nothing was checked" % e)
        return 2
    pages = read_pages(a.dist)
    if a.selftest:
        return 0 if selftest(pages, data) else 1
    findings, counts = check(pages, data)
    if findings is None:
        print("checkdossierfold: no person page, no name page or no roster in %s; nothing was checked" % a.dist)
        return 2
    if not counts.get("pointer pages with a note"):
        print("checkdossierfold: no duplicate's pointer page with a note on its name page; nothing was checked")
        return 2
    for f in findings:
        print("  FAIL  " + f)
    print("checkdossierfold: " + ", ".join("%d %s" % (v, k) for k, v in counts.items()) + "; %d finding%s" % (len(findings), "" if len(findings) == 1 else "s"))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
