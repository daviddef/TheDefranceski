#!/usr/bin/env python3
"""Plant ONE fault per check and confirm the check says so.

A check that has never been seen to fail is a claim, not a check. Every line of the
gate prints «ok» when the world is fine and when the check cannot see the world, and
those two look the same. This plants a fault the check is MEANT to catch, runs the
check, and reports whether it noticed. Whatever it does not notice is the finding.

    scripts/sweep-faults.py DIST [--only name,name]
    scripts/sweep-faults.py --zero DIST_EMPTY     # every dist-reading check against nothing

DIST is a BUILT tree (site/<DIST>) the sweep may edit in place: each fault is undone
in a finally block and the file's original bytes written back, so the build is the
same afterwards. Data faults edit the tracked file and restore it the same way —
`git diff` is the proof, and the sweep ends by running it.
"""
import os, sys, json, re, subprocess, shutil, glob, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
KIT = "node_modules/@daviddef/archive-kit/kit/tools"


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


class Edit:
    """Edit a file, undo on exit."""
    def __init__(self, path, fn):
        self.path, self.fn = path, fn
    def __enter__(self):
        self.orig = open(self.path, "rb").read()
        new = self.fn(self.orig.decode("utf-8"))
        if new == self.orig.decode("utf-8"):
            raise RuntimeError(f"fault did not change {self.path}")
        wr(self.path, new)
    def __exit__(self, *a):
        open(self.path, "wb").write(self.orig)


class Both:
    def __init__(self, *cs): self.cs = cs
    def __enter__(self):
        self.done = []
        for c in self.cs:
            c.__enter__(); self.done.append(c)
    def __exit__(self, *a):
        for c in reversed(self.done): c.__exit__(*a)


class Move:
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        os.rename(self.path, self.path + ".sweep")
    def __exit__(self, *a):
        os.rename(self.path + ".sweep", self.path)


