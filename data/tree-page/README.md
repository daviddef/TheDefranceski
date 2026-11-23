# Roots & Routes (the tree page)

> **23 November 2026 (the estate clean-up): the /roots/ page was removed** (the Tree Canvas on recordatlas.org replaced it; `/roots/` now redirects to `/tree/`). What is kept, because it is read:
> `tree.json`, `atlas-data.json`, `place_map.json` (the person pages read them), `roots.html` (served at `/roots/view.html`, the viewer the person pages frame) and the build script.
> `roots.embed.html` (the fragment the page rendered) is deleted and no longer built. `/roots/lines.json` stays: the Tree Canvas's Lines mode is written to read it.


Ten views of every person the archive holds: hourglass, fan, whole-tree and close-family maps, Atlas map, movements, kinship, place lanes,
eras, lifespans, and an Orphans tab that says where to start next. One self-contained page, `roots.html`.

| File | What it is | Edit by hand? |
|---|---|---|
| `tree.json` | people, parent links, years, places, the not-drawn list | no, generated |
| `place_map.json` | each place with coordinates, country and Record Atlas id | no, generated from `site/src/data/atlas.json` + `data/gazetteer.json` |
| `atlas-data.json` | the Record Atlas slice: outlines, regimes, flags, events, collections | no, generated |
| `roots.html` | the page | no, generated |
| `tree.report.json` | counts and the conflicts the research should settle | read it |

## Rebuild

```bash
python3 scripts/build-tree-page.py          # rebuild everything, run the checks
python3 scripts/build-tree-page.py --check  # exit 1 if the page is older than the data
```

Rebuild after any finding that changes the roster, `dossiers.json`, `households.json`, `directline*.json` or `atlas.json`. The record
of what the page was built from is `tree.json` → `meta.inputs`. Needs the Record Atlas checkout (`RECORD_ATLAS`, default
`~/Projects/Family Projects/Record Atlas`) and the kit's `living_rule.py` (via `scripts/living_v2.py`).

## Full dates (`bd`, `dd`) in `tree.json`

Each person in `tree.json` may carry two optional strings for the Record Atlas Tree Canvas (recordatlas.org/tree-canvas/): `bd`, the full birth date, and `dd`, the
full death date. Each is the roster's own `b` / `d` string, **byte for byte**, and only where a day is present: `1882-02-22`, `1950-Mar-19`, or `22 February 1882`. A year alone,
a year and month, or an estimate gets no field (`by` / `dy` and `bye` / `dye` carry those). Only people the builder draws appear (never living, never withheld), so a
living person can never carry either field. **Today no roster row carries a day: `b` and `d` are years, the person pages print years, and no person has `bd` or `dd`.**
The code is in place so the field appears the moment a day-level date is printed for someone. Day-level dates that exist in `households.json` (for example «06 Sep 1626») are
NOT used: the pages do not print them, and the rule is that the canvas shows what the page shows. Decision recorded 16 November 2026 (Record Atlas request; the Lerena pilot, TheLerena 78a663b9).

## Corrections marks (`cx`) in `tree.json`

