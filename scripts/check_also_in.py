#!/usr/bin/env python3
"""Does every confirmed cross-archive pair show its pointer on this archive's page, and nobody else?

Written 17 October 2026, after the pattern of D'Arcy's tools/check_also_in.py. The kit keeps the list of
people documented in two archives (kit/data/cross-archive.json) and draws «Also documented in The Blazevic
Archive» for a pair marked CONFIRMED. The component is silent for everything else, which is exactly why this
reads the BUILT page: a template that forgets to pass `archive` or `path` renders nothing, says nothing, and
every gate that reads the source or the list sees a correct input. Nothing else can tell «no pointer because
there is no confirmed pair» from «no pointer because the prop never arrived».

It checks both directions, because a rule checked one way drifts the other:
  - every CONFIRMED pair with a page of this archive: that page carries exactly one pointer, and it links to
    the other archive's page at the address the ring gives
  - no OTHER page carries one, and above all no LIVING page does: a living page is a name, a relationship
    and a town and country, and a pointer to another archive is none of those
  - an EMPTY build is refused: a check that examined no person page has passed on nothing

Only the dead are compared by name; nothing here prints a person, living or not, only an address.

    python3 scripts/check_also_in.py [--dist DIR]    DIR defaults to site/$ARCHIVE_OUT, else site/dist
    python3 scripts/check_also_in.py --self-test     plants one fault per rule and requires each be caught
"""
import os, re, sys, json, glob, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ME = "defranceski"
KIT = os.path.join(ROOT, "site", "node_modules", "@daviddef", "archive-kit", "kit", "data")
ALSO = re.compile(r'data-also-in="(\d+)"')
LINE = re.compile(r'<p class="also-in"[^>]*>(.*?)</p>', re.S)
HREF = re.compile(r'href="([^"]+)"')
LIVING = 'name="robots" content="noindex"'


def read(f):
    return open(f, encoding="utf-8", errors="ignore").read()


def default_dist():
    o = os.environ.get("ARCHIVE_OUT")
    return os.path.join(ROOT, "site", o) if o else os.path.join(ROOT, "site", "dist")


def expected(pairs, ring, me=ME):
    """my page path -> [the hrefs the ring says it must point to], for CONFIRMED pairs only."""
    expect = {}
    for p in pairs:
        if p.get("status") != "confirmed":
            continue
        a, b = p["a"], p["b"]
        mine, other = (a, b) if a["archive"] == me else (b, a) if b["archive"] == me else (None, None)
        if not mine or other["archive"] not in ring:
            continue
        expect.setdefault(mine["path"], []).append(ring[other["archive"]]["url"].rstrip("/") + other["path"])
    return expect


def check(pairs, ring, dist, me=ME):
    """-> (fails, shown, expect, n_pages)"""
    pages = glob.glob(os.path.join(dist, "person", "*", "index.html"))
    if not pages:
        return [f"no built person pages under {dist}: nothing was examined"], 0, {}, 0
    expect = expected(pairs, ring, me)
    fails, shown = [], 0
    for path, hrefs in sorted(expect.items()):
        f = os.path.join(dist, path.strip("/"), "index.html")
        if not os.path.exists(f):
            fails.append(f"{path} has a confirmed pair and no built page")
            continue
        html = read(f)
        if LIVING in html:
            # THE TEMPLATE IS RIGHT AND THE LIST IS WRONG. A living page never gets a pointer, so a pair
            # that names one leaves the page correctly silent, and a bare «no pointer» would blame the
            # template for the kit's mistake. Say which it is.
            fails.append(f"{path} is a LIVING person's page and a confirmed pair names it; a pointer is never "
                         f"drawn for the living, so the kit's cross-archive list should not hold this pair")
            continue
        marks = ALSO.findall(html)
        if not marks:
            fails.append(f"{path} has a confirmed pair and the page carries no pointer; the template is not passing its props")
            continue
        shown += 1
        if len(marks) != 1:
            fails.append(f"{path} carries the pointer {len(marks)} times, not once")
        line = LINE.search(html)
        links = HREF.findall(line.group(1)) if line else []
        for h in hrefs:
            if h not in links:
                fails.append(f"{path} points somewhere other than {h}")
        if int(marks[0]) != len(hrefs):
            fails.append(f"{path} draws {marks[0]} pointer(s) and {len(hrefs)} pair(s) are confirmed")
    for f in pages:
        pid = f.split(os.sep)[-2]
        path = f"/person/{pid}/"
        html = read(f)
        if not ALSO.search(html):
            continue
        if path not in expect:
            fails.append(f"{path} carries a pointer and no confirmed pair names it")
        if LIVING in html:
            fails.append(f"{path} is a LIVING page and carries a pointer to another archive")
    return fails, shown, expect, len(pages)


def load_kit():
    pairs = json.load(open(os.path.join(KIT, "cross-archive.json"), encoding="utf-8"))["pairs"]
    ring = {a["key"]: a for a in json.load(open(os.path.join(KIT, "archives.json"), encoding="utf-8"))["archives"]}
    return pairs, ring


