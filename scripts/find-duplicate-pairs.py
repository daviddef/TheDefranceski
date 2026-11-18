#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pairs of roster rows that may be ONE person held twice, for David to join (or to say are two people).

    python3 scripts/find-duplicate-pairs.py [--out DIR]        # default private/duplicate-pairs-<today>/

Reads site/src/data/roster.json and dossiers.json (to leave out a parent, child or spouse of the other) and the Record Atlas's two catalogues
(data/given-name-families.json, data/surname-families.json: forms of status same / attested / rule only; a lead is never a match). Writes ONLY under private/:
pairs.csv (one row per pair), groups.csv (pairs that chain, e.g. three rows of one man), REPORT.md.

THE RULE (the same as the Tree Canvas's «possible duplicates» badge, Record Atlas PR 78, plus what a roster row has that a tree card does not):
  * both rows have a birth year and it is the SAME year; neither is a living or window-born person with no death recorded;
  * the first given name is the same, or one family of the Atlas given-name catalogue (Antonio / Antonius);
  * a surname word is the same, or one family of the Atlas surname catalogue (Defranceschi / De Franceschi / Defranceski); a particle (de, di, da ...) is not a word;
  * if both have a death year they are within 2 years of each other;
  * neither is the other's parent, child or spouse in the dossiers.
A pair is TIER A when the given name is written the same, the birth place is the same or one is missing, and the death years agree or one is missing; everything else that passes is
TIER B (a given name only through the catalogue, or birth places that differ). NOTHING HERE IS A FINDING: two rows of one name and one birth year are a lead, and joining two rows
changes a page id (ids are minted once and frozen), so a join is David's decision, made pair by pair, against the records. «mh» says the two rows carry different tree ids, i.e. the tree
itself holds them as two people.
"""
import sys, os, io, re, csv, json, datetime, unicodedata, collections, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "src", "data")
ATLAS = os.environ.get("RECORD_ATLAS") or "/Volumes/DJ - Crucial - 4TB-SSD/Claude Projects/Family Projects/Record Atlas"
CUTOFF = datetime.date.today().year - 80

def fold(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]+", " ", s).strip()
def sq(s): return fold(s).replace(" ", "")
PART = {"de", "di", "da", "del", "della", "dei", "degli", "von", "van", "vd", "d", "la", "le", "du", "des"}
OK = {"same", "attested", "rule"}

def families(path):
    idx = collections.defaultdict(set)
    for fam in json.load(io.open(path, encoding="utf-8"))["families"]:
        forms = [fam.get("name")] + [m["form"] for m in fam.get("members", []) if m.get("status") in OK]
        for f in forms:
            if f: idx[sq(f)].add(fam["id"])
    return idx

def year(v):
    try: return int(str(v).strip()[:4])
    except Exception: return None

def parse(name):
    """given (first word) and the surname words: those of the text before the first « ( », « , » or « wife of », plus the ones inside the first bracket."""
    n = re.sub(r"\bwife of\b.*$", "", str(name or ""), flags=re.I)
    head = re.split(r"[(,]", n, 1)[0]
    inside = re.findall(r"\(([^)]*)\)", n)
    toks = [t for t in fold(head).split() if t]
    if not toks: return "", set()
    given, rest = toks[0], toks[1:]
    words = {t for t in rest if t not in PART and len(t) > 2}
    for ins in inside[:1]:
        words |= {t for t in fold(ins).split() if t not in PART and len(t) > 2 and not re.fullmatch(r"b|d|born|died|wife|daughter|son|of", t)}
    if len(rest) > 1: words.add("".join(rest))
    return given, words

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); a = ap.parse_args()
    out = a.out or os.path.join(ROOT, "private", "duplicate-pairs-" + datetime.date.today().isoformat())
    os.makedirs(out, exist_ok=True)
    GN = families(os.path.join(ATLAS, "data", "given-name-families.json"))
    SN = families(os.path.join(ATLAS, "data", "surname-families.json"))
    rows = json.load(io.open(os.path.join(DATA, "roster.json"), encoding="utf-8"))["rows"]
    dos = json.load(io.open(os.path.join(DATA, "dossiers.json"), encoding="utf-8")).get("persons", {})
    rel = collections.defaultdict(set)   # pid -> pids of a parent, child or spouse
    for pid, v in dos.items():
        t = v.get("ptree") or {}
        for q in (t.get("parents") or []) + (t.get("children") or []) + ([t["spouse"]] if t.get("spouse") else []):
            if q.get("pid"): rel[pid].add(q["pid"]); rel[q["pid"]].add(pid)
    people, buckets = {}, collections.defaultdict(list)
    for r in rows:
        pid = r.get("pid"); b, d = year(r.get("b")), year(r.get("d"))
        if not pid or b is None: continue
        if d is None and b >= CUTOFF: continue                     # living or window-born, no death recorded: never listed
        given, words = parse(r.get("name"))
        if len(given) < 3 or not words: continue
        gk = {given} | {x for fam in GN.get(given, ()) for x in [fam]}
        sk = set(words) | {("fam:" + f) for w in words for f in SN.get(w, ())}
        people[pid] = dict(r=r, b=b, d=d, given=given, gfam=set(GN.get(given, ())), words=words, sfam={f for w in words for f in SN.get(w, ())},
                           place=fold(str(r.get("place") or "").split(",")[0]))
        buckets[b].append(pid)
    pairs = []
    for b, ids in buckets.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                A, B = people[ids[i]], people[ids[j]]
                if ids[j] in rel.get(ids[i], ()): continue
                gexact = A["given"] == B["given"]; gfam = bool(A["gfam"] & B["gfam"])
                if not (gexact or gfam): continue
                sexact = bool(A["words"] & B["words"]); sfam = bool(A["sfam"] & B["sfam"])
                if not (sexact or sfam): continue
                if A["d"] is not None and B["d"] is not None and abs(A["d"] - B["d"]) > 2: continue
                pl = "same" if A["place"] and A["place"] == B["place"] else ("unknown" if not A["place"] or not B["place"] else "differ")
                dd = "same" if A["d"] is not None and A["d"] == B["d"] else ("unknown" if A["d"] is None or B["d"] is None else "close")
                tier = "A" if gexact and pl != "differ" else "B"
                why = ["same birth year", "same given name" if gexact else "one given name in the Atlas catalogue (%s / %s)" % (A["given"], B["given"]),
                       "same surname word" if sexact else "one surname in the Atlas catalogue"]
                if pl == "same": why.append("same birthplace")
                elif pl == "differ": why.append("birthplaces differ")
                if dd == "same": why.append("same death year")
                elif dd == "close": why.append("death years within 2")
                ra, rb = A["r"], B["r"]
                mh = "different tree ids" if ra.get("mh") and rb.get("mh") and ra["mh"] != rb["mh"] else ""
                pairs.append(dict(tier=tier, birth=b, a_pid=ra["pid"], a_name=ra["name"], a_d=ra.get("d") or "", a_place=ra.get("place") or "", a_src=ra.get("src") or "",
                                  b_pid=rb["pid"], b_name=rb["name"], b_d=rb.get("d") or "", b_place=rb.get("place") or "", b_src=rb.get("src") or "",
                                  why="; ".join(why), tree=mh))
    pairs.sort(key=lambda p: (p["tier"], p["birth"], p["a_name"]))
    # groups: pairs that chain
    par = {}
    def f(x):
        par.setdefault(x, x)
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for p in pairs: par[f(p["a_pid"])] = f(p["b_pid"])
    grp = collections.defaultdict(set)
    for p in pairs: grp[f(p["a_pid"])].update([p["a_pid"], p["b_pid"]])
    with io.open(os.path.join(out, "pairs.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pairs[0].keys()) if pairs else ["tier"]); w.writeheader(); w.writerows(pairs)
    with io.open(os.path.join(out, "groups.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["size", "pids", "names"])
        for g in sorted(grp.values(), key=lambda g: -len(g)):
            w.writerow([len(g), " | ".join(sorted(g)), " | ".join(people[x]["r"]["name"] for x in sorted(g))])
    nA = sum(1 for p in pairs if p["tier"] == "A"); big = [g for g in grp.values() if len(g) > 2]
    L = ["# Pairs of roster rows that may be one person (%s)" % datetime.date.today().isoformat(), "",
         "Rows with a birth year in `roster.json`: %d (living or window-born without a death left out). **%d pairs** (tier A %d, tier B %d) in %d groups; %d groups hold three rows or more." % (len(people), len(pairs), nA, len(pairs) - nA, len(grp), len(big)),
         "", "A lead, never a finding: the same first name (or one Atlas family), a surname word (or Atlas family) and one birth year. Joining changes a page id, so each is David's call.", "",
         "## Tier A (given name written the same, birthplace not contradicted, deaths agree or one missing)", ""]
    for p in [p for p in pairs if p["tier"] == "A"][:120]:
        L.append("- %d: **%s** (/person/%s/) and **%s** (/person/%s/): %s%s" % (p["birth"], p["a_name"][:60], p["a_pid"], p["b_name"][:60], p["b_pid"], p["why"], ("; " + p["tree"]) if p["tree"] else ""))
    L += ["", "Tier B and the full list are in pairs.csv; groups of three or more in groups.csv."]
    io.open(os.path.join(out, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("rows considered %d; pairs %d (A %d, B %d); groups %d (3+ rows: %d); written to %s" % (len(people), len(pairs), nA, len(pairs) - nA, len(grp), len(big), out))

if __name__ == "__main__":
    main()
