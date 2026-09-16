#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distil the GeoNames dumps down to the places this archive actually names.

Three builders needed coordinates and each found them somewhere different:
`build-atlas.py` read **`/tmp/harvest-geo.json`** — a hundred and seven places,
outside the repository, on a path the operating system is entitled to empty at
any moment; `build-graves-map.py` read `cities500.txt` from whatever directory
`--gaz` pointed at; `build-research-map.py` read eight country dumps from the
same place. The dumps are seventy-seven megabytes and do not belong in a git
repository. `/tmp` does not belong anywhere near a build.

So the dumps are read once, here, and everything the archive can actually name
is written to **`data/gazetteer.json`** — small enough to commit, complete
enough that no builder needs the dumps to run, and regenerable from them when
new place names appear.

    python3 scripts/build-gazetteer.py --gaz data/gaz

Run it after adding a place the archive has never named before. Without
--gaz it reports what is missing and changes nothing.
"""
import json, io, os, re, sys, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
OUT  = os.path.join(ROOT, "data", "gazetteer.json")

def strip(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")
def norm(s):   return re.sub(r"[^a-z0-9]+", " ", strip(s).lower()).strip()
def head(s):   return norm(str(s).split(",")[0])

def load(n):
    p = os.path.join(DATA, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None

# A place string names its own region, and throwing that away is how Prato
# Carnico ended up in Tuscany. «Memphis, Shelby, Tennessee, United States» and
# «Isabela, Puerto Rico, United States» are unambiguous the moment the tail is
# read: GeoNames files a US state or territory in the admin1 column under
# exactly these codes.
US_ADMIN = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA","colorado":"CO",
    "connecticut":"CT","delaware":"DE","district of columbia":"DC","florida":"FL","georgia":"GA",
    "hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA","kansas":"KS","kentucky":"KY",
    "louisiana":"LA","maine":"ME","maryland":"MD","massachusetts":"MA","michigan":"MI","minnesota":"MN",
    "mississippi":"MS","missouri":"MO","montana":"MT","nebraska":"NE","nevada":"NV","new hampshire":"NH",
    "new jersey":"NJ","new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND",
    "ohio":"OH","oklahoma":"OK","oregon":"OR","pennsylvania":"PA","rhode island":"RI",
    "south carolina":"SC","south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT",
    "virginia":"VA","washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY",
}
# Puerto Rico is its own country code in GeoNames, not a US admin1.
COUNTRY = {
    "united states":"US","usa":"US","puerto rico":"PR","australia":"AU","canada":"CA","england":"GB",
    "wales":"GB","scotland":"GB","ireland":"IE","turkey":"TR","argentina":"AR","panama":"PA",
    "italy":"IT","italia":"IT","croatia":"HR","hrvatska":"HR","slovenia":"SI","austria":"AT",
    "hungary":"HU","serbia":"RS","brazil":"BR","brasil":"BR","uruguay":"UY","venezuela":"VE",
    "south africa":"ZA","new zealand":"NZ","france":"FR","germany":"DE",
}

def hint(full):
    """(country code, admin1 code) implied by a place string's own tail."""
    parts = [norm(x) for x in str(full or "").split(",")]
    # Puerto Rico is a country code of its own in GeoNames while the string
    # calls it part of the United States, and the plain reading — last part
    # wins — put San Lorenzo, Puerto Rico in California. The territory is
    # tested first for that reason.
    if "puerto rico" in parts:
        return "PR", None
    cc = adm = None
    for x in reversed(parts):
        if not cc and x in COUNTRY:
            cc = COUNTRY[x]
            continue
        if cc == "US" and not adm and x in US_ADMIN:
            adm = US_ADMIN[x]
    return cc, adm


