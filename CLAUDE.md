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

The shared map lives at `~/Projects/Family Projects/Record Atlas` — **not**
`../Record Atlas`, which is where this file sent three sessions before one of
them looked. Research done here is only useful to the next person if it gets
there.

**You are not the only session in that tree.** `git status` before you touch
it; if files you did not change are modified, leave them and say so. To ask
what of this archive reaches the map, run its importer **to a scratch file** —
`scripts/import-research-sessions.py --out … --rejects …` — never over
`record-atlas-research-import.json`, which another session may be mid-edit.

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
- **Living people:** A living person (80 or younger, with no death recorded) is named with their relationships and their town and country, and nothing more. No dates, no records, no photograph, no `Person` data; the page is `noindex`. Possible minors are not published at all. The test is `scripts/living_v2.py` (the kit's `living_rule.py`, minus its hole: a public-source citation never un-lives a person who has a birth year); the cutoff is one derived constant (this year - 80), `L2.CUTOFF` / `site/src/lib/living.js`; the gate is `scripts/check-living-v2.py` (rule 7: no year at or after the cutoff without a death beside it, anywhere). Since kit 341af33 a bare death flag (`deceased: true`, a GEDCOM `DEAT Y`) is not a death record for a person born in the window (they stay living, `undated_dead`); a roster row records a death with `deathSource` + `deathGrade` (+ `deathRecorded: true` for the kit's gate), e.g. «family confirmation, David Defranceski, 25 October 2026», grade `lore`, no date needed. The kit's printed-year gate runs beside ours (`npm run check:living`: `--years --strict-allow`, registry `data/living-year-allow.json`, `living_years` in `standard.json`).

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

## Names on the narrative pages are linked at build time

The kit's `autolink.py` runs right after `astro build` (`npm run autolink`) and links the FIRST mention of a
person in each section of the built HTML; `checklinks.py` (`npm run check:links`, floor `site/.linkfloor.json`)
stops the count of unlinked names rising. It reads `private/autolink/names-index.json` and `living.json`,
both written by `scripts/build-names-index.py` from the COMMITTED roster (CI has no tree and builds the same
files; David's tree only adds names to `living.json`). The old browser linker (`wholink.js`, `whoindex.json`)
is gone. A person is linked only if the roster shows them dead and nobody else bears the name; a shared name
goes to its `/who/` page or to the search; a person born after 1900 with no death recorded is never linked.
A run on David's machine REFUSES when a living or held-out person of the tree bears the name of an indexed
dead person: add the page id it prints to `data/autolink-namesakes.json`. The person and name pages and the people
index (each lays out its own links) opt out with `noautolink` on `<Base>`. `scripts/check-names-index.py` judges the files and the linked
site, and its `--self-test` plants the faults.

## Starting a session

Read the worklist (`running`, then `next`), run the gate, note the `check-story`
count — and make sure it has not risen by the time you stop.

## The linking standard (18 October 2026)

The kit's `checkstandard.py` (docs: `kit/docs/linking-standard.md`) holds the twelve research narratives (`site/standard.json`: /gologorica-line/,
/corrections/, /carnia/, /liznjan/, /lines/, /seget/, /pfullingen/, /fiume-1626/, /carlos-letter/, /crikvenica-house/, /carlo/; the memoir
/cheryl-lerena/ is out on purpose, the reasons are in the file) to five counts that may only go down (`site/.standardfloor.json`, counts, never a
name): L1 names linked, L2 people read from records with no entry, L3 passages that cite a record with no link to it, L4 a scan the archive may show
beside the passage that relies on it, L5 bare given names and forms nobody wrote in full. `npm run check:standard` is the last step of the build
(`scripts/standard-run.py`; CI runs it on committed data only, after the kit's own self-test of the gate). A raised number is a person's edit in a
commit that says why.

* **A citation links to its record with the author's own words**: `[M01069230](rec:plate-golo-1787-parochus)` in the data (a DAPA image id to the
  plate of that page on the same page, anchor `#plate-<id>` from `components/Plates.astro`), `[an_ua667516](rec:antenati-an_ua667516)` (an Antenati
  volume), ``[`3:1:3QS7-L99F-W4CK`](rec:fs-3QS7-L99F-W4CK)`` (a FamilySearch image). `src/lib/md.js` draws them as the kit's `Rec` does (class `lk-rec`,
  `data-rec`, `data-cite`); an id the data does not hold STOPS the build. `src/data/records.json` is made by `scripts/build-records.py` from
  `antenati-catalogue.json` and the data's own arks (never by hand), `scripts/check-rec.py` judges every such link on the built site against the
  source data. **No address is made up**: a DAPA image id with no plate, a film, a frame or a folio has no public address and stays text, counted.