def main(dist):
    try:
        pairs, ring = load_kit()
    except Exception as e:
        print(f"  FAIL  alsoin     cannot read the kit's cross-archive data: {e}")
        return 1
    fails, shown, expect, n = check(pairs, ring, dist)
    if fails:
        print(f"  FAIL  alsoin     {len(fails)} finding(s) across {n} person page(s)")
        for m in fails[:6]:
            print(f"          {m}")
        return 1
    if not expect:
        print(f"  ok    alsoin     no confirmed pair involves this archive, so no page may carry a pointer, and none does ({n} checked)")
        return 0
    print(f"  ok    alsoin     {shown} of {len(expect)} confirmed pair(s) show their pointer on this archive's page, to the "
          f"address the ring gives; no other page and no living page carries one ({n} checked)")
    return 0


# ---------------------------------------------------------------------------------------------------------
# SELF-TEST. A check that has only ever passed is a claim, not a check. This builds a small INVENTED site in a
# temporary directory (made-up paths, no person) and requires: the clean fixture passes, and each planted fault
# is named. Exit 1 if the clean fixture fails or any fault goes unnoticed.
# ---------------------------------------------------------------------------------------------------------
RING = {"defranceski": {"key": "defranceski", "url": "https://archive.example/"},
        "other": {"key": "other", "url": "https://other.example/"}}
PAIRS = [{"status": "confirmed", "a": {"archive": "other", "path": "/people/p-one/"}, "b": {"archive": "defranceski", "path": "/person/t-one/"}},
         {"status": "confirmed", "a": {"archive": "other", "path": "/people/p-two/"}, "b": {"archive": "defranceski", "path": "/person/t-two/"}},
         {"status": "candidate", "a": {"archive": "other", "path": "/people/p-three/"}, "b": {"archive": "defranceski", "path": "/person/t-three/"}}]


def _page(dist, pid, pointer=None, living=False, count=1, times=1):
    d = os.path.join(dist, "person", pid)
    os.makedirs(d, exist_ok=True)
    head = '<meta name="robots" content="noindex">' if living else ""
    body = ""
    if pointer:
        body = (f'<p class="also-in" data-also-in="{count}">Also documented in <a href="{pointer}">The Other Archive</a>, '
                f'which may hold different evidence.</p>') * times
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(f"<html><head>{head}</head><body>{body}</body></html>")


def _fixture(tmp, **o):
    dist = os.path.join(tmp, "dist")
    shutil.rmtree(dist, ignore_errors=True)
    os.makedirs(dist)
    _page(dist, "t-one", "https://other.example/people/p-one/", living=o.get("one_living", False),
          count=o.get("count", 1), times=o.get("times", 1)) if not o.get("one_missing") else _page(dist, "t-one")
    if o.get("wrong"):
        _page(dist, "t-one", "https://other.example/people/p-WRONG/")
    _page(dist, "t-two", "https://other.example/people/p-two/")
    _page(dist, "t-three", "https://other.example/people/p-three/" if o.get("stray") else None)
    _page(dist, "t-plain")
    _page(dist, "t-living", "https://other.example/people/p-x/" if o.get("living_ptr") else None, living=True)
    if o.get("no_pair_page"):
        shutil.rmtree(os.path.join(dist, "person", "t-two"))
    if o.get("empty"):
        shutil.rmtree(dist); os.makedirs(dist)
    return dist


def self_test():
    tmp = tempfile.mkdtemp(prefix="alsoin-")
    cases = [("CLEAN fixture passes", {}, False),
             ("confirmed pair, page lacks the pointer", {"one_missing": True}, True),
             ("pointer to the wrong address", {"wrong": True}, True),
             ("pointer on a page no confirmed pair names (a candidate pair does not count)", {"stray": True}, True),
             ("pointer on a LIVING page that no pair names", {"living_ptr": True}, True),
             ("confirmed pair names a LIVING page (pointer drawn, or the list is wrong)", {"one_living": True}, True),
             ("pointer drawn twice on one page", {"times": 2}, True),
             ("pointer count disagrees with the pairs", {"count": 2}, True),
             ("confirmed pair with no built page", {"no_pair_page": True}, True),
             ("EMPTY build", {"empty": True}, True)]
    bad = 0
    try:
        for name, opt, want_fail in cases:
            fails, *_ = check(PAIRS, RING, _fixture(tmp, **opt))
            ok = bool(fails) == want_fail
            bad += (not ok)
            print(f"  {'ok  ' if ok else 'MISS'}  {name}" + (f"   -> {fails[0][:90]}" if fails else ""))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {'ok' if not bad else 'FAIL'}    alsoin-faults  {len(cases) - bad} of {len(cases)} cases behaved")
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--self-test" in a:
        sys.exit(self_test())
    d = a[a.index("--dist") + 1] if "--dist" in a else default_dist()
    sys.exit(main(d))
