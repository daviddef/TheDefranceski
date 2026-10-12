#!/usr/bin/env python3
"""Say WHICH ROSTER ROW each person on /households/ is, so the page can link them.

Until 12 October 2026 the households page drew every parent and child as plain
text. The kit's Households card already takes `headHref`, `spouseHref` and a
per-child `href`; nothing gave it one. This writes them as DATA, beside the
person they name, so a link is a stated claim in the file and not a guess made
at render time:

    child  : "pid", "pidBasis"
    couple : "fatherPid", "motherPid", "pidBasis_father", "pidBasis_mother"

THE RULES ARE STRICT ON PURPOSE. A wrong link says two records are one person,
which is worse than a missing link. A household parent carries no birth year,
so «same name» alone is not a match — «Leonardus Defranceschi» is three roster
rows. A link is made only when it is one of:

  CHILDREN
    fsid        the child's FamilySearch id appears in exactly one roster row
    name+year   the same name and the same birth year, exactly one row
    name+place  the same name, the roster row has NO birth year, and its parish
                is the child's — exactly one row

  PARENTS (no date of their own, so a date is inferred from the children)
    exact+place    the same normalised name AND the roster row is at the household's
                   place AND, if the row has a birth year, it fits the first child
                   (father 18–60, mother 16–50 at the first birth); exactly ONE row
                   passes. A unique name alone is NOT enough: the roster is
                   incomplete, so one same-named row can be a different man.
    variant+place  the same, through a forename variant (Joan. Bapt. = Giovanni
                   Battista) when no row has the exact name

Anything else is left unlinked and listed. It NEVER overwrites a pid already in
the file, so a hand-made link survives a re-run.

    scripts/link-household-people.py            # report only
    scripts/link-household-people.py --write    # fill the pids
"""
import json, io, re, sys, os, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HH = os.path.join(ROOT, "site/src/data/households.json")
RO = os.path.join(ROOT, "site/src/data/roster.json")


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s)


def norm(s):
    return fold(s).replace(" ", "")


def base_name(s):
    return re.sub(r"\(.*?\)|,.*$|\bq\.?m?\.?\s.*$|\bdef\S*\s.*$", "", s or "").strip()


def year(s):
    m = re.search(r"(1[5-9]\d\d|20\d\d)", str(s or ""))
    return int(m.group(1)) if m else None


# forename variants: the same man written by different scribes and indexers
FORE = {}
for group in (
    "giovanni gioannis joannes johannes joan joannis gio giovan zuane zuanne gian johann joannem",
    "giuseppe josephus josef joseph iosephus",
    "antonio antonius anto antoni",
    "francesco franciscus francisci",
    "nicolo niccolo nicolaus nicola nicolai",
    "pietro petrus piero",
    "matteo matheus mathaeus mattheus matthaeus mattio",
    "stefano stephanus",
    "gregorio gregorius gregorii",
    "leonardo leonardus",
    "giacomo jacobus jacobo iacobus",
    "alvise aloysius alois luigi lodovico ludovicus",
    "domenico dominicus dominico",
    "vittorio victorius valentinus valentin valentini",
    "pasqua pascha pasquale paschalis",
    "caterina catharina catterina catherina",
    "maria mariae",
    "lucia luciae",
    "giovanna joanna gioanna",
    "margherita margarita margaritha margaritta",
    "francesca francisca francisce",
    "elena helena ellena",
    "orsola ursula ursulae",
):
    toks = group.split()
    for t in toks:
        FORE[t] = toks[0]


def forename_key(name):
    t = fold(base_name(name)).split()
    if not t:
        return ""
    # «Gio Battista», «Joan. Bapt.» — two-word given names
    two = " ".join(t[:2])
    if two in ("gio battista", "gio batta", "joan bapt", "joannes baptista", "giovanni battista", "gio bta"):
        return "giovanni-battista"
    return FORE.get(t[0], t[0])


def surname_key(name):
    t = fold(base_name(name)).split()
    return norm(" ".join(t[-2:])) if len(t) > 1 else ""


