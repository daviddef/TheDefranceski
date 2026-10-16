#!/usr/bin/env python3
"""Give a roster row — and so a page — to every person on /households/ who has none.

Run AFTER scripts/link-household-people.py, which links everyone it can PROVE is
already on the roster. What is left over falls into three groups:

  OTHER-SURNAME PARENTS   the husbands and wives of the name — «Francesco Vellico»,
                          «Catterina Vlahovich» — plus mothers recorded by forename
                          only («Lutia», «Marta»)
  DAUGHTERS' CHILDREN     children of a Defranceschi woman who carry another family's
                          surname — the half of the family the surname loses
  BARE GIVEN NAMES        «Petrus», «Josephus» under a father who bears the name; the
                          surname is the father's and is supplied here

NOT MINTED, and deliberately: a child whose OWN name already bears the surname and
who could not be linked. Their same-named roster rows are probably the same person
and a wrong mint puts two people where there is one. Those stay unlinked, listed.

Every row says, in its own note, that it is index-only or read, what the page
actually prints about the person, and that nothing else is claimed. A person born
80 years ago or less, with no death recorded, is named with a town and country and nothing more (the living
rule, the estate's one definition); a child is not minted at all. The minted row is linked
back into households.json as it is made, so the link is by construction, not by
guess.

    scripts/mint-household-people.py            # report
    scripts/mint-household-people.py --write    # append rows + link, then run
                                                # scripts/mint-person-ids.py --write
"""
import json, io, re, sys, os, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_v2 as L2          # who is living, and who is held out, is the estate's one rule
HH = os.path.join(ROOT, "site/src/data/households.json")
RO = os.path.join(ROOT, "site/src/data/roster.json")
PL = os.path.join(ROOT, "site/src/data/places.json")

BEARS = re.compile(r"(franc|franz|frances)", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s)


def norm(s):
    return fold(s).replace(" ", "")


def year(s):
    m = re.search(r"(1[5-9]\d\d|20\d\d)", str(s or ""))
    return int(m.group(1)) if m else None


PART = {"de", "di", "degli", "dei", "del", "della", "van", "von", "da"}


def surname_of(name):
    """The family name of a PARENT, for supplying to a child recorded by given name only.
    «Gio Batta De Franceschi» -> «De Franceschi», «Francesco Vellico» -> «Vellico».
    Returns "" when the name carries no surname (forename only)."""
    t = re.sub(r"\(.*?\)|,.*$|\bq\.?m?\.?\s.*$", "", name or "").split()
    # a title or occupation written after the name is not part of it
    while t and t[-1].lower().strip(".") in {"regii", "regius", "cives", "civis", "agricola", "agr", "op"}:
        t.pop()
    if len(t) < 2:
        return ""
    for i, w in enumerate(t[1:], 1):
        if w.lower() in PART:
            return " ".join(t[i:])
    for i, w in enumerate(t[1:], 1):
        if BEARS.search(w):
            return " ".join(t[i:])
    return t[-1]


def first_place(p):
    return fold((p or "").split(",")[0].split("(")[0]).strip()


