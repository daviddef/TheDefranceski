#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The living people of this archive, as bare nodes, for the tree canvas — and for nothing else.

    python3 scripts/build-living-nodes.py            # write data/tree-page/living-nodes.json
    python3 scripts/build-living-nodes.py --check    # exit 1 if the committed file is not what the data builds

WHY THIS FILE EXISTS. `scripts/build-tree-page.py` refuses to put a living person into `tree.json`,
and it goes on refusing: `/roots/` is a public, indexed page whose tree data sits in the HTML, and the
living-people standard's `noindex` on a person page would mean nothing if the same name were searchable
there. But the tree canvas (a separate, noindex page built outside this repository) draws the family as
a graph, and with every living person absent the compiler and his own mother were missing from it.

WHAT IT MAY CARRY, and the reasoning. A living person's page already publishes their name, their
relationships and their town and country (living-people standard v2; this archive's CLAUDE.md). A node
carrying a NAME and RELATIONSHIP LINKS therefore discloses less than the page beside it. This file
carries that and stops: no year of any kind, no place of any kind, no occupation, no source, no
evidence grade, no photograph, no tree id. The canvas's own living filter keys off a birth year, so a
year here would make it silently drop the very people the file is for.

WHAT IT MUST NEVER BECOME. It is NOT written into `site/public`, it is NOT read by any built page, and
nothing in `site/` imports it. `scripts/check-living-data.py` fails the gate if any of that changes, if
a forbidden key appears, if a held-out or possibly-minor person is named, or if a person in this file is
also in `tree.json`. Keep `tree.json`'s `"living": "omit"` and its refuse-to-write gate exactly as they
are: this file is an addition beside that rail, never a loosening of it.

WHO IS LEFT OUT, and why each class is absent rather than blanked:
  * the four ids the ledger holds out (`data/living-ledger.json` → `held`), possible minors and the
    minor supplement — the standard does not publish them at all;
  * anyone whose status this archive cannot decide from its committed rows: a row with no birth year
    and no death recorded, or one whose years are an estimate (`bEst`). `living_v2.row_is_living`
    answers true or false and never reports doubt, so the doubt is applied here, by hand, in the open.
    If in doubt, leave them out.

WHERE THE LINKS COME FROM. The same committed sources the tree page uses — the dossiers' `ptree.parents`
and the households' parent/child rows, both keyed by pid — plus, for the compiler's own household, the
roster's `rel` field where it states a relationship that is a single edge («mother», «father», «wife»,
«husband», «son», «daughter»). A kinship label that is not one edge («first cousin», «uncle's wife») is
NOT turned into a graph: it is counted in the header and left to the person page's prose. No link is
invented, and nothing is read from the live MyHeritage tree, which stays outside this repository.
"""
import argparse, datetime, io, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(ROOT, "data", "tree-page", "living-nodes.json")
TREE = os.path.join(ROOT, "data", "tree-page", "tree.json")
LEDGER = os.path.join(ROOT, "data", "living-ledger.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_v2 as L2  # noqa: E402

RULE = ("living-people standard v2; name and relationship links only, no dates, no places. "
        "Not served, not indexed, not read by any built page.")
SECRECY = ("What this file buys is NON-INDEXABILITY, not secrecy. The names and the slugs in it are already "
           "committed in this public repository (the living ledger's own keys are name-slugs, and each person "
           "has a noindex page of their own). The point is that /roots/ is in the sitemap, carries no robots "
           "meta and embeds its tree data in the page, so a name that reaches it becomes searchable. Do not "
           "relax anything else on the belief that this file is hidden.")
LEFT_OUT = ("Absent rather than blanked: the ledger's held ids; possible minors and the minor supplement; "
            "anyone with no birth year and no recorded death; and anyone whose years are an estimate "
            "(bEst / bEstRange / bye / dye). living_v2.row_is_living answers true or false and never reports "
            "doubt, so the doubt is applied here, in the caller, and declared.")

# a `rel` label that is exactly one edge, seen from the row towards the compiler
EDGE = {"mother": "parent", "father": "parent", "wife": "spouse", "husband": "spouse",
        "spouse": "spouse", "son": "child", "daughter": "child"}


def jl(path):
    return json.load(io.open(path, encoding="utf-8"))


def guess_sex(given, row):
    """Only from the name's own ending and the row's own field; never from a relationship."""
    g = unicodedata.normalize("NFKD", str(given or "")).encode("ascii", "ignore").decode().strip().lower()
    first = re.split(r"[\s\-]+", g)[0] if g else ""
    if str(row.get("sex", "")).lower().startswith("f"):
        return "f"
    if str(row.get("sex", "")).lower().startswith("m"):
        return "m"
    if first.endswith(("a", "e")) and not first.endswith(("ea", "ia")) and first not in ("luka", "nikola", "andrea", "mattia", "nicola"):
        return "f"
    if first.endswith(("o", "n", "r", "s", "k", "l", "d", "t", "p", "v")):
        return "m"
    return "?"


def undecidable(r):
    """True when this archive cannot say from its own committed row whether the person is living."""
    dead = bool(r.get("d") or r.get("deathRecorded") or r.get("deceased") or r.get("deathSource"))
    if r.get("bEst") or r.get("bEstRange") or r.get("bye") or r.get("dye"):
        return True
    return (not dead) and not r.get("b") and not r.get("living")


def build():
    roster = jl(os.path.join(DATA, "roster.json"))["rows"]
    dossiers = jl(os.path.join(DATA, "dossiers.json")).get("persons", {})
    households = jl(os.path.join(DATA, "households.json"))
    ledger = jl(LEDGER) if os.path.exists(LEDGER) else {}
    held_uids = set(ledger.get("held") or [])
    uid_of = ledger.get("people") or {}
    held_pids = {pid for pid, uid in uid_of.items() if uid in held_uids}

    by_pid = {r["pid"]: r for r in roster if r.get("pid")}
    me = next((r["pid"] for r in roster if r.get("me")), None)

    living, skipped_undecidable, skipped_held = [], 0, 0
    for r in roster:
        pid = r.get("pid")
        if not pid:
            continue
        is_living = bool(r.get("living")) or L2.row_is_living(r)
        if not is_living:
            continue
        if pid in held_pids:
            skipped_held += 1
            continue
        if undecidable(r):
            skipped_undecidable += 1
            continue
        living.append(pid)
    live = set(living)

    # ---- edges from the committed structured data, pid to pid
    parents = {p: [] for p in living}
    children = {p: [] for p in living}
    spouses = {p: [] for p in living}

    def add_parent(child, par):
        if child == par or child not in by_pid or par not in by_pid:
            return
        if child in parents and par not in parents[child]:
            parents[child].append(par)
        if par in children and child not in children[par]:
            children[par].append(child)

    def add_spouse(a, b):
        if a == b or a not in by_pid or b not in by_pid:
            return
        for x, y in ((a, b), (b, a)):
            if x in spouses and y not in spouses[x]:
                spouses[x].append(y)

    for pid, v in dossiers.items():
        for q in ((v.get("ptree") or {}).get("parents") or []):
            if q.get("pid"):
                add_parent(pid, q["pid"])
    for h in households:
        pars = [x for x in (h.get("fatherPid"), h.get("motherPid")) if x]
        for c in (h.get("children") or []):
            if isinstance(c, dict) and c.get("pid"):
                for x in pars:
                    add_parent(c["pid"], x)
        if len(pars) == 2:
            add_spouse(pars[0], pars[1])

    # ---- the compiler's own household, from the roster's own `rel` field
    prose_only = 0
    if me:
        for r in roster:
            pid, rel = r.get("pid"), str(r.get("rel") or "").strip().lower()
            if not pid or pid not in live or not rel or pid == me:
                continue
            kind = EDGE.get(rel)
            if kind == "parent":
                add_parent(me, pid)
            elif kind == "child":
                add_parent(pid, me)
            elif kind == "spouse":
                add_spouse(me, pid)
            elif rel and rel != "this archive's compiler":
                prose_only += 1

    # ---- a link may point only at somebody in this file or already in tree.json
    in_tree = set()
    if os.path.exists(TREE):
        t = jl(TREE)
        for p in (t.get("people") or t.get("nodes") or []):
            if isinstance(p, dict) and p.get("id"):
                in_tree.add(p["id"])
    allowed = live | in_tree

    people = []
    for pid in living:
        r = by_pid[pid]
        people.append({
            "id": pid,
            "name": r.get("name"),
            "sex": guess_sex(str(r.get("name") or "").split()[0] if r.get("name") else "", r),
            "parents": [x for x in parents[pid] if x in allowed],
            "spouses": [x for x in spouses[pid] if x in allowed],
            "children": [x for x in children[pid] if x in allowed],
            "page": "/person/%s/" % pid,
        })
    people.sort(key=lambda p: p["id"])
    linked = sum(1 for p in people if p["parents"] or p["spouses"] or p["children"])
    return {
        "generated": datetime.date.today().isoformat(),
        "rule": RULE,
        "rule_version": "living-people standard v2, 16 October 2026 (scripts/living_v2.py; the kit's living_rule.py)",
        "counted_how": ("every roster row the rule holds as living on the date above, derived through "
                        "living_v2 from site/src/data/roster.json — never read off the living ledger, whose "
                        "pid→UID map counts rows matched to the tree, dead people among them."),
        "protection": SECRECY,
        "left_out": LEFT_OUT,
        "counts": {
            "people": len(people),
            "with_a_link": linked,
            "isolated": len(people) - linked,
            "left_out_held": skipped_held,
            "left_out_undecidable": skipped_undecidable,
            "relationship_stated_in_prose_only": prose_only,
        },
        "note": ("Relationship labels that are not a single edge — «first cousin», «uncle's wife» and the "
                 "like — are counted above and are NOT drawn as links: they live on the person's own page, "
                 "in words. Nothing here is read from the live tree."),
        "people": people,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    built = build()
    if a.check:
        if not os.path.exists(OUT):
            print("  FAIL  living-nodes  %s is missing; run scripts/build-living-nodes.py" % os.path.relpath(OUT, ROOT))
            return 1
        have = jl(OUT)
        if have.get("people") != built["people"]:
            print("  FAIL  living-nodes  the committed file is not what the roster builds; run scripts/build-living-nodes.py")
            return 1
        print("  ok    living-nodes  %d people, %d with a link; the file matches the roster"
              % (built["counts"]["people"], built["counts"]["with_a_link"]))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(built, indent=1, ensure_ascii=False) + "\n")
    c = built["counts"]
    print("living-nodes.json: %d people (%d with a link, %d isolated); left out %d held, %d undecidable; "
          "%d relationship(s) stated in prose only" % (c["people"], c["with_a_link"], c["isolated"],
                                                       c["left_out_held"], c["left_out_undecidable"],
                                                       c["relationship_stated_in_prose_only"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
