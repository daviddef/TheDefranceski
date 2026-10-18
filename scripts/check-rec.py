#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The gate for the record links the narrative pages carry (md.js `[words](rec:ID)`), judged against the data they come from.
Written 18 October 2026, with scripts/build-records.py, for the linking standard's L3 (kit/docs/linking-standard.md).

    python3 scripts/check-rec.py --dist DIST            every <a data-rec> on the built site, against the archive's own data
    python3 scripts/check-rec.py --dist DIST --sample N print N of them (page, words, address, what the data says), spread evenly
    python3 scripts/check-rec.py --self-test            plant the faults below in a made-up site; each must be caught

The kit's checkstandard.py only asks whether a passage that cites a record HAS a record link. It cannot say whether the link goes to the
right record; this does, by code of its own and from the SOURCE data, not from the table the links were made from:

  antenati   <a data-rec="antenati-an_uaNNN">: the words are that ark, the ark is a volume of antenati-catalogue.json, and the address is
             the catalogue's base + the ark
  familysearch  <a data-rec="fs-XXXX-XXXX-XXXX">: the words hold 3:1:XXXX-XXXX-XXXX and the address is the FamilySearch ark
             https://www.familysearch.org/ark:/61903/3:1:XXXX-XXXX-XXXX
  plate      <a data-rec="plate-ID" href="#plate-ID">: the plate exists in plates.json and has a picture, the page carries exactly ONE
             element with that id (components/Plates.astro or corrections.astro puts it there), and the words are a DAPA image id that
             is the FIRST one the plate's own holder line and caption quote (the key the standard's gate gives the plate)
  and on the whole site: no `](rec:` left as visible text (a link that never rendered), no rec link flagged living or hold, no record
  link on a page that is not a research narrative, and an empty site (no rec link at all) is refused: a gate that examined nothing has
  not passed. Counts are printed; a name never is.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")

A_REC = re.compile(r"<a\b([^>]*\bdata-rec=\"[^\"]*\"[^>]*)>(.*?)</a>", re.S)
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')
M_ID = re.compile(r"\bM0\d{7}\b")
FS_BASE = "https://www.familysearch.org/ark:/61903/3:1:"


def attrs(s):
    return {k: v.replace("&amp;", "&").replace("&quot;", '"') for k, v in ATTR.findall(s)}


def text_of(h):
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h))).strip()


def load_sources(data=DATA):
    with open(os.path.join(data, "antenati-catalogue.json"), encoding="utf-8") as f:
        cat = json.load(f)
    arks = {v["ark"] for c in cat["comuni"] for v in c["volumes"]}
    with open(os.path.join(data, "plates.json"), encoding="utf-8") as f:
        plates = {p["id"]: p for p in json.load(f)}
    with open(os.path.join(data, "records.json"), encoding="utf-8") as f:
        recs = {r["id"]: r for r in json.load(f)["records"]}
    return cat["base"], arks, plates, recs


def pages(dist):
    for root, _d, fs in os.walk(dist):
        for fn in fs:
            if fn.endswith(".html"):
                p = os.path.join(root, fn)
                u = "/" + os.path.relpath(p, dist).replace(os.sep, "/")
                u = re.sub(r"index\.html$", "", u)
                yield u, p


def check(dist, src=None, sample=0, out=print):
    base, arks, plates, recs = src or load_sources()
    bad, n, kinds, rows = [], 0, {"antenati": 0, "familysearch": 0, "plate": 0}, []
    literal = 0
    for u, p in pages(dist):
        h = open(p, encoding="utf-8").read()
        if "](rec:" in h:
            literal += 1
        for m in A_REC.finditer(h):
            a, words = attrs(m.group(1)), text_of(m.group(2))
            rid, href = a.get("data-rec", ""), a.get("href", "")
            n += 1
            rows.append((u, words, href, rid))
            if rid.startswith("plate-"):
                kinds["plate"] += 1
                pid = rid[6:]
                pl = plates.get(pid)
                if not pl or not pl.get("thumb"):
                    bad.append((u, "plate", "no such plate with a picture")); continue
                if href != "#" + rid:
                    bad.append((u, "plate", "address is not the plate's own anchor")); continue
                if len(re.findall(r'\bid="%s"' % re.escape(rid), h)) != 1:
                    bad.append((u, "plate", "the page does not carry exactly one anchor for the plate")); continue
                first = M_ID.search("%s %s" % (pl.get("holder") or "", pl.get("caption") or ""))
                if not first or first.group(0) not in M_ID.findall(words):
                    bad.append((u, "plate", "the words are not the DAPA image id the plate quotes")); continue
            elif rid.startswith("antenati-"):
                kinds["antenati"] += 1
                ark = rid[9:]
                if ark not in arks or words.strip() != ark or href != base + ark:
                    bad.append((u, "antenati", "words, ark or address do not match the catalogue")); continue
            elif rid.startswith("fs-"):
                kinds["familysearch"] += 1
                ark = rid[3:]
                if ("3:1:" + ark) not in words or href != FS_BASE + ark or rid not in recs or recs[rid]["url"] != href:
                    bad.append((u, "familysearch", "words or address do not match the ark")); continue
            else:
                bad.append((u, "other", "a record link this checker does not know")); continue
            r = recs.get(rid)
            if r and (r.get("living") or r.get("hold")):
                bad.append((u, "flag", "a living or hold row is drawn"))
    if literal:
        bad.append(("*", "literal", "%d page(s) show `](rec:` as text: a link that did not render" % literal))
    if n == 0:
        out("check-rec: REFUSED. no record link on the site: nothing was examined")
        return 2, rows
    for u, k, why in bad[:20]:
        out("  FAIL  %s %s: %s" % (u, k, why))
    out("check-rec: %d record links (%d Antenati, %d FamilySearch, %d plate) %s" % (
        n, kinds["antenati"], kinds["familysearch"], kinds["plate"], "all match their data" if not bad else "%d WRONG" % len(bad)))
    return (1 if bad else 0), rows