def main():
    write = "--write" in sys.argv
    hh = json.load(io.open(HH, encoding="utf-8"))
    ro = json.load(io.open(RO, encoding="utf-8"))
    rows = ro["rows"]
    pl = json.load(open(PL))
    pk = set(pl.keys()) if isinstance(pl, dict) else {p.get("slug") for p in pl}
    byname = collections.defaultdict(list)
    for r in rows:
        byname[norm(r["name"])].append(r)

    new, seen = [], {}      # seen: dedupe key -> index in `new`
    st = collections.Counter()
    YEAR = L2.THIS_YEAR

    def slugplace(p):
        k = first_place(p).replace(" ", "-")
        return k if k in pk else None

    def make(name, b, place, ark, note, living=False):
        row = {"name": name, "b": None if living else b, "d": None, "place": place or None,
               "src": "household", "href": "/households/", "note": note, "notable": False,
               "ark": ark or "", "mh": "", "line": "unplaced"}
        if place:
            row["parish"] = place.split(",")[0].split("(")[0].strip()
        sp = slugplace(place)
        if sp:
            row["placeSlug"] = sp
        if living:
            row["living"] = True
        return row

    # ------------------------------------------------------------ parents
    for h in hh:
        hid = h.get("id") or h.get("key")
        lab = ("household " + str(hid)) if re.match(r"^h\d+$", str(hid)) else ("the «" + str(hid) + "» household")
        place = (h.get("place") or "").strip()
        place = None if place in ("", "—") else place
        cls = ("**read — from registers this archive has read**" if h.get("src") == "read"
               else "**index only — no register has been read**")
        kids = "; ".join(c["name"] for c in h.get("children", [])[:4]) or "no recorded children"
        for role, key, other in (("father", "fatherPid", "mother"), ("mother", "motherPid", "father")):
            nm = (h.get(role) or "").strip()
            if not nm or h.get(key) or BEARS.search(nm):
                continue
            spouse = (h.get(other) or "").strip()
            forename_only = len(nm.split()) == 1
            # The same other-surname parent in two households is ONE person when the partner has
            # the same forename (Luca Franceschi / Luca Franceschi Raschich) or the archive's own
            # data says the two households are one under two readings (nearDup).
            near = set(h.get("nearDup") or [])
            sp_key = norm(fold(spouse).split()[0]) if spouse else ""
            dk = ("P", norm(nm), first_place(place), sp_key)
            if dk not in seen:
                for k2, v2 in seen.items():
                    if k2[0] == "P" and k2[1] == norm(nm) and k2[2] == first_place(place) \
                       and any(x in near or (x2 in (v2["hids"]) ) for x in v2["hids"] for x2 in near):
                        dk = k2
                        break
            if dk in seen:
                seen[dk]["hids"].append(hid)
                seen[dk]["households"].append(h)
                seen[dk]["slots"].append((hid, key))
                st["parent: same person in a second household"] += 1
                continue
            husband = role == "father"
            if BEARS.search(spouse):
                rel = (f"the **{'husband' if husband else 'wife'}** of **{spouse}**, a De Franceschi, "
                       f"and the {'father' if husband else 'mother'} of {kids}")
                scope = (" **Not of the name's surname** — kept because the person married into it; "
                         "the household list gives the couple and nothing about their origin.")
            else:
                rel = f"the **{'father' if husband else 'mother'}** of {kids}"
                scope = (" **Neither parent of this household bears the name**: the archive's Gologorica "
                         "sweep recorded the family beside it, for the Grah wives of the 1862 census.")
            ident = (" **Recorded by forename only** — no surname is printed, so this is a name and a role "
                     "and cannot be told apart from another woman of the same forename by anything on the page."
                     if forename_only else "")
            note = (f"Named in {lab} on [the households list](/households/)"
                    + (f", at {place}" if place else "") + f", as {rel}. Evidence class: {cls}. "
                    "No birth, death or occupation is printed for this person, so none is claimed."
                    + scope + ident)
            row = make(nm, None, place, "", note)
            new.append({"row": row, "kind": "parent", "hids": [hid], "households": [h],
                        "slots": [(hid, key)]})
            seen[dk] = new[-1]
            st["parent minted" + (" (forename only)" if forename_only else "")] += 1

    # ------------------------------------------------------------ children
    for h in hh:
        hid = h.get("id") or h.get("key")
        cls = ("**read — from registers this archive has read**" if h.get("src") == "read"
               else "**index only — no register has been read**")
        lab = ("household " + str(hid)) if re.match(r"^h\d+$", str(hid)) else ("the «" + str(hid) + "» household")
        father, mother = h.get("father", ""), h.get("mother", "")
        for ci, c in enumerate(h.get("children", [])):
            if c.get("pid"):
                continue
            nm = c["name"].strip()
            if BEARS.search(nm):
                st["child: bears the name, unlinked, NOT minted (probably already a row)"] += 1
                continue
            bare = len(nm.split()) == 1
            by = year(c.get("birth"))
            full = nm
            if bare:
                sur = surname_of(father)
                if not sur:
                    st["child: bare name, father has no surname to supply, NOT minted"] += 1
                    continue
                full = f"{nm} {sur}"
                same = [r for r in byname.get(norm(full), []) if by and year(r.get("b")) == by]
                if len(same) == 1:
                    c["pid"], c["pidBasis"] = same[0]["pid"], "name+year via father's surname"
                    st["child: linked via father's surname"] += 1
                    continue
            if L2.lr.possible_minor(by, False, (), False, YEAR):
                # a child is not published at all (living-people standard v2, 16 October 2026)
                st["child: a possible minor, held out, NOT minted"] += 1
                continue
            living = L2.lr.is_living(by, False, (), YEAR)
            place = (c.get("place") or "").strip() or None
            dk = ("C", norm(full), by, norm(father), norm(mother))
            if dk in seen:
                st["child: duplicate in batch"] += 1
                continue
            when = ("" if living else
                    (f" Dated **{c.get('birth')}**" if c.get("birth") else " No date is printed"))
            through = ("" if not BEARS.search(mother) else
                       " **Descends from the name through the mother** — the surname is another family's.")
            supplied = (f" The household list gives the given name only; the surname is the father's and is supplied here."
                        if bare else "")
            if living:
                note = (f"Child of **{father}** and **{mother}** ({lab}). A living person, so **named "
                        "with relationships and a town and country, and nothing more** under this archive's living-people rule.")
            else:
                note = (f"Child of **{father}** and **{mother}** ({lab} on [the households list](/households/))."
                        f"{when}" + (f", at {place}" if place else "") + f". Evidence class: {cls}."
                        + through + supplied + " Nothing else is claimed.")
            ark = f"1:1:{c['id']}" if c.get("id") else ""
            row = make(full, by, place, ark, note, living)
            new.append({"row": row, "kind": "child", "child": c, "slots": [(hid, ci)]})
            seen[dk] = new[-1]
            st["child minted" + (" (surname supplied)" if bare else "")] += 1

    print("mint-household-people:", "WRITING" if write else "report only")
    for k, v in sorted(st.items()):
        print(f"  {v:5}  {k}")
    print(f"\n  TOTAL new roster rows: {len(new)}  (living-flagged: {sum(1 for n in new if n['row'].get('living'))})")
    for n in new[:5] + new[-3:]:
        print("   ·", n["kind"], "|", n["row"]["name"], "|", n["row"].get("b"), "|", n["row"]["note"][:150])
    if not write:
        return
    for n in new:
        if len(n.get("hids", [])) > 1:
            others = ", ".join(str(x) for x in n["hids"][1:])
            n["row"]["note"] += (f" **Also named in household {others}** — the same name at the same place with a "
                                 "partner of the same forename, or households the archive itself flags as one "
                                 "under two readings. **One person is inferred, not stated.**")
        n["row"]["_link"] = [list(x) for x in n["slots"]]
        rows.append(n["row"])
    io.open(RO, "w", encoding="utf-8").write(json.dumps(ro, indent=1, ensure_ascii=False))
    io.open(HH, "w", encoding="utf-8").write(json.dumps(hh, indent=1, ensure_ascii=False))
    print("\n  rows appended with a pending link. NEXT: scripts/mint-person-ids.py --write, then "
          "scripts/mint-household-people.py --finish")


def finish():
    """After ids exist: point each household slot at the row minted FOR it, then drop the marker."""
    hh = json.load(io.open(HH, encoding="utf-8"))
    ro = json.load(io.open(RO, encoding="utf-8"))
    byid = {(h.get("id") or h.get("key")): h for h in hh}
    n = 0
    for r in ro["rows"]:
        for hid, slot in r.pop("_link", []):
            h = byid[hid]
            if isinstance(slot, int):
                h["children"][slot]["pid"], h["children"][slot]["pidBasis"] = r["pid"], "minted for this household"
            else:
                h[slot], h["pidBasis_" + ("father" if slot == "fatherPid" else "mother")] = r["pid"], "minted for this household"
            n += 1
    io.open(HH, "w", encoding="utf-8").write(json.dumps(hh, indent=1, ensure_ascii=False))
    io.open(RO, "w", encoding="utf-8").write(json.dumps(ro, indent=1, ensure_ascii=False))
    print(f"mint-household-people --finish: {n} household slots linked to the rows minted for them")

finish() if "--finish" in sys.argv else main()
