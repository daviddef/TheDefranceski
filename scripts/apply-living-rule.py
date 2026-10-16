#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the living-people standard (version 2) to the roster, at the source.

    python3 scripts/apply-living-rule.py            # report only; writes nothing
    python3 scripts/apply-living-rule.py --write    # rewrite roster.json and the ledger

THE RULE is the shared one (scripts/living_v2.py -> the kit's living_rule.py): living
is 80 or younger with no death recorded and no public source; a person with no birth
year is not living; a possible minor is held out.

WHERE THE FACTS COME FROM. A living person's birth year is never committed, so it
cannot be read back out of the roster. It is read from David's MyHeritage tree, the
GEDCOM export that lives outside the repository (`$ARCHIVE_GEDCOM`, or the newest
MyHeritage export in ~/Downloads). Without that file this script REFUSES to write:
it would otherwise decide everybody is undated, and undated is not living.

WHAT IT WRITES.
  * A person who is living becomes a scrubbed row: name, page address, relationship
    to David where the archive has one, and a full town and country. The birth year,
    death year, note, citations, parish, MyHeritage id and photographs are emptied.
  * A person who was flagged living and is not (over 80, a death recorded, a public
    source, or undated) loses the flag. If the tree gives a birth year and a death
    year they are restored, because they may be shown; the note loses the sentence
    that said they were living.
  * A person held out (UNDATED with a living parent: a possible minor) is removed from the roster.
    Their tree id is recorded, never their name, in data/living-ledger.json so a later import does
    not republish them. A child with a KNOWN birth year is not held out: they are a living row.
  * data/living-ledger.json maps each tree-matched row to the tree's opaque _UID.
    It holds no date.

This script prints COUNTS only. Run with --names to see who, on your own screen.
"""
import os, sys, re, io, json, copy, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_v2 as L2

lr = L2.lr
ROOT = L2.ROOT
ROSTER = os.path.join(ROOT, "site", "src", "data", "roster.json")

# A row the name alone cannot place (a woman the archive wrote under another spelling) is placed by hand:
# add `pid: _UID` to data/living-ledger.json. The ledger is read before any name is tried, so the hand
# decision is kept and no person's name or birth year is written into this file.

# Rows that are the SAME PERSON as another row (a household list read before the tree was), so
# they take that row's tree person: a person is not made older by being written down twice.
TWINS = {
    "michael-baviello-horsham": "michael-baviello",
    "antonia-baviello-jeffery-2": "antonia-baviello-jeffery",
    "carla-baviello-hendy-2": "carla-baviello-hendy",
}

LIVING_SENTENCES = [
    re.compile(r"^\s*\*\*Living — named, and placed, and never dated\.\*\*\s*"),
    re.compile(r"^\s*(The rule changed on 15 September 2026:[^.]*\.\s*No dates, no photograph\.\s*)"),
    re.compile(r"^\s*A living person appears here by name and by town and by nothing else: no date of birth, no photograph\.\s*"),
]

# fields a living row keeps; every other field is emptied
KEEP_LIVING = ("name", "pid", "who", "line", "place", "places", "rel", "me", "mine", "direct",
               "notable", "living", "src", "href", "b", "d", "note", "ark", "mh", "sameAs")


ROWS = {}


def match(row, tree, led, by_name):
    pid = row["pid"]
    uid = led["people"].get(pid)
    if uid and uid in tree.people:
        return uid, "ledger"
    if pid in TWINS and TWINS[pid] in ROWS:
        u2, _ = match(ROWS[TWINS[pid]], tree, led, by_name)
        if u2:
            return u2, "twin"
    k = L2.name_key(row["name"])
    c = by_name.get(k, [])
    if len(c) == 1:
        return c[0]["uid"], "name"
    if not c:
        toks = set(k.split())
        c = [p for p in tree.people.values() if toks and toks <= set(L2.fold(p["name"]).split())]
        if len(c) == 1:
            return c[0]["uid"], "tokens"
    return None, "ambiguous" if c else "none"


def reason_not_living(p, year):
    if p["dead"]:
        return "death recorded"
    if lr.public_source(p["cites"]):
        return "public source"
    if p["by"] is None:
        return "no birth year"
    return "over 80"


def scrub_living(r, p, year):
    """The only things a living row may hold."""
    if r.get("pid") in TWINS and not r.get("places") and ROWS.get(TWINS[r["pid"]], {}).get("places"):
        r = dict(r, places=ROWS[TWINS[r["pid"]]]["places"])      # the same person's own places
    out = {k: copy.deepcopy(r[k]) for k in KEEP_LIVING if k in r}
    out.update({"b": None, "d": None, "note": "", "ark": "", "mh": "", "living": True, "notable": False})
    # place: the curated list David gave (normalised), else the tree's birth place
    lines = []
    tt, tc = L2.town_country(p["place"]) if p is not None else ("", "")
    for x in (r.get("places") or []):
        t, c = L2.town_country(x)
        pl = L2.place_line(x)
        if t and not c and tt and L2.fold(t) == L2.fold(tt):
            pl = ", ".join(z for z in (tt, tc) if z)      # the tree names the country for this town
        if pl and pl not in lines:
            lines.append(pl)
    if not lines and p is not None:
        pl = L2.place_line(p["place"])
        if pl and "," in pl:            # a tree place that parses to a town and a country
            lines.append(pl)
    if not lines and r.get("place") and "\u2192" not in r["place"]:
        pl = L2.place_line(r["place"])  # the place the archive already held: 'Brooklyn, New York'
        if pl:
            lines.append(pl)
    if not lines and p is not None:
        pl = L2.place_line(p["place"])
        if pl:
            lines.append(pl)
    out["places"] = lines
    out["place"] = " → ".join(lines)
    if not lines:
        out.pop("places")
    # relationship to David, kept; spouse reduced to the name
    return out


def restore_ordinary(r, p, year):
    """A row that was flagged living and is not: the flag goes, the dates the tree gives come back."""
    out = {k: v for k, v in r.items() if k not in ("living", "bHeldNotPrinted")}
    if p is not None:
        if p["by"] and not out.get("b"):
            out["b"] = p["by"]
        if p["dead"]:
            if p["dy"] and not out.get("d"):
                out["d"] = p["dy"]
            elif not p["dy"]:
                out["deceased"] = True
    if p is not None and lr.public_source(p["cites"]) and not L2.row_citations(out):
        # why this person is not living has to be readable from the committed row, not only from the tree
        out["cited"] = "FamilySearch" if any("familysearch" in c.lower() for c in p["cites"]) else "MyHeritage record collection"
    note = out.get("note") or ""
    for pat in LIVING_SENTENCES:
        note = pat.sub("", note, count=1)
    out["note"] = note.strip()
    # the places David gave are where the person is, and the page reads `place`
    if out.get("places") and not out.get("place"):
        out["place"] = " → ".join(filter(None, (L2.place_line(x) for x in out["places"])))
    return out


def redeclare(old_rows, new_rows, held_pids):
    """The frozen ids (data/decisions.json) and the published-address ledger follow the roster.
    Changing a declared id's name|b|d, or removing one, is a deliberate act: this is it, made
    in the same commit as the roster change that required it."""
    dec_p = os.path.join(ROOT, "data", "decisions.json")
    dec = json.load(io.open(dec_p, encoding="utf-8"))
    pids = dec["decisions"]["pids"]
    new = {r["pid"]: "%s|%s|%s" % (r.get("name", ""), r.get("b") or "", r.get("d") or "")
           for r in new_rows if r.get("pid")}
    n_changed = sum(1 for k, v in new.items() if k in pids and pids[k] != v)
    n_added = sum(1 for k in new if k not in pids)
    for k, v in new.items():            # a released person's frozen id is declared again (adding is free)
        pids.setdefault(k, v)
    for k in held_pids:
        pids.pop(k, None)
    pids.update({k: v for k, v in new.items() if k in pids})
    with io.open(dec_p, "w", encoding="utf-8") as f:
        json.dump(dec, f, ensure_ascii=False, indent=1, sort_keys=True)
    # addresses: a held-out person must not be derivable from the ledger either
    led_p = os.path.join(ROOT, "data", "published-addresses.json")
    pa = json.load(io.open(led_p, encoding="utf-8"))
    whos_left = {(r.get("who") or "").strip("/").split("/")[-1] for r in new_rows if r.get("who")}
    held_who = {(r.get("who") or "").strip("/").split("/")[-1] for r in old_rows
                if r.get("pid") in set(held_pids) and r.get("who")}
    for slug in held_who - whos_left:
        if slug in pa["families"].get("who", []):
            pa["families"]["who"].remove(slug)
    for k in held_pids:
        if k in pa["families"].get("person", []):
            pa["families"]["person"].remove(k)
    with io.open(led_p, "w", encoding="utf-8") as f:
        json.dump(pa, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("re-declared: %d id(s) changed, %d added, %d removed (decisions.json, published-addresses.json)"
          % (n_changed, n_added, len(held_pids)))


def prune_dossiers(old_rows, new_rows, held_pids):
    """dossiers.json is additive by design (a page that existed keeps existing), so a person who
    is no longer published has to be taken out of it by hand: the name page and the person tree."""
    import unicodedata
    def slugify(s):
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower().replace("\u0111", "d")
        return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    p = os.path.join(ROOT, "site", "src", "data", "dossiers.json")
    raw = io.open(p, encoding="utf-8").read()
    d = json.loads(raw)
    keep = {slugify(r["name"]) for r in new_rows}
    gone = {slugify(r["name"]) for r in old_rows if r.get("pid") in set(held_pids)} - keep
    for s_ in gone:
        d["people"].pop(s_, None)
    for pid in held_pids:
        d["persons"].pop(pid, None)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("pruned dossiers: %d name page(s), %d person tree(s)" % (len(gone), len(held_pids)))


def prune_maps(old_rows, new_rows, held_pids):
    """atlas.json and map-data.json are assembled by builders that do not reproduce byte for byte, so
    they are edited, not rebuilt: a held-out person is taken off every pin that lists them."""
    keep = {(r.get("who") or "") for r in new_rows}
    held_who = {(r.get("who") or "") for r in old_rows if r.get("pid") in set(held_pids)} - keep
    held_who.discard("")
    n_off = 0
    for rel, indent in (("site/src/data/atlas.json", 1), ("site/public/map-data.json", None)):
        pth = os.path.join(ROOT, rel)
        d = json.loads(io.open(pth, encoding="utf-8").read())
        for pl in d.get("places", []):
            ppl = pl.get("people")
            if not isinstance(ppl, list):
                continue
            kept = [x for x in ppl if x.get("w") not in held_who]
            if len(kept) != len(ppl):
                n_off += len(ppl) - len(kept)
                pl["people"] = kept
                if "n" in pl and pl["n"] == len(ppl):
                    pl["n"] = len(kept)
                if isinstance(pl.get("ns"), dict) and pl["ns"].get("people") == len(ppl):
                    pl["ns"]["people"] = len(kept)
        if "stats" in d and isinstance(d["stats"].get("people"), int) and rel.endswith("atlas.json"):
            pass
        with io.open(pth, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=indent)
    print("maps: %d pin listing(s) removed" % n_off)


def patch_reconcile(new_rows):
    """/live-tree/ lists the people the tree gave the archive. Its living flag was the old rule's; it
    follows the roster now, so a person the roster no longer calls living shows their years, and a
    living person shows a full town and country and no year."""
    pth = os.path.join(ROOT, "site", "src", "data", "reconcile.json")
    raw = io.open(pth, encoding="utf-8").read()
    d = json.loads(raw)
    by = collections.defaultdict(list)
    for r in new_rows:
        by[L2.name_key(r["name"])].append(r)
    n_live = n_dead = 0
    for e in d["new"]:
        rs = by.get(L2.name_key(e["n"]), [])
        if not rs:
            continue
        r = rs[0]
        if all(x.get("living") for x in rs):
            e["living"], e["y"] = True, ""
            e["p"] = r.get("place") or e.get("p", "")
            n_live += 1
        else:
            e["living"] = False
            yrs = "\u2013".join([str(r["b"]) if r.get("b") else "", str(r["d"]) if r.get("d") else ""]).strip("\u2013")
            if yrs and not e.get("y"):
                e["y"] = yrs
            n_dead += 1
    with io.open(pth, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("reconcile: %d living entries, %d not" % (n_live, n_dead))


def main():
    write = "--write" in sys.argv
    names = "--names" in sys.argv
    gpath = L2.gedcom_path(sys.argv[sys.argv.index("--gedcom") + 1] if "--gedcom" in sys.argv else None)
    if not gpath:
        sys.exit("apply-living-rule: no MyHeritage GEDCOM found (set ARCHIVE_GEDCOM). Without the tree "
                 "nobody has a birth year and the rule would call everybody not living. Refusing.")
    year = L2.THIS_YEAR
    tree = L2.load_tree(gpath)
    if len(tree.people) < 1000:
        sys.exit("apply-living-rule: the tree has %d people. Refusing to decide anything from that." % len(tree.people))
    led = L2.load_ledger()
    # held out is now only an UNDATED person with a living parent (kit 6cefc79; a child with a known
    # birth year follows the standard). A tree id the rule no longer holds out is released.
    led["held"] = [u for u in led.get("held", []) if u in tree.people and tree.verdict(u, year)[1]]
    d = json.load(io.open(ROSTER, encoding="utf-8"))
    rows = d["rows"]
    ROWS.update({r["pid"]: r for r in rows if r.get("pid")})
    by_name = collections.defaultdict(list)
    for p in tree.people.values():
        by_name[L2.name_key(p["name"])].append(p)

    C = collections.Counter()
    new_rows, held_pids, changed = [], [], []
    for r in rows:
        pid = r.get("pid")
        was = bool(r.get("living"))
        uid, how = (None, "n/a")
        if was or (pid in led["people"]) or (pid in TWINS):
            uid, how = match(r, tree, led, by_name)
        p = tree.people.get(uid) if uid else None
        if was and p is None:
            C["flagged living, no tree match (%s)" % how] += 1
        # --- the verdict ---
        if p is not None:
            living, minor = tree.verdict(uid, year)
        else:
            living = L2.row_is_living(r, year) and not was      # committed data only
            minor = False
        if was and p is None:
            living = False          # no birth year the archive can show: not living by the rule
        if minor:
            held_pids.append(pid)
            if uid and uid not in led["held"]:
                led["held"].append(uid)
            C["held out (undated, living parent)"] += 1
            continue
        if living:
            nr = scrub_living(r, p, year)
            if uid:
                led["people"][pid] = uid
            C["living (stays or becomes)"] += 1
            if not was:
                C["  of which: was shown as not living"] += 1
            new_rows.append(nr)
            continue
        if was:
            why = reason_not_living(p, year) if p is not None else "no tree match"
            C["living -> not living: " + why] += 1
            nr = restore_ordinary(r, p, year)
            if uid:
                led["people"][pid] = uid
            new_rows.append(nr)
            changed.append((pid, why))
            continue
        if p is not None and L2.row_is_living(r, year) and lr.public_source(p["cites"]):
            r = dict(r, cited="FamilySearch" if any("familysearch" in c.lower() for c in p["cites"]) else "MyHeritage record collection")
            C["not living: public source now recorded on the row"] += 1
        new_rows.append(r)

    # places, for the report
    kinds = collections.Counter()
    for r in new_rows:
        if r.get("living"):
            pl = r.get("places") or []
            if not pl:
                kinds["no place"] += 1
            else:
                t, c = L2.town_country(pl[0])
                kinds["town and country" if t and c else ("country only" if c else "town only")] += 1

    print("tree: %d people, export %s" % (len(tree.people), os.path.basename(gpath)))
    for k, v in sorted(C.items()):
        print("  %-52s %d" % (k, v))
    for k, v in sorted(kinds.items()):
        print("  living place: %-38s %d" % (k, v))
    print("  roster rows: %d -> %d" % (len(rows), len(new_rows)))
    if names:
        for pid, why in changed:
            print("   not living (%s): %s" % (why, pid))
        for pid in held_pids:
            print("   HELD:", pid)
    if not write:
        print("(report only; --write to rewrite)")
        return
    d["rows"] = new_rows
    with io.open(ROSTER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    led["note"] = ("pid -> the tree's opaque _UID for every roster row matched to David's MyHeritage tree "
                   "while applying the living-people standard (v2). `held` lists tree ids, never names, of "
                   "people held out as possible minors. No date is recorded here.")
    led["rule"] = "living-people standard v2, 16 October 2026; shared definition kit/tools/living_rule.py"
    led["year"] = year
    L2.save_ledger(led)
    print("written: roster.json, data/living-ledger.json")
    redeclare(rows, new_rows, held_pids)
    prune_dossiers(rows, new_rows, held_pids)
    prune_maps(rows, new_rows, held_pids)
    patch_reconcile(new_rows)
    if "--held-out" in sys.argv:        # a scratch file OUTSIDE the repository, for the purge step
        with io.open(sys.argv[sys.argv.index("--held-out") + 1], "w") as f:
            f.write("\n".join(held_pids))


if __name__ == "__main__":
    main()
