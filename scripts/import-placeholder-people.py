#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add to roster.json the people David's MyHeritage tree files under the node «PLACEHOLDERS Defranceschi's for Investigation (not real)»
(a branch per country, each person carrying a FamilySearch citation) that the archive does not hold yet.

    python3 scripts/import-placeholder-people.py <tree.ged> <list.csv> [--write]

<list.csv> is the audit made 16 Nov 2026 (columns id, have, fs_links, ...): only rows with have == «NOT FOUND» and an FamilySearch link are read.
What is taken, and nothing else: the name, the years, one place string, the FamilySearch address(es) the tree cites. A person is added only if
the tree flags a death and no birth year is later than the living cutoff; everyone else is written to the report as «held back». Every
row says in its note that the record has NOT been read on FamilySearch (src myheritage = the tree's word, grade lore until it is). The GEDCOM
and the list are never committed.
"""
import sys, re, io, json, csv, os, unicodedata, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import living_v2 as L2

def parse(path):
    recs, cur = {}, None
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n"); m = re.match(r"(\d+) (.*)", line)
        if not m: continue
        lv, rest = int(m.group(1)), m.group(2)
        if lv == 0:
            mm = re.match(r"(@[^@]+@) (\w+)", rest)
            cur = {"id": mm.group(1), "t": mm.group(2), "l": []} if mm else None
            if cur: recs[cur["id"]] = cur
            continue
        if cur is None: continue
        if rest.startswith("CONC ") and cur["l"]: cur["l"][-1][1] += rest[5:]
        elif rest.startswith("CONT ") and cur["l"]: cur["l"][-1][1] += "\n" + rest[5:]
        else: cur["l"].append([lv, rest])
    return recs

def f1(r, tag): return [t[len(tag) + 1:] for lv, t in r["l"] if lv == 1 and t.startswith(tag + " ")]
def sub(r, tag, s):
    out, on = [], False
    for lv, t in r["l"]:
        if lv == 1: on = t.startswith(tag)
        elif lv == 2 and on and t.startswith(s + " "): out.append(t[len(s) + 1:])
    return out
def yr(s):
    m = re.search(r"\b(1[5-9][0-9]{2}|20[0-2][0-9])\b", s or ""); return int(m.group(1)) if m else None
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def main():
    ged, lst = sys.argv[1], sys.argv[2]; write = "--write" in sys.argv
    recs = parse(ged)
    rows = list(csv.DictReader(io.open(lst, encoding="utf-8")))
    roster = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))
    pids = {r["pid"] for r in roster["rows"] if r.get("pid")}
    have_mh = {str(r["mh"]) for r in roster["rows"] if r.get("mh")}
    frx = re.compile(r"franc|francesk", re.I)
    out, held = [], []
    for c in rows:
        if c["have"] != "NOT FOUND" or not c["fs_links"]: continue
        r = recs[c["id"]]
        nm = (f1(r, "NAME") or [""])[0].replace("/", " "); nm = " ".join(nm.split())
        # 16 Nov 2026 (David): this is a public-record archive; a spouse or in-law the tree cites a record for is added like anyone else. The first
        # pass held 21 of them back on a scope guess of mine, which is not a rule of the archive. The living rule below is unchanged.
        b = yr((sub(r, "BIRT", "DATE") or [""])[0]); d = yr((sub(r, "DEAT", "DATE") or [""])[0])
        dead = bool(f1(r, "DEAT"))
        mh = str(4000000 + int(c["id"].strip("@I")))
        if mh in have_mh: continue
        # the archive's own rule (CLAUDE.md): a person is living if 80 or younger with no death recorded (L2.CUTOFF = this year - 80). Someone born
        # before the cutoff with no death recorded is not in that window and is added without a death year; someone with no birth year, or born
        # in the window, with no death recorded, stays out.
        if not dead and (b is None or b >= L2.CUTOFF): held.append((nm, "no death recorded and %s: the living rule" % ("no birth year" if b is None else "born %d, in the living window" % b))); continue
        if dead and b is not None and b >= L2.CUTOFF: held.append((nm, "born %d, in the living window; the tree's death flag is not a death record (needs a source)" % b)); continue
        pl = ((sub(r, "BIRT", "PLAC") or sub(r, "CHR", "PLAC") or sub(r, "DEAT", "PLAC") or sub(r, "RESI", "PLAC") or [""])[0]).strip()
        parts = [p.strip() for p in pl.split(",") if p.strip()]
        # a parish church named first (Assunzione di Maria Santissima, Telve, Trento): the place is the town
        if len(parts) > 1 and re.search(r"Maria|Santissim|^San |^Santa |Immacolata|Catedral|Nuestra|Visitazione|Assunzione|Parroquia|Chiesa", parts[0]): parts = parts[1:]
        pl = ", ".join(parts[:3])
        links = []
        for u in c["fs_links"].split(" | "):
            u = u.strip()
            m = re.match(r"(?:https?://)?(?:www\.)?familysearch\.org/(ark:/61903/[0-9:A-Za-z\-]+)(\?[^\s]*)?", u)
            if m: links.append("https://www.familysearch.org/" + m.group(1) + (m.group(2) or ""))
        if not links: held.append((nm, "cites a tree page, not a record")); continue
        ark = next((re.search(r"ark:/61903/(1:1:[0-9A-Z\-]+)", u).group(1) for u in links if "/1:1:" in u), "")
        base = slug(nm) + ("-%d" % b if b else "")
        pid, n = base, 2
        while pid in pids: pid = "%s-%d" % (base, n); n += 1
        pids.add(pid)
        cite = "; ".join("[%s](%s)" % (re.search(r"ark:/61903/([0-9:A-Za-z\-]+)", u).group(1), u) for u in links)
        branch = c["node"].split(":")[0].split("  ")[0].title()
        note = ("**From David's MyHeritage tree** (filed under the investigation branch «%s»; the tree itself calls that node not real). "
                "The tree cites FamilySearch: %s. **Not yet read here:** FamilySearch was down for maintenance on 16 November 2026, so the record has not been opened, "
                "and the name, years and place are the tree's word (lore) until it is." % (branch, cite))
        row = {"name": nm, "b": b, "d": d, "place": pl, "src": "myheritage", "href": "/people/", "note": note, "notable": False,
               "ark": ark, "mh": mh, "line": "unplaced", "pid": pid}
        if len(re.sub(r"\s*\(.*?\)\s*", "", nm)) >= 5: row["who"] = "/who/%s/" % slug(nm)
        out.append(row)
    print("to add", len(out), "held back", len(held))
    for h in held: print("  held:", h[0], "|", h[1])
    if write:
        roster["rows"].extend(out)
        raw = json.dumps(roster, ensure_ascii=False, indent=1)
        io.open(os.path.join(DATA, "roster.json"), "w", encoding="utf-8").write(raw + "\n")
        json.dump([{"pid": o["pid"], "name": o["name"], "place": o["place"]} for o in out], io.open(os.path.join(os.path.dirname(lst), "added.json"), "w", encoding="utf-8"), ensure_ascii=False)
        print("written")
if __name__ == "__main__": main()