def main():
    write = "--write" in sys.argv
    hh = json.load(io.open(HH, encoding="utf-8"))
    ro = json.load(io.open(RO, encoding="utf-8"))["rows"]

    by_id = collections.defaultdict(set)
    by_name = collections.defaultdict(list)
    for r in ro:
        blob = json.dumps([r.get(k) for k in ("ark", "arks", "mh", "imageArk", "sameAs")])
        for i in set(re.findall(r"[0-9A-Z]{4}-[0-9A-Z]{3,4}", blob)):
            by_id[i].add(r["pid"])
        by_name[norm(r["name"])].append(r)
        b = norm(base_name(r["name"]))
        if b != norm(r["name"]):
            by_name[b].append(r)
    byp = {r["pid"]: r for r in ro}

    stats = collections.Counter()
    unlinked = []

    for h in hh:
        hid = h.get("id") or h.get("key")
        hplace = fold((h.get("place") or "").split(",")[0].split("(")[0])
        first = min([year(c.get("birth")) for c in h.get("children", []) if year(c.get("birth"))] or [year(h.get("from"))] or [None] or [None], default=None)
        # ---- children
        for c in h.get("children", []):
            if c.get("pid"):
                stats["child kept"] += 1
                continue
            pid = basis = None
            cid = c.get("id")
            if cid and len(by_id.get(cid, ())) == 1:
                pid, basis = next(iter(by_id[cid])), "fsid"
            if not pid:
                y = year(c.get("birth"))
                same = [r for r in by_name.get(norm(c["name"]), []) if y and year(r.get("b")) == y]
                if len(same) == 1:
                    pid, basis = same[0]["pid"], "name+year"
            if not pid:
                cplace = fold((c.get("place") or "").split(",")[0].split("(")[0])
                same = [r for r in by_name.get(norm(c["name"]), [])
                        if r.get("b") is None and cplace and cplace[:5] in fold(r.get("parish") or r.get("place") or "")]
                if len(same) == 1:
                    pid, basis = same[0]["pid"], "name+place"
            if pid:
                stats["child linked:" + basis] += 1
                if write:
                    c["pid"], c["pidBasis"] = pid, basis
            else:
                stats["child unlinked"] += 1
                unlinked.append((hid, "child", c["name"], c.get("birth")))

        # ---- parents
        for role, key, lo, hi in (("father", "fatherPid", 18, 60), ("mother", "motherPid", 16, 50)):
            nm = (h.get(role) or "").strip()
            if not nm or h.get(key):
                stats["parent kept/none"] += 1
                continue
            pid = basis = None
            exact = by_name.get(norm(nm), []) or by_name.get(norm(base_name(nm)), [])
            exact = list({r["pid"]: r for r in exact}.values())
            pool, kind = (exact, "exact") if exact else ([], "variant")
            if not exact:
                fk, sk = forename_key(nm), surname_key(nm)
                pool = [r for r in ro if forename_key(r["name"]) == fk and surname_key(r["name"]) == sk]

            # A UNIQUE NAME IS NOT EVIDENCE. The roster is incomplete, so one same-named row
            # can still be a different man. Every link needs POSITIVE place evidence and an
            # age that fits the first child; the name only decides which rows are considered.
            def ok(r):
                if not hplace or hplace[:5] not in fold(r.get("parish") or r.get("place") or ""):
                    return False
                rb = year(r.get("b"))
                return rb is None or (first is not None and lo <= first - rb <= hi)
            passing = [r for r in pool if ok(r)]
            if len(passing) == 1:
                pid, basis = passing[0]["pid"], kind + "+place"
            exact = pool
            if pid:
                stats[f"{role} linked:{basis}"] += 1
                if write:
                    h[key], h["pidBasis_" + role] = pid, basis
            else:
                n = len(exact)
                stats[f"{role} unlinked"] += 1
                unlinked.append((hid, role, nm, f"{n} same-named rows" if n > 1 else "no match"))

    print("link-household-people:", "WRITING" if write else "report only")
    for k, v in sorted(stats.items()):
        print(f"  {v:5}  {k}")
    ambiguous = [u for u in unlinked if "same-named" in str(u[3])]
    print(f"\n  unlinked parents with several same-named rows (ambiguous, left alone): {len(ambiguous)}")
    for u in ambiguous[:40]:
        print("    ", u)
    if write:
        io.open(HH, "w", encoding="utf-8").write(json.dumps(hh, indent=1, ensure_ascii=False))
        print("\n  households.json written")
    json.dump(unlinked, open(os.environ.get("UNLINKED_OUT", os.devnull), "w"), ensure_ascii=False, indent=1) if os.environ.get("UNLINKED_OUT") else None


main()
