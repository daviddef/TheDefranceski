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

sg = L("seget.json")
for i, m in enumerate(sg["umago"]["mayors"]):
    if "Franceschi" in m["n"]:
        add("Person", m["n"], f"Mayor of Umago, 1815–1918 · {m['note']}".strip(" ·"), "/seget/", sg["umago"]["count"])

kb = L("kobler.json")
for it in kb["funeral"]["items"]:
    add("Press notice", it["kicker"], it["cite"], "/carlos-letter/",
        f"{it.get('text','')} {it.get('quote','')} {it.get('en','')} {it.get('why','')}"[:400])

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
