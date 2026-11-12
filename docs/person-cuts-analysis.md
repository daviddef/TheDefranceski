# The five cuts of the same persons: what each holds that no other holds

12 November 2026. Written for David, on request of the Family research landing site session. **Nothing here is merged or changed:** these five stay five until David decides. Counts are from the main build (`722e9d00`) and its data files, not from memory.

## The short answer

| Page | What it is | Size | Holds that no other cut holds | Strict subset of another? |
|---|---|---|---|---|
| `/people/` | The roster, one paragraph per person | 2,063 people, ~197,000 words, 2.4 MB | The prose on every person: dates, place, source, note, and the "Others who carried the name" section. 2,063 `/person/` links, 1,359 outbound record links | No. It holds all but 4 of `/who/`'s names, and all of `/households/`' people (631 of 631 `/person/` ids), but only 334 of the register's 1,076 distinct names |
| `/who/` | A bare name index to the `/who/<slug>/` dossier pages | 1,842 names, ~7,400 words | **192 names that are not on `/people/`** (not checked against the register) (names read from records and from the narratives that the roster has no row for) | Not a subset: 1,557 of its names are on `/people/`, 192 are not. `/people/` has 4 names `/who/` lacks |
| `/register/` | The FamilySearch index catch, entry by entry, graded | 1,508 entries, ~31,700 words | **1,153 entries graded `lead`** and 20 `cand` that are in no roster row; all 1,508 are outbound FamilySearch links (1,508 of 1,515 links). Only 335 are graded `in` and found in the roster | No. About 77% of it exists nowhere else |
| `/households/` | The reconstructed parent pairs, with children | 164 households (161 distinct), ~25,000 words | The household as a unit: 688 `/person/` links, the "large households" narrative, the confirmed/read grading. 540 of its links come *from* `/people/` | No. It is the base the explorer is drawn from |
| `/explorer/` | A search / year / region / chain view over the households | 52 households (50 distinct), 200 children, ~1,000 words | The filter UI and the up/down chain links between households; 2 couples (of 50) that `households.json` lacks | **Almost.** 48 of its 50 couples are also in `/households/`; it adds an instrument, not data |

## What each one is for

* **`/people/`** is the only page that says what is known about a person. Everything else points to it (540 inbound links from it to `/households/` alone).
* **`/who/`** is not a duplicate of `/people/`: it is the door to the dossier pages, and it holds 192 names that exist only because a narrative or a register reading named them. Merging it into `/people/` would drop those 192 unless the roster first grew rows for them. The kit's L2 rule ("people read from records with no entry") says that is deliberate.
* **`/register/`** is the least duplicated of the five. It is the unsorted catch, and its own text says "this is the catch, not the family. An entry is not a person." Folding it into `/people/` would put 1,153 unverified leads next to 335 verified people, which is exactly what the page exists to keep apart.
* **`/households/`** and **`/explorer/`** are one dataset (`households.json`, 164 rows; `explorer.json`, 52 nodes) shown two ways. The explorer is a strict subset of the households *as data*, bar 2 couples, but not as an instrument (it filters and walks chains; the households page does not). **The explorer already moved: it is now the `#households` section of `/bloodline/` in PR B (#7), because it reads the chart's link graph.** The households page itself is untouched.

## Who links to each (from page bodies, not the menu)

| Page | Pages linking in | Total links in |
|---|---:|---:|
| `/people/` | 12 | 30 (8 from `/corrections/`, 6 from `/searched/`) |
| `/who/` | 9 | 19 |
| `/register/` | 14 | 56 (24 from `/searched/`) |
| `/households/` | 21 | 618 (540 from `/people/`) |
| `/explorer/` | 3 | 3 |

So the explorer was the only one of the five that almost nothing in the archive pointed to (3 links), which is why it was the safe one to fold in.

## Recommendation (David's call, nothing done)

1. Keep `/people/`, `/register/` and `/households/` as three pages: each holds a different thing (the people, the unverified catch, the family units).
2. Keep `/who/`, but consider whether it should be the *menu's* "Every Name" door only, since it adds 192 names and no prose.
3. The explorer merge in PR B already removes the one cut that was an instrument over another cut's data.

## Other pairs that overlap by content

From the hashed text blocks of the 82 in-scope pages (main build). Share is of the *smaller* page's blocks.

| Pair | Shared blocks | Share of smaller | What it is |
|---|---:|---:|---|
| `/research/` and `/research/sources-and-method/` | 19 | 90% | Both are the Research hub listing the same deep dives. Likely intentional (the trial's two entry points), but the largest overlap on the site |
| `/` and `/lines/` | 259 | 67% | **The home page repeats about two thirds of the Lines page.** Worth a look: one of them is the source and the other a copy |
| `/changes/` and `/searched/` | 507 | 32% | Two generated logs that quote each other's rows |
| `/imotski/` and `/omis-line/` | 69 | 28% | Two Dalmatian pages that share a block of household and place text |
| `/maternal/*` (kovacina, salomon, fernasar) | 9 each | 39% of the smaller | Shared lead-in blocks across the three maternal pages |