* **Link-only**: FamilySearch frames, Antenati scans and Matricula pages are never drawn beside a passage (David, 18 October 2026). Only plates of the
  family's own copy of the Pazin films (DAPA) are placed beside the passage that cites them (L4), and only ones the archive already shows.
* **Names read from records** (L2): `scripts/build-read-names.py` lists, from the structured files (`register.json`, `fsrecords.json`,
  `households.json`), the names the narratives use that the roster does not hold and that those files show dead; each has a /who/ page and is a
  `people` row of the names index (`site/src/data/read-names.json`, the second source of `build-names-index.py`, judged again by
  `check-names-index.py`). The parish-book readings themselves exist only as prose: no name is taken from prose.
* Do not add the generic `page N` / `act N` patterns, or a table mode, to `standard.json` to make a count fall; add a record link or a full name.

## The "at the time" notes (25 October 2026)

A quiet line under the Place row of a deceased person's page, from the Record Atlas's region eras (kit/docs/era-notes.md; snapshot version 5, kit 2ce1fa4):
`· At the time: Habsburg / Austria–Hungary per the Record Atlas, drawn from this archive's own research`. Text only, no flag, no ruler (rulers are OFF; only Calabria has them), nothing on a
living page or a duplicate. The page prints one place and the person's years, so a note is drawn only where every plain year the page prints (born, died) has the SAME note.

* **The place table is geometry, not a name guess.** `data/era-ground.tsv` names the TOWN each place string is (or leaves it empty: a country, a route "A → B", two places, a homonym), `data/era-towns.tsv` holds the
  point (and an `exclude` reason where a ring is known to reach over ground that was not the region's), and `scripts/build-era.py --decide <context.json>` sets the region from the Atlas's ring that contains the
  point (the smallest ring; two peer rings and no edge in sight: no region). A new place string fails `npm run check:era-ground` until it has a row.
* **The snapshot is committed, never fetched**: `scripts/build-era.py --snapshot <context.json>` (copy `Record Atlas/site/public/context.json` first; the Atlas repo is read-only here) rebuilds
  `site/src/data/era-snapshot.json` with `--unassessed allow` (the recorded policy: the notes say whether the era was assessed). Refresh deliberately and review the diff.
* The Istria, Kvarner, Carnia and Dalmatia eras are SEEDED from `sovereignty.json`, so those notes say so. `scripts/compare-sovereignty.py <context.json>` counts where our bands and the Atlas's eras disagree.
* Gates: `check:era-ground`, `check:era` (the kit's `checkera.py` on the built pages), `check:era:selftest`, all in the build and in `scripts/gate-isolated.sh`. `scripts/verify-era-independent.py --contract <context.json> --dist <dist>`
  re-derives every note from the contract and the rings with no kit code, both directions (0 wrong, 0 missing is the standard). A tool that reads built text must skip `.era-note` and `<style data-era-css>`.
* The note's source words are long on a seeded era: `[pid].astro` lets them wrap (the kit sets `white-space:nowrap`), or a phone's page runs wider than the screen.
