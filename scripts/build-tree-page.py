#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Roots & Routes: the tree page for this archive, built from this archive's own committed data.

    python3 scripts/build-tree-page.py            # rebuild data/tree-page/ (tree.json, atlas-data.json, roots.html, roots.embed.html)
    python3 scripts/build-tree-page.py --check    # exit 1 if the page is older than the data it was built from

WHERE THE PEOPLE COME FROM. There is no committed GEDCOM (David's tree export carries living dates and stays outside the repo), so
the people are the archive's own: every row of roster.json, with the parent links the dossiers assert (`ptree.parents`, by pid),
the parents and children of the households, and the direct line. Nothing is read from the live tree. Identity is by record
(see roster.json's note): two rows may be one person, and the page says so by showing them as separate.

THE LIVING RULE IS NOT RE-IMPLEMENTED. `living_v2.row_is_living` decides, as everywhere else on this site, and the page adds the
tree-page skill's floor on top: nobody with no death recorded and a birth year in the last 110 years. Living and held-out people are
absent from the JSON, not hidden by the page. `scripts/check-living-data.py` and the checker in scripts/tree-page judge the output.

PLACES come from the archive's own atlas.json (coordinates from data/gazetteer.json), the country from the Record Atlas's own
`geo.country_of` (coordinates, never the importer's context), and a Record Atlas place only when it has the same name within 15 km.

Estimated years are flagged, never passed off: `bye` (born about) and `dye` (deceased, death year not recorded) show as "c. 1809" and
"1809–?". A person with no year and no relative with a year is not drawn and is counted in the report.

The scripts in scripts/tree-page/ are the family-tree-page skill's, vendored so CI and other sessions do not depend on ~/.claude.
"""
import argparse, collections, datetime, hashlib, io, json, math, os, re, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OUT = os.path.join(ROOT, "data", "tree-page")
TP = os.path.join(ROOT, "scripts", "tree-page")
EXT = os.path.join(TP, "painted-lines.ext.html")   # the five animated views (Night sky, Ink ledger, Household, Generations, Where they lived)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tree-page"))
NOW = datetime.date.today().year
HOST = "archive.defranceski.com"
ATLAS_CANDIDATES = [os.environ.get("RECORD_ATLAS", ""), os.path.expanduser("~/Projects/Family Projects/Record Atlas"),
                    os.path.join(os.path.dirname(ROOT), "Record Atlas")]

def jl(path): return json.load(io.open(path, encoding="utf-8"))
def fold(s): return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()).strip()
def head(s): return fold(str(s).split(",")[0])
def yr(v):
    try: return int(v)
    except (TypeError, ValueError): return None

INPUTS = ["roster.json", "dossiers.json", "households.json", "directline.json", "directline-pids.json", "atlas.json"]
def inputs_hash():
    h = hashlib.sha1()
    for n in INPUTS: h.update(io.open(os.path.join(DATA, n), "rb").read())
    h.update(io.open(os.path.join(TP, "tree-views.template.html"), "rb").read())
    h.update(io.open(os.path.join(TP, "painted-lines.ext.html"), "rb").read())
    h.update(io.open(os.path.join(ROOT, "scripts", "build-tree-page.py"), "rb").read())
    for n in ("place-crosswalk.json", "shelf-cats.json"): h.update(io.open(os.path.join(ROOT, "site", "src", "data", n), "rb").read())
    return h.hexdigest()[:16]

LINES = [("carnia", "Carnia"), ("south", "S. Istria"), ("venice", "Venice"), ("abroad", "Abroad"), ("trentino", "Trentino"), ("other", "Other lines"),
         ("unplaced", "Not yet placed")]
LINE_OF = {"carnia": 0, "gologorica": 0, "married-in": 0, "south": 1, "istria": 1, "liznjan": 1, "svetvincenat": 1, "venice": 2, "corsica": 2, "abroad": 3,
           "trentino": 4, "other": 5}   # everything else shares the last colour

SURN = re.compile(r"\b(?:(?:de|di|da|degli|dei|del)\s+)?(?:de)?fran[cz]esch\w*|\bdefranceski\w*|\bfranceschi\w*|\bfranchesch\w*", re.I)
FEMALE_A = {"luca", "nicola", "andrea", "battista", "toma", "jaka", "ilija", "sava", "costa", "mattia", "zaccaria"}
def split_name(name):
    n = re.sub(r"\s*\([^)]*\)", "", str(name)).strip(" ,")
    m = SURN.search(n)
    if m:
        sur = n[m.start():m.end()].strip(); given = (n[:m.start()] + " " + n[m.end():]).strip(" ,")
    else:
        parts = n.split()
        sur, given = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else ("", n)
    return (given or "?"), sur
def guess_sex(given):
    g = fold(given).split(" ")[0] if given else ""
    if not g: return "m"
    return "f" if g.endswith("a") and g not in FEMALE_A else "m"

def km(a, b):
    R = 6371; p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1]); dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def find_atlas():
    for c in ATLAS_CANDIDATES:
        if c and os.path.exists(os.path.join(c, "data", "countries.json")): return c
    sys.exit("Record Atlas checkout not found; set RECORD_ATLAS")

def plain(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", str(s or "")); s = re.sub(r"[*_`]+", "", s)
    return re.sub(r"\s+", " ", s).strip()

DETAIL = {}   # filled by build(): who is behind each count in the report

def build(args):
    import living_v2 as L2
    atlas = args.atlas or find_atlas()
    sys.path.insert(0, os.path.join(atlas, "scripts")); import geo
    cj = jl(os.path.join(atlas, "data", "countries.json"))["countries"]
    apl = jl(os.path.join(atlas, "data", "places.json"))["places"]
    roster = jl(os.path.join(DATA, "roster.json"))["rows"]
    dossiers = jl(os.path.join(DATA, "dossiers.json"))["persons"]
    households = jl(os.path.join(DATA, "households.json"))
    site_atlas = jl(os.path.join(DATA, "atlas.json"))["places"]
    rep = collections.Counter()
    detail = {"dropped": [], "inferred_place": [], "weak": []}   # who is behind each count, for the worklist rows (--worklist)

    # ---- the archive's own places: head name -> (name, lat, lon)
    sp = {}
    byhead = {}
    for p in site_atlas:
        names = [p["name"]] + list(p.get("also") or [])
        for nme in names: byhead.setdefault(head(nme), p)
        sp[p["name"]] = p
    placemap = {}
    def route_of(row):
        """The places a row names, in order. A route ("Senj → Johannesburg → Brisbane"), a `places` list, or "born X; died Y":
        the FIRST is where they were born, the LAST where they died. Read as one string, a route matched nothing and the person
        silently took a relative's place (Ivan, born Senj, appeared in Klenovica)."""
        pl = row.get("places")
        if isinstance(pl, list) and pl: parts = [str(x) for x in pl]
        else:
            s_ = str(row.get("place") or "")
            m = re.match(r"\s*born\s+(.+?)\s*;\s*died\s+(.+)", s_, re.I)
            parts = [m.group(1), m.group(2)] if m else [x.strip() for x in s_.split("→")]
        return [x for x in parts if x and x != "None"]
    def lookup(cand):
        return byhead.get(head(str(cand).split("/")[0]))
    def resolve_place(row):
        route = route_of(row)
        if route:
            p = lookup(route[0])
            if p: return p
        for cand in (row.get("parish"), row.get("placeSlug")):
            if cand and str(cand) != "None":
                p = lookup(cand)
                if p: return p
        return None
    def resolve_death_place(row):
        route = route_of(row)
        return lookup(route[-1]) if len(route) > 1 else None

    # ---- who is in
    def is_living(r):
        if L2.row_is_living(r): return True
        b = yr(r.get("b")); dead = bool(r.get("d") or r.get("deathRecorded") or r.get("deceased") or r.get("deathSource"))
        return (not dead) and b is not None and b > NOW - 110
    P, order = {}, []
    for r in roster:
        pid = r["pid"]
        if is_living(r): rep["living_withheld"] += 1; continue
        given, sur = split_name(r["name"]); b = yr(r.get("b")); d = yr(r.get("d"))
        P[pid] = dict(id=pid, given=given, sur=sur, sex=guess_sex(given), by=b, bye=False, dy=d, dye=False, row=r,
                      line=LINE_OF.get(r.get("line"), 6 if r.get("line") in ("unplaced", "unknown", None) else 5),
                      father=None, mother=None, spouse=[], kids=[])
        order.append(pid)

    # ---- sex from households
    for h in households:
        for c in h["children"]:
            if c.get("pid") in P and c.get("sex"): P[c["pid"]]["sex"] = "f" if str(c["sex"]).lower().startswith("f") else "m"

    # ---- parent links, in order of strength: the dossiers (read from a register), the households, the direct line
    parents = collections.defaultdict(list)   # child -> [parent pids in order seen]
    grade = {}   # (child, parent) -> strongest evidence behind the link: 2 read from a register, 1 the household tree, 0 an index entry only
    def add(child, par, g=0):
        if child in P and par in P and child != par:
            if par not in parents[child]: parents[child].append(par)
            grade[(child, par)] = max(g, grade.get((child, par), 0))
    VIA = {"read": 2, "tree": 1, "index": 0}
    for pid, v in dossiers.items():
        for q in v.get("ptree", {}).get("parents", []): add(pid, q.get("pid"), VIA.get(q.get("via"), 0))
    for h in households:
        pars = [x for x in (h.get("fatherPid"), h.get("motherPid")) if x]
        for c in h["children"]:
            for x in pars: add(c.get("pid"), x, VIA.get(h.get("src"), 0))
    try:   # the direct line: consecutive generations are parent and child by definition
        seq = [g.get("pid") for g in sorted(jl(os.path.join(DATA, "directline-pids.json"))["generations"], key=lambda g: g["gen"])]
        for a_, b_ in zip(seq, seq[1:]):
            if a_ and b_: add(b_, a_, 2)
    except Exception:
        rep["directline_skipped"] += 1
    # sex-aware father/mother; a parent who is also a descendant would make a loop, so test before linking
    def descends(x, of, seen=None):
        seen = seen if seen is not None else set()
        for k in P[of]["kids"]:
            if k == x: return True
            if k not in seen:
                seen.add(k)
                if descends(x, k, seen): return True
        return False
    for child in list(parents):
        ps = [x for x in parents[child] if not descends(x, child)][:2]
        if not ps: continue
        if len(ps) == 2:
            m_, f_ = [x for x in ps if P[x]["sex"] == "m"], [x for x in ps if P[x]["sex"] == "f"]
            fa, mo = (m_[0], f_[0]) if m_ and f_ else (ps[0], ps[1])
        else:
            fa, mo = (ps[0], None) if P[ps[0]]["sex"] == "m" else (None, ps[0])
        P[child]["father"], P[child]["mother"] = fa, mo
        for x in (fa, mo):
            if x: P[x]["kids"].append(child)
        if fa and mo and mo not in P[fa]["spouse"]: P[fa]["spouse"].append(mo); P[mo]["spouse"].append(fa)

    # ---- years: recorded, then estimated from relatives, then from a death year, always flagged
    def from_relatives(p):
        for k in ("father", "mother"):
            if p[k] and P[p[k]]["by"]: return P[p[k]]["by"] + (30 if k == "father" else 28)
        ks = [P[k]["by"] for k in p["kids"] if P[k]["by"]]
        if ks: return min(ks) - 28
        ss = [P[s]["by"] for s in p["spouse"] if P[s]["by"]]
        return ss[0] if ss else None
    recorded = {i for i, p in P.items() if p["by"] is not None}
    for _ in range(5):
        for p in P.values():
            if p["by"] is None:
                c = from_relatives(p)
                if c is not None: p["by"], p["bye"] = c, True
    for p in P.values():
        if p["by"] is None and p["dy"] is not None: p["by"], p["bye"] = p["dy"] - 60, True
    for _ in range(3):
        for p in P.values():
            if p["by"] is None:
                c = from_relatives(p)
                if c is not None: p["by"], p["bye"] = c, True
    for p in P.values():   # an estimate from relatives that contradicts a RECORDED death year gives way to the death year
        if p["bye"] and p["dy"] is not None and not (0 <= p["dy"] - p["by"] <= 100): p["by"] = p["dy"] - 60
    for p in P.values():
        if p["by"] is not None and p["dy"] is None: p["dy"], p["dye"] = min(p["by"] + 70, NOW - 1), True
    # a link between two RECORDED years that cannot be a parent and child is dropped, not displayed; estimates never cause a drop
    for p in list(P.values()):
        for k in ("father", "mother"):
            x = p[k]
            if x and p["id"] in recorded and x in recorded and not (12 <= p["by"] - P[x]["by"] <= 75):
                P[x]["kids"].remove(p["id"]); p[k] = None; rep["links_dropped_implausible_gap"] += 1
                detail["dropped"].append({"child": p["id"], "parent": x, "child_born": p["by"], "parent_born": P[x]["by"]})
    # two recorded years that cannot be one life (over 110 years, or death before birth) are a conflict in the archive's own rows:
    # the death year is not drawn, the person is listed in the report for the research to settle
    conflicts = []
    for p in P.values():
        if p["id"] in recorded and p["dy"] is not None and not p["dye"] and p["by"] is not None and not (0 <= p["dy"] - p["by"] <= 110):
            conflicts.append({"pid": p["id"], "born": p["by"], "died": p["dy"]}); p["dy"], p["dye"] = min(p["by"] + 70, NOW - 1), True
    rep["life_span_conflicts"] = conflicts
    detail["weak"] = [{"child": c, "parent": q, "grade": g} for (c, q), g in grade.items() if g == 0 and P[c]["father"] == q or g == 0 and P[c]["mother"] == q]
    for p in P.values():
        if p["dy"] is not None and p["by"] is not None and p["dy"] < p["by"]: p["dy"], p["dye"] = p["by"], True
        if p["dye"] and p["dy"] is not None:
            kd = [P[k]["by"] for k in p["kids"] if P[k]["by"]]
            if kd and p["dy"] < max(kd):
                p["dy"] = min(max(kd) + 1, p["by"] + 100, NOW - 1)
                if max(kd) - p["by"] > 100: conflicts.append({"pid": p["id"], "born": p["by"], "child_born": max(kd), "why": "a child is dated more than 100 years after the parent"})

    # nobody whose years are ESTIMATED and who would be living if the estimate were true: the page never draws a possible living person
    # (the living rule needs a recorded death for anyone born in the window; an estimated death is not a record)
    for pid in [i for i, p in P.items() if p["by"] is not None and p["by"] > NOW - 110 and (p["dye"] or p["bye"] and p["dy"] is None)]:
        for q in P.values():
            for k in ("father", "mother"):
                if q[k] == pid: q[k] = None
            q["kids"] = [x for x in q["kids"] if x != pid]; q["spouse"] = [x for x in q["spouse"] if x != pid]
        del P[pid]; rep["living_withheld_estimated_window"] += 1
    # ---- places
    for p in P.values():
        sp_ = resolve_place(p["row"]); p["site_place"] = sp_["name"] if sp_ else None; p["bpe"] = False
        dq = resolve_death_place(p["row"]); p["death_place"] = dq["name"] if dq and p["site_place"] else None
    for _ in range(3):
        for p in P.values():
            if p["site_place"]: continue
            for rid in [p["father"], p["mother"]] + p["spouse"] + p["kids"]:
                if rid and P[rid]["site_place"]: p["site_place"] = P[rid]["site_place"]; p["bpe"] = True; rep["placed_from_relative"] += 1; detail["inferred_place"].append({"pid": p["id"], "place": p["site_place"], "from": rid}); break
    # THE WHOLE ROUTE, NOT ITS ENDS. The roster holds a route in order ("Senj → Harare → Johannesburg → Brisbane"); until 2 November 2026 only the
    # first and the last place were drawn, so Ivan Defranceski (born Senj, Zimbabwe, South Africa, Brisbane) was drawn Senj → Brisbane as if
    # he had made one move. A roster row may carry `moves`: [{"place", "y", "est", "g"}], the year a person arrived at a stop (approximate when
    # est). The first stop is the birth place (born there, no arrival year) and a stop with no year has an undated arrival: the views draw
    # it dashed and say so. A route that does not start at the person's drawn birth place is a data question, listed in the report, not drawn.
    rep["routes_with_stops_between"] = 0; rep["route_start_mismatch"] = []
    for p in P.values():
        p["route"] = None
        if not (p["site_place"] and p.get("death_place")): continue
        stops = []
        for x in route_of(p["row"]):
            q = lookup(x)
            if q and (not stops or stops[-1] != q["name"]): stops.append(q["name"])
        if len(stops) < 3: continue
        if stops[0] != p["site_place"] or stops[-1] != p["death_place"]:
            rep["route_start_mismatch"].append(p["id"]); continue
        yrs_ = {}
        for m_ in (p["row"].get("moves") or []):
            q = lookup(m_.get("place") or "")
            if q and m_.get("y") is not None: yrs_[q["name"]] = (int(m_["y"]), 1 if m_.get("est", True) else 0)
        p["route"] = [[n, yrs_.get(n, (None, 0))[0], yrs_.get(n, (None, 0))[1]] for n in stops]
        rep["routes_with_stops_between"] += 1
    names_used = ({p["site_place"] for p in P.values() if p["site_place"]} | {p["death_place"] for p in P.values() if p.get("death_place")}
                  | {s_[0] for p in P.values() if p.get("route") for s_ in p["route"]})
    # Record Atlas ids by name within 15 km
    aidx = {}
    for x in apl:
        for nme in [x["name"]] + [n["n"].split(",")[0] for n in x.get("names", [])]: aidx.setdefault(fold(nme), []).append(x)
    for nme in sorted(names_used):
        s = sp[nme]; lat, lon = s["lat"], s["lon"]; iso = geo.country_of(lat, lon)
        aid = None
        for cand in aidx.get(fold(nme), []) + [c for a_ in (s.get("also") or []) for c in aidx.get(head(a_), [])]:
            if km((lat, lon), (cand["lat"], cand["lon"])) <= 15: aid = cand["id"]; break
        placemap[nme] = {"name": nme, "lat": lat, "lon": lon, "iso": iso, "country": (cj.get(iso) or {}).get("name", iso or ""), "atlas_id": aid}
    bad = [k for k, v in placemap.items() if not v["iso"]]
    if bad: sys.exit("no country for coordinates: %s" % bad[:8])

    for p in P.values():   # a route that ends elsewhere is a move; its year is not recorded, so it is estimated at 60% of the life and counted
        p["my"] = None; p["mye"] = False
        if p.get("route"): continue    # the route's own stops, dated or not, replace the single estimated year
        if p["site_place"] and p.get("death_place") and p["death_place"] != p["site_place"] and p["by"] is not None and p["dy"] is not None and p["dy"] - p["by"] > 24:
            p["my"] = p["by"] + int((p["dy"] - p["by"]) * .6); p["mye"] = True; rep["move_years_estimated"] += 1
    # ---- keep only people we can draw
    keep = {i: p for i, p in P.items() if p["by"] is not None and p["site_place"]}
    rep["not_drawn_no_year"] = sum(1 for p in P.values() if p["by"] is None)
    rep["not_drawn_no_place"] = sum(1 for p in P.values() if p["by"] is not None and not p["site_place"])
    undrawn = []   # a birth year at or after the cutoff is never printed beside a name here (the rule wants a death beside it)
    for pid, p in P.items():
        if pid in keep: continue
        r = p["row"]; who = r.get("who")
        undrawn.append({"id": pid, "name": plain(r["name"])[:80], "href": who if who and str(who).startswith("/") else None,
                        "b": (yr(r.get("b")) if yr(r.get("b")) is None or yr(r.get("b")) < L2.CUTOFF else None), "place": (plain(r.get("place")) if r.get("place") and str(r.get("place")) != "None" else None),
                        "why": "year" if p["by"] is None else "place"})
    undrawn.sort(key=lambda u: (u["why"], u["name"]))
    people = []
    for pid, p in keep.items():
        r = p["row"]; who = r.get("who")
        srcs = []
        for a_ in ([r.get("ark")] if r.get("ark") else []) + list(r.get("arks") or []):
            if a_ and not any(x["u"].endswith(str(a_)) for x in srcs): srcs.append({"t": "FamilySearch record " + str(a_), "u": "https://www.familysearch.org/ark:/61903/" + str(a_)})
        people.append({"id": pid, "sex": p["sex"], "given": p["given"], "sur": p["sur"], "line": p["line"], "by": p["by"], "bp": p["site_place"],
                       "dy": p["dy"], "dp": p["death_place"] or p["site_place"], "my": p["my"], "mye": 1 if p.get("mye") else 0, "route": p.get("route"), "bpe": p["bpe"], "occ": None,
                       "father": p["father"] if p["father"] in keep else None, "mother": p["mother"] if p["mother"] in keep else None,
                       "fg": grade.get((p["id"], p["father"])) if p["father"] in keep else None, "mg": grade.get((p["id"], p["mother"])) if p["mother"] in keep else None,
                       "spouse": [s for s in p["spouse"] if s in keep], "kids": [k for k in p["kids"] if k in keep],
                       "srcs": srcs[:4], "href": who if who and str(who).startswith("/") else None, "page": "/person/%s/" % pid,   # this exact person's page (every roster person id has one); href is the name index several people share
                       "bye": p["bye"], "dye": p["dye"], "note": plain(r.get("note"))[:320] or None})
    # symmetric relations after the filter
    ids = {x["id"] for x in people}
    for x in people:
        for k in ("father", "mother"):
            if x[k] and x[k] not in ids: x[k] = None
    kid_of = {x["id"]: x for x in people}
    for x in people:
        x["kids"] = [k for k in x["kids"] if k in ids and x["id"] in (kid_of[k]["father"], kid_of[k]["mother"])]
    # focus: the direct line's best-connected deceased member
    def n_desc(i, seen=None):
        seen = seen if seen is not None else set()
        for k in kid_of[i]["kids"]:
            if k not in seen: seen.add(k); n_desc(k, seen)
        return seen
    def n_anc(i, seen=None):
        seen = seen if seen is not None else set()
        for k in (kid_of[i]["father"], kid_of[i]["mother"]):
            if k and k not in seen: seen.add(k); n_anc(k, seen)
        return seen
    focus, best = None, -1
    for pid, p in keep.items():
        sc = min(len(n_desc(pid)), 40) + min(len(n_anc(pid)), 40) + (25 if p["row"].get("direct") else 0)
        if sc > best: best, focus = sc, pid
    meta = {"title": "Roots & Routes", "sub": "Every person this archive holds, by generation, place, era and relationship. Click anyone and every view follows. A dashed line is a link seen in an index entry only, not yet read from a register.",
            "living": "omit", "generated": datetime.date.today().isoformat(), "inputs": inputs_hash(), "source": "the archive's own roster, dossiers, households and direct line",
            "rowLabel": "Research line", "lineLabel": "Research line"}
    tree = {"meta": meta, "lines": [{"sur": n, "host": HOST} for _, n in LINES] + [{"sur": "Other", "host": HOST}], "focus": focus, "people": people, "undrawn": undrawn}
    tree["lines"] = tree["lines"][:8]
    os.makedirs(OUT, exist_ok=True)
    # the living rule, asked once more of the finished file: refuse to write it if anyone breaks it
    rows = {r["pid"]: r for r in roster}
    broken = [x["id"] for x in people if L2.row_is_living(rows[x["id"]]) or x["dye"] and x["by"] > NOW - 110 or x["by"] >= L2.CUTOFF and x["dye"]
              or any(u["b"] and u["b"] >= L2.CUTOFF for u in undrawn)]
    if broken: sys.exit("LIVING RULE: %d people in the output break it, e.g. %s. Nothing written." % (len(broken), broken[:3]))
    json.dump(tree, io.open(os.path.join(OUT, "tree.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(placemap, io.open(os.path.join(OUT, "place_map.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    deg = collections.Counter(("orphan" if not (x["father"] or x["mother"] or x["kids"] or x["spouse"]) else "linked") for x in people)
    rep = dict(rep); rep.update({"roster_rows": len(roster), "people_drawn": len(people), "places": len(placemap), "in_record_atlas": sum(1 for v in placemap.values() if v["atlas_id"]),
                "estimated_birth": sum(1 for x in people if x["bye"]), "estimated_death": sum(1 for x in people if x["dye"]),
                "linked": deg["linked"], "orphans": deg["orphan"], "parent_links": sum(1 for x in people if x["father"]) + sum(1 for x in people if x["mother"]),
                "focus": focus})
    json.dump(rep, io.open(os.path.join(OUT, "tree.report.json"), "w"), indent=1)
    detail["names"] = {i: {"name": plain(p["row"]["name"])[:80], "b": yr(p["row"].get("b")), "href": p["row"].get("who") if str(p["row"].get("who") or "").startswith("/") else None}
                       for i, p in P.items() if p["by"] is not None and p["by"] < L2.CUTOFF}   # nobody born at or after the living cutoff is named
    detail["drawn"] = sorted(keep)
    DETAIL.update(detail)
    print(json.dumps(dict(rep), indent=1))
    return atlas

def worklist_rows(rep):
    """The research the tree page turns up, as rows for site/src/data/worklist.json. Rows carry `gen` so a re-run replaces them in place."""
    D = DETAIL; N = D["names"]; drawn = set(D["drawn"])
    def nm(i):
        n = N.get(i)
        if not n: return "*a person born too recently to name here*"
        return ("[%s](%s)" % (n["name"], n["href"]) if n["href"] else n["name"])
    def table(head, rows, more=None, cap=25):
        out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows[:cap]]
        if len(rows) > cap: out.append("\n*…and %d more; the full list is rebuilt with `python3 scripts/build-tree-page.py --worklist`.*" % (len(rows) - cap))
        return "\n".join(out)
    today = datetime.date.today().isoformat()
    base = dict(state="next", owner="this archive", since=today, covers=[])
    rows = []
    conf = [c for c in rep["life_span_conflicts"]]
    def why(c):
        if "child_born" in c: return "a child is dated %d years later (%d)" % (c["child_born"] - c["born"], c["child_born"])
        return "recorded death %s is over 110 years after the birth, or before it" % c["died"]
    rows.append(dict(gen="roots-routes:conflicts", what="Roots & Routes: %d people whose recorded dates cannot be one life" % len(conf), **base,
        note="**The archive's own rows disagree with themselves.** Either two people are one row, or a year is a misreading, or a child belongs to a different parent. The tree page keeps the person and does not trust the impossible date. Open the person and the register behind each date.\n\n"
        + table(["person", "born", "the conflict"], [(nm(c["pid"]), c["born"], why(c)) for c in conf])))
    dr = [d for d in D["dropped"]]
    rows.append(dict(gen="roots-routes:dropped", what="Roots & Routes: %d parent links dropped because the two recorded years cannot be parent and child" % len(dr), **base,
        note="**A link was asserted by a dossier or a household, but the recorded birth years put parent and child less than 12 or more than 75 years apart, so the tree page does not draw it.** Either the link is wrong (two people with one name) or a year is. Each needs the page it came from.\n\n"
        + table(["child", "born", "asserted parent", "born"], [(nm(d["child"]), d["child_born"], nm(d["parent"]), d["parent_born"]) for d in dr])))
    wk = [w for w in D["weak"] if w["child"] in drawn and w["parent"] in drawn]
    line = set()
    try:
        line = {g.get("pid") for g in jl(os.path.join(DATA, "directline-pids.json"))["generations"]}
    except Exception: pass
    wl = sorted([w for w in wk if w["child"] in line or w["parent"] in line], key=lambda w: (N.get(w["child"], {}).get("b") or 9999))
    rows.append(dict(gen="roots-routes:weak", what="Roots & Routes: %d parent links rest on an index entry only; read the register behind them" % len(wk), **base,
        note="**These links are drawn as dashed lines on [Roots & Routes](/roots/).** Each was seen in an index or a household built from index entries, and no register page has been read to confirm the parents.\n\n"
        "**%d of them touch the direct line, and those are worth doing first:**\n\n" % len(wl)
        + table(["child", "born", "index-only parent", "born"], [(nm(w["child"]), N.get(w["child"], {}).get("b") or "?", nm(w["parent"]), N.get(w["parent"], {}).get("b") or "?") for w in wl])))
    ip = [x for x in D["inferred_place"] if x["pid"] in drawn]
    rows.append(dict(gen="roots-routes:inferred", what="Roots & Routes: %d people drawn at a place taken from a relative, not recorded" % len(ip), **base,
        note="**These people have a birth year and no place of their own, so the tree page puts them where their parent, spouse or child was (marked with an asterisk).** Each needs its own record.\n\n"
        + table(["person", "born", "drawn at", "taken from"], [(nm(x["pid"]), N.get(x["pid"], {}).get("b") or "?", x["place"], nm(x["from"])) for x in ip])))
    rows.append(dict(gen="roots-routes:undrawn", what="Roots & Routes: %d people are not drawn yet (%d with no year, %d with no place)" % (rep["not_drawn_no_year"] + rep["not_drawn_no_place"], rep["not_drawn_no_year"], rep["not_drawn_no_place"]), **base,
        note="**Anyone with no birth year (own or from a relative) or no place is left off the picture and listed in its *Not drawn yet* tab.** The fastest way to shrink the number is a person who links two people already drawn: a year or a place for them also places their relatives.\n\n"
        "The list is on [Roots & Routes](/roots/), tab *Not drawn yet*, with each person's page."))
    return rows

def write_worklist(rep):
    path = os.path.join(DATA, "worklist.json")
    w = jl(path); have = {r.get("gen"): r for r in w["rows"] if r.get("gen")}
    fresh = worklist_rows(rep); n = max(r["n"] for r in w["rows"])
    for r in fresh:
        old = have.get(r["gen"])
        if old: r["n"], r["since"], r["state"] = old["n"], old.get("since", r["since"]), old["state"]; w["rows"][w["rows"].index(old)] = r
        else: n += 1; r["n"] = n; w["rows"].insert(0, r)
    io.open(path, "w", encoding="utf-8").write(json.dumps(w, ensure_ascii=False, indent=2) + "\n")
    print("worklist: %d tree-page rows written (%s)" % (len(fresh), ", ".join(r["gen"] for r in fresh)))

def link_map(ad):
    """Join each Roots & Routes place to its marker on /map/ (site/src/data/place-crosswalk.json, scripts/build-place-crosswalk.py) and the shelf state the map shows.
    A place is linked only when the crosswalk matched it to ONE marker (status ok or offset); ATLAS.site carries the link base and the state labels."""
    X = {r["rr"]: r for r in jl(os.path.join(ROOT, "site", "src", "data", "place-crosswalk.json"))["places"]}
    S = jl(os.path.join(ROOT, "site", "src", "data", "shelf-cats.json"))["states"]
    d = jl(ad); n = 0
    for p in d["places"]:
        r = X.get(p["n"])
        p.pop("mp", None); p.pop("sh", None)
        if r and r.get("map") and r["status"] in ("ok", "offset"):
            p["mp"] = r["map"]; n += 1
            if r.get("shelf"): p["sh"] = r["shelf"]
    d["site"] = {"mapBase": "/map/?at=", "shelf": {k: [lab, col] for k, lab, col in S}}
    io.open(ad, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    print("link-map: %d of %d places carry a marker on /map/" % (n, len(d["places"])))

def write_roots_links(tree):
    """site/public/roots-links.json: the people Roots & Routes DRAWS (one id each). /map/ (site/src/components/AtlasRootsLinks.astro) offers 'in Roots & Routes'
    only for those: a person the page withholds (living, possibly living) or cannot place would be a link to nothing."""
    ids = sorted(p["id"] for p in jl(tree)["people"])
    out = {"note": "The people Roots & Routes draws, by person id. Made by scripts/build-tree-page.py; do not edit by hand.", "people": ids}
    io.open(os.path.join(ROOT, "site", "public", "roots-links.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("roots-links: %d people" % len(ids))

def write_gaps(tree, ad):
    """What is missing for each person and where to look (scripts/tree-page/gaps.py), written into tree.json as p.gaps for the person card's 'What's missing' list."""
    import gaps as G
    t = jl(tree); allg, _ = G.all_gaps(tree, ad); n = 0
    for p in t["people"]:
        g = [{"k": x["kind"], "t": x["text"], "l": [{"w": l["what"], "u": l["url"], "y": "%s–%s" % (l["from"], l["to"]), "b": l["by"], "p": l["place"]} for l in x["look"]]} for x in allg.get(p["id"], [])]
        if g: p["gaps"] = g; n += 1
        else: p.pop("gaps", None)
    io.open(tree, "w", encoding="utf-8").write(json.dumps(t, ensure_ascii=False, separators=(",", ":")))
    print("gaps: %d of %d people have a 'what's missing' list" % (n, len(t["people"])))

def write_gap_rows(tree, ad):
    """One worklist row per birthplace with five or more people who have an actionable gap (no parents, an index-only parent link), one row for the smaller places,
    and one each for estimated birth years and children with no spouse. Rows are tagged roots-routes:gap:* and replaced in place; rows for a place that no longer qualifies are removed."""
    import gaps as G
    t = jl(tree); allg, _ = G.all_gaps(tree, ad); P = {p["id"]: p for p in t["people"]}
    today = datetime.date.today().isoformat(); base = dict(state="next", owner="this archive", since=today, covers=[])
    def link(p): return "[%s](%s)" % ((p["given"] + " " + p["sur"]).strip(), p["page"]) if p.get("page") else (p["given"] + " " + p["sur"]).strip()
    def table(head, rows, cap=30):
        out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows[:cap]]
        if len(rows) > cap: out.append("\n*…and %d more, each listed in its *What is missing* box on [Roots & Routes](/roots/).*" % (len(rows) - cap))
        return "\n".join(out)
    def look(ids, want):
        seen = {}
        for i in ids:
            for x in allg[i]:
                if x["kind"] in want:
                    for l in x["look"]: seen.setdefault((l["what"], l["by"]), l)
        return "; ".join("%s (%s, %s–%s)" % (k[0].strip(), k[1], l["from"], l["to"]) for k, l in list(seen.items())[:4]) or "no collection is listed for this place yet — check Record Atlas"
    by_place = collections.defaultdict(list)
    for i, v in allg.items():
        if any(x["kind"] in ("parents", "parent_index") for x in v): by_place[P[i]["bp"]].append(i)
    rows = []; small = []
    for place, ids in sorted(by_place.items(), key=lambda kv: -len(kv[1])):
        ids.sort(key=lambda i: (P[i]["line"] != 0, P[i]["by"]))
        if len(ids) < 5: small += ids; continue
        kinds = lambda i: ", ".join("no parents" if x["kind"] == "parents" else "parent link from an index only" for x in allg[i] if x["kind"] in ("parents", "parent_index"))
        rows.append(dict(gen="roots-routes:gap:" + re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", place).encode("ascii", "ignore").decode().lower()).strip("-"),
            what="Roots & Routes: find the missing parents of %d people born at %s" % (len(ids), place), **base,
            note="**%d people born at %s have no parents recorded or only an index-entry link.** Direct-line people are listed first. Where to look: %s.\n\n" % (len(ids), place, look(ids, ("parents", "parent_index")))
            + table(["person", "born", "gap"], [(link(P[i]), P[i]["by"], kinds(i)) for i in ids])))
    if small:
        rows.append(dict(gen="roots-routes:gap:other-places", what="Roots & Routes: find the missing parents of %d people born at the %d smaller places" % (len(small), len({P[i]["bp"] for i in small})), **base,
            note="**These places each have fewer than five people with this gap.** Where to look: see each person's *What is missing* box on [Roots & Routes](/roots/).\n\n" + table(["person", "born at", "born"], [(link(P[i]), P[i]["bp"], P[i]["by"]) for i in small])))
    ey = sorted((i for i, v in allg.items() if any(x["kind"] == "birth_year" for x in v)), key=lambda i: P[i]["by"])
    rows.append(dict(gen="roots-routes:gap:birth-years", what="Roots & Routes: %d birth years are estimates, not recorded dates" % len(ey), **base,
        note="**Each of these people is drawn at an estimated birth year.** A baptism or birth entry replaces the estimate.\n\n" + table(["person", "estimated", "born at"], [(link(P[i]), P[i]["by"], P[i]["bp"]) for i in ey])))
    ns = sorted((i for i, v in allg.items() if any(x["kind"] == "spouse" for x in v)), key=lambda i: P[i]["by"])
    rows.append(dict(gen="roots-routes:gap:spouses", what="Roots & Routes: %d people have children recorded but no spouse" % len(ns), **base,
        note="**The marriage record would name the other parent and often both sets of grandparents.**\n\n" + table(["person", "born", "born at"], [(link(P[i]), P[i]["by"], P[i]["bp"]) for i in ns])))
    path = os.path.join(DATA, "worklist.json"); w = jl(path)
    have = {r.get("gen"): r for r in w["rows"] if r.get("gen")}; keep = {r["gen"] for r in rows}
    w["rows"] = [r for r in w["rows"] if not (str(r.get("gen", "")).startswith("roots-routes:gap:") and r["gen"] not in keep)]
    n = max(r["n"] for r in w["rows"])
    for r in rows:
        old = have.get(r["gen"])
        if old: r["n"], r["since"], r["state"] = old["n"], old.get("since", r["since"]), old["state"]; w["rows"][w["rows"].index(old)] = r
        else: n += 1; r["n"] = n; w["rows"].insert(0, r)
    io.open(path, "w", encoding="utf-8").write(json.dumps(w, ensure_ascii=False, indent=2) + "\n")
    print("worklist: %d gap rows written (%d places with five or more, %d people at smaller places)" % (len(rows), len(rows) - 3, len(small)))

def run(cmd):
    print("$", " ".join(os.path.relpath(c, ROOT) if os.path.isabs(c) and c.startswith(ROOT) else c for c in cmd))
    r = subprocess.run(cmd)
    if r.returncode: sys.exit(r.returncode)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--atlas"); ap.add_argument("--worklist", action="store_true", help="also write the research rows into site/src/data/worklist.json")
    a = ap.parse_args()
    if a.check:
        try: have = jl(os.path.join(OUT, "tree.json"))["meta"]["inputs"]
        except Exception: print("tree page: not built yet. python3 scripts/build-tree-page.py"); sys.exit(1)
        if have != inputs_hash(): print("tree page is STALE: the roster, dossiers, households, atlas or builder changed since it was built.\n  python3 scripts/build-tree-page.py"); sys.exit(1)
        print("tree page is current"); return
    atlas = build(a) or a.atlas
    if a.worklist: write_worklist(jl(os.path.join(OUT, "tree.report.json")))
    py = sys.executable; tree = os.path.join(OUT, "tree.json"); pm = os.path.join(OUT, "place_map.json"); ad = os.path.join(OUT, "atlas-data.json"); page = os.path.join(OUT, "roots.html")
    run([py, os.path.join(TP, "build_atlas_data.py"), "--atlas", atlas, "--tree", tree, "--place-map", pm, "--out", ad])
    link_map(ad)
    write_roots_links(tree)
    write_gaps(tree, ad)
    if a.worklist: write_gap_rows(tree, ad)
    run([py, os.path.join(TP, "build_page.py"), "--template", os.path.join(TP, "tree-views.template.html"), "--tree", tree, "--atlas-data", ad, "--out", page, "--ext", EXT])
    embed = os.path.join(OUT, "roots.embed.html")   # the same page as a fragment, rendered inside the site layout by site/src/pages/roots/index.astro
    run([py, os.path.join(TP, "build_page.py"), "--template", os.path.join(TP, "tree-views.template.html"), "--tree", tree, "--atlas-data", ad, "--out", embed, "--embed", "--ext", EXT])
    run([py, os.path.join(TP, "check_tree_page.py"), "--tree", tree, "--atlas-data", ad, "--page", page])
    run([py, os.path.join(TP, "check_tree_page.py"), "--tree", tree, "--atlas-data", ad, "--page", embed])

if __name__ == "__main__": main()
