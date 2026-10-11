#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A lead that already describes somebody in the roster, and is not linked to them.

WHY THIS EXISTS. On 11-12 October 2026 the archive found the same thing three
times in two days at Ližnjan, and each time it was a discovery of something it
already held:

  Fusca, 1870          `register.json` held BOTH halves of her life as two
                       separate leads, with identical parents, and never joined
                       them. The roster ignored both and copied the family tree,
                       taking the wrong spelling with it.
  Mathæus, 1890-1891   held from the burial index with the right year — and
                       duplicated by the tree with the wrong one.
  Fusca née Lazarić    held as lead XQM3-P992 and never in the roster at all.

None of that was a research problem. The evidence was on disk. What was missing
was anything that noticed.

WHAT THIS CHECKS, AND WHAT IT DELIBERATELY DOES NOT. There are ~1,500 lead ids
and most are not cited by any roster row. That is *not* a fault — a lead is a
candidate, and a one-name study collects many it will never promote. Counting
the backlog would produce a number nobody can act on.

So this looks for the much narrower and much sharper thing: a lead that
**matches a person the roster already has** — same place, same given name,
within a year — and is **not linked to them**. That is the archive holding one
person twice without knowing it, which is the failure that actually cost time.

THE REMEDY IS A LINK, NOT A COPY. When a lead matches, add its id to that
roster row's `leads` list. Do NOT copy the lead's dates into the person: an
index is a transcription of a page nobody here has read, and this archive's
rule is that a finding comes from the document. Linking says «this lead is
accounted for»; reading the page is still the work.

THE COUNT RATCHETS, like `check-story.py`. It may fall. It must not rise.
"""
import io, json, os, re, sys, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "src", "data")
BASELINE = os.path.join(ROOT, "data", "leads-baseline.json")


def fold(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", s)


# Given names that are the same name in two languages or two centuries. Kept
# short on purpose: a loose table invents collisions, which is the one thing
# this check must not do.
GIVEN = {
    "mathaeus": "mat", "mathus": "mat", "mattheus": "mat", "matteo": "mat",
    "mattio": "mat", "mattia": "mat", "mattea": "mat", "mathias": "mat",
    "maria": "mar", "marie": "mar", "mary": "mar",
    "magdalena": "mag", "maddalena": "mag", "madalena": "mag", "magdlaena": "mag",
    "josephus": "jos", "joseph": "jos", "josephi": "jos", "giuseppe": "jos",
    "joannes": "joa", "giovanni": "joa", "joanna": "joa",
    "antonius": "ant", "antonio": "ant", "antonii": "ant",
    "catharina": "cat", "cattarina": "cat", "catarina": "cat", "caterina": "cat",
    "anastasia": "ana", "anna": "ann", "ana": "ann",
    "fusca": "fus", "fosca": "fus", "tusca": "fus",
    "gregorio": "gre", "gregorius": "gre", "gregorii": "gre",
    "justina": "jus", "paschalis": "pas", "paschal": "pas",
    "lucia": "luc", "agatha": "aga", "agata": "aga",
}


def given(n):
    f = fold((n or "").split()[0] if n else "")
    return GIVEN.get(f, f[:3])


def year(v):
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", str(v or ""))
    return int(m.group(1)) if m else None


def place(p):
    return fold(re.split(r"[,(]", p or "")[0])


def load(name):
    return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))


def main():
    blob = json.dumps(load("register.json"), ensure_ascii=False)
    leads = []
    for m in re.finditer(
        r'\{"id": "([A-Z0-9-]{6,})", "n": "([^"]*)",(?:[^{}]*?)"y": ([^,]*), '
        r'"says": "([^"]*)", "p": "([^"]*)"', blob):
        leads.append({"id": m.group(1), "n": m.group(2), "y": m.group(3).strip(),
                      "says": m.group(4), "p": m.group(5)})

    ros = load("roster.json")
    rows = ros if isinstance(ros, list) else ros.get("people", ros.get("rows", []))

    linked = set()
    for r in rows:
        for k in ("ark", "imageArk"):
            v = r.get(k) or ""
            if v:
                linked.add(v.split(":")[-1])
        for v in (r.get("leads") or []):
            linked.add(v)

    by_place = collections.defaultdict(list)
    for r in rows:
        by_place[fold(r.get("placeSlug") or "")].append(r)

    hits = []
    for L in leads:
        if L["id"] in linked:
            continue
        ly = year(L["y"]) or year(L["says"])
        lp, lk = place(L["p"]), given(L["n"])
        if not (ly and lp and lk):
            continue
        for r in by_place.get(lp, []):
            ry = year(r.get("b")) or year(r.get("d"))
            if ry and abs(ry - ly) <= 1 and given(r.get("name")) == lk:
                hits.append((L, r))
                break

    base = 10 ** 9
    if os.path.isfile(BASELINE):
        base = json.load(io.open(BASELINE, encoding="utf-8")).get("unlinked", base)

    print("check-leads: %d lead(s) describe somebody the roster already has, "
          "and are not linked to them" % len(hits))
    for L, r in sorted(hits, key=lambda x: (place(x[0]["p"]), x[0]["y"])):
        print("   %-14s %-20s -> %-28s  %s"
              % (L["id"], (L["n"] or "?")[:20], (r.get("name") or "?")[:28],
                 L["says"][:54]))
    if hits:
        print("   Link each to its person with a `leads` entry on the roster row —"
              " then read the page. Do not copy an index's dates into a person.")

    if len(hits) > base:
        print("   FAIL — this was %d and is now %d. The count may fall; it must "
              "not rise." % (base, len(hits)))
        return 1
    if len(hits) < base:
        print("   (down from %d — baseline updated)" % base)
        json.dump({"unlinked": len(hits)},
                  io.open(BASELINE, "w", encoding="utf-8"), indent=1)
    elif not os.path.isfile(BASELINE):
        json.dump({"unlinked": len(hits)},
                  io.open(BASELINE, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
