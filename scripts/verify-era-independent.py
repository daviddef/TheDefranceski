#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An independent judge of the "at the time" notes. It shares NO code with the kit (nothing is imported from kit/lib/era.js, eralib.py,
erasnap.py or checkera.py) and does not read the committed snapshot: it reads the Record Atlas's context.json (the contract), the rings in it,
this archive's own place decisions (data/era-ground.tsv, data/era-towns.tsv) and the roster, derives from the rules in kit/docs/era-notes.md
what every deceased person's page may say, and compares that with the BUILT pages, in both directions: a note the rules do not allow is WRONG,
a note the rules allow and the page lacks is MISSING.

    python3 scripts/verify-era-independent.py --contract <context.json> --dist site/dist-wt [--report out.json]

Prints counts only (no name, no date, no place that belongs to a person). Exit 0 only when there are 0 wrong and 0 missing.

THE RULES IT APPLIES (kit/docs/era-notes.md a-l, written out again here): a contract era is KEPT unless its start is not a whole year, its end is neither a
whole year nor null (a running era), its id/url is not the one its region and start imply, its regime is the shorthand 'feudal' or 'german', its
contestedScope is regime or part (or contested is true with no scope), or a margin it needs is null (a bound it cannot say). A kept era's label is the
regimeLabel (the shorthand 'napo' is shown with the era's polity). A year gets a note only if exactly one kept era covers it and no refused era
does and no kept era overlaps that one anywhere; the era is not still running at or after 1990; the year is more than max(5, margin) (plus 5 more
where marginSourced is false) from each numeric bound; and, for a place within 15 km of its region's ring edge (or inside another ring and not its
own), every neighbouring region (ring containing the place or within 15 km) has in that year exactly one kept era, no refused era over the year,
no overlap, the same label, a usable margin, and (if its era begins in that year) a kept predecessor of the same label that is neither approximate
nor contested. A place with such a neighbourhood and no neighbour is silent. A page prints no event date, only the years of the person: the note is
drawn only where EVERY printed plain year (born, died) has a note and they are the same note. Never on a living page or a duplicate.
"""
import argparse
import collections
import glob
import html
import json
import math
import os
import re
import sys
import unicodedata

N = 5
RECENT = 1990
EDGE = 15.0
PEER = 3.0
SRC_PLAIN = "per the Record Atlas"
SRC_SEEDED = "per the Record Atlas, drawn from this archive's own research"
BASE = "https://recordatlas.org"


def fold(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"['’`]", "", s)
    return re.sub(r"[^\w]+", " ", s).replace("_", " ").strip()


def is_year(x):
    return isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= 9999


def contains(lat, lon, ring):
    inside = False
    for i in range(len(ring)):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def area(ring):
    k = math.cos(math.radians(sum(p[0] for p in ring) / len(ring)))
    s = 0.0
    for i in range(len(ring)):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % len(ring)]
        s += x1 * k * y2 - x2 * k * y1
    return abs(s) / 2 * 111.195 ** 2


def edge_km(lat, lon, ring):
    k = math.cos(math.radians(lat))
    best = 1e18
    for i in range(len(ring)):
        ay, ax = ring[i]
        by, bx = ring[(i + 1) % len(ring)]
        px, py = (lon - ax) * k * 111.195, (lat - ay) * 111.195
        qx, qy = (bx - ax) * k * 111.195, (by - ay) * 111.195
        L = qx * qx + qy * qy
        t = 0 if L == 0 else max(0.0, min(1.0, (px * qx + py * qy) / L))
        best = min(best, math.hypot(px - t * qx, py - t * qy))
    return best


class Contract:
    def __init__(self, path):
        d = json.load(open(path, encoding="utf-8"))
        self.rule = d.get("rule")
        self.regions = {}
        self.rings = {}
        for r in d["regions"]:
            rid = r["id"]
            kept, refused = [], []
            for e in r.get("eras") or []:
                ok, lab = self.keep(rid, e)
                (kept if ok else refused).append(dict(e, _label=lab) if ok else e)
            self.regions[rid] = (kept, refused)
            if r.get("ring"):
                self.rings[rid] = r["ring"]

    @staticmethod
    def keep(rid, e):
        f, t = e.get("from"), e.get("to")
        if not is_year(f):
            return False, None
        if t is not None and not is_year(t):
            return False, None
        if t is None and e.get("present") is not True:
            return False, None
        if t is not None and not f < t:
            return False, None
        if e.get("id") != "%s--era-%d" % (rid, f) or e.get("url") != "/region/%s/#era-%d" % (rid, f):
            return False, None
        rl = e.get("regimeLabel")
        if not isinstance(rl, str) or not rl.strip():
            return False, None
        if e.get("regime") in ("feudal", "german"):
            return False, None
        lab = rl.strip()
        if e.get("regime") == "napo":
            pol = e.get("polity")
            if not isinstance(pol, str) or not pol.strip():
                return False, None
            pol = pol.strip()
            lab = pol if pol.lower().startswith(lab.lower()) else "%s — %s" % (lab, pol)
        scope = e.get("contestedScope") if isinstance(e.get("contestedScope"), str) else None
        if scope in ("regime", "part") or (scope is not None and scope not in ("none", "bounds")):
            return False, None
        if e.get("contested") is True and scope is None:
            return False, None
        has = "fromMargin" in e or "toMargin" in e
        if has:
            for key in ("fromMargin", "toMargin") if t is not None else ("fromMargin",):
                m = e.get(key)
                if not (isinstance(m, int) and not isinstance(m, bool) and m >= 0):
                    return False, None
        return True, lab

    def span(self, e):
        """first and last year (last None: running) a note may use, from the era's own margins and the floor."""
        soft = e.get("marginSourced") is False
        def reach(m):
            return max(N, m) + (N if soft else 0)
        rf = reach(e["fromMargin"]) if isinstance(e.get("fromMargin"), int) else None
        rt = None if e["to"] is None else (reach(e["toMargin"]) if isinstance(e.get("toMargin"), int) else None)
        if not e.get("approx") and not e.get("contested") and rf is None and rt is None:
            return None
        first = e["from"] + (rf + 1 if rf else 0)
        last = None if e["to"] is None else e["to"] - 1 - (rt or 0)
        return first, last

    def margin_ok(self, e, y):
        sp = self.span(e)
        if sp is None:
            return True
        return y >= sp[0] and (sp[1] is None or y <= sp[1])

    def era_for(self, rid, y):
        """-> ('ok', era, boundary) or ('no', reason)"""
        kept, refused = self.regions[rid]
        cov = [e for e in kept if e["from"] <= y and (e["to"] is None or y < e["to"])]
        ref = [e for e in refused if is_year(e.get("from")) and (e.get("to") is None or (is_year(e.get("to")) and e["from"] < e["to"]))
               and e["from"] <= y and (e.get("to") is None or y < e["to"])]
        if not cov:
            return ("no", "era-refused" if ref else "no-era")
        meets = lambda a, b: a["from"] < (b["to"] if b["to"] is not None else 1e9) and b["from"] < (a["to"] if a["to"] is not None else 1e9)
        if len(cov) > 1 or ref or any(o is not cov[0] and meets(cov[0], o) for o in kept):
            return ("no", "era-refused")
        e = cov[0]
        if e["to"] is None and y >= RECENT:
            return ("no", "recent")
        boundary = False
        if y == e["from"]:
            pred = any(o is not e and o["to"] == e["from"] for o in kept) or any(isinstance(d.get("to"), int) and d["to"] == e["from"] for d in refused)
            if pred:
                boundary = True
        if not self.margin_ok(e, y):
            return ("no", "margin")
        return ("ok", e, boundary)

    def agrees(self, nb, y, mine, boundary):
        if nb not in self.regions:
            return False
        kept, refused = self.regions[nb]
        if any(is_year(d.get("from")) and d["from"] <= y and (d.get("to") is None or (is_year(d.get("to")) and y < d["to"])) for d in refused):
            return False
        cov = [x for x in kept if x["from"] <= y and (x["to"] is None or y < x["to"])]
        if len(cov) != 1:
            return False
        x = cov[0]
        meets = lambda a, b: a["from"] < (b["to"] if b["to"] is not None else 1e9) and b["from"] < (a["to"] if a["to"] is not None else 1e9)
        if any(o is not x and meets(x, o) for o in kept):
            return False
        if not self.margin_ok(x, y):
            return False
        if x["_label"] != mine["_label"]:
            return False
        if not boundary and y == x["from"]:
            if any(d.get("to") == y for d in refused):
                return False
            before = [o for o in kept if o is not x and o["to"] == y]
            if not before or any(o["_label"] != mine["_label"] or o.get("approx") is True or o.get("contested") is True for o in before):
                return False
        return True


