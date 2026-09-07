#!/usr/bin/env python3
"""Build a person dossier for every named individual: every mention of them
anywhere in the site's data, with the page it appears on and the text around it.

Identity here is by NAME, not by resolved individual. Two people of one name
share a dossier, and the page says so. That is deliberate: this archive has
already had to separate three unrelated De Franceschi families, and a
generator that silently merged them would be worse than no generator."""
import json, os, re, unicodedata, glob, collections

D = "site/src/data"
P = "site/src/pages"

def slug(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60]

# ---- 1. which page renders which data file
page_of = {}
for f in glob.glob(os.path.join(P, "*.astro")):
    name = os.path.basename(f)[:-6]
    route = "/" if name == "index" else f"/{name}/"
    for m in re.finditer(r'from\s+"\.\./data/([a-z0-9_\-]+\.json)"', open(f, encoding="utf-8").read()):
        page_of.setdefault(m.group(1), []).append(route)
TITLES = {}
for f in glob.glob(os.path.join(P, "*.astro")):
    name = os.path.basename(f)[:-6]
    t = re.search(r'title="([^"]+)"', open(f, encoding="utf-8").read())
    TITLES["/" if name == "index" else f"/{name}/"] = t.group(1) if t else name

# ---- 2. harvest candidate names
names = {}
def add_name(n, note=""):
    n = re.sub(r"\s+", " ", str(n)).strip(" ,.;·—-")
    if len(n) < 5 or len(n) > 64: return
    if not re.search(r"[A-Za-zÀ-ž]", n): return
    if n.lower() in ("the living", "unknown", "n n"): return
    names.setdefault(n, set()).add(note)

def crawl(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("name", "n", "t", "who", "lab") and isinstance(v, str):
                add_name(v)
            crawl(v)
    elif isinstance(o, list):
        for v in o: crawl(v)

for fn in ("tree.json", "eleven.json", "people.json", "households.json", "explorer.json",
           "pfullingen.json", "seget.json", "namesakes.json", "crikvenica.json",
           "gologorica.json", "senjline.json", "imotski.json", "omis-line.json"):
    p = os.path.join(D, fn)
    if os.path.exists(p): crawl(json.load(open(p, encoding="utf-8")))

# anything shaped like a person record: has a name and a birth/date field
def crawl2(o):
    if isinstance(o, dict):
        if isinstance(o.get("name"), str) and any(k in o for k in ("born", "dates", "birth", "died", "b", "d")):
            add_name(o["name"])
        for v in o.values(): crawl2(v)
    elif isinstance(o, list):
        for v in o: crawl2(v)
for p in glob.glob(os.path.join(D, "*.json")):
    if os.path.basename(p) in ("searchindex.json", "dossiers.json"): continue
    try: crawl2(json.load(open(p, encoding="utf-8")))
    except Exception: pass
for row in json.load(open(os.path.join(D, "searchindex.json"), encoding="utf-8")):
    if row.get("k") in ("Person", "Namesake", "Household", "Maternal line", "Direct line", "Seget colonist 1764"):
        add_name(row.get("t", ""))

# only keep names that look like people
KEEP = re.compile(r"^[A-ZÀ-Ž][\wÀ-ž'’.«»-]*(\s+[\wÀ-ž'’.«»(),-]+){1,5}$")
# drop phrases, not names: anything with a lowercase connective in it
STOP = re.compile(r"\b(born|died|baptis|buried|at|in|of|the|and|from|to|his|her|aged|house|line|and|nee|née)\b", re.I)
names = {n: v for n, v in names.items() if not STOP.search(n)}
names = {n: v for n, v in names.items() if KEEP.match(n)}

# ---- 3. find every mention
blobs = {}
for p in glob.glob(os.path.join(D, "*.json")):
    fn = os.path.basename(p)
    if fn in ("searchindex.json", "dossiers.json"): continue
    blobs[fn] = open(p, encoding="utf-8").read()

def variants(n):
    """A person may be written 'Anton Rudolf Defranceski' or just 'Anton Rudolf'."""
    v = {n}
    parts = n.split()
    if len(parts) >= 3: v.add(" ".join(parts[:2]))
    return sorted(v, key=len, reverse=True)

dossiers = {}
for n in sorted(names):
    hits, seen = [], set()
    for v in variants(n):
        pat = re.compile(re.escape(v), re.I)
        for fn, blob in blobs.items():
            for m in pat.finditer(blob):
                a = max(0, m.start() - 320); b = min(len(blob), m.end() + 380)
                seg = blob[a:b]
                seg = re.sub(r'","[a-zA-Z_]+":"', " — ", seg)
                seg = re.sub(r'[{}\[\]"]|\\n|\\"', " ", seg)
                seg = re.sub(r"\s*:\s*", ": ", seg)
                seg = re.sub(r"\s+", " ", seg).strip()
                if len(seg) < 60: continue
                key = seg[40:140]
                if key in seen: continue
                seen.add(key)
                for route in page_of.get(fn, []):
                    hits.append({"page": route, "title": TITLES.get(route, route), "text": seg})
                    break
                else:
                    hits.append({"page": "", "title": fn.replace(".json", ""), "text": seg})
        if hits: break
    if len(hits) < 1: continue
    pages = sorted({h["page"] for h in hits if h["page"]})
    dossiers[slug(n)] = {"name": n, "slug": slug(n), "n": len(hits),
                         "pages": [{"h": p, "t": TITLES.get(p, p)} for p in pages],
                         "hits": hits[:24]}

out = {"note": ("A dossier is every mention of a name anywhere in this archive's data, gathered automatically and "
                "linked back to the page it appears on. Identity here is by NAME, not by resolved individual: "
                "where two people share a name they share a dossier, and the archive says so on the page rather "
                "than guessing. Nothing on a dossier page is new evidence — it is the same evidence, brought together."),
       "people": dossiers}
json.dump(out, open(os.path.join(D, "dossiers.json"), "w"), ensure_ascii=False, indent=1)
print(f"{len(dossiers)} dossiers, {sum(v['n'] for v in dossiers.values())} mentions")
big = sorted(dossiers.values(), key=lambda v: -v["n"])[:8]
for b in big: print(f"  {b['n']:4d}  {b['name']}  ({len(b['pages'])} pages)")
