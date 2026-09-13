#!/usr/bin/env python3
"""Standing audit. Every number the queue notes quote, computed from the data.

Written 13 Sept 2026 after three separate stale figures were found in
notes/when-we-return.md ("56 unplaced households" when there was 1; "55
suppressed charts" when there were 206) and after a hand audit found Vitipolis
and two mislabelled lanes on the lines chart. A number that is typed goes
stale the day after it is typed. Run this instead.

    python3 scripts/audit.py            # human report
    python3 scripts/audit.py --md       # markdown block for the queue note
"""
import json, re, sys, unicodedata, collections, pathlib

D = pathlib.Path(__file__).resolve().parent.parent / "site" / "src" / "data"
def load(n): return json.load(open(D / f"{n}.json", encoding="utf-8"))

def key(s):
    s = unicodedata.normalize("NFD", (s or "").split(",")[0].strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", s)   # punctuation out: "Rijeka — Fiume" must meet "Rijeka"

# one place, many names — the Vitipolis lesson
ALIAS = {"pola": "pula", "vitipolis": "rijeka", "fiume": "rijeka", "parenzo": "porec",
         "dignano": "vodnjan", "almissa": "omis", "spalato": "split", "promontore": "premantura",
         "sanvincenti": "svetvincenat", "rovigno": "rovinj", "pisino": "pazin",
         "capodistria": "koper", "umago": "umag", "verteneglio": "brtonigla",
         "sissano": "sisan", "lisignano": "liznjan", "fasana": "fazana", "veglia": "krk",
         "sebenico": "sibenik", "zara": "zadar", "albona": "labin", "montona": "motovun",
         "sovignacco": "sovinjak", "castellier": "kastelir", "buccari": "bakar",
         "segna": "senj", "volosko": "opatija", "torre": "tar"}
# not towns — a record whose place is a country tells you nothing about a lane
COUNTRY = {"croazia", "hrvatska", "austria", "osterreich", "italia", "italy", "regnumcroatiae",
           "kraljevinahrvatska", "croatiaslavonia", "ungheria", "magyarorszag", "madarska",
           "jugoslavija", "yugoslavia", "kustenland", "dalmazia", "istra", "istria", "france",
           "unitedstates", "usa", "germany", "deutschland", "brazil", "brasil", "argentina"}
def norm(s):
    k = key(s); return ALIAS.get(k, k)

def main(md=False):
    ros = load("roster")["rows"]; hh = load("households"); reg = load("register")["rows"]
    dos = load("dossiers")["people"]
    src = (pathlib.Path(__file__).resolve().parent.parent /
           "site/src/components/BranchRivers.astro").read_text(encoding="utf-8")
    chart = set()
    for x in re.findall(r'"([A-ZŠŽČĆĐ][^"\\]{2,60})"', src):
        for part in re.split(r"[—·,/]| - | and ", x):   # "Kaštelir and Tar" is two towns
            k = norm(part)
            if len(k) > 2: chart.add(k)

    R = {"roster": len(ros),
         "roster_noplace": sum(1 for r in ros if not (r.get("place") or "").strip()),
         "households": len(hh),
         "hh_noplace": sum(1 for h in hh if not (h.get("place") or "").strip()),
         "dossiers": len(dos),
         # three different states, and they were being reported as one
         "chart_real": sum(1 for v in dos.values() if v.get("ptree") and not v["ptree"].get("none")),
         "chart_gated": sum(1 for v in dos.values() if v.get("ptree") and v["ptree"].get("none")),
         "chart_none": sum(1 for v in dos.values() if not v.get("ptree")),
         "reg": len(reg)}
    R["reg_status"] = dict(collections.Counter(r.get("st") for r in reg))

    # accepted records sitting at a place no lane mentions
    off = collections.Counter(); spell = collections.defaultdict(collections.Counter)
    for r in reg:
        p = (r.get("p") or "").strip()
        if not p or p == "—": continue
        n = norm(p)
        if len(n) < 3 or n in chart or n in COUNTRY: continue
        if r.get("st") == "in": off[p.split(",")[0].strip()] += 1
        spell[n][r.get("sp") or "?"] += 1
    R["offchart"] = off.most_common(12)
    R["offchart_spellings"] = {p: spell[norm(p)].most_common(3) for p, _ in off.most_common(12)}

    # one town written several ways — alias candidates
    forms = collections.defaultdict(set)
    for r in reg:
        p = (r.get("p") or "").split(",")[0].strip()
        if p and p != "—" and norm(p) not in COUNTRY: forms[norm(p)].add(p)
    R["multiform"] = {k: sorted(v) for k, v in forms.items() if len(v) > 1}

    # married-out daughters sitting unworked in the index
    import unicodedata as _u
    def _nk(x):
        x = _u.normalize("NFD", (x or "").lower())
        x = "".join(c for c in x if _u.category(c) != "Mn")
        return re.sub(r"[^a-z ]", "", x).strip()
    DFN = re.compile(r"de\s*franceschi|defranceschi|defrancesch", re.I)
    # only unambiguously female given names: a Latin genitive ("Jacobi", "Victorii") is the FATHER,
    # and a child with "Surname not indexed" may be a De Franceschi the indexer never captured
    FEMP = re.compile(r"^(maria|marietta|michiela|michaela|domenica|dominica|lucia|veniera|veneranda|"
                      r"antonia|giovanna|catterina|cattarina|anna|elena|eufemia|pasqua|pascha|francisca|"
                      r"francesca|perina|mariana|luigia|orsola|magdalena|maddalena|bona|oliva|fosca|"
                      r"nicoletta|martina|marina|bonetta|giacoma|teresa|angela|apollonia|vincenza|"
                      r"cristina|elisabetta)\b", re.I)
    known = {_nk(a) for h in hh for a in (h.get("father"), h.get("mother")) if a}
    kids = collections.defaultdict(list)
    for r in reg:
        if r.get("st") != "lead": continue
        if DFN.search(r.get("n") or ""): continue
        df = [o for o in (r.get("o") or []) if DFN.search(o) and FEMP.match(o)]
        if df: kids[_nk(df[0])].append(r)
    R["lost_parents"] = [k for k in kids if k not in known]
    R["lost_children"] = sum(len(kids[k]) for k in R["lost_parents"])
    R["lost_top"] = sorted(((len(v), [o for o in (v[0].get("o") or []) if DFN.search(o)][0])
                            for k, v in kids.items() if k not in known), reverse=True)[:10]

    # a woman with no household is not the same as a woman with no location:
    # rows resolved to a parish by film number carry pl, and those are readable, not lost.
    lost_rows = [r for k in R["lost_parents"] for r in kids[k]]
    R["lost_rows"] = len(lost_rows)
    R["lost_placed"] = sum(1 for r in lost_rows if (r.get("pl") or "").strip())
    R["lost_where"] = collections.Counter(
        (r.get("pl") or "").strip() for r in lost_rows if (r.get("pl") or "").strip()).most_common(12)

    # parents in the wrong slot — the index harvest assigned couples by position, not sex
    FEMN = re.compile(r"^(maria|marietta|michiela|michaela|domenica|dominica|lucia|veniera|antonia|giovanna|"
                      r"catterina|caterina|cattarina|anna|elena|eufemia|pasqua|margarita|orsola|francesca|"
                      r"luigia|natalia|marina|bonetta|giacoma|martina|teresa|rosa|angela|magdalena|maddalena|"
                      r"nicoletta|damiana|fosca|apollonia|cristina|vincenza|oliva|olivia|elisabetta)\b", re.I)
    R["swapped"] = [h.get("father", "") for h in hh if FEMN.match((h.get("father") or "").strip())]

    # the no-place figure, broken down — a single number hides who is blocked on what
    R["noplace_src"] = dict(collections.Counter(
        r.get("src") for r in ros if not (r.get("place") or "").strip()).most_common())

    if md:
        s = R["reg_status"]
        print(f"**Computed by `scripts/audit.py`, not typed.** "
              f"{R['roster']} people · {R['households']} households · {R['reg']} indexed records "
              f"({s.get('in',0)} accepted, {s.get('cand',0)} candidate, {s.get('lead',0)} lead).\n")
        ns = R["noplace_src"]
        print(f"- **{R['roster_noplace']}** people with no place "
              + "(" + ", ".join(f"{v} {k}" for k, v in ns.items()) + ")"
              + f" · **{R['hh_noplace']}** households with no place")
        print(f"- pedigree charts, of {R['dossiers']} dossiers: **{R['chart_real']}** drawn · "
              f"**{R['chart_gated']}** suppressed by the date gate (candidates existed, all rejected) · "
              f"**{R['chart_none']}** with nothing to draw (no household link at all)")
        if R["offchart"]:
            print(f"- **{len(R['offchart'])}** places hold accepted records but appear on no lane: "
                  + ", ".join(f"{p} ({n})" for p, n in R["offchart"][:8]))
        if R["multiform"]:
            print(f"- **{len(R['multiform'])}** towns are written under more than one name in the register")
        print(f"- **{len(R['lost_parents'])}** De Franceschi *women* named as a mother in the unworked leads belong to **no household** — "
              f"**{R['lost_children']}** indexed children hang off them. These are the married-out daughters." + (
            "\n- Of those %d rows, **%d** now carry a parish resolved from the film they were photographed on: %s."
            % (R["lost_rows"], R["lost_placed"], " · ".join("%s %d" % (p, n) for p, n in R["lost_where"]))
            if R.get("lost_placed") else ""))
        if R["swapped"]:
            print(f"- **{len(R['swapped'])}** households have a woman in the father field — parents swapped")
        return

    print("ROSTER      %5d rows, %d with no place  %s" % (R["roster"], R["roster_noplace"], R["noplace_src"]))
    print("HOUSEHOLDS  %5d, %d with no place" % (R["households"], R["hh_noplace"]))
    print("DOSSIERS    %5d  charts: %d drawn, %d gate-suppressed, %d nothing to draw"
          % (R["dossiers"], R["chart_real"], R["chart_gated"], R["chart_none"]))
    print("REGISTER    %5d rows  %s" % (R["reg"], R["reg_status"]))
    print("\nACCEPTED RECORDS AT PLACES ON NO LANE")
    for p, n in R["offchart"]:
        sp = ", ".join(f"{a}×{b}" for a, b in R["offchart_spellings"][p])
        print("  %4d  %-22s %s" % (n, p, sp))
    print("\nMARRIED-OUT DAUGHTERS UNWORKED: %d women, %d children" % (len(R["lost_parents"]), R["lost_children"]))
    for n, nm in R["lost_top"]: print("  %3d  %s" % (n, nm))
    if R.get("lost_rows"):
        print("    of %d rows, %d carry a parish resolved from the film:" % (R["lost_rows"], R["lost_placed"]))
        if R["lost_where"]:
            print("      " + " · ".join("%s %d" % (p, n) for p, n in R["lost_where"]))
    print("\nHOUSEHOLDS WITH A WOMAN IN THE FATHER FIELD: %d" % len(R["swapped"]))
    for f in R["swapped"]: print("  ", f)
    print("\nTOWNS WRITTEN UNDER MORE THAN ONE NAME")
    for k, v in sorted(R["multiform"].items()):
        print("  %-14s %s" % (k, " · ".join(v)))

if __name__ == "__main__":
    main("--md" in sys.argv)
