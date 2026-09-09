#!/usr/bin/env python3
"""Rebuild site/src/data/dossiers.json — one page per person.

The roster is the authoritative list of people. For each of them this walks
every data file the site actually renders, finds every mention of the name,
and records it with a link back to the page it appears on. Roster facts
(place, years, source, line, what the archive knows) are carried onto the
page so a person's dossier opens with the finding, not just the quotations.

Entries already in dossiers.json that are not roster people are kept as they
are, so no existing /who/ link breaks.

    python3 scripts/build-dossiers.py
"""
import json, os, re, glob, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
PAGES = os.path.join(ROOT, "site", "src", "pages")

def slugify(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("đ", "d")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def plain(s):
    s = str(s)
    s = s.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"')
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`#>]", "", s)
    # strip the JSON scaffolding a raw blob drags in
    s = re.sub(r'"\s*[,:]\s*(true|false|null|\d+)\s*[,}\]]*', " ", s)
    s = re.sub(r'"\s*[},\]]+\s*[{\[]?\s*"?', " ", s)
    s = re.sub(r'"[a-z][a-zA-Z_]{1,12}"\s*:\s*"?', " ", s)
    s = re.sub(r'[{}\[\]"]', " ", s)
    s = re.sub(r"\s+([·,;.])", r"\1", s)
    s = re.sub(r"(?<![A-Za-z])[a-z][a-zA-Z_]{0,14}\s+:\s*", " ", s)  # JSON keys, once the quotes are gone
    s = re.sub(r"(?<![A-Za-z])(key|true|false|null)(?![A-Za-z])", " ", s)
    s = re.sub(r"\s+([·,;.])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip(" ·,;:-")

# ---- which data file is rendered by which page -------------------------
route_of = {}
for f in glob.glob(os.path.join(PAGES, "**", "*.astro"), recursive=True):
    rel = os.path.relpath(f, PAGES)
    if "[" in rel:          # dynamic routes have no single href
        continue
    href = "/" + rel[:-6].replace(os.sep, "/")
    href = href.replace("/index", "") or "/"
    if not href.endswith("/"): href += "/"
    src = open(f, encoding="utf-8").read()
    m = re.search(r'title=\{?["\`]([^"\`]{2,80})["\`]', src)
    title = m.group(1) if m else href.strip("/").replace("-", " ").title() or "Home"
    for dm in re.finditer(r'from\s+["\'][^"\']*data/([a-z0-9_-]+)\.json["\']', src):
        route_of.setdefault(dm.group(1), (href, title))

roster = json.load(open(os.path.join(DATA, "roster.json")))
srclabel = roster.get("srclabel", {})
legend = dict(roster.get("legend") or [])

# ---- load every data file once ----------------------------------------
SKIP = {"dossiers", "searchindex"}
# Structured record files: they get a page link, but their rows are field/value
# data and make unreadable quotations, so no snippets are taken from them.
TABULAR = {"households", "explorer", "roster", "fsrecords", "registers", "sweep",
           "istriasweep", "marriages", "burials", "graves", "plates", "art-src",
           "tree", "names", "givennames", "atlas", "searched", "eleven", "arrivals",
           "lineages", "onename", "parishmap", "parishbooks", "library", "sources"}
blobs = {}
for f in sorted(glob.glob(os.path.join(DATA, "*.json"))):
    name = os.path.basename(f)[:-5]
    if name in SKIP or name not in route_of:
        continue
    try:
        blobs[name] = json.dumps(json.load(open(f, encoding="utf-8")), ensure_ascii=False)
    except Exception:
        pass

old = json.load(open(os.path.join(DATA, "dossiers.json"), encoding="utf-8"))
people = {}

# people the roster names
by_slug = {}
for r in roster["rows"]:
    by_slug.setdefault(slugify(r["name"]), []).append(r)

for slug, rows in by_slug.items():
    name = rows[0]["name"]
    needle = re.sub(r"\s*\(.*?\)\s*", "", name).strip()
    if len(needle) < 5:
        continue
    hits, pages = [], []
    for dataname, blob in blobs.items():
        href, title = route_of[dataname]
        if dataname in TABULAR:
            if needle in blob and not any(pp["h"] == href for pp in pages):
                pages.append({"h": href, "t": title})
            continue
        for m in re.finditer(re.escape(needle), blob):
            a, b = max(0, m.start() - 260), min(len(blob), m.end() + 260)
            snip = plain(blob[a:b])
            snip = " ".join(snip.split(" ")[1:-1]) if len(snip.split(" ")) > 6 else snip
            hits.append({"page": href, "title": title, "text": snip})
            if len(hits) >= 24: break
        if any(h["page"] == href for h in hits) and not any(p["h"] == href for p in pages):
            pages.append({"h": href, "t": title})
    facts = []
    r0 = rows[0]
    yrs = "–".join([str(r0["b"]) if r0.get("b") else "", str(r0["d"]) if r0.get("d") else ""]).strip("–")
    if r0.get("place"): facts.append(["Place", r0["place"]])
    if yrs: facts.append(["Years", yrs])
    if r0.get("parish"): facts.append(["Parish", r0["parish"]])
    if r0.get("line") and legend.get(r0["line"]): facts.append(["Line", legend[r0["line"]].split("—")[0].strip()])
    srcs = sorted({srclabel.get(r["src"], r["src"]) for r in rows})
    if srcs: facts.append(["Found in", " · ".join(srcs)])
    notes = [r["note"] for r in rows if r.get("note")]
    people[slug] = {
        "name": name, "slug": slug, "n": len(hits) or len(rows),
        "pages": pages or [{"h": r0.get("href") or "/people/", "t": "Everyone"}],
        "hits": hits,
        "facts": facts,
        "known": notes[0] if notes else "",
        "more": notes[1:],
        "roster": True,
    }

# keep anything that already had a page and is not a roster person
kept = 0
for slug, p in old.get("people", {}).items():
    if slug not in people:
        p.setdefault("facts", []); p.setdefault("known", ""); p.setdefault("more", [])
        p["roster"] = False
        people[slug] = p
        kept += 1

out = {"note": old.get("note", ""), "people": people}
out["note"] = ("A dossier is every mention of a name anywhere in this archive's data, gathered automatically and "
  "linked back to the page it appears on, with what the archive knows about the person set out at the top. "
  "**Identity here is by NAME, not by resolved individual**: where two people share a name they share a dossier, "
  "and the archive says so rather than guessing. Rebuilt from the roster, so every person the archive can name "
  "has a page — including the ones read straight off a register that no index anywhere contains.")
json.dump(out, open(os.path.join(DATA, "dossiers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"roster people {len(by_slug)} · pages written {len(people)} · non-roster kept {kept}")
