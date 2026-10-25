#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prove check-living-v2.py can fail. A check that has only ever passed is a claim, not a check.

    python3 scripts/test-living-v2.py

This builds a SMALL INVENTED ARCHIVE in a temporary directory (a roster, built pages, a sitemap, a search
index, a ledger and a GEDCOM, all of them made up, none of them a person) and runs the gate over it:

  1. the clean fixture must PASS, or the faults below prove nothing;
  2. for every rule the gate enforces, one fault is planted in a COPY and the gate must name it.

Planted values are ones no living person can have: a birth year of 1799, a name that is not a name. No real
person appears in this file, in the fixture, or in the output. Exit 1 if the clean fixture fails or any
planted fault goes unnoticed.
"""
import os, sys, io, json, shutil, tempfile, importlib.util, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_v2 as L2

spec = importlib.util.spec_from_file_location("check_living_v2", os.path.join(HERE, "check-living-v2.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

YEAR = datetime.date.today().year
CUT = L2.cutoff(YEAR)          # the oldest birth year that is still living (1946 in 2026)
UID = {"live1": "TESTUID-LIVE-1", "live2": "TESTUID-LIVE-2", "child": "TESTUID-CHILD-1", "old": "TESTUID-OLD-1",
       "dead": "TESTUID-DEAD-1", "cited": "TESTUID-CITED-1", "undated": "TESTUID-UNDATED-1"}
N_FILLER = 110


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


def page(name, living, *, noindex=None, ld=None, table=False, img=False, extra=""):
    noindex = living if noindex is None else noindex
    ld = (not living) if ld is None else ld
    head = '<title>%s</title>' % name
    if noindex:
        head += '<meta name="robots" content="noindex">'
    if ld:
        head += '<script type="application/ld+json">{"@type":"Person","name":"%s","birthDate":"1799"}</script>' % name
    body = "<h1>%s</h1><p>%s</p>" % (name, "Testville, Testland" if living else "born 1799, died 1850")
    if table:
        body += "<table><tr><td>x</td></tr></table>"
    if img:
        body += '<img src="/x.png" alt="">'
    return "<!doctype html><html><head>%s</head><body><header>menu</header><main>%s%s</main><footer>Built %d</footer></body></html>" % (
        head, body, extra, YEAR)


def gedcom():
    def indi(i, uid, name, by=None, dead=False, fam=None, cite=None):
        s = "0 @I%d@ INDI\n1 NAME %s\n1 _UID %s\n" % (i, name, uid)
        if by:
            s += "1 BIRT\n2 DATE %d\n" % by
        if dead:
            s += "1 DEAT\n2 DATE 1850\n"
        if cite:
            s += "1 NOTE %s\n" % cite
        if fam:
            s += "1 FAMC @F1@\n"
        return s
    out = "0 HEAD\n1 SOUR MYHERITAGE\n"
    out += indi(1, UID["live1"], "Qx /Livone/", YEAR - 36)
    out += indi(2, UID["live2"], "Qx /Livtwo/", YEAR - 41)
    out += indi(3, UID["child"], "Qx /Childone/", YEAR - 9)
    out += indi(4, UID["old"], "Qx /Oldone/", 1799)
    out += indi(5, UID["dead"], "Qx /Deadone/", YEAR - 50, dead=True)
    out += indi(6, UID["cited"], "Qx /Citedone/", YEAR - 30, cite="FamilySearch ark:/61903/1:1:TEST")
    out += indi(7, UID["undated"], "Qx /Undatedone/", None, fam=True)       # no birth year, a living parent
    out += "0 @F1@ FAM\n1 HUSB @I1@\n1 CHIL @I7@\n"
    out += "0 TRLR\n"
    return out


def fixture(root):
    data = os.path.join(root, "site", "src", "data")
    dist = os.path.join(root, "site", "dist")
    rows = []
    for i in range(N_FILLER):
        rows.append({"name": "Zz Filler%d" % i, "pid": "zz-filler-%d" % i, "who": "/who/zz-filler-%d/" % i,
                     "b": 1700 + i, "d": 1760 + i, "place": "Oldtown, Testland", "src": "burial", "note": "a note"})
    live = [("Qx Livone", "qx-livone", "first cousin"), ("Qx Livtwo", "qx-livtwo", ""),
            ("Qx Childone", "qx-childone", "son")]       # a known child: a living row with a page, like anyone
    for name, pid, rel in live:
        r = {"name": name, "pid": pid, "who": "/who/%s/" % pid, "line": "x", "place": "Testville, Testland",
             "places": ["Testville, Testland"], "src": "life", "href": "/x/", "b": None, "d": None, "note": "",
             "ark": "", "mh": "", "notable": False, "living": True}
        if rel:
            r["rel"] = rel
        rows.append(r)
    rows.append({"name": "Qx Oldone", "pid": "qx-oldone", "who": "/who/qx-oldone/", "b": 1799, "d": None,
                 "place": "Oldtown, Testland", "src": "index", "note": ""})
    # POSITIVE CONTROLS for rule 7: the year just outside the window is not a living person's; a person born in the
    # window who has a death is not either. A gate that refuses these is a gate that cries wolf.
    rows.append({"name": "Qx Eightyone", "pid": "qx-eightyone", "who": "/who/qx-eightyone/", "b": CUT - 1, "d": None,
                 "place": "Oldtown, Testland", "src": "index", "note": ""})
    rows.append({"name": "Qx Gone", "pid": "qx-gone", "who": "/who/qx-gone/", "b": YEAR - 30, "d": YEAR - 3,
                 "place": "Oldtown, Testland", "src": "index", "note": ""})
    json.dump({"rows": rows}, io.open(os.path.join(data, "roster.json"), "w", encoding="utf-8")) if os.makedirs(data, exist_ok=True) is None else None
    # pages
    for r in rows:
        w(os.path.join(dist, "person", r["pid"], "index.html"), page(r["name"], bool(r.get("living"))))
        w(os.path.join(dist, "who", r["pid"], "index.html"), page(r["name"], bool(r.get("living"))))
    w(os.path.join(data, "zz-controls.json"), json.dumps(
        [{"name": "Qx Gone", "pid": "qx-gone", "b": YEAR - 30, "d": YEAR - 3}, {"name": "Qx Eightyone", "b": CUT - 1},
         {"n": "Qx Gone", "y": str(YEAR - 30), "p": "", "living": False}]))
    w(os.path.join(root, "data", "living-year-allow.json"),
      json.dumps({"allow": [{"text": "Qx Allowed b. %d" % CUT, "why": "a reviewed exception (control)"}]}))
    w(os.path.join(dist, "controls", "index.html"),
      "<!doctype html><html><head><title>controls</title></head><body><main><p>Qx Gone (b. %d, died %d). Qx Eightyone b. %d. "
      "Qx Allowed b. %d. Written in %d.</p></main></body></html>" % (YEAR - 30, YEAR - 3, CUT - 1, CUT, YEAR))
    w(os.path.join(dist, "about", "index.html"),
      "<!doctype html><html><head><title>about</title></head><body><main><p>About this archive.</p></main></body></html>")
    # who pages are keyed by slug = pid in the fixture
    sm = "".join("<url><loc>https://x.test/person/%s/</loc></url>" % r["pid"] for r in rows if not r.get("living"))
    w(os.path.join(dist, "sitemap.xml"), "<urlset>%s</urlset>" % sm)
    idx = [{"k": "Person", "t": r["name"], "h": r["who"], "q": r["name"].lower()} for r in rows if not r.get("living")]
    for rel in ("site/src/data/searchindex.json", "site/public/searchindex.json", "site/dist/searchindex.json"):
        w(os.path.join(root, rel), json.dumps(idx))
    led = {"people": {"qx-livone": UID["live1"], "qx-livtwo": UID["live2"], "qx-oldone": UID["old"],
                      "qx-childone": UID["child"]},
           "held": [UID["undated"]], "unlinked_on_living_pages": 0}
    w(os.path.join(root, "data", "living-ledger.json"), json.dumps(led))
    w(os.path.join(root, "tree.ged"), gedcom())
    return rows


def load(root):
    p = os.path.join(root, "site", "src", "data", "roster.json")
    return json.load(io.open(p, encoding="utf-8"))


def save(root, d):
    json.dump(d, io.open(os.path.join(root, "site", "src", "data", "roster.json"), "w", encoding="utf-8"))


def run_gate(root, tree=True, require_tree=False):
    t = L2.load_tree(os.path.join(root, "tree.ged")) if tree else None
    dist = os.path.join(root, "site", "dist")
    return G.run(root, dist, t, YEAR, require_tree)


def person(root, pid):
    return os.path.join(root, "site", "dist", "person", pid, "index.html")


def row(root, pid):
    d = load(root)
    return d, next(r for r in d["rows"] if r["pid"] == pid)


# ---- the planted faults: (name, expected fragment in a problem, mutate(root)) ----
def F_rule(root):
    d, _ = row(root, "qx-oldone"); d["rows"].append({"name": "Qx Young", "pid": "qx-young", "b": YEAR - 30, "d": None,
                                                     "src": "index", "note": ""}); save(root, d)
    w(person(root, "qx-young"), page("Qx Young", False))

def F_scrub_b(root):
    d, r = row(root, "qx-livone"); r["b"] = 1799; save(root, d)

def F_scrub_note(root):
    d, r = row(root, "qx-livone"); r["note"] = "an occupation and a note"; save(root, d)

def F_scrub_key(root):
    d, r = row(root, "qx-livtwo"); r["parish"] = "Testparish"; save(root, d)

def F_place(root):
    d, r = row(root, "qx-livone"); r["places"] = ["12 Zz Street, Testville, Testland"]; save(root, d)

def F_place_inst(root):
    d, r = row(root, "qx-livone"); r["places"] = ["Zz General Hospital, Testland"]; save(root, d)

def F_child_dates(root):
    d, r = row(root, "qx-childone"); r["b"] = YEAR - 9; save(root, d)

def F_noindex(root):
    w(person(root, "qx-livone"), page("Qx Livone", True, noindex=False))

def F_ld(root):
    w(person(root, "qx-livone"), page("Qx Livone", True, ld=True))

def F_table(root):
    w(person(root, "qx-livone"), page("Qx Livone", True, table=True))

def F_img(root):
    w(person(root, "qx-livone"), page("Qx Livone", True, img=True))

def F_year(root):
    w(person(root, "qx-livone"), page("Qx Livone", True, extra="<p>1799</p>"))

def F_whopage(root):
    w(os.path.join(root, "site", "dist", "who", "qx-livone", "index.html"), page("Qx Livone", True, noindex=False))

def F_sitemap(root):
    p = os.path.join(root, "site", "dist", "sitemap.xml")
    w(p, io.open(p, encoding="utf-8").read().replace("</urlset>", "<url><loc>https://x.test/person/qx-livone/</loc></url></urlset>"))

def F_search(root):
    for rel in ("site/src/data/searchindex.json",):
        p = os.path.join(root, rel)
        j = json.load(io.open(p, encoding="utf-8")); j.append({"k": "Person", "t": "Qx Livone", "h": "/who/qx-livone/", "q": "qx"}); w(p, json.dumps(j))

def F_search_built(root):
    p = os.path.join(root, "site", "dist", "searchindex.json")
    j = json.load(io.open(p, encoding="utf-8")); j.append({"k": "Person", "t": "Qx Livtwo", "h": "/who/qx-livtwo/", "q": "qx"}); w(p, json.dumps(j))

def F_nopage(root):
    os.remove(person(root, "zz-filler-3"))

def F_links(root):
    fig = '<figure class="ptree"><div class="node">x</div><span class="node">y</span></figure>'
    w(person(root, "qx-livone"), page("Qx Livone", True, extra=fig))

def F_tree_disagree(root):
    d, r = row(root, "qx-oldone"); r["living"] = True; r.update({"b": None}); save(root, d)

def F_tree_not_living_flag(root):
    d, r = row(root, "qx-livone"); r["living"] = False; r["b"] = YEAR - 36; save(root, d)

def F_child_held(root):
    led = json.load(io.open(os.path.join(root, "data", "living-ledger.json"), encoding="utf-8"))
    led["held"].append(UID["child"]); w(os.path.join(root, "data", "living-ledger.json"), json.dumps(led))

def F_child_nopage(root):
    d = load(root); d["rows"] = [r for r in d["rows"] if r["pid"] != "qx-childone"]; save(root, d)
    shutil.rmtree(os.path.join(root, "site", "dist", "person", "qx-childone"))
    w(os.path.join(root, "site", "src", "data", "worklist.json"), json.dumps({"rows": [{"note": "Qx Childone was here"}]}))

def F_tree_minor_row(root):
    led = json.load(io.open(os.path.join(root, "data", "living-ledger.json"), encoding="utf-8"))
    led["people"]["qx-kid"] = UID["undated"]; w(os.path.join(root, "data", "living-ledger.json"), json.dumps(led))
    d, _ = row(root, "qx-oldone"); d["rows"].append({"name": "Qx Kid", "pid": "qx-kid", "b": None, "d": None, "living": True,
                                                     "src": "life", "place": "Testville, Testland", "note": "", "ark": "", "mh": ""}); save(root, d)
    w(person(root, "qx-kid"), page("Qx Kid", True))

def F_held_in_data(root):
    w(os.path.join(root, "site", "src", "data", "worklist.json"), json.dumps({"rows": [{"note": "Qx Undatedone was here"}]}))

def F_held_in_page(root):
    w(os.path.join(root, "site", "dist", "about", "index.html"), "<main><p>about Qx Undatedone</p></main>")

def F_cited_living(root):
    d, _ = row(root, "qx-oldone"); d["rows"].append({"name": "Qx Citedone", "pid": "qx-citedone", "b": YEAR - 30, "d": None,
                                                     "src": "index", "note": ""}); save(root, d)
    w(person(root, "qx-citedone"), page("Qx Citedone", False))
    led = json.load(io.open(os.path.join(root, "data", "living-ledger.json"), encoding="utf-8"))
    led["people"]["qx-citedone"] = UID["cited"]; w(os.path.join(root, "data", "living-ledger.json"), json.dumps(led))

def F_empty_living(root):
    d = load(root)
    for r in d["rows"]:
        r.pop("living", None); r["b"] = 1799; r["d"] = 1850
    save(root, d)

def F_empty_dist(root):
    shutil.rmtree(os.path.join(root, "site", "dist", "person"))

def F_no_tree(root):
    pass

def _about(root, extra):
    p = os.path.join(root, "site", "dist", "about", "index.html")
    w(p, io.open(p, encoding="utf-8").read().replace("</main>", extra + "</main>"))

def F_boundary(root):
    d, _ = row(root, "qx-oldone"); d["rows"].append({"name": "Qx Boundary", "pid": "qx-boundary", "b": CUT, "d": None,
                                                     "src": "index", "note": ""}); save(root, d)
    w(person(root, "qx-boundary"), page("Qx Boundary", False))

def F_cited_dated(root):
    d, _ = row(root, "qx-oldone"); d["rows"].append({"name": "Qx Citedrow", "pid": "qx-citedrow", "b": CUT, "d": None,
                                                     "src": "index", "note": "", "cited": "FamilySearch", "ark": "ark:/61903/1:1:TEST"}); save(root, d)
    w(person(root, "qx-citedrow"), page("Qx Citedrow", False))

def F_data_living(root):
    w(os.path.join(root, "site", "src", "data", "zz-planted.json"), json.dumps([{"pid": "qx-livone", "name": "Qx Livone", "b": YEAR - 36}]))

def F_data_living_dt(root):
    w(os.path.join(root, "site", "src", "data", "zz-planted.json"),
      json.dumps({"ptree": {"parents": [{"n": "Qx Livtwo", "dt": str(YEAR - 41), "slug": "qx-livtwo", "pid": "qx-livtwo"}]}}))

def F_data_nodeath(root):
    w(os.path.join(root, "site", "src", "data", "zz-planted.json"), json.dumps([{"name": "Qx Nobody", "b": CUT + 3}]))

def F_data_reconcile(root):
    w(os.path.join(root, "site", "src", "data", "zz-planted.json"), json.dumps({"new": [{"n": "Qx Nobody", "y": str(CUT), "p": "", "living": False}]}))

def F_data_built(root):
    w(os.path.join(root, "site", "dist", "zz-planted.json"), json.dumps({"places": [{"people": [{"n": "Qx Nobody", "y": CUT + 1, "d": None, "w": "/who/qx-nobody/"}]}]}))

def F_page_b(root):
    _about(root, "<p>Qx Nobody (b. %d)</p>" % (CUT + 2))

def F_page_born_run(root):
    _about(root, "<p>Three children born 1942, %d and %d.</p>" % (CUT, CUT + 1))

def F_page_born_in(root):
    _about(root, "<p>Where the child was born at Testville in %d.</p>" % (YEAR - 5))

def F_page_born_ordinary(root):
    _about(root, "<p>Qx Nobody, born %d, a stranger.</p>" % (CUT - 30))

def F_jsonld(root):
    _about(root, '<script type="application/ld+json">{"@type":"Person","name":"Qx Nobody","birthDate":"%d"}</script>' % (CUT + 4))

def F_name_year(root):
    _about(root, "<p>Qx Livone, %d, of Testville.</p>" % (YEAR - 36))

def F_name_year_b(root):
    _about(root, "<p>Qx Livtwo (b. %d)</p>" % (YEAR - 41))

def F_tree_name_year(root):
    _about(root, "<p>Qx Citedone %d</p>" % (YEAR - 30))

def F_literal_cutoff(root):
    w(os.path.join(root, "site", "src", "pages", "zz.astro"), "---\nconst NOW = new Date().getFullYear();\nconst maybe = (c) => (NOW - c.by) < 80;\n---\n")

def F_literal_const(root):
    w(os.path.join(root, "scripts", "zz-planted.py"), "PRESUME_DEAD_AFTER = 80\n")

FAULTS = [
    ("rule: an unmarked row the rule calls living", "rule:", F_rule, {}),
    ("scrub: a living row with a birth year", "scrub:", F_scrub_b, {}),
    ("scrub: a living row with a note", "scrub:", F_scrub_note, {}),
    ("scrub: a living row with a parish", "scrub:", F_scrub_key, {}),
    ("place: a street in a living place", "place:", F_place, {}),
    ("place: a hospital in a living place", "place:", F_place_inst, {}),
    ("child: a known child's row carries a birth year (a child follows the standard)", "scrub:", F_child_dates, {}),
    ("child: a known child wrongly held out by the ledger", "child:", F_child_held, {}),
    ("child: a known child named but with no page", "no person page", F_child_nopage, {}),
    ("page: a living page that is not noindex", "not noindex", F_noindex, {}),
    ("page: a living page with structured data", "structured data", F_ld, {}),
    ("page: a living page with a table", "table", F_table, {}),
    ("page: a living page with an image", "image", F_img, {}),
    ("page: a living page with a year (1799)", "four-digit year", F_year, {}),
    ("name page: every bearer living and not noindex", "name page", F_whopage, {}),
    ("sitemap: a living page listed", "sitemap:", F_sitemap, {}),
    ("search: a living person in the source index", "search:", F_search, {}),
    ("search: a living person in the built index", "search:", F_search_built, {}),
    ("pages: a roster row with no page", "no page", F_nopage, {}),
    ("links: more unlinked relatives than recorded", "links:", F_links, {}),
    ("tree: the roster says living, the rule says not", "tree:", F_tree_disagree, {}),
    ("tree: the roster says not living, the rule says living", "tree:", F_tree_not_living_flag, {}),
    ("tree: an undated person with a living parent published as a row", "possible minor", F_tree_minor_row, {}),
    ("held out: an undated person with a living parent, named in a data file", "held out:", F_held_in_data, {}),
    ("held out: the same, named in a built page", "held out:", F_held_in_page, {}),
    ("empty: no living person in the roster", "empty:", F_empty_living, {}),
    ("empty: no built person pages", "empty:", F_empty_dist, {}),
    ("tree absent but required", "tree:", F_no_tree, {"tree": False, "require_tree": True}),
    ("rule 7: a person born in the cutoff year (exactly 80) published with no living mark", "rule:", F_boundary, {}),
    ("rule 7: a dated person under 81 with a public-source citation published as not living (the 1946 fault)", "rule:", F_cited_dated, {}),
    ("rule 7: a data row naming a living person carries a birth year", "year:", F_data_living, {}),
    ("rule 7: a family-tree node of a living person carries a dated line (dt)", "year:", F_data_living_dt, {}),
    ("rule 7: a data row with a birth year in the window, no death, no living flag", "year:", F_data_nodeath, {}),
    ("rule 7: a reconciliation row (y, living false) with a year in the window", "year:", F_data_reconcile, {}),
    ("rule 7: the same in a BUILT data file (atlas pin: y, d null)", "year:", F_data_built, {}),
    ("rule 7: «b. YYYY» in the window on a built page", "year:", F_page_b, {}),
    ("rule 7: «born 1942, YYYY and YYYY» (a run of years) on a built page", "year:", F_page_born_run, {}),
    ("rule 7: «born at Testville in YYYY» on a built page", "year:", F_page_born_in, {}),
    ("rule 7: Person JSON-LD with a birthDate in the window and no deathDate", "year:", F_jsonld, {}),
    ("rule 7: a living person's name followed by a year in the window", "year:", F_name_year, {}),
    ("rule 7: a living person's name followed by «(b. YYYY)»", "year:", F_name_year_b, {}),
    ("rule 7: a person the tree gives as 80 or younger followed by their own year", "year:", F_tree_name_year, {}),
    ("rule 8: a page that spells the 80-year boundary out (NOW - by < 80)", "cutoff:", F_literal_cutoff, {}),
    ("rule 8: a script that sets its own PRESUME_DEAD_AFTER = 80", "cutoff:", F_literal_const, {}),
]


def main():
    base = tempfile.mkdtemp(prefix="living-v2-")
    bad = []
    try:
        clean = os.path.join(base, "clean")
        fixture(clean)
        P, N, S = run_gate(clean)
        print("clean fixture: %s  (%d living rows incl. a known child, %d living pages read, %d ledger entries agree, %d held out by rule)" % (
            "PASSES" if not P else "FAILS", S["living rows"], S["living pages examined"], S["ledger entries checked"],
            S["possible minors in the tree"]))
        if P:
            for p in P[:8]:
                print("    ", p)
            print("The clean fixture must pass or nothing below proves anything.")
            return 1
        print("%-62s %s" % ("planted fault", "caught?"))
        for name, expect, mut, opt in FAULTS:
            d = os.path.join(base, "f%02d" % FAULTS.index((name, expect, mut, opt)))
            shutil.copytree(clean, d)
            mut(d)
            P, N, S = run_gate(d, tree=opt.get("tree", True), require_tree=opt.get("require_tree", False))
            hit = [p for p in P if expect in p]
            print("%-62s %s" % (name, "YES  (%d)" % len(P) if hit else "NO  <<<<"))
            if not hit:
                bad.append(name)
        # NEGATIVE CONTROLS: ordinary content that must not be refused (a gate that cries wolf stops being read)
        for name, mut in (("an ordinary «born» year long before the window", F_page_born_ordinary),):
            d = os.path.join(base, "n%d" % len(bad))
            shutil.copytree(clean, d)
            mut(d)
            P, N, S = run_gate(d)
            ok = not P
            print("%-62s %s" % ("control: " + name, "passes (right)" if ok else "REFUSED <<<<"))
            if not ok:
                bad.append("control: " + name)
        print("\n%d planted faults, %d caught, %d missed" % (len(FAULTS), len(FAULTS) - len(bad), len(bad)))
        return 1 if bad else 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
