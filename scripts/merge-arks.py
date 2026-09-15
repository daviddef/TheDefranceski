#!/usr/bin/env python3
"""Fold a harvest of first-image arks back into data/fs-catalogue.json.

A volume in the catalogue is [title, waypointPrefix, extraSegments]. A fourth
element — the ark of its first image — is what makes the title clickable on the
research map, and it is the one field the catalogue walk cannot supply: it takes
its own call, one per book, 5,482 of them.

Input is the JSONL the browser harvester POSTs to the local receiver: each line
a JSON array of [shelfKey, bookIndex, ark], where the ark may still carry the
"?cc=&wc=" tail the viewer URL uses. The tail is thrown away — the map rebuilds
it from the waypoint, which it already holds.
"""
import json, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "data", "fs-catalogue.json")

def main(src):
    cat = json.load(open(CAT, encoding="utf-8"))
    rows = []
    for line in open(src, encoding="utf-8"):
        line = line.strip()
        if not line or not line.startswith("["):
            continue
        try:
            rows += json.loads(line)
        except json.JSONDecodeError:
            pass                      # a half-written flush; the next run gets it

    new = miss = same = 0
    for key, i, ark in rows:
        ark = ark.split("?")[0]
        books = cat["b"].get(key)
        if not books or i >= len(books):
            miss += 1
            continue
        b = books[i]
        while len(b) < 4:
            b.append(None)
        if b[3] == ark:
            same += 1
        else:
            b[3] = ark
            new += 1

    json.dump(cat, open(CAT, "w", encoding="utf-8"), ensure_ascii=False)
    total = sum(1 for v in cat["b"].values() for b in v)
    have = sum(1 for v in cat["b"].values() for b in v if len(b) > 3 and b[3])
    print(json.dumps({"lines": len(rows), "new": new, "unchanged": same,
                      "unmatched": miss, "volumes": total, "linkable": have}))

if __name__ == "__main__":
    main(sys.argv[1])
