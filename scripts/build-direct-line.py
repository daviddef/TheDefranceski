#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Make site/src/data/direct-line.json from the story's own ribbon (story-book.json), by the kit's spec.

    python3 scripts/build-direct-line.py                       # write site/src/data/direct-line.json
    python3 scripts/build-direct-line.py --check               # fail if the file is not what the story makes (CI)
    python3 scripts/build-direct-line.py --kit-story PATH      # also write the story ribbon in the kit's shape, for the kit's gates

WHY THIS AND NOT THE KIT'S directline.py ALONE. The kit makes direct-line.json from a kit story (src/data/story.json with
`ribbon.cards`). This archive's story is its own (src/pages/story.astro over src/data/story-book.json; the archive's
story.json is the older chapter cards and has no ribbon). So the ribbon is read here, and turned into the kit's card shape
(--kit-story), and the kit's own tools are then run on that: `kit/tools/directline.py --check` holds direct-line.json to it
and `kit/tools/checkfamilyribbon.py --story` holds the tint on the built pages to it. Nothing is typed.

THE KIT'S SPEC (kit/docs/family-ribbon.md, "The direct line"):
  people    one entry for each ribbon card that names a person page (`pid`): generation = the card's number, chapter = its `link`;
  unlinked  a card with no person page;
  partners  the spouse on a card who is herself our ancestor (`spouseDirect`). This archive marks no card so; the story says it
            in its own chapter trees instead, and that is what is read: the spouse of card n is on the line when the chapter
            tree in which she is one of the couple has, in its children's row, the person of card n+1 marked `line: true`.
            A spouse with no person page cannot be listed (Francisca Salomon, generation 2, has none). A spouse who is the
            mother of nobody on the ribbon (the last card's) is not on the line.
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, "site", "src", "data", "story-book.json")
OUT = os.path.join(ROOT, "site", "src", "data", "direct-line.json")
NOTE = ("Made by scripts/build-direct-line.py from the story's ribbon (story-book.json) by the kit's spec "
        "(kit/docs/family-ribbon.md); do not edit by hand.")

AT = re.compile(r"^(?:at|in|worked at)\s+(.+?)(?:,\s*(\d{4}))?$")


def chapter_trees(book):
    return {c["id"]: c.get("tree") for c in book["chapters"] + [book.get("closing") or {}] if c.get("id")}


def spouse_direct(book, i):
    """Is the spouse of ribbon card i (0-based) the mother of card i+1, by the story's own chapter tree?"""
    cards = book["ribbon"]
    sp = (cards[i].get("spouse") or {}).get("pid")
    if not sp or i + 1 >= len(cards) or not cards[i + 1].get("pid"):
        return False
    nxt = cards[i + 1]["pid"]
    for tree in chapter_trees(book).values():
        if not tree:
            continue
        rows = tree.get("rows") or []
        couple = [r for r in rows if r.get("role") == "couple" and any(p.get("pid") == sp for p in r.get("people") or [])]
        if not couple:
            continue
        for r in rows:
            if r.get("role") == "kids" and any(p.get("pid") == nxt and p.get("line") for p in r.get("people") or []):
                return True
    return False


def kit_card(book, i):
    """One story-book ribbon card in the kit's card shape (kit/lib/story.js RIBBON_FIELDS + person, spousePerson, chapter)."""
    r = book["ribbon"][i]
    sp = r.get("spouse") or {}
    town = r.get("town") or ""
    m = AT.match(town)
    living = bool(r.get("living"))
    card = {
        "name": r.get("name", ""), "years": "" if living else (r.get("years") or ""),
        "origin": r.get("place", ""), "originGrade": r.get("support", ""),
        "spouse": sp.get("name", ""), "spouseOrigin": sp.get("place", ""),
        "atPlace": (m.group(1) if m else town), "atYear": "" if living else ((m.group(2) or "") if m else ""),
        "living": living, "chapter": r.get("link", ""),
    }
    if r.get("pid"):
        card["person"] = r["pid"]
    if sp.get("pid"):
        card["spousePerson"] = sp["pid"]
    if sp.get("href"):
        card["spouseHref"] = sp["href"]
    if sp.get("living"):
        card["spouseLiving"] = True
    if spouse_direct(book, i):
        card["spouseDirect"] = True
    return card


def kit_story(book):
    return {"_note": "Written by scripts/build-direct-line.py from story-book.json for the kit's gates; not published.",
            "ribbon": {"cards": [kit_card(book, i) for i in range(len(book["ribbon"]))]}}


def from_story(story):
    """The kit's own rule (kit/tools/directline.py from_story, kit/lib/directline.js fromStory), names kept."""
    people, partners, unlinked = [], [], []
    for i, c in enumerate(story["ribbon"]["cards"]):
        if c.get("person"):
            people.append({"slug": c["person"], "generation": i + 1, "storyChapter": c.get("chapter", ""), "name": c.get("name", "")})
        else:
            unlinked.append({"generation": i + 1, "storyChapter": c.get("chapter", ""), "name": c.get("name", "")})
        if c.get("spouseDirect") and c.get("spousePerson"):
            partners.append({"slug": c["spousePerson"], "generation": i + 1, "storyChapter": c.get("chapter", ""),
                             "partnerOf": c.get("person", ""), "name": c.get("spouse", "")})
    return {"_note": NOTE, "generationLabel": "generation", "people": people, "partners": partners, "unlinked": unlinked}


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--kit-story")
    a = ap.parse_args()
    book = json.load(open(BOOK, encoding="utf-8"))
    story = kit_story(book)
    want = dump(from_story(story))
    if a.kit_story:
        os.makedirs(os.path.dirname(os.path.abspath(a.kit_story)), exist_ok=True)
        open(a.kit_story, "w", encoding="utf-8").write(dump(story))
    if a.check:
        have = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != want:
            print("build-direct-line: %s is not what the story's ribbon makes; run scripts/build-direct-line.py" % os.path.relpath(OUT, ROOT))
            return 1
        d = json.loads(want)
        print("build-direct-line: direct-line.json is the story's ribbon (%d people, %d partners, %d unlinked)"
              % (len(d["people"]), len(d["partners"]), len(d["unlinked"])))
        return 0
    open(OUT, "w", encoding="utf-8").write(want)
    d = json.loads(want)
    print("build-direct-line: wrote %s (%d people, %d partners, %d unlinked)" % (os.path.relpath(OUT, ROOT), len(d["people"]), len(d["partners"]), len(d["unlinked"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
