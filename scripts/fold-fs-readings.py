#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fold FamilySearch record-page readings into the roster rows added from the MyHeritage placeholder branch (16 Nov 2026).

    python3 scripts/fold-fs-readings.py <records.json> <links.json> [--write]

records.json: {ark: page text | "RESTRICTED"} read from the signed-in browser pane (a same-origin iframe per ark, main.innerText).
links.json:   [[pid, name, ark], ...] the FamilySearch links of the rows (from the roster notes).
Only the rows whose note still carries the «Not yet read here» sentence are touched. What the index record states is written as the
record's words (an index entry, grade doc for what it says, the image not opened); the tree's year is kept in the note where the two
differ. A record's year replaces the row's b / d only where the record gives it and the row disagrees or is empty (the pid is frozen).
"""
import json, re, sys, unicodedata

ROSTER = "site/src/data/roster.json"
MARK = re.compile(r"\*\*Not yet read here:\*\*[^*]*?until it is\.")


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def blocks(t):
    """[(indexed name, {field: value})] from the «X person details» blocks."""
    lines = [x.strip() for x in t.split("\n")]
    out = []
    idx = [i for i, x in enumerate(lines) if x.endswith(" person details")]
    for n, i in enumerate(idx):
        name = lines[i][: -len(" person details")]
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        d = {}
        j = i + 1
        while j < end:
            k = lines[j]
            if k in ("Name", "Sex", "Age", "Birth Date", "Birthplace", "Birth Place", "Death Date", "Death Place", "Event Type", "Event Date",
                     "Event Place", "Marital Status", "Occupation", "Burial Date", "Burial Place", "Residence Place", "Arrival Date",
                     "Marriage Date", "Spouse", "Event Place (Original)", "Page Number"):
                for y in lines[j + 1: j + 5]:
                    if y:
                        d.setdefault(k, y)
                        break
            j += 1
        out.append((name, d))
    return out


def rels(t):
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"^([^\t\n]+)\t(Father|Mother|Husband|Wife|Spouse)\t", t, re.M)]


def coll(t):
    m = re.search(r"^(.+?) • (.+)$", t, re.M)
    ev = None
    for ln in t.split("\n"):
        if " • " in ln and not ln.startswith(("Records",)):
            ev = ln.strip()
            break
    return ev or ""


def yr(s):
    m = re.findall(r"\b(1[5-9]\d\d|20[0-2]\d)\b", s or "")
    return int(m[-1]) if m else None


def pick(bl, name):
    toks = set(fold(name).replace("-", " ").split())
    best, sc = None, -1
    for k, (n, d) in enumerate(bl):
        s = len(toks & set(fold(n).replace("-", " ").split())) * 10 - k
        if s > sc:
            best, sc = (n, d, k), s
    return best


def main():
    recs = json.load(open(sys.argv[1], encoding="utf-8"))
    links = json.load(open(sys.argv[2], encoding="utf-8"))
    write = "--write" in sys.argv
    roster = json.load(open(ROSTER, encoding="utf-8"))
    rows = {r["pid"]: r for r in roster["rows"]}
    per = {}
    for pid, name, ark in links:
        per.setdefault(pid, []).append(ark)
    report = {"read": 0, "restricted": 0, "unloaded": 0, "image": 0, "b_changed": [], "d_changed": [], "b_filled": 0, "d_filled": 0}
    for pid, arks in per.items():
        r = rows[pid]
        if not MARK.search(r.get("note", "")):
            continue
        parts, anyread = [], False
        for a in arks:
            if a.startswith("3:1"):
                report["image"] += 1
                continue
            t = recs.get(a)
            if t is None:
                report["unloaded"] += 1
                parts.append("one FamilySearch page did not load on 16 November 2026 and is not read")
                continue
            if t == "RESTRICTED":
                report["restricted"] += 1
                parts.append("FamilySearch withholds one of the cited records from this account («can only be displayed on certain accounts»), so it is not read")
                continue
            bl = blocks(t)
            if not bl:
                report["unloaded"] += 1
                continue
            n, d, k = pick(bl, r["name"])
            report["read"] += 1
            anyread = True
            ev = coll(t)
            bits = []
            if n and fold(n) != fold(r["name"]):
                bits.append("indexed as «%s»" % n)
            if d.get("Birth Date") and "Birth Year (Estimated)" in t:
                bits.append("age %s, so the index estimates birth about %s (an estimate, not a recorded date)" % (d.get("Age", "?"), d["Birth Date"]))
            elif d.get("Birth Date"):
                by = d["Birth Date"]
                bits.append("born %s%s" % (by, (" at " + (d.get("Birthplace") or d.get("Birth Place"))) if (d.get("Birthplace") or d.get("Birth Place")) else ""))
            if d.get("Age") and not d.get("Birth Date"):
                bits.append("age %s" % d["Age"])
            et = d.get("Event Type")
            ed = d.get("Event Date")
            ep = d.get("Event Place") or d.get("Event Place (Original)")
            if et or ed or ep:
                bits.append("%s%s%s" % ((et + " ") if et else "", ed or "", (" at " + ep) if ep else ""))
            if d.get("Death Date"):
                bits.append("died %s%s" % (d["Death Date"], (" at " + d["Death Place"]) if d.get("Death Place") else ""))
            if d.get("Marital Status"):
                bits.append(d["Marital Status"].lower())
            if d.get("Occupation"):
                bits.append("occupation " + d["Occupation"].lower())
            if k == 0:
                rl = rels(t)
                if rl:
                    bits.append("on the record with " + ", ".join("%s (%s)" % (x, y.lower()) for x, y in rl[:4]))
            else:
                bits.append("named on another person's record (the primary person there is «%s»)" % bl[0][0])
            parts.append("«%s»: %s" % (ev, "; ".join(bits)))
            # years
            ry = yr(d.get("Birth Date"))
            if ry and "Birth Year (Estimated)" not in t:
                if r.get("b") is None:
                    r["b"] = ry
                    report["b_filled"] += 1
                elif r["b"] != ry:
                    parts.append("**the tree has %s, the record %s**" % (r["b"], ry))
                    report["b_changed"].append((pid, r["b"], ry))
                    r["b"] = ry
            if et and "Death" in (et or "") and yr(ed):
                dy = yr(ed)
                if r.get("d") is None:
                    r["d"] = dy
                    report["d_filled"] += 1
                elif r["d"] != dy:
                    parts.append("**the tree has %s, the record %s**" % (r["d"], dy))
                    report["d_changed"].append((pid, r["d"], dy))
                    r["d"] = dy
        if parts:
            if anyread:
                new = ("**Read on FamilySearch, 16 November 2026 (an index record, not the page image):** " + " | ".join(parts) +
                       ". The index is a transcription: it is the record's own word for these facts (doc), and any link to a parent, spouse or line stays the tree's word (lore) until the image is read.")
            else:
                new = "**Not read:** " + "; ".join(parts) + "; the name, years and place stay the tree's word (lore)."
            r["note"] = MARK.sub(lambda m: new, r["note"], 1)
    print(json.dumps(report, ensure_ascii=False))
    if write:
        with open(ROSTER, "w", encoding="utf-8") as f:
            json.dump(roster, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("written")


main()
