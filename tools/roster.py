#!/usr/bin/env python3
"""Build the master roster: every person of the name this archive holds.

Merges the record sets that name individuals — FamilySearch record hits,
parish burials, headstones, reconstructed households, the Eleven, the Omis
chart, the namesakes and the deep biographies — into one list, deduplicated
by name and year, with a line assigned from the place and a link back to
wherever that person is written up.

Living people are excluded, not hidden: anyone with no death recorded and a
birth after LIVING_CUTOFF is dropped, and the count of drops is reported.
"""
import json, os, re, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D    = os.path.join(ROOT, "site", "src", "data")
LIVING_CUTOFF = 1926

def load(n):
    with open(os.path.join(D, n), encoding="utf-8") as f: return json.load(f)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return " ".join(s.split())

SUR = re.compile(r"\b(de\s*)?franc?[ei]sc?h?[ei]?(sk|sch)?i?\b|frances[ck]", re.I)

def yr(v):
    if v is None: return None
    m = re.search(r"\b(1[5-9]\d\d|20[0-2]\d)\b", str(v))
    return int(m.group(1)) if m else None

# line assignment from place text
LINES = [
 ("trentino",["telve","strigno","primiero","laives","leifers","bozen","bolzano","tirol","tyrol","cles",
              "rovereto","trento","ravina","sacco","predazzo","fiemme","fassa","cavalese"]),
 ("corsica", ["tomino","mandolacce","cap corse","ersa","haute-corse","corse","bastia"]),
 ("carnia",  ["mione","ovaro","muina","agrons","carnia","gorto","luincis","paluzza","givigliana",
              "gologor","moncalvo","gracis","gallignana","gracisce","crikvenica","klenovica","senj",
              "bribir","novi vinodol","pfullingen","reutlingen","metzingen","neuhausen","bad urach",
              "johannesburg","south africa","horsham","ipswich","queensland","victoria","zimbabwe",
              "jackson heights","brooklyn","new york","krivi put","karlobag","fuzine"]),
 ("venice",  ["venice","venezia","zadar","zara","omis","almissa","imotski","perinusa","prolozac",
              "split","spalato","opacac","sibenik "]),
 ("crete",   ["candia","heraklion","zante","seget","seghetto","umag","umago","brtonigla","verteneglio",
              "koper","capodistria","buje","buie"]),
 ("south",   ["pula","pola","fazana","fasana","premantura","medulin","barban","barbana","liznjan",
              "lisignano","vodnjan","dignano","galizana","galignana","peroj"]),
]
UNPLACED = ["rijeka","fiume","bakar","buccari","svetvin","sanvincenti","labin","albona","kastelir",
            "sterna","oprtalj","rovinj","rovigno","pazin","pisino","trieste","trst","porec","parenzo",
            "plomin","fianona","sovinjak","motovun","montona","buzet","pinguente","roc ","hum","colmo",
            "cerovlje","lindar","boljun","gimino","zminj","tinjan","antignana","kanfanar","canfanaro",
            "vrsar","orsera","pican","pedena","istra","istria","kustenland","kuestenland","litorale"]
VAGUE    = ["croazia austria","croatia parish not named","kraljevina hrvatska","not stated",
            "austria","croazia","hrvatska","croatia","dalmatia","ungheria","osterreich"]
ABROAD   = ["united states","usa","canada","australia","brasil","brazil","argentina","uruguay",
            "switzerland","svizzera","ticino","france","francia","germany","deutschland","venezuela",
            "puerto rico","trinidad","chile","new jersey","new york state","connecticut","michigan",
            "illinois","pennsylvania","arizona","missouri","ohio","california","ontario","wisconsin",
            "colorado","florida","texas","minnesota","washington","oregon","nevada","maryland"]

def line_of(place):
    p = norm(place)
    for key, keys in LINES:
        if any(k in p for k in keys): return key
    if any(k in p for k in UNPLACED): return "unplaced"
    if any(k in p for k in ABROAD):   return "abroad"
    if not p.strip() or any(k == p.strip() or k in p for k in VAGUE): return "unknown"
    return "other"

rows = []
def add(name, born, died, place, src, href, note="", notable=False, ark="", mh=""):
    name = str(name or "")
    if not name.strip(): return
    rows.append({"name": " ".join(name.split()), "b": yr(born), "d": yr(died),
                 "place": str(place or "").strip(), "src": src, "href": href,
                 "note": str(note or ""), "notable": notable,
                 "ark": ark or "", "mh": mh or ""})

# 1. FamilySearch record hits
for r in load("fsrecords.json"):
    add(r["name"], r.get("birth") or r.get("christening"), r.get("death") or r.get("burial"),
        r.get("place"), "record", "/archive/", ark=("1:1:" + r["id"]) if r.get("id") else "")