Each person in `tree.json` may carry `cx`, a whole number of 1 or more: how many rows of `site/src/data/corrections.json` (the archive's public list at `/corrections/`) name this
person. **A count only, never what a correction says.** A row names people through its own `pids` list (person ids, written by hand where the person is plain; a correction about a
claim with no one person in it carries none). The field is omitted when the count is 0, and, like `bd` / `dd`, only people the builder draws can carry it, so a living or withheld
person never does. The person page prints the same count from the same rows (`site/src/pages/person/[pid].astro`, the `CX` constant), linking to `/corrections/`. Added 16 November 2026 (Record Atlas Tree Canvas request;
the coordinator's rules: a count only, derived in the build, never for a living person, the count agrees with the page).

## Details on the not-drawn people, and the living names (17 November 2026, for the Record Atlas Tree Canvas)

**`undrawn` entries carry details.** Besides `id`, `name`, `href`, `b`, `place`, `why`, each now has `given`, `sur`, `sex` (guessed from the first name unless a household says, as for every dead person here),
`by` / `bye`, `dy` / `dye` (a year at or after the living cutoff is never sent), and `father`, `mother`, `spouse`, `kids` (ids in this file). Dead people only. The canvas draws them as unplaced cards.

**Living rows (`meta.living` is `"names"`, was `"omit"`).** David decided on 17 November 2026, "Dead and living, as asked": the people whose own pages already name them as living appear in `people`
as `{id, sex, given, sur, father, mother, spouse, kids, living: true}` (+ `surAlso`, a married name the roster already writes in brackets). **A name and relationship links and nothing else**: no year, place, route,
page link, source, corrections count or occupation. `sex` is `u` unless a household records it (a guess from the end of a given name is Person data inferred from nothing). Who:
roster rows the rule, the archive's own `living` flag, or the floor (no death recorded, born within 110 years) calls living, minus the ledger's held ids, minus a birth year at or after the minor line, minus anyone the committed row cannot decide (no birth year and no
death recorded; an estimated year). Second ruling, same day: the 41 people the floor used to withhold (no death recorded, born 1917-1945, so neither dead nor living by the 80-year rule) are named the same way, name and links only
(David: "Yes, name and links only"). **Still out: 10 people whose birth year is only an estimate**, withheld by the estimated-window rule in `build-tree-page.py`
(`living_withheld_estimated_window`): they need David's decision one by one. The 10 estimated-year people are named the same way (David: "Add all of them now"): vincenzo-franceschi-molinella, peter-defranceski, pietro-franceschi-almissa-1828-omis, marion-g-bain-adelaide, robert-robbie-defranceski-1953, daria-de-franceschi, nelida-albina-de-franceschi-mercedes, feliciano-de-franceschi, richard-defranceschi, assunta-maria-de-franceschi-gracisce. `living: true` there means "name only, no dates": Robbie and Daria are dead by family confirmation (no date), Pietro (Almissa, 1828) is almost certainly long dead; none carries a year.
Anyone the archive does not name stays unnamed.

**Stand-ins (`placeholder: true`).** People a household names that have no roster row, so no person page: a parent written in the household (`father` / `mother`, no pid) and a child with no pid. Each is `{id, sex, given, sur, father, mother, spouse, kids, placeholder: true}` with the name as written, **no dates, no places**; ids are `ph-<household key>-<role>` or `ph-<household key>-c<n>-<name>`. Only households read from a register or an index (never David's own tree) that start by 1900, and a child only if born by 1900 (or undated): nobody here can be alive. Some may be a roster person under another spelling whose household link failed; they are cards, not claims of identity. Links run from the stand-in to dead people and other stand-ins; a dead person's row never lists one (the roots page draws no stand-in). A relationship label that is not one edge («first cousin») is not turned into a link, and a living parent whose role no household states
is dropped, both counted in `tree.report.json`. The links run from the living row to the dead people (a dead person's `kids` does not list a living child).

**The price, and what was done about it (David, 17 November 2026).** `tree.json` is embedded in `/roots/` and `/roots/view.html`, so they carry the names. First David accepted that they be searchable; the same day his rule for every archive became: a page that names a living person is `noindex` and out of the sitemap. **Both pages are therefore `noindex`** (a `robots` meta on each) and the kit's `sitemap.py` leaves `/roots/` out. The roots page and the person pages draw no living row (the template drops `living: true` and `placeholder: true` rows on load; `TREE_BY` filters them).

## What is and is not on the page

- **Living and possibly-living people are absent from the drawn people and from the page** (the people the archive names as living or possibly living appear only as name-and-links rows, see above), decided by `living_v2.row_is_living` plus a floor: nobody with no recorded
  death born in the last 110 years, and nobody whose only evidence of death is an estimate. The builder refuses to write if its own
  output breaks the rule. No birth year at or after the cutoff is ever printed without a recorded death.
- **Identity is by record** (see `roster.json`): two rows may be one person; the page shows them as two.
- **Estimated years are flagged**: "c. 1809" is a birth estimated from a parent, child, spouse or death year; "1809–?" is a death not recorded.
- **Sex is guessed from the first name** unless a household says. It only affects kinship wording (mother/father, aunt/uncle).
- **Not drawn yet** lists everyone who cannot be drawn (no year, or no place) with a link to their page. Every roster row is on the page,
  in the withheld count, or on that list.
- **Colour and rows are research lines** (Carnia, S. Istria, Venice, Abroad, Trentino, Other lines, Not yet placed), not surnames,
  because this is a one-name study.

## The five animated views (Painted Lines)

Five more tabs sit beside the ten: **Night sky**, **Ink ledger**, **Household**, **Generations** and **Where they lived**. They are an optional extension of the
template, `scripts/tree-page/painted-lines.ext.html` (tabs, views, style and script in one file), injected by `build_page.py --ext` at the markers in
`tree-views.template.html` (`<!--EXT:TABS-->`, `<!--EXT:VIEWS-->`, `/*EXT:STYLE*/`, `/*EXT:SCRIPT*/`). Without `--ext` the markers are removed and the page is as before.

- **One selection.** They read the page's own `P`, `PL`, `ERA`, `ATLAS`, `st.focus` and `go()`, so choosing a person in the search box, the hourglass or the card redraws
  all fifteen views. Clicking a head, star, name or node inside an animated view re-centres everything.
- **No new data.** Ancestors, descendants and spouses come from the people already in `tree.json`; ground colour and events from the Atlas slice already in `atlas-data.json`.
  Only people with a recorded death are drawn; a `living: true` row is never drawn.
- **A parent link is not drawn where the parent would have been under 13 or over 60 at the birth** (the page says how many). The roster is not edited.
- **Moves are windows.** A person's place is known at their birth, at their children's births, at a recorded move year (`my`) and at death. A leg is drawn between two such
  records and the dot travelling along it only marks the window. A child's birthplace is evidence, not proof.
- **Not in the Atlas yet:** wars and famines. Only the Atlas's own events are drawn (flu 1918, Jasenovac, the Holocaust and so on).
- The hash is `#sky`, `#ink`, `#house`, `#gen` or `#routes`; `#p=<id>` chooses the person.

## Routes (three or more places)

A roster row's `places` (or a `place` written "A → B → C") is the route of a life in order. `build-tree-page.py` carries it whole as `route` when it has three or more
places and starts at the drawn birth place and ends at the drawn death place (a mismatch is listed in `tree.report.json` as `route_start_mismatch`, not drawn). A row may
also carry `moves: [{"place", "y", "est", "g"}]`: the (approximate, when `est`) year a person arrived at a stop, and the grade of that statement (`lore`, `tree`, `doc`).
A stop with no year is an undated arrival: the views list it, draw it dashed, and do not place the person on a map for the years between undated stops. Until 2 November 2026
only the first and last place were drawn, and a father who went Senj, Zimbabwe, South Africa, Brisbane was drawn Senj to Brisbane. `scripts/check-propagation.py` now
holds the old route out of every file that does not quote it on purpose.

## Publishing it

Not wired into the Astro build yet, on purpose: `site/public/*`, the nav and `package.json` are shared ground, and a standalone page in `dist` has
to pass the dist checks (nav, pages, kit, living scan). To publish, decide where it lives, run those checks against a throwaway build, and use
`scripts/whose.sh --allow-shared` if it touches shared files. `roots.html` is a complete document and needs no framework.

## Sync with the skill

`scripts/tree-page/` is the `family-tree-page` skill's code, vendored so CI and other sessions do not need `~/.claude`. The skill's copy is the
master; `build_page.py --check` compares versions.
