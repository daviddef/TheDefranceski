# Menu reach, 23 November 2026 (the estate clean-up, Task C)

David's rule: nothing is lost from reach. Every page that left a menu is linked from a hub that is itself in the menu. Proved with the kit's
`menu_inventory.py` (`snapshot` of the build before, `compare` against the build after; the scope is `docs/menu-scope.json` plus every `/map/*` and `/married-in/*` page).
Result: every old URL still answers; every text block that stood on a page still stands somewhere on the site, except the five reworded or removed on purpose (below).

## Menu links, before and after (header menu of the home page, group headings counted)

| Group | Before | After |
|---|---|---|
| Start | 3 | 3 |
| Our line | 15 | 15 (as is: the archive's own line pages) |
| People | 13 | 8 (Lists 7, one link "Drawn") |
| Places & families | 18 | 14 (Places 6, The families 5, Walking it 3) |
| The name | 9 | 4 |
| Research | 24 | 13 (the eight core pages and Gallery in three groups, one "Deep dives") |
| Total | 82 | 57 |

## What left a menu, and where it is reached from

| Left the menu | Reached from now |
|---|---|
| People / Drawn: Our line, drawn; The trees; Blood relatives, drawn; Household Explorer; The Timeline (Roots & Routes was removed in Task A) | `/drawn/` (these, and The Spine, Lives on one scale, The Lines, each with one line) |
| The families: Svetvinčenat, Omiš, Imotski, Seget, Ližnjan, Rijeka, Dubrovnik, Corsica, Trentino; "Bakar, Fiume & the unplaced" | `/families/` ("All the families", every family of the book: the seven families, the mothers' families, all 21 `/married-in/*` pages). Ližnjan, Omiš, Rijeka and Svetvinčenat stay named. "Bakar, Fiume & the unplaced" is `/lines/#regions`; `/lines/` stays in Places. |
| The name / In the records: imperial service, Julius, Fiume 1626, At sea, the Giornaletto | `/research/deep-dives/` ("The name in the records") |
| Research / Deep dives (Carlo's Letter, Carlo's Book, The Library, Findmypast, the live tree, the DNA) and Registers and places (Archive, Parish Books, The Map, Every collection walked, The undigitised, Antenati) | `/research/deep-dives/`, which is the one "Deep dives" entry of the menu |
| `/map/*` (nine provider layers, outside every menu until now) | `/research/deep-dives/` ("The map, one provider at a time"), and `/map/` as before |
| `/married-in/*` (21 pages, outside every menu until now) | `/families/` ("Families that married in", "The mothers' families"), and `/marriages/` as before |

The three hubs (`/drawn/`, `/families/`, `/research/deep-dives/`) are indexable, in the sitemap, in the book (`src/data/book.json`, so on `/contents/` and in the running heads) and in `docs/menu-scope.json`.
The Research hub (`/research/`) and `/research/sources-and-method/` still list every deep dive in full; their "Deep dives" heading now links to the hub.

## Blocks that are not on the new site, on purpose

- `/contents/`: 52 chapter lines renumbered because three chapters were added (the hubs) and one removed (Roots & Routes); the same chapters stand.
- `/map/`: the Atlas list item "Roots & routes on the Atlas" (Task A).
- `/omis-line/` and `/worklist/` (56 blocks): "Roots & Routes" reworded to "the tree" (Task A).