class Make:
    """Create a file, remove on exit."""
    def __init__(self, path, body):
        self.path, self.body = path, body
    def __enter__(self):
        assert not os.path.exists(self.path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        wr(self.path, self.body)
    def __exit__(self, *a):
        os.remove(self.path)


def run(cmd, env=None):
    e = dict(os.environ)
    if env: e.update(env)
    r = subprocess.run(cmd, cwd=SITE, capture_output=True, text=True, env=e, shell=isinstance(cmd, str))
    out = (r.stdout or "") + (r.stderr or "")
    bad = r.returncode != 0 or "FAIL" in out
    return bad, out


def build_cases(D):
    d = os.path.join(SITE, D)
    page = lambda p: os.path.join(d, p.strip("/"), "index.html")
    LZ, IDX, SRC = page("liznjan"), os.path.join(d, "index.html"), page("sources")
    PERSON = page("person/magdalena-davic-pomer")
    kit = lambda t, *a: ["python3", f"{KIT}/{t}", *a]
    KARCH = kit("checkarchive.py", "--dist", D)
    def app(s, extra): return s.replace("</body>", extra + "</body>", 1)
    C = []
    def add(name, tool, cmd, ctx, env=None):
        C.append(dict(name=name, tool=tool, cmd=cmd, ctx=ctx, env=env))
    env = {"ARCHIVE_OUT": D}
    add("links: a hand-written href to a page that does not exist", "kit checkarchive", KARCH,
        lambda: Edit(LZ, lambda s: app(s, '<a href="/this-page-does-not-exist/">x</a>')))
    add("anchors: a #fragment that names no section", "kit checkarchive", KARCH,
        lambda: Edit(LZ, lambda s: app(s, '<a href="/liznjan/#no-such-section">x</a>')))
    add("ambiguous: two sections carry the same id", "kit checkarchive", KARCH,
        lambda: Edit(LZ, lambda s: app(s, '<h2 id="dupe-zz">a</h2><h2 id="dupe-zz">b</h2><a href="/liznjan/#dupe-zz">x</a>')))
    add("searchindex: /searchindex.json missing", "kit checkarchive", KARCH,
        lambda: Move(os.path.join(d, "searchindex.json")))
    add("titles: a page with no <title>", "kit checkarchive", KARCH,
        lambda: Edit(LZ, lambda s: re.sub(r"<title>.*?</title>", "", s, count=1, flags=re.S)))
    add("images: an <img> pointing at nothing", "kit checkarchive", KARCH,
        lambda: Edit(LZ, lambda s: app(s, '<img src="/plates/does-not-exist-zz.webp" alt="x" width="10" height="10">')))
    add("counter render: count and label as adjacent spans, no gap", "kit checkarchive", KARCH,
        lambda: Edit(IDX, lambda s: re.sub(r"\.vc-l[^{,]*\{[^}]*\}", "", app(s, '<span class="vc-n">0</span><span class="vc-l">times read</span>'))))
    add("counter host: pageviews logged to somebody else's account", "check_counter", ["python3", "../scripts/check_counter.py"],
        lambda: Edit(IDX, lambda s: re.sub(r'data-goatcounter="https?://[^./"]+\.goatcounter\.com', 'data-goatcounter="https://thefalco.goatcounter.com', s, count=1)), env)
    add("nav: an Evidence menu entry removed", "kit checknav", kit("checknav.py", "--dist", D, "--strict"),
        lambda: Edit(IDX, lambda s: s.replace('href="/method/"', 'href="/method-gone/"')))
    add("absence: a page still says «no archive of her own line yet»", "check-absence", ["python3", "../scripts/check-absence.py", "--dist", f"site/{D}"],
        lambda: Edit(IDX, lambda s: app(s, "<p>Francisca Salomon — no archive of her own line yet</p>")))
    add("licences: GeoNames used and no longer credited", "check-licences", ["python3", "../scripts/check-licences.py", "--dist", D],
        lambda: Edit(SRC, lambda s: re.sub(r"GeoNames", "Gazetteer", s)))
    add("evidence: a person with evidence on disk whose page carries no record", "check-evidence", ["python3", "../scripts/check-evidence.py", "--dist", D],
        lambda: Edit(page("who/" + vsl), lambda s: s.replace('class="rk"', 'class="xx"').replace('class="recstrip"', 'class="xx"')))
    return C


def living_v2_cases(D):
    """The living-people standard v2 gate, over the REAL tree: a fault in a built page, in the sitemap, in the
    search index, and in the roster. The faults that need David's tree (a minor's name in a data file, a ledger
    the rule disagrees with) are planted in a made-up archive by scripts/test-living-v2.py, because a real
    person's name must not be written to a tracked path even for a moment."""
    ro = json.load(open(os.path.join(SITE, "src/data/roster.json")))["rows"]
    lv = next((x for x in ro if x.get("living") and x.get("pid")), None)
    if not lv:
        return []
    d = os.path.join(SITE, D)
    LP = os.path.join(d, "person", lv["pid"], "index.html")
    SM = next((p for p in glob.glob(os.path.join(d, "sitemap*.xml"))), None)
    SI = os.path.join(d, "searchindex.json")
    RO = os.path.join(SITE, "src/data/roster.json")
    cmd = ["python3", "../scripts/check-living-v2.py", "--dist", D, "--no-tree"]
    env = {"ARCHIVE_OUT": D}
    def jedit(fn):
        def g(s):
            o = json.loads(s); fn(o); return json.dumps(o, indent=1, ensure_ascii=False)
        return g
    def rows(o): return o["rows"] if isinstance(o, dict) else o
    def idx(o): o.append({"k": "Person", "t": lv["name"], "h": "/person/%s/" % lv["pid"], "q": "x"})
    C = []
    def add(name, ctx): C.append(dict(name=name, tool="check-living-v2", cmd=cmd, ctx=ctx, env=env))
    add("living v2: a living person's page loses its noindex",
        lambda: Edit(LP, lambda s: s.replace('<meta name="robots" content="noindex">', "", 1)))
    add("living v2: a living person's page gains Person structured data",
        lambda: Edit(LP, lambda s: s.replace("</head>", '<script type="application/ld+json">{"@type":"Person","name":"x","birthDate":"1799"}</script></head>', 1)))
    add("living v2: a living person's page gains a table",
        lambda: Edit(LP, lambda s: s.replace("</main>", "<table><tr><td>x</td></tr></table></main>", 1)))
    add("living v2: a living person's page gains an image",
        lambda: Edit(LP, lambda s: s.replace("</main>", '<img src="/x.png" alt=""></main>', 1)))
    add("living v2: a living person's page gains a year (1799)",
        lambda: Edit(LP, lambda s: s.replace("</main>", "<p>1799</p></main>", 1)))
    if SM:
        add("living v2: a living person's page is listed in the sitemap",
            lambda: Edit(SM, lambda s: s.replace("</urlset>", "<url><loc>https://x.test/person/%s/</loc></url></urlset>" % lv["pid"], 1)))
    add("living v2: a living person is in the built search index",
        lambda: Edit(SI, jedit(idx)))
    add("living v2: a living row carries a birth year (1799)",
        lambda: Edit(RO, jedit(lambda o: [x.__setitem__("b", 1799) for x in rows(o) if x.get("pid") == lv["pid"]])))
    add("living v2: a living row carries a note",
        lambda: Edit(RO, jedit(lambda o: [x.__setitem__("note", "an occupation") for x in rows(o) if x.get("pid") == lv["pid"]])))
    add("living v2: a street in a living place",
        lambda: Edit(RO, jedit(lambda o: [x.__setitem__("places", ["12 Zz Street, Testville, Testland"]) for x in rows(o) if x.get("pid") == lv["pid"]])))
    add("living v2: an unmarked row the rule calls living (born 30 years ago)",
        lambda: Edit(RO, jedit(lambda o: rows(o).append(dict(rows(o)[0], pid="zz-sweep-v2", name="Zz Sweep V2", b=datetime.date.today().year - 30, d=None, ark="", living=False)))))
    add("living v2: a known child shown with a birth year and no living mark (born 9 years ago)",
        lambda: Edit(RO, jedit(lambda o: rows(o).append(dict(rows(o)[0], pid="zz-sweep-kid", name="Zz Sweep Kid", b=datetime.date.today().year - 9, d=None, ark="", living=False)))))
    add("living v2: the first person page is gone",
        lambda: Move(os.path.join(d, "person", rows(ro)[0]["pid"], "index.html")))
    return C


def living_case(D):
    """A living person's full date: the data attaches it, a built page prints it."""
    rp = os.path.join(SITE, "src/data/roster.json")
    ro = json.load(open(rp))["rows"]
    living = [x for x in ro if x.get("living") and x.get("who")]
    for x in living:
        p = os.path.join(SITE, D, x["who"].strip("/"), "index.html")
        if os.path.exists(p):
            def dated(s):
                o = json.loads(s)
                for r in (o["rows"] if isinstance(o, dict) else o):
                    if r.get("pid") == x["pid"]: r["born"] = "4 March 1951"
                return json.dumps(o, indent=1, ensure_ascii=False)
            return dict(name="living: the data holds a living person's full date and a page prints it", tool="kit checkliving",
                        cmd=["../scripts/kit-living.sh", "--dist", D, "--data", "src/data", "--policy", "named-bare"],
                        ctx=lambda: Both(Edit(rp, dated), Edit(p, lambda s: s.replace("</body>", "<p>4 March 1951</p></body>", 1))), env=None)
    return None


def data_cases(D):
    dd = os.path.join(SITE, "src/data")
    RO, WL, PL, SE = (os.path.join(dd, n) for n in ("roster.json", "worklist.json", "plates.json", "searched.json"))
    CO = os.path.join(dd, "corrections.json")
    DEC = os.path.join(ROOT, "data/decisions.json")
    def jedit(fn):
        def g(s):
            o = json.loads(s); fn(o); return json.dumps(o, indent=1, ensure_ascii=False)
        return g
    def rows(o): return o["rows"] if isinstance(o, dict) else o
    kit = lambda t, *a: ["python3", f"{KIT}/{t}", *a]
    C = []
    def add(name, tool, cmd, ctx): C.append(dict(name=name, tool=tool, cmd=cmd, ctx=ctx, env=None))
    add("propagation: a corrected claim put back (Magdalena Davić)", "check-propagation", ["python3", "../scripts/check-propagation.py"],
        lambda: Edit(RO, jedit(lambda o: rows(o)[0].__setitem__("note", (rows(o)[0].get("note") or "") + " Magdalena Davić"))))
    add("decisions: a frozen person's name edited without re-declaring", "check-decisions", ["python3", "../scripts/check-decisions.py"],
        lambda: Edit(RO, jedit(lambda o: rows(o)[0].__setitem__("name", rows(o)[0]["name"] + " Zz"))))
    add("atlas outcomes: a searched row with an outcome word the atlas cannot read", "check-atlas-outcomes", ["python3", "../scripts/check-atlas-outcomes.py"],
        lambda: Edit(SE, jedit(lambda o: rows(o)[0].__setitem__("outcome", "probably-something"))))
    add("dates: a birth date inside the 80-year rule, unexplained", "check-dates-everywhere", ["python3", "../scripts/check-dates-everywhere.py"],
        lambda: Edit(RO, jedit(lambda o: rows(o).append(dict(rows(o)[0], pid="zz-sweep-date", name="Zz Sweep Two", b=1995, d=None)))))
    add("kin: a death before the birth", "kit checkkin", kit("checkkin.py", "--data", "src/data/roster.json", "--born", "b", "--died", "d", "--max", "0"),
        lambda: Edit(RO, jedit(lambda o: rows(o).append(dict(rows(o)[0], pid="zz-sweep-kin", name="Zz Sweep Three", b=1900, d=1850)))))
    add("worklist: a row loses its state", "kit checkworklist", kit("checkworklist.py", "--root", "."),
        lambda: Edit(WL, jedit(lambda o: [r.pop("state", None) for r in rows(o)[:1]])))
    add("pin: package.json names a kit the lockfile did not resolve", "kit checkpin", kit("checkpin.py", "--root", "."),
        lambda: Edit(os.path.join(SITE, "package.json"), lambda s: re.sub(r"(archive-kit\"?: \"github:daviddef/TheArchiveKit#)[0-9a-f]{40}", r"\g<1>" + "0" * 40, s, count=1)))
    add("living data: a living flag beside a death year", "check-living-data", ["python3", "../scripts/check-living-data.py"],
        lambda: Edit(RO, jedit(lambda o: rows(o).append(dict(rows(o)[0], pid="zz-sweep-living", name="Zz Sweep", b=1962, d=1990, living=True)))))
    add("covers: a pending search the work list does not account for", "kit checkcovers", kit("checkcovers.py", "--root", "."),
        lambda: Edit(SE, jedit(lambda o: rows(o).append(dict(src="zz sweep search", what="zz", when="16 Oct 2026", outcome="pending")))))
    add("places: a Croatian place pinned in the Philippines", "kit checkplaces", kit("checkplaces.py", "--data", "public/atlas-data.json"),
        lambda: Edit(os.path.join(SITE, "public/atlas-data.json"), lambda s: _pin_wrong(s)))
    add("pages: a shared page rewritten by hand (bespoke count up)", "kit checkpages", kit("checkpages.py", "--root", ".", "--estate", "../../Family Projects", "--max-bespoke", "0"),
        lambda: Edit(os.path.join(SITE, "src/pages/worklist.astro"), lambda s: '---\nimport Base from "../layouts/Base.astro";\n---\n<Base title="zz"><p>zz</p></Base>\n'))
    big = "[\n" + ",\n".join('  { n: "place %d", t: "a long descriptive string about a place and what happened there %d", href: "/x/%d/" }' % (i, i, i) for i in range(60)) + "\n]"
    add("inline: a list of 60 evidence rows inside a template", "kit checkinline", kit("checkinline.py", "--root", ".", "--max-inline", "2"),
        lambda: Make(os.path.join(SITE, "src/pages/zz-sweep2.astro"), '---\nimport Base from "../layouts/Base.astro";\nconst PLACES = ' + big + ';\n---\n<Base title="zz"><p>{PLACES.length}</p></Base>\n'))
    SRC_J = os.path.join(SITE, "src/data/sources.json")
    newsrc = lambda: Edit(SRC_J, jedit(lambda o: rows(o).append({"name": "Zz sweep source", "what": "no link and not held"})))
    add("sources AS WIRED: a source row with no link and not held", "kit checksources (as wired)", kit("checksources.py", "--root", ".", "--dist", D), newsrc)
    add("sources WITH THE RATCHET at today's ten", "kit checksources (ratchet 10)", kit("checksources.py", "--root", ".", "--dist", D, "--max-unreachable", "10"), newsrc)
    add("sources: the source list is gone", "kit checksources (as wired)", kit("checksources.py", "--root", ".", "--dist", D), lambda: Move(SRC_J))
    return C


def _pin_wrong(s):
    o = json.loads(s)
    for pl in o["places"]:
        if "Croatia" in json.dumps(pl, ensure_ascii=False) or "Istria" in json.dumps(pl, ensure_ascii=False):
            pl["lat"], pl["lon"] = 14.6, 121.0
            break
    return json.dumps(o, ensure_ascii=False)


def _break_places(s):
    o = json.loads(s)
    arr = o if isinstance(o, list) else (o.get("places") or o.get("features") or o)
    if isinstance(arr, list) and arr:
        first = arr[0]
        for k in ("lat", "lon", "lng", "coords", "latitude", "longitude"):
            first.pop(k, None)
    return json.dumps(o, ensure_ascii=False)


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "--zero":
        D = a[1]
        os.makedirs(os.path.join(SITE, D), exist_ok=True)
        cmds = [("kit checkarchive", ["python3", f"{KIT}/checkarchive.py", "--dist", D]),
                ("kit checknav", ["python3", f"{KIT}/checknav.py", "--dist", D, "--strict"]),
                ("kit checkliving", ["../scripts/kit-living.sh", "--dist", D, "--data", "src/data", "--policy", "named-bare"]),
                ("check-living-v2", ["python3", "../scripts/check-living-v2.py", "--dist", D, "--no-tree"]),
                ("check_counter", ["python3", "../scripts/check_counter.py"]),
                ("check-absence", ["python3", "../scripts/check-absence.py", "--dist", f"site/{D}"]),
                ("check-licences", ["python3", "../scripts/check-licences.py", "--dist", D]),
                ("kit checksources", ["python3", f"{KIT}/checksources.py", "--root", ".", "--dist", D]),
                ("check-evidence", ["python3", "../scripts/check-evidence.py", "--dist", D])]
        print(f"{'check':20}  verdict on an EMPTY build tree")
        for n, c in cmds:
            bad, out = run(c, {"ARCHIVE_OUT": D} if n == "check_counter" else None)
            last = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
            print(f"{n:20}  {'REFUSES' if bad else 'PASSES (examined nothing and said ok)'}   | {last[0][:110]}")
        return
    D = a[0]
    only = None
    if "--only" in a: only = set(a[a.index("--only") + 1].split(","))
    cases = build_cases(D) + ([living_case(D)] if living_case(D) else []) + living_v2_cases(D) + data_cases(D)
    if "--baseline" in a:
        print("every command on the UNMODIFIED tree — each must be green or the sweep means nothing")
        for c in cases:
            bad, out = run(c["cmd"], c["env"])
            print(f"{'RED' if bad else 'green':6} {c['tool']:24} {c['name'][:60]}" + (f"   | {out.strip().splitlines()[-1][:100]}" if bad else ""))
        return
    print(f"{'caught':7} {'check':24} fault")
    miss = []
    for c in cases:
        if only and c["tool"] not in only: continue
        try:
            with c["ctx"]():
                bad, out = run(c["cmd"], c["env"])
        except Exception as e:
            print(f"{'ERR':7} {c['tool']:24} {c['name']}  ({e})"); miss.append((c, str(e))); continue
        print(f"{'YES' if bad else 'NO  <<':7} {c['tool']:24} {c['name']}")
        if not bad: miss.append((c, out.strip().splitlines()[-1:] or [""]))
    print(f"\n{len(cases)-len(miss)} caught, {len(miss)} not caught")
    r = subprocess.run(["git", "status", "--short", "--", "site/src", "site/package.json", "data"], cwd=ROOT, capture_output=True, text=True)
    print("tree after sweep (should show only this script and untracked files):", r.stdout.strip() or "clean")

main()
