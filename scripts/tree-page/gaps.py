#!/usr/bin/env python3
"""What is missing for each person in the Roots & Routes tree, and where to look.

Reads data/tree-page/tree.json and atlas-data.json (the files the page is built from) and returns, per person, a list of gaps:
    {"kind": ..., "text": ..., "look": [{"place", "what", "url", "from", "to"}]}
Nothing here guesses: a gap is stated from a field that is empty, estimated, borrowed from a relative, or an index-only link,
and "look" lists only collections the Record Atlas holds for that place and a year inside the collection's range.
Living people are never in tree.json, so none can appear here.

    python3 scripts/tree-page/gaps.py [--person ID] [--summary]
"""
import argparse, json, collections, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOW = {"death_year", "atlas_place"}   # shown on the card, but alone they do not earn a worklist row
KINDS = {   # kind -> (order, short label); order puts the gaps that unlock most first
    "parents":      (1, "No parents recorded"),
    "parent_index": (2, "Parent link seen in an index only"),
    "birth_year":   (3, "Birth year estimated"),
    "birth_place":  (4, "Birth place borrowed from a relative"),
    "death_year":   (5, "Death year estimated"),
    "spouse":       (6, "Children but no spouse recorded"),
    "atlas_place":  (7, "Place not in Record Atlas yet"),
}


def load(tree=None, atlas=None):
    t = json.load(open(tree or ROOT / "data/tree-page/tree.json"))
    a = json.load(open(atlas or ROOT / "data/tree-page/atlas-data.json"))
    return t, a


def look_for(place, year, atlas_places, prov, want=None, window=15, regions={}):
    """Atlas collections held for `place` whose years reach `year` (±window), as plain dicts."""
    out = []
    for c in atlas_places.get(place, {}).get("cols", []):
        title, url, y0, y1, src = c[:5]
        if year is None or (y0 - window <= year <= y1 + window):
            if want and not any(w in title.lower() for w in want):
                continue
            out.append({"place": place, "what": title, "url": url, "from": y0, "to": y1, "by": prov.get(src, src)})
    if not out and year is not None:   # no collection listed for this exact place: the Atlas's region timeline says what exists then
        reg = atlas_places.get(place, {}).get("reg")
        for e in (regions.get(reg, {}).get("eras", []) if reg else []):
            if e[0] <= year < e[1] and e[5]:
                out += [{"place": regions[reg]["label"], "what": e[3] + (" — " + e[4] if e[4] and e[4].isupper() is False else ""), "url": None, "from": e[0], "to": e[1], "by": ", ".join(prov.get(c, c) for c in e[5])}]
    return out[:6]


def gaps_for(p, byid, atlas):
    places = {x["n"]: x for x in atlas["places"]}
    prov = atlas.get("prov", {})
    regions = atlas.get("regions", {})
    g = []
    by, bp = p["by"], p["bp"]
    unlinked = [r for r in ("father", "mother") if not p[r]]
    if unlinked:
        who = "parents" if len(unlinked) == 2 else unlinked[0]
        g.append({"kind": "parents", "text": "No %s recorded." % who,
                  "look": look_for(bp, by, places, prov, regions=regions, want=("birth", "baptism", "rođeni", "born", "census"))})
    weak = [r for r, k in (("father", "fg"), ("mother", "mg")) if p[r] and p.get(k) == 0]
    if weak:
        g.append({"kind": "parent_index", "text": "The link to the %s comes from an index entry, not a register page that has been read." % " and ".join(weak),
                  "look": look_for(bp, by, places, prov, regions=regions, want=("birth", "baptism", "rođeni", "born"))})
    if p.get("bye"):
        g.append({"kind": "birth_year", "text": "The birth year (%s) is an estimate, not a recorded date." % by, "look": look_for(bp, by, places, prov, regions=regions, want=("birth", "baptism", "rođeni", "born"))})
    if p.get("bpe"):
        g.append({"kind": "birth_place", "text": "The birth place (%s) is borrowed from a relative." % bp, "look": []})
    if p.get("dye") and p.get("dy") is not None:
        g.append({"kind": "death_year", "text": "The death year (%s) is an estimate." % p["dy"],
                  "look": look_for(p.get("dp") or bp, p["dy"], places, prov, regions=regions, want=("death", "burial", "umrli", "died"))})
    if p["kids"] and not p["spouse"]:
        g.append({"kind": "spouse", "text": "Has children recorded but no spouse.", "look": look_for(bp, by, places, prov, regions=regions, want=("marriage", "vjenčani", "matrimon"))})
    if bp and places.get(bp) and not places[bp].get("id"):
        g.append({"kind": "atlas_place", "text": "%s is not yet in Record Atlas, so no collections are listed for it." % bp, "look": []})
    g.sort(key=lambda x: KINDS[x["kind"]][0])
    return g


def all_gaps(tree=None, atlas=None):
    t, a = load(tree, atlas)
    byid = {p["id"]: p for p in t["people"]}
    return {p["id"]: gaps_for(p, byid, a) for p in t["people"]}, t


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--person"); ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    G, t = all_gaps()
    if a.person:
        print(json.dumps(G[a.person], indent=2, ensure_ascii=False)); sys.exit()
    c = collections.Counter(x["kind"] for v in G.values() for x in v)
    print(len(G), "people;", sum(1 for v in G.values() if v), "with at least one gap;", sum(1 for v in G.values() if any(x["look"] for x in v)), "with somewhere to look")
    for k, (o, lab) in sorted(KINDS.items(), key=lambda kv: kv[1][0]): print("%5d  %s" % (c[k], lab))