def tsv(path):
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        yield line.rstrip("\n").split("\t")


class Notes:
    def __init__(self, contract, ground, towns):
        self.c = contract
        self.towns = {}
        for cols in tsv(towns):
            if cols[0] == "town":
                continue
            cols = (cols + [""] * 5)[:5]
            self.towns[cols[0]] = (float(cols[1]), float(cols[2]), cols[4])
        self.ground = {}
        for cols in tsv(ground):
            if cols[0] == "place":
                continue
            cols = (cols + [""] * 4)[:4]
            self.ground[cols[0]] = cols[3]

    def region_of(self, place):
        """-> (region, lat, lon, reason-if-none)"""
        if place not in self.ground:
            return None, 0, 0, "no-row"
        town = self.ground[place]
        if not town:
            return None, 0, 0, "no-town"
        lat, lon, excl = self.towns[town]
        if excl:
            return None, lat, lon, "excluded"
        hit = sorted((area(r), k) for k, r in self.c.rings.items() if self.c.regions.get(k) and contains(lat, lon, r))
        if not hit:
            return None, lat, lon, "no-ring"
        own = hit[0][1]
        if len(hit) > 1 and hit[1][0] < PEER * hit[0][0] and edge_km(lat, lon, self.c.rings[own]) > EDGE:
            return None, lat, lon, "peer"
        return own, lat, lon, None

    def neighbours(self, own, lat, lon):
        ring = self.c.rings[own]
        mine = contains(lat, lon, ring)
        inside = [o for o, r in self.c.rings.items() if o != own and contains(lat, lon, r)]
        conflict = (not mine) and bool(inside)
        if conflict or edge_km(lat, lon, ring) <= EDGE:
            return sorted(o for o, r in self.c.rings.items() if o != own and (o in inside or edge_km(lat, lon, r) <= EDGE)) or None
        return []

    def note_year(self, place, y):
        """-> ('ok', note dict) or ('no', reason)"""
        own, lat, lon, why = self.region_of(place)
        if own is None:
            return ("no", "place:" + why)
        nb = self.neighbours(own, lat, lon)
        if nb is None:
            return ("no", "edge")
        r = self.c.era_for(own, y)
        if r[0] == "no":
            return ("no", r[1])
        _, e, boundary = r
        if nb and not all(self.c.agrees(n, y, e, boundary) for n in nb):
            return ("no", "edge")
        return ("ok", {"id": e["id"], "label": e["_label"], "boundary": boundary,
                       "assessed": e.get("approx") is not None and e.get("contested") is not None,
                       "approx": e.get("approx") is True, "contested": e.get("contested") is True,
                       "unsourced": e.get("marginSourced") is False and self.c.span(e) is not None,
                       "edge": bool(nb), "seeded": str(e.get("basis", "")).startswith("seeded:"), "place": fold(place)})

    def page(self, row):
        """-> (note or None, reason or None)"""
        if row.get("living"):
            return None, "living"
        if row.get("sameAs"):
            return None, "duplicate"
        place = row.get("place")
        if not place or not any(c.isalnum() for c in str(place)):
            return None, "no-place"
        years = [row[k] for k in ("b", "d") if isinstance(row.get(k), int) and not isinstance(row.get(k), bool)]
        if not years:
            return None, "no-plain-year"
        res = [self.note_year(place, y) for y in years]
        bad = [r for r in res if r[0] == "no"]
        if bad:
            return None, bad[0][1]
        base = {k: v for k, v in res[0][1].items()}
        for r in res[1:]:
            if r[1] != base:
                return None, "years-straddle"
        return dict(base, year=years[0]), None


