# The Defranceschi Archive

A public, evidence-first **one-name study** — the surname, not one family — published
from `site/` to <https://daviddef.github.io/TheDefranceski/>.

**Full rules: `scripts/WORKING-RULES.md`. Read it. What follows is the part that,
forgotten, does the most damage.**

---

## A finding is done when it is TOLD, not when it is logged

Two kinds of file, not interchangeable:

- **LOG** — `worklist` `searched` `corrections` `sources` `method`. Receipts.
- **STORY** — `families` `lines` `rivers` `households` and the topic pages
  (`carlo` `atsea` `namesakes` `clusters` `spines`). **What a reader reads.**

`roster.json` is neither: a person page *is* story, but a finding living **only**
on one person's page has not been told — nobody browses the roster to find it.

> **Every finding must be written into the story of the Defranceschi families and
> lines.** A search log that points at itself is work nobody will ever read.

`python3 scripts/check-story.py` counts findings that never reached a reader.
**It must only ever go down.**

## Record Atlas

The shared map lives at `../Record Atlas`. Research done here is only
useful to the next person if it gets there.

Invoke the `record-atlas-feedback` skill whenever you finish a search,
open a register, write to an archive, or find a source the atlas does
not list — as you do it, not in a sweep at the end. Record the
FamilySearch waypoint, not just the film number; the skill explains why.

## A correction is done when the old claim is gone from EVERY file

Not when it is written. A name fixed on a person page and left standing in
`households.json` kept a child under the wrong parents for five days *after* the
archive knew better. `scripts/check-propagation.py` runs in the gate.

## Check before claiming a discovery

Grep `sources.json`, `searched.json`, `roster.json` for the source and the name
**first**. Twice in one day a "find" was a re-run of a search already recorded.
Say so when it is. Verification is worth publishing; it is not discovery.

## Evidence

- Every claim states **`doc` / `inf` / `lore` / `dna`**.
- **A hand is only legible against itself**: before writing a doubtful word, find
  the same scribe writing *both* candidate names elsewhere in the same book and
  compare at one magnification. Staring harder settles nothing.
- Never read rank or trade off an abbreviation without a second construction.
- **A nil names the exact terms tried.** "Nothing in every spelling" is an
  assertion about a list nobody kept — one such claim proved simply wrong.
- Record the **film and frame**, never only the ark.

## Hard limits

- **Never work around a bot check, CAPTCHA or rate limit.** Stop, record where,
  say so. A *different, open* source for the same question is fine.
- **Never enter credentials.** David signs in; sessions drive.
- **Living people: name only** — no dates, no places, no photographs.

## Ground you do not own

`./scripts/whose.sh` before every commit. **Shared** = `site/public/*`, layouts,
components, nav, `site/package*.json`, the kit, repo root. Another session owns
the cross-site UI. If David asks for a shared change: `--allow-shared`, and flag
the collision risk in the commit message.

## Committing

```bash
./scripts/gate-isolated.sh     # capture ITS exit status — never grep for "FAIL"
```

`grep -E "ALL GREEN|FAIL"` exits 0 on finding the word FAIL. That once pushed a
red gate.

- **Commit and push after each finding**, not in batches.
- Rebuild `build-dossiers.py` + `build-search-index.py` when the roster changes.
- Person ids are **minted once and frozen**; a moved id is a dead URL.
- Never commit raw GEDCOM; never publish living DNA-match names.

## Starting a session

Read the worklist (`running`, then `next`), run the gate, note the `check-story`
count — and make sure it has not risen by the time you stop.
