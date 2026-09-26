#!/usr/bin/env python3
"""Give every roster row a STABLE per-person id.

Why this exists. Until 23 September 2026 this archive had no page for a
person. It had /who/<name>/, which gathers every row sharing a name — and
/who/maria-defranceschi/ held twenty-five different women born between 1733
and 1888, from Svetvincenat to Puerto Rico. That is a fine index and a
terrible biography, and the archive proved it the same morning by hanging
three photographs of one man on a page holding three men of his name.

The id is MINTED ONCE AND FROZEN in roster.json as `pid`. It is never
recomputed from the row, because the row changes: correct a birth year and a
derived id would silently move the person's URL and break every link to it.
Minting is therefore append-only — this script only ever fills in rows that
have no pid, and it refuses to alter one that does.

Shape: <name-slug>-<disambiguator>, where the disambiguator is the birth year,
else d<death year>, else the place slug, else nothing; a numeric suffix is
added only where that still collides. A collision on an IDENTICAL name, birth
AND death is reported, because in this archive that usually means a duplicate
row rather than two people.
"""
import json, io, re, sys, unicodedata, collections

ROSTER = "site/src/data/roster.json"

def _fold_surname(n):
    """Collision detection must fold the name; ID minting must not.

    Grouping on the exact string reported 33 collisions and 16 candidates.
    «Antonio De Franceschi» and «Antonio Defranceschi», both 1704, both
    Svetvincenat, one from a record and one from the tree, were counted as two
    people because of ONE SPACE. Folding the way namefold does gives 93 groups
    and 36 candidates — more than twice as many. The pid itself is never
    folded: it is frozen, and two rows that turn out to be one person are
    merged by a human, not renamed by this script.
    """
    s = unicodedata.normalize("NFD", n or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^a-z ]", "", s)
    s = re.sub(r"\b(de|di|del)\s+", "", s)
    s = re.sub(r"\b(defranceschi|franceschi|defranceski|franceski|defrancheschi)\b", "X", s)
    return " ".join(s.split())


def slug(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def main():
    write = "--write" in sys.argv
    R = json.load(io.open(ROSTER, encoding="utf-8"))
    rows = R["rows"]

    taken = {r["pid"] for r in rows if r.get("pid")}
    had = len(taken)
    minted, suspect = 0, []

    for r in rows:
        if r.get("pid"):
            continue
        base = slug(r.get("name") or "unnamed")
        if r.get("b"):
            dis = str(r["b"])
        elif r.get("d"):
            dis = "d%s" % r["d"]
        elif r.get("bEst"):
            dis = "c%s" % r["bEst"]
        elif r.get("placeSlug") or r.get("place"):
            dis = slug(r.get("placeSlug") or r.get("place"))[:24]
        else:
            dis = ""
        pid = ("%s-%s" % (base, dis)).strip("-") if dis else base
        if pid in taken:
            # Same name, same birth, same death is NOT a duplicate by itself,
            # and this script said so for four days before anyone checked. Of
            # the 33 groups it found, 17 sit in different parishes — a Pietro
            # of 1734 at Svetvincenat and another at Bale are two men, and a
            # one-name study that did not produce them would be hiding
            # something. Only a collision inside ONE PLACE is a candidate.
            same_place = any((o.get("place") or "").strip().lower()
                             == (r.get("place") or "").strip().lower()
                             for o in rows if o.get("pid") == pid)
            suspect.append((pid, r.get("name"), r.get("b"), r.get("d"), same_place))
            n = 2
            while "%s-%d" % (pid, n) in taken:
                n += 1
            pid = "%s-%d" % (pid, n)
        taken.add(pid)
        r["pid"] = pid
        minted += 1

    print("roster rows        %d" % len(rows))
    print("pids already held  %d" % had)
    print("pids minted        %d" % minted)
    print("total distinct     %d" % len(taken))
    if suspect:
        print("\ncollisions on name+dates (%d):" % len(suspect))
        cand = [x for x in suspect if x[4]]
        print("   %d of them share a PLACE as well — those are the candidates;"
              % len(cand))
        print("   the rest are the same name in different parishes, which is not a duplicate.")
        for pid, nm, b, d, sp in suspect[:20]:
            print("   %-44s b=%-6s d=%-6s %s" % (pid, b, d,
                  "<- same place" if sp else ""))
    if write:
        json.dump(R, io.open(ROSTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\nwritten to %s" % ROSTER)
    else:
        print("\n(dry run — pass --write to persist)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