# ---- every place string the archive names ------------------------------
def wanted():
    w = collections.Counter()
    for r in (load("roster.json") or {}).get("rows", []):
        for k in ("place", "parish"):
            if r.get(k): w[head(r[k])] += 1
        for x in (r.get("places") or []): w[head(x)] += 1
    for r in (load("graves.json") or {}).get("rows", []):
        if r.get("place"): w[head(r["place"])] += 1
        # a burial ground is often named only by its cemetery
        if r.get("cem"):   w[norm(r["cem"])] += 1
    for p in (load("atlas-seed.json") or {}).get("places", []):
        w[head(p["name"])] += 1
    for p in (load("places.json") or []):
        if isinstance(p, dict) and p.get("name"): w[head(p["name"])] += 1
    for p in (load("researchmap.json") or {}).get("places", []):
        w[head(p["name"])] += 1
        for a in (p.get("alt") or []) + (p.get("older") or []): w[head(a)] += 1
    # A record's place can be a church, a census enumeration district or a
    # ward — «St Anthony of Padua, Manhattan, New York», «19-Wd Memphis,
    # Shelby, Tennessee». None of those is in a gazetteer and all of them say
    # plainly what town they are in, one comma along. Every part is offered,
    # and the map takes the first that resolves.
    for p in (load("findmypast-map.json") or {}).get("places", []):
        h = hint(p["loc"])
        for part in str(p["loc"]).split(","):
            k = norm(re.sub(r"^\s*\d+[-\s]?\w{0,3}\s+", "", part))
            # Never fall back onto the country or the state itself. «St Peter,
            # Roath, Glamorganshire, Wales» walked all the way to the last part
            # and found Wales — a village in South Yorkshire. A country name is
            # the tail of the string, not a place in it.
            if k in COUNTRY or k in US_ADMIN:
                continue
            if len(k) > 2:
                w[k] += p.get("n", 1)
                HINTS.setdefault(k, set()).add(h)
    w.pop("", None)
    return {k: v for k, v in w.items() if len(k) > 2}

# head -> the (country, admin1) pairs the archive's own strings imply for it.
HINTS = {}

# A name the archive uses that belongs to a bigger town somewhere else. The
# lookup below keeps the most populous bearer of a name, which is right almost
# always and catastrophic twice: Ledenice — where Anton Defranceschi was born
# in 1890 — went to Ledenice in South Bohemia, and Ragusa, which is what every
# Venetian document calls Dubrovnik, went to Ragusa in Sicily, a town of
# sixty-nine thousand people seven hundred kilometres away. Population cannot
# tell them apart; only knowing which country the archive means can.
PREFER = {
    "ledenice": ("HR", None),          # the Vinodol village, not South Bohemia
    "ragusa":   ("HR", "Dubrovnik"),   # the Republic, not Sicily
}

def scan(gdir, want):
    """One pass per dump, keeping only the names the archive asked for and,
    where a name is ambiguous, the most populous bearer of it."""
    got = {}
    files = [f for f in sorted(os.listdir(gdir)) if f.endswith(".txt")]
    for fn in files:
        for line in io.open(os.path.join(gdir, fn), encoding="utf-8"):
            f = line.rstrip("\n").split("\t")
            if len(f) < 15: continue
            try: lat, lon, pop = float(f[4]), float(f[5]), int(f[14] or 0)
            except ValueError: continue
            names = {f[1], f[2]} | {x.strip() for x in (f[3] or "").split(",") if x.strip()}
            for nme in names:
                k = norm(nme)
                if k not in want:
                    continue
                hs = {h for h in HINTS.get(k, set()) if h[0]}
                if hs:
                    # The archive's own string said where this is. Take only a
                    # candidate that agrees with it.
                    if not any(f[8] == c and (not a or (len(f) > 10 and f[10] == a))
                               for c, a in hs):
                        continue
                pref = PREFER.get(k)
                if pref:
                    # A forced name takes only the country it was forced to,
                    # and the named town when one is named — otherwise the
                    # whole point is lost to whichever hotel or hill shares
                    # the word.
                    if f[8] != pref[0]:
                        continue
                    if pref[1] and f[1] != pref[1]:
                        continue
                if k not in got or pop > got[k][2]:
                    got[k] = (round(lat, 5), round(lon, 5), pop, f[1], f[8])
    return got

def main():
    want = wanted()
    have = {}
    if os.path.exists(OUT):
        have = json.load(io.open(OUT, encoding="utf-8")).get("places", {})
    gdir = sys.argv[sys.argv.index("--gaz") + 1] if "--gaz" in sys.argv else None
    if gdir:
        got = scan(gdir, want)
        for k, v in got.items():
            have[k] = {"lat": v[0], "lon": v[1], "name": v[3], "cc": v[4], "pop": v[2]}
    missing = sorted(k for k in want if k not in have)
    json.dump({"note": __doc__.strip().split("\n\n")[1],
               "built": "from the GeoNames dumps, kept out of this repository",
               "places": dict(sorted(have.items()))},
              io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(json.dumps({"named_by_archive": len(want), "resolved": len(have),
                      "missing": len(missing), "first_missing": missing[:20]},
                     ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