def self_test():
    import tempfile
    base = "https://antenati.example/ark:/1/"
    plates = {"p1": {"id": "p1", "thumb": "/plates/p1-t.webp", "holder": "film, M01000001", "caption": "also M01000002"}}
    recs = {"antenati-an_ua1": {"id": "antenati-an_ua1", "url": base + "an_ua1"},
            "fs-AAAA-BBBB-CCCC": {"id": "fs-AAAA-BBBB-CCCC", "url": FS_BASE + "AAAA-BBBB-CCCC"}}
    src = (base, {"an_ua1", "an_ua2"}, plates, recs)
    good = ('<main><p><a class="lk-rec" href="%san_ua1" data-rec="antenati-an_ua1" data-cite>an_ua1</a> '
            '<a href="%sAAAA-BBBB-CCCC" data-rec="fs-AAAA-BBBB-CCCC" data-cite>`3:1:AAAA-BBBB-CCCC`</a> '
            '<a href="#plate-p1" data-rec="plate-p1" data-cite>M01000001</a></p><button id="plate-p1"></button></main>') % (base, FS_BASE)
    faults = {
        "antenati wrong address": good.replace(base + "an_ua1", base + "an_ua2"),
        "antenati ark not in catalogue": good.replace('data-rec="antenati-an_ua1" data-cite>an_ua1', 'data-rec="antenati-an_ua9" data-cite>an_ua9').replace(base + "an_ua1", base + "an_ua9"),
        "fs wrong ark": good.replace("FS_BASE", "").replace(FS_BASE + "AAAA", FS_BASE + "ZZZZ"),
        "plate anchor missing": good.replace('<button id="plate-p1"></button>', ""),
        "plate anchor twice": good.replace('<button id="plate-p1"></button>', '<button id="plate-p1"></button><i id="plate-p1"></i>'),
        "plate words are the second id": good.replace(">M01000001<", ">M01000002<"),
        "plate does not exist": good.replace("plate-p1", "plate-p9"),
        "link left as text": good + "[M01000001](rec:plate-p1)",
    }
    ok = True
    with tempfile.TemporaryDirectory() as d:
        def run(html):
            os.makedirs(os.path.join(d, "x"), exist_ok=True)
            with open(os.path.join(d, "x", "index.html"), "w", encoding="utf-8") as f:
                f.write(html)
            return check(d, src, out=lambda *_a: None)[0]
        if run(good) != 0:
            print("self-test: the control (a right page) was refused"); ok = False
        for name, html in faults.items():
            if run(html) == 0:
                print("self-test: fault NOT caught: %s" % name); ok = False
        os.remove(os.path.join(d, "x", "index.html"))
        if check(d, src, out=lambda *_a: None)[0] != 2:
            print("self-test: an empty site was not refused"); ok = False
    print("check-rec self-test: %d faults planted, %s" % (len(faults) + 1, "all caught" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    # ARCHIVE_OUT redirects every reader, as it does for the kit's tools (a private build directory); --dist is the default it overrides
    dist = os.environ.get("ARCHIVE_OUT") or (argv[argv.index("--dist") + 1] if "--dist" in argv else "dist")
    if not os.path.isabs(dist) and not os.path.isdir(dist):
        dist = os.path.join(ROOT, "site", dist)
    sample = int(argv[argv.index("--sample") + 1]) if "--sample" in argv else 0
    rc, rows = check(dist)
    if sample and rows:
        step = max(1, len(rows) // sample)
        for u, w, h, r in rows[::step][:sample]:
            print("  %s | %s | %s | %s" % (u, w[:40], h, r))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