# 2. Parish burials
for r in load("burials.json")["rows"]:
    add(r["name"], r.get("born") or r.get("by"), r.get("died") or r.get("dy") or r.get("buried"),
        r.get("place"), "burial", "/burials/")

# 3. Headstones
for r in load("graves.json")["rows"]:
    add(r["name"], r.get("b"), r.get("d"), r.get("place"), "grave", "/graves/", note=r.get("cem",""))

# 4. Households — the children, who are the people
for h in load("households.json"):
    for c in h.get("children", []):
        add(c["name"], c.get("by") or c.get("birth"), c.get("dy") or c.get("death"),
            c.get("place") or h.get("place"), "household", "/households/")

# 5. The Eleven
ev = load("eleven.json")
for c in ev["children"]:
    add("%s Defranceschi" % c["n"].split("—")[0].replace("“","").replace("”","").strip(),
        c.get("born"), c.get("died"), "Gračišće", "eleven", "/the-eleven/", note=c.get("where",""))

# 6. The Omiš chart
om = load("omis.json")
for r in om.get("line", []) + om.get("siblings", []):
    if not isinstance(r, list) or len(r) < 2: continue
    m = re.match(r"\s*(\d{4})\s*[–-]\s*(\d{4})", str(r[1]))
    add("%s de Franceschi" % r[0], m.group(1) if m else None, m.group(2) if m else None,
        "Omiš", "chart", "/omis-line/", note=(r[2] if len(r) > 2 else ""))

# 7. Deep biographies
for p in load("people.json"):
    add(p["name"], p.get("born"), p.get("died"), p.get("line",""), "life",
        "/people/%s/" % p["slug"], note=", ".join(p.get("roles", [])))

# 8. Namesakes — notable
for n in load("namesakes.json"):
    m = re.search(r"(1[0-9]{3})\D+(1[0-9]{3})", n.get("dates",""))
    add(n["name"], m.group(1) if m else n.get("dates"), m.group(2) if m else None,
        n.get("where",""), "namesake", "/namesakes/", note=n.get("field",""), notable=True)

# 9. The Gologorica GEDCOM people
for r in load("gologorica.json").get("people", []):
    add(r["name"], r.get("birthYear") or r.get("birth"), r.get("deathYear") or r.get("death"),
        r.get("place") or "Gologorica", "golo", "/gologorica-line/",
        note=(r.get("title") or ""))

# 10. The direct line, the Senj spine, Crikvenica, Pfullingen, the Imotski chain
for f, key, href, place in [("directline.json","generations","/direct-line/",""),
                            ("senjline.json","spine","/senj-line/","Senj"),
                            ("crikvenica.json","children","/crikvenica-house/","Crikvenica"),
                            ("pfullingen.json","people","/pfullingen/","Pfullingen"),
                            ("imotski.json","chain","/imotski/","Imotski")]:
    for r in load(f).get(key, []):
        if not isinstance(r, dict): continue
        nm = r.get("name") or r.get("n") or ""
        add(nm, r.get("born") or r.get("b") or r.get("birth"),
            r.get("died") or r.get("d") or r.get("death"),
            r.get("place") or r.get("where") or place, "line", href,
            note=r.get("role") or r.get("what") or "")

# 11. David's MyHeritage tree (tree 4 only), harvested 8 September 2026
MHTSV = os.path.join(ROOT, "data", "myheritage-surname-2026-09.tsv")
if os.path.exists(MHTSV):
    with open(MHTSV, encoding="utf-8") as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if len(c) < 6: continue
            mid, nm, b, d, pl, ark = c[0], c[1], c[2], c[3], c[4], c[5]
            add(nm, b, d, pl, "myheritage", "/people/", ark=ark, mh=mid)

# ---- filter to the surname, drop the living, dedupe -------------------------
kept, living, notsur = [], 0, 0
for r in rows:
    if not SUR.search(r["name"]): notsur += 1; continue
    if r["d"] is None and (r["b"] or 0) >= LIVING_CUTOFF: living += 1; continue
    if r["d"] is None and r["b"] is None and r["src"] in ("record",): pass
    r["line"] = line_of(r["place"] + " " + r["note"])
    kept.append(r)