NOTE = re.compile(r'<span class="era-note"([^>]*)>(.*?</a>)</span>', re.S)
ATTR = re.compile(r'(data-[a-z-]+)="([^"]*)"')


def read_page(path):
    h = open(path, encoding="utf-8").read()
    h = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
    m = re.search(r"<main\b.*?</main>", h, re.S)
    body = m.group(0) if m else h
    notes = NOTE.findall(body)
    out = []
    for attrs, inner in notes:
        a = dict(ATTR.findall(attrs))
        pre = re.search(r'<span class="era-pre">(.*?)</span>', inner, re.S)
        lab = re.search(r'<span class="era-lab">(.*?)</span>', inner, re.S)
        src = re.search(r'<a class="era-src" href="([^"]*)" rel="noopener">(.*?)</a>', inner, re.S)
        rest = re.sub(r"<[^>]+>", "", inner)
        out.append((a, html.unescape(pre.group(1)) if pre else None, html.unescape(lab.group(1)) if lab else None,
                    (src.group(1), html.unescape(src.group(2))) if src else None, html.unescape(rest)))
    return out, len(re.findall(r'class="era-note"', h))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--contract", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    root = a.root
    c = Contract(a.contract)
    nt = Notes(c, os.path.join(root, "data", "era-ground.tsv"), os.path.join(root, "data", "era-towns.tsv"))
    rows = json.load(open(os.path.join(root, "site", "src", "data", "roster.json"), encoding="utf-8"))["rows"]
    wrong = collections.Counter()
    missing = 0
    silent = collections.Counter()
    st = collections.Counter()
    for row in rows:
        exp, why = nt.page(row)
        path = os.path.join(a.dist, "person", row["pid"], "index.html")
        if not os.path.exists(path):
            wrong["page-absent"] += 1
            continue
        got, raw = read_page(path)
        st["pages"] += 1
        if row.get("living"):
            st["living"] += 1
            if raw:
                wrong["living-page-with-note"] += 1
            continue
        st["deceased"] += 1
        if row.get("sameAs"):
            st["duplicates"] += 1
        if len(got) > 1 or raw != len(got):
            wrong["more-than-one-note"] += 1
            continue
        if exp is None:
            silent[why] += 1
            if got:
                wrong["note-the-rules-do-not-allow"] += 1
            continue
        if not got:
            missing += 1
            continue
        attrs, pre, lab, src, rest = got[0]
        st["notes"] += 1
        if exp["seeded"]:
            st["seeded"] += 1
        if not exp["assessed"]:
            st["unassessed"] += 1
        if exp["unsourced"]:
            st["unsourced"] += 1
        if exp["edge"]:
            st["edge"] += 1
        if exp["approx"]:
            st["approx"] += 1
        if exp["contested"]:
            st["contested"] += 1
        if exp["boundary"]:
            st["boundary"] += 1
        want = {"data-era": exp["id"], "data-era-year": str(exp["year"]), "data-era-assessed": "1" if exp["assessed"] else "0",
                "data-era-place": exp["place"]}
        for k, f in (("data-era-boundary", "boundary"), ("data-era-approx", "approx"), ("data-era-contested", "contested"),
                     ("data-era-margin-unsourced", "unsourced"), ("data-era-edge-agree", "edge"), ("data-era-seeded", "seeded")):
            if exp[f]:
                want[k] = "1"
        if attrs != want:
            for k in set(attrs) | set(want):
                if attrs.get(k) != want.get(k):
                    wrong["attribute:" + k] += 1
        if lab != exp["label"]:
            wrong["label"] += 1
        if pre != ("· From that year: " if exp["boundary"] else "· At the time: "):
            wrong["prefix"] += 1
        region, era_from = exp["id"].split("--era-")
        if src is None or src[0] != "%s/region/%s/#era-%s" % (BASE, region, era_from) or src[1] != (SRC_SEEDED if exp["seeded"] else SRC_PLAIN):
            wrong["source"] += 1
        if rest != pre + lab + " " + (SRC_SEEDED if exp["seeded"] else SRC_PLAIN):
            wrong["text"] += 1
    # any note on a page that is not a person page
    stray = 0
    for p in glob.glob(os.path.join(a.dist, "**", "index.html"), recursive=True):
        rel = os.path.relpath(p, a.dist).split(os.sep)
        if rel[0] == "person" and len(rel) == 3:
            continue
        if 'class="era-note"' in open(p, encoding="utf-8").read():
            stray += 1
    if stray:
        wrong["note-on-a-page-that-is-not-a-person-page"] = stray
    nwrong = sum(wrong.values())
    print("verify-era-independent: %d person pages read, %d deceased (%d duplicates), %d living" % (st["pages"], st["deceased"], st["duplicates"], st["living"]))
    print("  notes %d on %d pages; seeded %d; on an unassessed era %d; on an unsourced margin %d; at an agreed edge %d; approx %d; contested %d; boundary %d"
          % (st["notes"], st["notes"], st["seeded"], st["unassessed"], st["unsourced"], st["edge"], st["approx"], st["contested"], st["boundary"]))
    print("  silent deceased pages by reason: " + "; ".join("%s %d" % (k, v) for k, v in sorted(silent.items(), key=lambda z: -z[1])))
    print("  WRONG %d %s; MISSING %d" % (nwrong, dict(wrong) if wrong else "", missing))
    if a.report:
        json.dump({"stats": dict(st), "silent": dict(silent), "wrong": dict(wrong), "missing": missing}, open(a.report, "w"), indent=1, sort_keys=True)
    if st["pages"] == 0 or st["notes"] == 0:
        print("  FAIL  nothing examined")
        return 2
    return 0 if nwrong == 0 and missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
