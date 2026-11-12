#!/usr/bin/env python3
"""Build site/src/data/changes.json — one reverse-chronological feed.

Merges the Search Register (every search, including the ones that found
nothing) with Corrections (every claim taken back) and the few hand-written
entries about the site itself (site/src/data/changes-built.json), so a reader
can see what the archive did on a given day and what it had to undo.

    python3 scripts/build-changes.py

12 November 2026 (the research-menu trial). The file had not been rebuilt since
20 September: its newest day was 6 October while the logs ran to 12 November,
and the one entry written by hand (a new page, 6 October) lived only inside the
generated file, so a plain regeneration would have dropped it. Now the hand
entries have a file of their own; dates are read in every shape the logs use
(a day, a month, a range, "12 Sept 2026, answered"); and a row's kind is the
archive's one outcome vocabulary (scripts/vocab.py), not whatever word it was
written with.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import vocab

DATA = os.path.join(ROOT, "site", "src", "data")
load = lambda n: json.load(open(os.path.join(DATA, n), encoding="utf-8"))

MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
NAME = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"}


def when_key(when):
    """(year, month, day, label) from the archive's informal dates. A month alone is day 0 and is labelled by its month;
    a range ("Aug–Sept 2026") takes its last month; no date at all sorts last under "Undated"."""
    w = str(when or "")
    m = re.search(r"(?:(\d{1,2})\s+)?([A-Za-z]{3,})\.?\s+(\d{4})", w)
    if m and m.group(2)[:3].lower() in MON:
        d, mo, y = int(m.group(1) or 0), MON[m.group(2)[:3].lower()], int(m.group(3))
        # "Aug–Sept 2026": the regex finds "Sept 2026" (the last month before the year), which is the one that counts
        label = ("%d %s %d" % (d, NAME[mo], y)) if d else ("%s %d" % (NAME[mo], y))
        return (y, mo, d, label)
    m = re.search(r"\b(20\d\d)\b", w)
    if m:
        return (int(m.group(1)), 0, 0, m.group(1))
    return (0, 0, 0, "Undated")


rows = []
# The Search Register's entries link to the Search Register (the register is /searched/; "/research-log/" was never its name).
for r in load("searched.json")["rows"]:
    kind = vocab.OUTCOME.get(str(r.get("outcome", "")).strip().lower(), r.get("outcome", "search"))
    rows.append({"when": r.get("when", ""), "kind": kind,
                 "what": r.get("what", ""), "src": r.get("src", ""),
                 "text": r.get("got", ""), "href": "/searched/"})
for r in load("corrections.json")["rows"]:
    rows.append({"when": r.get("when", ""), "kind": "correction",
                 "what": r.get("what", ""), "src": "A claim taken back",
                 "text": "**This archive said** " + r.get("said", "") +
                         "\n\n**What is true** " + r.get("true", "") +
                         "\n\n**How it happened** " + r.get("how", ""),
                 "href": r.get("where") or "/corrections/"})
for r in load("changes-built.json")["rows"]:
    rows.append({k: r.get(k, "") for k in ("when", "kind", "what", "src", "text")} | {"href": r.get("href", "")})

# newest day first; within a day the order of the logs is kept (Python's sort is stable), searches before corrections
rows.sort(key=lambda r: when_key(r["when"])[:3], reverse=True)
days = []
for r in rows:
    label = when_key(r["when"])[3]
    if not days or days[-1]["when"] != label:
        days.append({"when": label, "rows": []})
    days[-1]["rows"].append(r)

n_cor = sum(1 for r in rows if r["kind"] == "correction")
out = {
 "title": "What changed",
 "eyebrow": f"{len(rows)} entries · {n_cor} of them corrections",
 "dek": "Every search this archive has run and every claim it has taken back, newest first.",
 "lead": "Most family archives publish only what they found. This one publishes **what it looked for, what it found, what it did not find, and what it got wrong** — in one feed, in the order it happened.\n\nA search that returned nothing is kept because **an absence from a named source is a finding**, and because the next person should not have to repeat it. A correction is kept because an archive that only shows its successes is not telling you how reliable it is.",
 "days": days,
 "close": "This page is generated from the Search Register and the Corrections list; neither is written for it. If something is here twice, it is because it was both a search and a mistake.",
}
raw = json.dumps(out, ensure_ascii=False, indent=1)
open(os.path.join(DATA, "changes.json"), "w", encoding="utf-8").write(raw)
print(f"changes.json · {len(rows)} entries across {len(days)} days · newest {days[0]['when']}")
