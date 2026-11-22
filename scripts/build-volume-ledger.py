#!/usr/bin/env python3
"""Per-volume ledger: images read against images in each FamilySearch volume.

Reads site/src/data/searched.json (every FamilySearch row that carries a waypoint) and writes
  data/volume-ledger.json   one record per waypoint
  data/volume-ledger.csv    the same, flat, for a spreadsheet
  data/volume-ledger.md     the summary David reads

WHAT THIS IS AND IS NOT
 * The `pages` field of a searched row is free text written by many sessions over two months. This script
   PARSES it with heuristics and says how sure it is: `clean` (a bare range list such as "3-143, 150-224"),
   `keyword` (ranges taken after the words images / frames / image indexes, parentheses dropped), `all`
   ("all 187 images"), or `none` (no range could be parsed: the volume is listed with 0 images read and the
   row text is the only evidence). A parsed range is a CLAIM IN A ROW, not a verified fact.
 * "read" means the row says those images were looked at. It does not mean every entry of every image was
   read or that every cell was zoomed; `walked` is the row's own flag and is repeated, never upgraded.
 * The total (images in the volume) comes, in order, from data/volume-totals.json (the FamilySearch waypoint
   API, one call per volume, written by a browser session), then from a number the rows themselves state
   ("of 40", "132 images listed"), else it is unknown and no percentage is given.
 * Half-page references (35R) count the image once.
"""
import csv, json, re, sys, collections, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEARCHED = ROOT / "site/src/data/searched.json"
TOTALS = ROOT / "data/volume-totals.json"
ATLAS = pathlib.Path("/Volumes/DJ - Crucial - 4TB-SSD/Claude Projects/Family Projects/Record Atlas/data/fs-volumes.json")
OUT = ROOT / "data"
# the places David asked about (Senj to Istria): Atlas place ids
PLACES = ["senj","crikvenica","bakar","kraljevica","novi-vinodolski","hreljin","bribir","ledenice","draga","kastav","trsat","rijeka","volosko","lovran","jelenje","klana","pazin","pula","vodnjan","svetvincenat","liznjan","medulin","premantura","fazana","rovinj","porec","vrsar","labin","buzet","barban","novigrad"]

NUM = r"\d+[RL]?"
RANGE = rf"{NUM}(?:\s*[–\-—]\s*{NUM})?"
LIST = rf"{RANGE}(?:\s*(?:,|and|&|;)\s*{RANGE})*"
PURE = re.compile(rf"^\s*{LIST}\s*$")
KEY = re.compile(rf"(?:images?|frames?|image\s+indexes|image\s+index|imgs?)\s*:?\s*({LIST})", re.I)
ALL = re.compile(r"\ball\s+(\d+)\s+(?:images|frames)\b", re.I)
OF = re.compile(r"\b(?:of|from)\s+(\d{2,4})\b(?:[-\s]image|\s+images|\s+frames)?", re.I)
LISTS = re.compile(r"(\d{2,4})[-\s]?(?:images|frames)\b", re.I)


def ranges_from(s):
    out = []
    for part in re.split(r"\s*(?:,|and|&|;)\s*", s):
        m = re.match(r"^(\d+)[RL]?(?:\s*[–\-—]\s*(\d+)[RL]?)?$", part.strip())
        if not m:
            continue
        a = int(m.group(1)); b = int(m.group(2) or m.group(1))
        if b < a:
            a, b = b, a
        out.append((a, b))
    return out


def merge(rs):
    rs = sorted(rs)
    out = []
    for a, b in rs:
        if out and a <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def parse_pages(p):
    """-> (ranges, quality, stated_total or None)"""
    if not p:
        return [], "none", None
    p = str(p)
    orig = p
    stated = None
    m = ALL.search(p)
    if m:
        n = int(m.group(1))
        return [(0, n - 1)], "all", n
    # drop every clause that says the images were NOT read ("images 80-628 not read", "NOT yet read", "unread")
    neg = re.compile(r"not\s+(?:yet\s+)?(?:read|opened|walked|seen)|unread|not\s+on\s+the\s+(?:film|roll)", re.I)
    clauses = re.split(r"(?<=[.;])\s+|\s+[—⚠]+\s*|;", p)
    p = "; ".join(c for c in clauses if c and not neg.search(c))
    if not p.strip():
        return [], "none", None
    flat = re.sub(r"\([^)]*\)", " ", p)
    if PURE.match(flat):
        return ranges_from(flat), "clean", None
    rs = []
    for m in KEY.finditer(flat):
        rs += ranges_from(m.group(1))
    mo = OF.search(orig)
    if mo:
        stated = int(mo.group(1))
    if rs:
        return rs, "keyword", stated
    return [], "none", stated