best = {}
for r in kept:
    k = (norm(r["name"]), r["b"] or r["d"] or "")
    cur = best.get(k)
    rank = {"life":0,"line":1,"namesake":2,"eleven":3,"golo":4,"chart":5,"grave":6,"burial":7,"myheritage":8,"household":9,"record":10}
    if cur is None or rank[r["src"]] < rank[cur["src"]]:
        if cur:
            r["also"] = sorted(set((cur.get("also") or []) + [cur["src"]]))
            if not r.get("ark") and cur.get("ark"): r["ark"] = cur["ark"]
            if not r.get("mh") and cur.get("mh"): r["mh"] = cur["mh"]
        best[k] = r
    else:
        cur["also"] = sorted(set((cur.get("also") or []) + [r["src"]]))
        if not cur["place"] and r["place"]: cur["place"] = r["place"]
        if cur["d"] is None and r["d"]: cur["d"] = r["d"]
        if cur["b"] is None and r["b"]: cur["b"] = r["b"]
        if r["notable"]: cur["notable"] = True
        if not cur.get("ark") and r.get("ark"): cur["ark"] = r["ark"]
        if not cur.get("mh") and r.get("mh"): cur["mh"] = r["mh"]

# dossier links
dos = load("dossiers.json")["people"]
byname = {norm(p["name"]): p["slug"] for p in dos.values()}
out = []
for r in best.values():
    s = byname.get(norm(r["name"]))
    if s: r["who"] = "/who/%s/" % s
    out.append(r)

out.sort(key=lambda r: (r["b"] or r["d"] or 9999, norm(r["name"])))
counts = collections.Counter(r["line"] for r in out)
src    = collections.Counter(r["src"] for r in out)
META = {
 "note": "Every person of this surname the archive can name, gathered from every record set it holds and from David's own MyHeritage tree — parish burials, headstones, reconstructed households, FamilySearch record hits, the Gologorica pedigree, the Eleven of Gračišće, the Omiš chart, the direct line, the namesakes, and 555 individuals harvested from the live tree on 8 September 2026. **Identity here is by record, not by resolved individual**: two entries may be one person, and where the archive knows they are it has merged them. Nothing here is new evidence — it is all of the evidence, in one list, for the first time.",
 "legend": [
  [
   "carnia",
   "Out of Carnia — our own line, from Mione and Agrons to Gologorica, Gračišće, Crikvenica, Senj and the diaspora"
  ],
  [
   "venice",
   "Out of Venice — Zadar, Omiš, Imotski, Perinuša, Split"
  ],
  [
   "crete",
   "Out of Crete — Candia, Zante, Šibenik, Seget, Umag"
  ],
  [
   "south",
   "Southern Istria — Pula, Fažana, Premantura, Medulin, Barban, Ližnjan"
  ],
  [
   "unplaced",
   "A documented Istrian or Kvarner household this archive will not attach to any line — Rijeka, Bakar, Svetvinčenat, Vodnjan, Kaštelir, Poreč, Labin and the rest"
  ],
  [
   "trentino",
   "Trentino and South Tyrol — Telve, Strigno, Fiera di Primiero, Laives, Cles. A large and quite separate stock of the name, in the tree because the surname is the same"
  ],
  [
   "corsica",
   "Cap Corse — Tomino and Mandolacce. Its own lane on the Lines page, and never in Istria"
  ],
  [
   "abroad",
   "Abroad, and the line not established — the United States, Australia, Brazil, Argentina, Switzerland, Canada, France"
  ],
  [
   "unknown",
   "The record names no place, or names only «Croatia» or «Austria»"
  ],
  [
   "other",
   "A place that fits none of the above"
  ]
 ],
 "srclabel": {
  "life": "Biography",
  "line": "Direct line",
  "namesake": "Namesake",
  "eleven": "The Eleven",
  "golo": "Gologorica pedigree",
  "chart": "Omiš chart",
  "grave": "Headstone",
  "burial": "Parish burial",
  "myheritage": "Family tree",
  "household": "Household",
  "record": "Record index"
 },
 "links": "**572 of them have a record behind them** — a FamilySearch document you can open — and **513 are in the family tree**. Where a row has both, both links are given. A record link opens the indexed document; a tree link opens the person in David's MyHeritage tree, which is private, so it will only work for people he has given access to.",
 "warn": "**Living people are omitted, not hidden.** Anyone with no recorded death and a birth after 1925 is dropped from this list, and the count of drops is printed below."
}
man = dict(META, **{"rows": out,
       "stats": {"total": len(out), "living_omitted": living,
                 "with_record": sum(1 for r in out if r.get("ark")),
                 "with_tree": sum(1 for r in out if r.get("mh")),
                 "lines": dict(counts), "sources": dict(src)}})
with open(os.path.join(D, "roster.json"), "w", encoding="utf-8") as f:
    json.dump(man, f, ensure_ascii=False, indent=1)
print("roster:", len(out), "people;", living, "living omitted;", notsur, "not of the surname")
print("lines:", dict(counts)); print("sources:", dict(src))
