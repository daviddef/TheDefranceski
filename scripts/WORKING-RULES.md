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

Name only. **No dates, no places of birth, no photographs.** Where a page would
say "withheld", show initials and surname. Family only, as written: strangers
found in public indexes keep their dates.

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