def titles():
    t = {}
    try:
        d = json.load(open(ATLAS))
        for place, vols in (d.get("byPlace") or {}).items():
            for v in vols:
                wp = (v.get("waypoint") or "").split(":")[0]
                if wp:
                    t[wp] = {"title": v.get("t"), "place": place, "from": v.get("from"), "to": v.get("to")}
    except Exception as e:
        print("atlas titles unavailable:", e, file=sys.stderr)
    return t


def main():
    rows = json.load(open(SEARCHED))["rows"]
    totals = json.load(open(TOTALS)) if TOTALS.exists() else {}
    tl = titles()
    by = collections.OrderedDict()
    for r in rows:
        wp = (r.get("waypoint") or "").strip()
        if not wp:
            continue
        if re.search(r"[;,\s]", wp):
            for w in re.split(r"\s*[;,]\s*", wp):
                by.setdefault(w, {"rows": [], "multi": True})["rows"].append(r)
            continue
        by.setdefault(wp, {"rows": []})["rows"].append(r)
    recs = []
    for wp, v in by.items():
        rs = []; quals = []; stated = []; walked_rows = 0; notes = set(); dests = collections.Counter()
        whens = []
        for r in v["rows"]:
            rg, q, st = parse_pages(r.get("pages"))
            rs += rg; quals.append(q)
            if st: stated.append(st)
            if r.get("walked") is True: walked_rows += 1
            dests[r.get("dest") or ""] += 1
            whens.append(r.get("when", ""))
            txt = (str(r.get("pages", "")) + " " + str(r.get("what", ""))).lower()
            if re.search(r"not (?:yet )?read|unread|not opened|not walked|only [a-z ]*image", txt):
                notes.add("a row says part is unread")
        merged = merge(rs)
        # a stated total, else the largest "of N"; read can never exceed it, so clip
        tot = totals.get(wp)
        tsrc = "waypoint API" if tot else None
        if not tot and stated:
            tot = max(stated); tsrc = "stated in a row"
        read = sum(b - a + 1 for a, b in merged)
        q = "clean" if quals and all(x == "clean" for x in quals) else \
            "none" if all(x == "none" for x in quals) else "keyword/mixed"
        if v.get("multi"):
            q = "multi-volume row"; notes.add("row names several waypoints; ranges not attributed")
            merged = []; read = 0
        if tot and read > tot:
            notes.add("parsed ranges exceed the total: check the rows")
        info = tl.get(wp, {})
        recs.append({
            "waypoint": wp, "title": info.get("title"), "place": info.get("place"),
            "years": [info.get("from"), info.get("to")],
            "dest": dests.most_common(1)[0][0] if dests else "",
            "rows": len(v["rows"]), "rows_walked_true": walked_rows,
            "first": min(whens) if whens else "", "last": max(whens) if whens else "",
            "ranges_read": [[a, b] for a, b in merged], "images_read": read,
            "images_total": tot, "total_source": tsrc,
            "fraction": round(min(read, tot) / tot, 3) if tot else None,
            "parse": q, "notes": sorted(notes),
        })
    recs.sort(key=lambda x: (x["dest"] or "~", x["waypoint"]))
    OUT.mkdir(exist_ok=True)
    json.dump({"generated_from": "site/src/data/searched.json", "volumes": recs}, open(OUT / "volume-ledger.json", "w"),
              ensure_ascii=False, indent=1)
    with open(OUT / "volume-ledger.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["waypoint", "title", "dest", "years", "rows", "rows_walked_true", "images_read", "images_total",
                    "total_source", "fraction", "parse", "ranges_read", "notes"])
        for x in recs:
            w.writerow([x["waypoint"], x["title"] or "", x["dest"], "-".join(str(y) for y in x["years"] if y),
                        x["rows"], x["rows_walked_true"], x["images_read"], x["images_total"] or "", x["total_source"] or "",
                        x["fraction"] if x["fraction"] is not None else "", x["parse"],
                        "; ".join(f"{a}-{b}" for a, b in x["ranges_read"]), "; ".join(x["notes"])])
    # summary
    known = [x for x in recs if x["images_total"]]
    n_all = len(recs)
    full = [x for x in known if x["fraction"] and x["fraction"] >= 0.95]
    md = ["# Volume ledger", "",
          f"{n_all} FamilySearch volumes appear in `searched.json`; the images-in-volume total is known for {len(known)} of them.",
          f"{len(full)} of those are at 95% or more of their images by the rows' own ranges. "
          "Every figure below is parsed from free text (see the script's docstring) and is a claim in a row, not a re-count.", ""]
    md += ["| waypoint | place | volume | read / total | parse | walked-true rows | flags |", "|---|---|---|---|---|---|---|"]
    for x in recs:
        t = f"{x['images_read']} / {x['images_total']}" if x["images_total"] else f"{x['images_read']} / ?"
        fl = "; ".join(x["notes"])
        md.append(f"| {x['waypoint']} | {x['dest']} | {(x['title'] or '')[:60]} | {t} | {x['parse']} | {x['rows_walked_true']} | {fl} |")
    # places: Atlas volumes of each place against the volumes this archive has any row for
    have = {x["waypoint"]: x for x in recs}
    try:
        byplace = json.load(open(ATLAS)).get("byPlace") or {}
    except Exception:
        byplace = {}
    md += ["", "## By place: how many of the Atlas's FamilySearch volumes have any row at all", "",
           "A volume with a row is not a volume read; a volume with no row has not been opened by this archive. "
           "Images are from the FamilySearch waypoint API where `data/volume-totals.json` has the volume, else unknown. **Only this archive's `searched.json` is read**: a place with no row here (Senj, for one) may have been read by another family archive (Blažević, Kosina), which this ledger does not see. Volumes that bundle several books (a waypoint is one roll) count every image of the roll.", "",
           "| place | volumes in the Atlas | with a row | no row | images in no-row volumes | images read in rowed volumes / images in them |", "|---|---|---|---|---|---|"]
    untouched = []
    for pl in PLACES:
        vols = byplace.get(pl) or []
        wps = []
        for v in vols:
            w = (v.get("waypoint") or "").split(":")[0]
            if w and w not in wps:
                wps.append(w)
        if not wps:
            continue
        rowed = [w for w in wps if w in have]
        norow = [w for w in wps if w not in have]
        n_no = sum(totals.get(w, 0) for w in norow)
        unk = sum(1 for w in norow if w not in totals)
        r_read = sum(min(have[w]["images_read"], have[w]["images_total"] or have[w]["images_read"]) for w in rowed)
        r_tot = sum(have[w]["images_total"] or 0 for w in rowed)
        md.append(f"| {pl} | {len(wps)} | {len(rowed)} | {len(norow)} | {n_no}{' (+%d unknown)' % unk if unk else ''} | {r_read} / {r_tot} |")
        for w in norow:
            info = tl.get(w, {})
            untouched.append({"place": pl, "waypoint": w, "title": info.get("title"), "years": [info.get("from"), info.get("to")],
                              "images_total": totals.get(w)})
    md += ["", "## Volumes with no row, by place", "", "| place | waypoint | volume | years | images |", "|---|---|---|---|---|"]
    for u in untouched:
        md.append(f"| {u['place']} | {u['waypoint']} | {(u['title'] or '')[:60]} | {'-'.join(str(y) for y in u['years'] if y)} | {u['images_total'] or '?'} |")
    json.dump({"generated_from": "site/src/data/searched.json", "volumes": recs, "no_row": untouched},
              open(OUT / "volume-ledger.json", "w"), ensure_ascii=False, indent=1)
    open(OUT / "volume-ledger.md", "w").write("\n".join(md) + "\n")
    print(f"{n_all} volumes; totals known {len(known)}; parse clean {sum(1 for x in recs if x['parse']=='clean')}, "
          f"keyword/mixed {sum(1 for x in recs if x['parse']=='keyword/mixed')}, none {sum(1 for x in recs if x['parse']=='none')}")


if __name__ == "__main__":
    main()
