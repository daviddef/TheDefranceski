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
         "sebenico": "sibenik", "zara": "zadar", "albona": "labin", "montona": "motovun"}
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
        for part in re.split(r"[—·,/]| - ", x):
            k = norm(part)
            if len(k) > 2: chart.add(k)

    R = {"roster": len(ros),
         "roster_noplace": sum(1 for r in ros if not (r.get("place") or "").strip()),
         "households": len(hh),
         "hh_noplace": sum(1 for h in hh if not (h.get("place") or "").strip()),
         "dossiers": len(dos),
         "no_chart": sum(1 for v in dos.values() if not v.get("ptree")),
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
        print(f"- **{R['no_chart']}** of {R['dossiers']} dossiers have no pedigree chart")
        if R["offchart"]:
            print(f"- **{len(R['offchart'])}** places hold accepted records but appear on no lane: "
                  + ", ".join(f"{p} ({n})" for p, n in R["offchart"][:8]))
        if R["multiform"]:
            print(f"- **{len(R['multiform'])}** towns are written under more than one name in the register")
        if R["swapped"]:
            print(f"- **{len(R['swapped'])}** households have a woman in the father field — parents swapped")
        return

    print("ROSTER      %5d rows, %d with no place  %s" % (R["roster"], R["roster_noplace"], R["noplace_src"]))
    print("HOUSEHOLDS  %5d, %d with no place" % (R["households"], R["hh_noplace"]))
    print("DOSSIERS    %5d, %d with no pedigree chart" % (R["dossiers"], R["no_chart"]))
    print("REGISTER    %5d rows  %s" % (R["reg"], R["reg_status"]))
    print("\nACCEPTED RECORDS AT PLACES ON NO LANE")
    for p, n in R["offchart"]:
        sp = ", ".join(f"{a}×{b}" for a, b in R["offchart_spellings"][p])
        print("  %4d  %-22s %s" % (n, p, sp))
    print("\nHOUSEHOLDS WITH A WOMAN IN THE FATHER FIELD: %d" % len(R["swapped"]))
    for f in R["swapped"]: print("  ", f)
    print("\nTOWNS WRITTEN UNDER MORE THAN ONE NAME")
    for k, v in sorted(R["multiform"].items()):
        print("  %-14s %s" % (k, " · ".join(v)))

if __name__ == "__main__":
    main("--md" in sys.argv)
