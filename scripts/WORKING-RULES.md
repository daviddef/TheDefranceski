# Working rules for this archive

*Written 28 September 2026, after a day in which findings were made, logged, and
never told. Point any session at this file. `scripts/*` is this archive's own
ground, so this file is safe to edit from a research session.*

---

## 1. A finding is not done when it is logged. It is done when it is told.

This archive has two kinds of file and they are not interchangeable.

| | files | what they are |
|---|---|---|
| **LOG** | `worklist.json` `searched.json` `corrections.json` `sources.json` `method.json` | **receipts** — what was searched, what was fixed, how |
| **STORY** | `families.json` `lines.json` `rivers.json` `households.json` and the topic files (`carlo` `atsea` `namesakes` `clusters` `spines`) | **what a reader reads** |

`roster.json` is both and counts as neither: a person page *is* story, but **a
finding that lives only on one person's page has not been told**, because nobody
browses the roster looking for it.

> **Every new finding must be incorporated into the story of the Defranceschi
> families and lines. A search log that points at itself is work nobody will
> ever read.**

Run `python3 scripts/check-story.py`. It counts searches recorded as *hits*
whose evidence links go only to logs. When it was written, **44 of 158 hits —
28%** had never reached a reader. **That number should only ever go down.**

## 2. A correction is not done when it is written, either.

It is done when the old claim is **gone from every file that asserts it**.

A name corrected on a person page and left standing in `households.json` kept a
child filed under the wrong parents for five days *after* the archive knew
better. `python3 scripts/check-propagation.py` (in the gate) catches exactly
this. If it goes red, either fix the file or add it to that rule's allowed set
**and say why it quotes the error on purpose**.

## 3. Before claiming a discovery, check whether the archive already has it.

Twice in one day a "new" find turned out to be a re-run — a newspaper portal
recorded as **done** under Sources while the worklist still called it
**pending**. Grep `sources.json`, `searched.json` and `roster.json` for the
source and the name *before* writing anything up, and if it is a re-run, **say
so**. Verification is worth recording; it is not discovery.

**And grep the SIBLING ARCHIVES too — `./scripts/whoelse.sh <term>`.**
On 29 September 2026 this rule was obeyed to the letter and still failed. The
logs of *this* archive were grepped, they were clean, and the "first step" that
followed — are the Brinje registers filmed? — had been taken a fortnight earlier
by the Blažević archive, which had located both films, measured that nothing is
indexed, and was reading the marriage book that same day. The check could not
see it because the work was in another repository. **David caught it, and no
script did.** Three repeats the same day were caught by grepping this archive;
the fourth was invisible to that.

The estate is one body of research kept in several trees. **A question answered
in any of them is answered.** `whoelse.sh` greps every sibling archive's data
for a term and prints where it appears; a hit is not a verdict, it is an
instruction to go and read that file.

## 4. Evidence discipline

- **Every claim states its confidence**: `doc` / `inf` / `lore` / `dna`.
- **A hand is only legible against itself.** Before writing down a doubtful
  word, find the same scribe writing *both* the name you think it is and the
  name you fear it is, elsewhere in the same book, and compare at one
  magnification. Staring harder at one word settles nothing.
- **Never read rank or trade off an abbreviation** without a second
  construction that puts it beyond doubt.
- **A nil result names the exact terms tried.** "Nothing under X, Y and Z" is a
  finding. "Nothing in every spelling" is an assertion about a list nobody kept —
  and one such claim was found to be simply wrong.
- **Record the film and the frame, never only the ark.**

## 5. Bot checks and paywalls

**Never work around a bot check, a CAPTCHA, or a rate limit.** Stop, record
where you stopped, and say so. Using a *different, open* source for the same
question is fine and encouraged; disguising, throttling or retrying past a
challenge is not. Never enter credentials — David signs in, sessions drive.

## 6. Living people

**A living person (80 or younger, with no death recorded) is named with their relationships and their town and country, and nothing more.**
That is David's ruling of 16 October 2026 (the living-people standard, version 2), the same in every
archive. Living is *80 or younger, by year, with no death or burial recorded*; a citation from a public
record source does **not** un-live a person who has a birth year (25 October 2026: a source can show someone
was born, never that they died; the kit's rule says otherwise, so `living_v2.py` withholds the citations from it
for the dated). The boundary is one derived constant, `CUTOFF = this year - 80` (1946 in 2026): `living_v2.py` for
scripts, `site/src/lib/living.js` for pages, nothing else spells the number; a person with no birth year is not living; an undated person with a living parent is not published at all (a child with a known birth year follows the standard).
The test is `scripts/living_v2.py` over the kit's `living_rule.py`, never a hand-set flag. A birth year is
never committed for a living person: `scripts/apply-living-rule.py` reads David's MyHeritage GEDCOM
(outside the repository) and writes only the verdict (`--roster-only` decides from the committed fields where there is no tree).
`scripts/check-living-v2.py` is the gate: rule 7 fails the build on a year at or after the cutoff with no death beside it
anywhere (data rows, built pages, JSON-LD, titles, after a living name; reviewed exceptions in `data/living-year-allow.json`),
rule 8 on a page or script that spells the boundary out. `scripts/test-living-v2.py` plants the faults and runs in `check:living-v2`.

## 7. Ground you do not own

`scripts/whose.sh` before every commit. **Shared** = `site/public/*`, layouts,
components, the nav, `site/package*.json`, the kit, repo root. Another session
owns the cross-site UI and will collide with you. If David explicitly asks for a
shared change, use `--allow-shared` **and flag the collision risk in the commit
message**.

## 8. The gate, and committing

```bash
./scripts/gate-isolated.sh        # capture ITS exit status, never grep for "FAIL"
```

A `grep -E "ALL GREEN|FAIL"` exits 0 on finding the word FAIL, and that once
pushed a red gate. Then:

- **Commit and push after each finding**, not in batches.
- Rebuild `build-dossiers.py` and `build-search-index.py` when roster changes.
- Person ids are **minted once and frozen**. A moved id is a dead URL.
- Never commit raw GEDCOM; never publish living DNA-match names.

## 9. What to do at the start of a session

1. Read the worklist: `running` first, then `next`.
2. Run the gate. Note the `check-story` count.
3. When you finish a finding: **write it into a story page**, add the `ev` link,
   commit, push, and check the count did not rise.
