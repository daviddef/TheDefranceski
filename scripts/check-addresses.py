#!/usr/bin/env python3
"""Every address this archive has ever published must still lead somewhere.

check-links cannot see this class by construction. It follows links that exist;
a rename updates every inbound reference, so the old address has no link left
pointing at it and the build is internally consistent while a published page
404s. Found 12 October 2026, from a peer archive (Lerena) that lost five this
way in one day, two of them dead for three weeks before anyone noticed.

This check asks the question from the other end. For each address family whose
slug is DERIVED from data, it walks the whole git history of that data and
collects every slug that ever built, then requires each one to be either still
built or named in the redirect table of site/astro.config.mjs.

A frozen ledger prevents REORDERING and is not enough: person ids are minted
once, so a set difference over them is zero by design. The families that bite
are the ones whose address comes from a name. See worklist 238.

    scripts/check-addresses.py                 # exit 1 if anything is stranded
    scripts/check-addresses.py --config PATH   # judge against another config
    scripts/check-addresses.py --rebuild       # walk ALL history and rewrite the ledger

The first full walk takes about ninety seconds, which is too slow for a gate
that runs on every commit. So data/published-addresses.json records every slug
seen up to a commit, and a normal run walks only the commits NEWER than that.
The ledger can only ever grow: a slug is added when first seen and never
removed, because "this address once existed" is the fact being kept. Run
--rebuild to refresh it after intentionally retiring pages with redirects.

`--config` exists so the check can be shown to FAIL on a known-broken tree:
hand it a config with a redirect removed and it must name that address. A test
run against the artefact you just fixed is not a test.

WITHDRAWN ON PURPOSE. A person held out under the living-people standard (a possible minor, 16 October 2026)
has no page and must not be derivable from anything published, so the answer to «stranded» for them is
NEVER a redirect, which would write their name into astro.config.mjs. Their slugs are taken out of the
ledger and `upto` is advanced to the commit that removed them, so an ordinary run does not walk back
to the commits where they existed. `--rebuild` walks all of history and WILL find them again: after a
rebuild, remove them from the ledger by hand and say why in the commit.

Limits, stated because they are real: it sees only addresses that reached a
COMMITTED data file or page. An address that was deployed between two commits
and never committed is invisible, and so is anything a hand-written page
published and later lost without its slug ever living in data.
"""
import json, re, subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CONFIG = "site/astro.config.mjs"
LEDGER = "data/published-addresses.json"
if "--config" in sys.argv:
    CONFIG = sys.argv[sys.argv.index("--config") + 1]


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True)


def revs(path):
    return git("log", "--format=%h", "--", path).stdout.split()


def load(rev, path):
    r = git("show", f"{rev}:{path}")
    if r.returncode or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def load_disk(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def roster_rows(o):
    return o.get("rows", []) if isinstance(o, dict) else (o or [])


def who_slugs(roster, dossiers):
    out = set()
    for r in roster_rows(roster) if roster else []:
        m = re.match(r"^/who/([^/]+)/$", (r.get("who") or "")) if isinstance(r, dict) else None
        if m:
            out.add(m.group(1))
    if dossiers and isinstance(dossiers.get("people"), dict):
        for p in dossiers["people"].values():
            if isinstance(p, dict) and p.get("slug"):
                out.add(p["slug"])
    return out


# family -> (prefix, [data files], extractor over the loaded files)
D = "site/src/data/"
FAMILIES = {
    "person": ("/person/", [D + "roster.json"],
               lambda f: {r["pid"] for r in roster_rows(f[0]) if isinstance(r, dict) and r.get("pid")}),
    "who": ("/who/", [D + "roster.json", D + "dossiers.json"],
            lambda f: who_slugs(f[0], f[1])),
    "people": ("/people/", [D + "people.json"],
               lambda f: {p["slug"] for p in f[0] if isinstance(p, dict) and p.get("slug")}),
    "places": ("/places/", [D + "places.json"],
               lambda f: set(f[0].keys()) if isinstance(f[0], dict)
               else {p.get("slug") for p in f[0] if isinstance(p, dict)} - {None}),
    "married-in": ("/married-in/", [D + "marriedin.json"],
                   lambda f: set((f[0].get("detail") or {}).keys())),
    "maternal": ("/maternal/", [D + "maternal.json"],
                 lambda f: set((f[0].get("lines") or {}).keys())),
    "map": ("/map/", [D + "researchmap.json"],
            lambda f: {s["key"] for s in f[0].get("sources", []) if "key" in s}),
}


def load_ledger():
    try:
        return json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        return {"upto": None, "families": {}}


def redirect_sources():
    t = open(CONFIG, encoding="utf-8").read()
    m = re.search(r"redirects:\s*\{(.*?)\n\s*\}", t, re.S)
    body = m.group(1) if m else ""
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return {re.sub(r"/+$", "", k) for k in re.findall(r"'([^']+)'\s*:", body)}


def main():
    redir = redirect_sources()
    rebuild = "--rebuild" in sys.argv
    led = {"upto": None, "families": {}} if rebuild else load_ledger()
    head = git("rev-parse", "HEAD").stdout.strip()
    upto = led.get("upto")
    stranded, summary = [], []
    out = {"upto": head, "families": {}}
    for fam, (prefix, paths, get) in FAMILIES.items():
        # revisions of every file feeding the family — only those newer than the
        # ledger when there is one, otherwise all of history
        allrevs = []
        for p in paths:
            span = [f"{upto}..HEAD"] if upto else []
            rr = git("log", "--format=%h", *span, "--", p).stdout.split()
            allrevs += [(rv, p) for rv in rr]
        # "now" is the WORKING TREE, not HEAD: the gate runs before the commit, and
        # a rename sitting uncommitted is exactly the thing to catch. Reading HEAD
        # made this check one commit behind, passing on every rename it was for.
        now_files = [load_disk(p) for p in paths]
        if any(f is None for f in now_files):
            summary.append(f"  ?     {fam:11} cannot read current data")
            continue
        now = get(now_files)
        ever = set(now) | set(led["families"].get(fam, []))
        cache = {}
        for rv, p in allrevs:
            files = []
            for q in paths:
                if (rv, q) not in cache:
                    cache[(rv, q)] = load(rv, q)
                files.append(cache[(rv, q)])
            if any(f is None for f in files):
                continue
            try:
                ever |= get(files)
            except Exception:
                continue
        out["families"][fam] = sorted(ever)
        gone = sorted(ever - now)
        bad = [g for g in gone if re.sub(r"/+$", "", f"{prefix}{g}") not in redir]
        stranded += [f"{prefix}{g}/" for g in bad]
        summary.append(f"  {'FAIL' if bad else 'ok  '}  {fam:11} ever {len(ever):5}  now {len(now):5}  "
                       f"retired {len(gone):2}  stranded {len(bad)}")

    if rebuild or "--write-ledger" in sys.argv:
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        summary.append(f"  ledger written: {LEDGER} up to {head[:7]}")

    print("check-addresses: every published address, against git history and the redirect table")
    print("\n".join(summary))
    if stranded:
        print("\n  STRANDED — published once, built nowhere now, and not in the redirect table:")
        for s in stranded:
            print("    ", s)
        print("  Add each to `redirects` in site/astro.config.mjs, pointing at the page that now")
        print("  holds the subject. A retired page with no redirect is a published address that 404s.")
        return 1
    return 0


sys.exit(main())
