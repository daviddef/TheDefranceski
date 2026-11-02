# Roots & Routes (the tree page)

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

## What is and is not on the page

- **Living and possibly-living people are absent from the files**, decided by `living_v2.row_is_living` plus a floor: nobody with no recorded
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
  Only people with a recorded death are in `tree.json`, so no living person can be drawn.
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
