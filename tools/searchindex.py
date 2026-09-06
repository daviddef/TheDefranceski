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
