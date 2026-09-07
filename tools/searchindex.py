#!/usr/bin/env python3
"""One flat index over everything the archive can point at."""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "site", "src", "data")
L = lambda f: json.load(open(os.path.join(D, f), encoding="utf-8"))

rows = []
def fold(s):
    """Strip diacritics so a reader typing Gracisce finds Gračišće."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return (s.replace("đ", "d").replace("Đ", "D")
             .replace("ø", "o").replace("ł", "l").replace("æ", "ae"))

def add(kind, title, sub, href, extra=""):
    raw = " ".join(x for x in (title, sub, extra) if x).lower()
    q = raw + " " + fold(raw)
    rows.append({"k": kind, "t": title, "s": sub, "h": href, "q": q})

for p in L("people.json"):
    add("Person", p["name"], f"{p.get('born') or '?'}–{p.get('died') or '?'} · {', '.join(p.get('roles', []))}",
        f"/people/{p['slug']}/", p.get("lead", ""))

for p in L("places.json"):
    alt = " ".join((p.get("alt") or {}).values())
    add("Place", p["name"], (p.get("lead") or "")[:90], f"/places/{p['slug']}/", alt + " " + p.get("parish", ""))

for i, h in enumerate(L("households.json")):
    kids = ", ".join(c["name"] for c in h.get("children", [])[:6])
    add("Household", f"{h.get('father') or '—'} & {h.get('mother') or '—'}",
        f"{h.get('place')} · {h.get('from')}–{h.get('to')} · {h.get('n', 0)} children",
        "/explorer/", kids)

for r in L("fsrecords.json"):
    when = r.get("birth") or r.get("christening") or r.get("marriage") or r.get("death") or ""
    add("Record", r["name"], f"{when} · {r.get('place', '')}".strip(" ·"), "/archive/",
        f"{r.get('parents', '')} {r.get('spouses', '')} {r.get('id', '')}")

for n in L("namesakes.json"):
    add("Namesake", n["name"], f"{n['dates']} · {n['where']} · {n['field']}", "/namesakes/", n["text"][:180])

for p in L("plates.json"):
    add("Plate", p["title"], p["holder"], "/gallery/", p["caption"][:180])

for g in L("directline.json")["generations"]:
    sp = (g.get("spouse") or {}).get("name", "")
    kids = " ".join(c["name"] for c in g.get("children", []))
    add("Direct line", g["name"], f"Generation {g['n']} · {g['place']}",
        f"/direct-line/#gen-{g['n']}", f"{g.get('latin','')} {sp} {kids}")

im = L("imotski.json")
for g in im["chain"]:
    add("Imotski line", g["who"], f"{g['dates']} · Dalmatia — a separate family", "/imotski/", g["what"][:180])
for c in im["children"]:
    if c["dates"]:
        add("Imotski line", c["who"], f"{c['dates']} · Perinuša — a separate family", "/imotski/", c["what"][:180])
for r in im["salvage"]["rows"]:
    if r["died"]:
        add("Person", r["who"], f"{r['born'] or '?'} – {r['died']}", "/imotski/", r["what"][:180])

li = L("listria.json")
for r in li["seget"]["list"]["rows"]:
    add("Seget colonist 1764", r["who"], f"{r['n']} souls · from {r['from']}", "/carlos-book/",
        "Roll of colonist families on the Seget and Giuba estate, 30 April 1764")
for r in li["pedena"]["rows"] + li["wars"]["rows"]:
    add("Carlo's book", r.get("lab") or r.get("t"), r.get("y", "L'Istria, 1879"), "/carlos-book/",
        (r.get("text") or r.get("w"))[:180])

cg = L("carnia.json").get("ginut")
if cg:
    for g in cg["chain"]:
        add("Mione household", g["who"], f"with {g['with']} · Mione, Carnia", "/carnia/", g["what"][:180])
    for r in cg["children"]["rows"]:
        add("Mione household", r["who"] + " De Franceschi", f"{r['born']} – {r['died']}", "/carnia/",
            "Child of Checo dal Ginut and Maria Giuseppina Fedele, Mione")

ck = L("crikvenica.json").get("kovacina")
if ck:
    for r in ck["rows"]:
        add("Person", r["who"], "Crikvenica house 119", "/crikvenica-house/", r["what"][:180])

sj = L("senjline.json")
for g in sj["spine"]:
    add("Senj line", g["who"], f"Generation {g['n']} · {g['where']}", "/senj-line/", g["what"][:180])
for grp in sj["karlobag"]["gens"]:
    for r in grp["rows"]:
        add("Karlobag ancestry", r["who"], f"{r['b'] or '?'} – {r['d'] or '?'}", "/senj-line/",
            "From the ancestor chart of Matia Papic, born Pilipic, of Karlobag")

gg = L("gologorica.json")
for r in gg["bandnight"]["rows"]:
    add("Village 1893–95", r["t"], f"{r['y']} · Gologorica", "/gologorica-line/", r["w"][:300])
add("Person", "Piero (Pietro) De Franceschi", "m. 22 Jan 1795 at Valle · of Gologorizza",
    "/gologorica-line/", gg["bembo"]["quote"][:300])
add("Person", "Anna Bembo", "m. 22 Jan 1795 at Valle · daughter of Tommaso Bembo",
    "/gologorica-line/", gg["bembo"]["en"][:300])
add("Person", "Vittorio Defranceschi", "b. c. 1872 · son of Francesco · Gologorica",
    "/gologorica-line/", gg["bandnight"]["person"])

for st in L("kobler.json")["threestocks"]["stocks"]:
    for w, x in st["rows"]:
        add("Fiume family", w, f"Kobler, stock {st['n']} · {st['t']}", "/carlos-letter/", x[:320])

cg = L("carnia.json")
for n, dt, x in cg["gorto"]["stones"]:
    add("Gorto grave", n, f"{dt} · Pieve di Santa Maria di Gorto", "/carnia/", x)
for r in cg["gorto_war"]["rows"]:
    add("War memorial", r["lab"], "Val Degano", "/carnia/", r["text"][:320])

sg = L("seget.json")
for i, m in enumerate(sg["umago"]["mayors"]):
    if "Franceschi" in m["n"]:
        add("Person", m["n"], f"Mayor of Umago, 1815–1918 · {m['note']}".strip(" ·"), "/seget/", sg["umago"]["count"])

kb = L("kobler.json")
for it in kb["funeral"]["items"]:
    add("Press notice", it["kicker"], it["cite"], "/carlos-letter/",
        f"{it.get('text','')} {it.get('quote','')} {it.get('en','')} {it.get('why','')}"[:400])

add("Person", "Giovanni Antonio de Benzoni", "Fiume 1687 – Fiume 1745 · vicar general of the bishop of Pedena, bishop of Senj and Modrus 1730", "/carlos-letter/", kb["benzoni"]["en"])
add("Person", "Giovanni Battista Defranceschi", "suppanus (headman) of Gologorica 1733-1743; his wife Joanna godmother at Gallignana twice", "/direct-line/", "8 Jan 1733: Ioana Uxor Sup.ni Ioanis Bap.tae Defranceschi. 26 June 1743: Joanna uxor Suppani Jo: Baptistae Defranceschi a Golagoriza.")
add("Person", "Joannes Petrus Defranceschi", "Dominus, godfather at Gallignana 5 May 1744", "/direct-line/", "Patrini fuerunt D.nus Joannes Petrus Defranceschi et Mattia uxor supradicti Joannis Grach.")

for _n, _d, _b in (
    ("Francesca de Franceschi", "d. 1 January 1924, aged 77 \u2014 Umag", "Named on the loose five-name tablet in the cemetery at Umag, in the De Franceschi di Seghetto plot."),
    ("Giorgio de Franceschi", "ragioniere; d. 4 February 1940, aged 26 \u2014 Umag", "Named on the loose five-name tablet in the cemetery at Umag."),
    ("Italo de Franceschi", "ingegnere; d. 3 December 1944, aged 68 \u2014 Umag", "Named on the loose five-name tablet in the cemetery at Umag."),
    ("Feramondo de Franceschi", "d. 12 December 1945, aged 74 \u2014 Umag; the stone spells it with one R", "Named on the loose five-name tablet at Umag. The family's origin legend in La Voce del Popolo has a Ferramondo who fought Odoacer; this man's own stone reads FERAMONDO."),
    ("Anna Fragiacomo, ved. de Franceschi", "d. 27 August 1960, aged 70 \u2014 Umag", "Named on the loose five-name tablet at Umag as FRAGIACOMO ANNA VED. DE FRANCESCHI."),
    ("Ettore de Franceschi", "family plot at Umag, walled and empty but for a name plate", "An enclosure west of the canopy tomb with no monument and a wall pocked with the sockets of removed plaques. The iron plate reads FAMIGLIA ETTORE DE FRANCESCHI."),
):
    add("Person", _n, _d, "/seget/", _b)

for _n, _d, _b in (
    ("Maria Defranceschi, nee Valhart", "b. 6 April 1867, d. 3 October 1945 \u2014 buried at Gracisce", "Named on the obelisk in the family plot at Gracisce as MARIA DEFRANCESCHI 6.IV.1867 - 3.X.1945. The American chart of 2012 gives her birth as 4/6/1867 and only the year of death."),
    ("Antonio DeFranceschi", "185[5 or 6] - 19[2]4 \u2014 buried at Gracisce; head of the eleven children", "Obelisk in the family plot at Gracisce, worn. The American chart of 2012 gives 6 August 1856 - 23 October 1924."),
):
    add("Person", _n, _d, "/the-eleven/", _b)

for _n, _d, _b in (
    ("Francesco de Franceschi", "Bishop of Pola about 1424", "In Kobler's series of the bishops of Pola, from acts of Fiume, and independently in Cavalli 1845, between Tommaso Tommasini and Domenico de Luschis (1426-1451). No primary act seen."),
    ("Philippus de Franceschi", "priest; celebrated a baptism at Gallignana 19 March 1734", "Presbiter Philippus de Franceschi Baptisavit Josephum Antonium filium legitimum Ignatij Marinich et Uxoris Luciae. Folio 138 of the Gallignana baptism book."),
    ("Giuseppa Defranceschi", "daughter of Valentino Defranceschi of Carnia; wife of Carlo Rossi, British vice-consul at Fiume", "Held the house in the Contrada dei Cappuccini after her father; it passed in 1794 to Elena widow Faribault. Named by Kobler in his topography, not in his family article."),
    ("Margherita de Franceschi", "married Ascanio Giacomini of Fiume, 1697", "Their son Antonio was made a municipal councillor of Fiume in 1733."),
    ("Antonio De Franceschi", "secretary of the city of Fiume, 1682", "From Kobler's series of secretaries drawn from the public books."),
    ("Giovanni de Franceschi", "vice-chancellor of the city of Fiume, 1682", "From Kobler's series of vice-chancellors drawn from the public books."),
    ("Girolamo Franceschi", "councillor of Fiume, 1651-1700 roll", "Listed with Giulio and Giovanni Antonio Franceschi; not in Kobler's family article."),
    ("Giulio Franceschi", "councillor of Fiume, 1651-1700 roll", "Listed with Girolamo and Giovanni Antonio Franceschi; not in Kobler's family article."),
    ("Francesco Defranceschi", "patrician councillor of Fiume in 1848; royal harbourmaster; d. 22 December 1885", "Son of Valentino di Giuseppe Defranceschi and Orsola de Benzoni. On the same 1848 roll as Giovanni Kobler."),
):
    add("Person", _n, _d, "/carlos-letter/", _b)

for _n, _d, _b in (
    ("Felice de Benzoni", "d. Fiume 24 July 1716 \u2014 imperial inspector of the maritime crown estates; killed on the public square by a bursting saluting mortar", "Married Orsola di Nicolo Marotti. Father of Bishop Giovanni Antonio de Benzoni. Buried in the chapel of the Immaculate Conception at Fiume."),
    ("Stefano Giovanni de Benzoni", "b. 1690 \u2014 municipal councillor of Fiume 1724, lieutenant in the County of Pazin, imperial councillor; d. 1749", "Brother of Bishop Giovanni Antonio. Held office over the county containing Gologorica and Gallignana. Tomb in St Vitus, Fiume, 1749."),
    ("Orsola de Benzoni", "m. Valentino Defranceschi at Fiume 1793; d. 1807", "Eight children. Her husband built the family tomb in the cemetery where she lay. Her place in Kobler's Benzoni pedigree is unresolved."),
):
    add("Person", _n, _d, "/carlos-letter/", _b)

sjb = L("senjline.json")["behind"]
for key, lab in (("blazevic", "Blažević line"), ("zubrinic", "Žubrinić line")):
    for who, what in sjb[key]["rows"]:
        add("Maternal line", who, lab + " · family file", "/senj-line/", what)

for p in L("parishbooks.json") if os.path.exists(os.path.join(D, "parishbooks.json")) else []:
    if isinstance(p, dict) and p.get("parish"):
        add("Parish book", p["parish"], p.get("span") or p.get("kind") or "", "/parish-books/")

# de-duplicate on title+href, keep the richest row
seen = {}
for r in rows:
    key = (r["k"], r["t"], r["s"], r["h"])
    if key not in seen or len(r["q"]) > len(seen[key]["q"]):
        seen[key] = r
out = sorted(seen.values(), key=lambda r: (r["k"], r["t"]))
json.dump(out, open(os.path.join(D, "searchindex.json"), "w"), ensure_ascii=False, separators=(",", ":"))
kinds = {}
for r in out: kinds[r["k"]] = kinds.get(r["k"], 0) + 1
print(f"{len(out)} entries: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
print("size", os.path.getsize(os.path.join(D, "searchindex.json")) // 1024, "KB")
