# defranceski.com — the reckoning of the old Google Site (retired page, kept as a record)

> **Retired on 22 November 2026, at David's instruction.** David said of the page *https://archive.defranceski.com/old-site/*:
> "my users are new, save it for our own record, but doesnt need to be kept, remove it". The page was taken off the public
> archive in the pull request that adds this file; `/old-site/` now redirects to `/mymap/` (David's Map). This file is the
> record. It is **not served**: it lives in `docs/`, outside `site/`, and the deploy publishes only `site/dist`.
>
> **Which "defranceski.com" is meant.** The page below was about the *old Google Site* (`sites.google.com/defranceski.com/defranceski/`),
> which the page was written to record before it was switched off. The domain **https://defranceski.com/ is now the landing site**
> (its own repo, `daviddef/Defranceski-Home`), not the old Google Site.
>
> **Faithful copy.** Everything below is the page's own text, taken from `site/src/data/oldsite.json` as it stood on `main` just before
> removal (a lossless copy of that file is kept beside this one as `old-site-data.json`; the page template is `site/src/pages/old-site.astro`
> in the git history, last present in the commit before the retirement). The text is unchanged; only the layout (cards, table, link
> lists) is flattened to plain Markdown. Dates and counts are as of when the page was written (September 2026); phrases such as
> "still live" and "before it is switched off" describe that time, not now. The page's section order is kept.

---

## Page title and strapline

**Title:** defranceski.com  
**Eyebrow:** Before the old site is switched off

Before defranceski.com is switched off, everything on it was captured, compared against this archive page by page, and either matched to where it already lives here or written down as something new. This is that reckoning. It is published rather than kept in a notebook so that anyone who remembers the old site can see what became of each part of it.

## 1. The old site is on the public record now

David is switching **defranceski.com** off. Before that happened, **all twelve of its pages were submitted to the Wayback Machine and captured** — on **14 September 2026**. This is the standing reference: the permanent address of every page, and the live one while it lasts.

### Every page, permanently, at the Internet Archive

Twelve captures, all reported **success** by Save Page Now and verified by fetching them back. *The People* came back at 413 KB — byte for byte the size of the live page — so these are whole captures and not stubs.

- The site root · 14.09.2026 — <https://web.archive.org/web/20260914000832/https://sites.google.com/defranceski.com/defranceski/>
- Home · 14.09.2026 — <https://web.archive.org/web/20260914000817/https://sites.google.com/defranceski.com/defranceski/home>
- Family Trees · 14.09.2026 — <https://web.archive.org/web/20260914000908/https://sites.google.com/defranceski.com/defranceski/family-trees>
- The People · 14.09.2026 — <https://web.archive.org/web/20260914000929/https://sites.google.com/defranceski.com/defranceski/the-people>
- The Places · 14.09.2026 — <https://web.archive.org/web/20260914001719/https://sites.google.com/defranceski.com/defranceski/the-places>
- The Places · The Map · 14.09.2026 — <https://web.archive.org/web/20260914001729/https://sites.google.com/defranceski.com/defranceski/the-places/the-map>
- The Story · 14.09.2026 — <https://web.archive.org/web/20260914001835/https://sites.google.com/defranceski.com/defranceski/the-story>
- The Story · The Name · 14.09.2026 — <https://web.archive.org/web/20260914001922/https://sites.google.com/defranceski.com/defranceski/the-story/the-name>
- The Story · The Coat of Arms · 14.09.2026 — <https://web.archive.org/web/20260914001942/https://sites.google.com/defranceski.com/defranceski/the-story/the-coat-of-arms>
- About · 14.09.2026 — <https://web.archive.org/web/20260914001807/https://sites.google.com/defranceski.com/defranceski/about>
- About · Publications · 14.09.2026 — <https://web.archive.org/web/20260914001815/https://sites.google.com/defranceski.com/defranceski/about/publications>
- About · Resources · 14.09.2026 — <https://web.archive.org/web/20260914001825/https://sites.google.com/defranceski.com/defranceski/about/resources>

**Before this, the Wayback Machine held two pages of the site and no more**: the root of 1 January 2022 and the home page of 11 July 2025. Family Trees, The People, The Places, The Map, The Name, The Coat of Arms, Publications, Resources and About were archived nowhere on the public net. Google Sites builds its navigation in script, so the crawler had never followed it below the front page — and the page list had to be read out of the page source rather than crawled, for the same reason.

The two sub-pages under *The Story* were not in the archive's own reckoning table, which folded them into their parent. Reading the source found them. **Twelve pages, not nine.**

### One thing the capture cannot hold, and the reason the KML matters

*The Places · The Map* archived at 150 KB, and the surname does not appear in it once. That is correct and expected: the page is a frame around **Google My Map `mid=1NSF2idD4Q8mN0VQGpBwWPgoJp6Ba1sk`**, and a Wayback capture keeps the frame, not the map inside it. The reference survives; the pins do not.

**This is why both My Maps were exported as KML on 8 September 2026** and are held with the archive's own material. A My Map dies with the account and no crawler saves one — it is the single part of the old site that archiving could never have rescued.

### What it took, which is worth writing down

**Save Page Now no longer accepts anonymous requests.** A POST without a session returns *401 «You need to be logged in to use Save Page Now»* — a change from the days when that endpoint was open to anyone. David signed in; no credential passed through this project.

It also rate-limits a signed-in account: submitting twelve pages nine seconds apart drew **429** twice, and both were taken on a later pass. The other Google Site on the same domain, **drawinglight**, keeps its single capture of 28 November 2021. It is not family history, and is noted only so that nobody later wonders whether it was missed.

- drawinglight, 28 November 2021 — <https://web.archive.org/web/20211128205016/https://sites.google.com/defranceski.com/drawinglight/home>

### The live site, while it is still up

Until David turns it off, the original is still the easiest thing to read.

- defranceski.com — <https://sites.google.com/defranceski.com/defranceski/home>

## 2. What was taken off it, and where those files are

### The whole site, as HTML

All eleven pages fetched and stored: home, about, about/publications, about/resources, family-trees, the-people, the-places, the-places/the-map, the-story, the-story/the-coat-of-arms, the-story/the-name. In this project's source library under «oldsite/html-capture-2026-09». It is a Google Site, so it will not be recoverable once the account is closed.

### Both Google MyMaps, exported as KML

«Defranceski Family» — the primary map, 1,345 placemarks in ten layers — and «Old Defranceski Family», 93 placemarks. Exported as KML while they were still live and archived. This was the single most urgent thing on the site: the maps are David's own research, not published anywhere else, and a MyMap dies with the Google account that holds it.

### What is in the primary map

«Family Search Books Available», 1,022 pins — every Croatian place with a FamilySearch book, which is a research instrument in its own right. «My Known Defranceski Family», 37. «Istra Lines of Defranceschi», 42. «Bepo and Nana De Franceschi», 21 — the Omiš–Imotski narrative. «Italian Lines», 90. «High Level of Emigration from Here», 44. «German Defranceski's», 14. «Early Line in Rijeka», 4. «Random Markers», 6. And an untitled layer of 75.

### The two maps themselves

Both are still live at the time of writing and both are archived as KML. If the Google account goes, the archived files are the copy of record.

- Defranceski Family — the primary map, 1,345 placemarks — <https://www.google.com/maps/d/viewer?mid=1NSF2idD4Q8mN0VQGpBwWPgoJp6Ba1sk>
- Old Defranceski Family — 93 placemarks — <https://www.google.com/maps/d/viewer?mid=1c_ed3kiZa4vw9k0NKH0mjpUmOPlFsL1a>

## 3. Page by page: what the old site said, and where it is now

Three columns on the page: *On the old site* · *What it said* · *Where it is now*.

### Home — the purpose, and the six hotspots

- **What it said:** Seget, Gologorica, Ližnjan, Omiš, Mione, Corsica, and onward to Koper, Crete, Johannesburg, Germany, the United States and Australia.
- **Where it is now (as of September 2026):** Every one of those is a page or a section here. Ližnjan is now third of eighteen towns in the record sweep and has its own man in Ante Defrančeski; Corsica is on the roadmap; Crete is the Seget tradition, argued against on the Carnia page.

### Family Trees — the linear chart

- **What it said:** Giovanni 1750–1829 · Giovanni 1787–1846 · Antonio 1825–1894 · Josip 1863–1951 · Antonio 1890–1943 · Ivan 1925–1995 · Ivan · David.
- **Where it is now (as of September 2026):** Carried across exactly, and every one of those dates is now on the Direct Line page — most of them with the register page behind them rather than the chart. Nothing was lost and a good deal was added.

### The People

- **What it said:** Carlo, Camillo, Andrea and Titian, Girolamo, Alessandro OP, Francesco the painter, Francesco the printer, Domenico, Mariano, Carlo Francesco the composer, the two Napoleonic Defrance / Franceschi-Delonne.
- **Where it is now (as of September 2026):** All on the Namesakes page, most now with fuller lives and every one labelled as kin or not kin. Two remain owed: Andrea and Titian, and Francesco the painter — both still open, both listed on the roadmap.

### The Places, and The Map

- **What it said:** Google MyMaps embeds.
- **Where it is now (as of September 2026):** The Atlas replaces the embed; the KML is archived so the underlying pins survive independently of Google.

### The Story · The Name

- **What it said:** The spellings: Franceschi, De Franceschi, Franceschini, Defrančeski, Defranceschi, Dei Francesci, de Franceschi.
- **Where it is now (as of September 2026):** The Name page carries all of these and more, with counts. «Defrančeski» is now evidenced three times in print and in five Zagreb graves; «Franceschini» and «Dei Francesci» are noted as variants this archive has not found in its own records.

### The Story · The Coat of Arms

- **What it said:** houseofnames, heraldrysinstitute, coadb, plemstvo.hr, and the Blasonario Giuliano PDFs.
- **Where it is now (as of September 2026):** The Arms page rests on the Blasonario Giuliano entry and on Carlo's own blazon in his letter to Kobler — and now on photographs of the carving itself. The commercial crest sites are recorded below as consulted, and not relied on.

### About · Publications

- **What it said:** The works of Carlo and Camillo, with links.
- **Where it is now (as of September 2026):** Sources page and the person pages, with the acquisition list in the Search Register.

### About · Resources

- **What it said:** A link list for researchers.
- **Where it is now (as of September 2026):** Carried over in full, below.

### About

- **What it said:** A Google Sites template that was never filled in — «Tell your viewers about how the club got started».
- **Where it is now (as of September 2026):** Nothing to migrate.

## 4. Checked again, line by line, on the three pages you named

The reckoning above was made from the whole site at once. On 8 September 2026 the three pages you asked about — **The Name**, **The Coat of Arms** and **The People** — were re-read out of the stored HTML, claim by claim, against what this archive now publishes. Three things were genuinely missing. They have been written. Two things are deliberately not carried, and here is why.

### The Name — closed

The old page's variant list ended with two forms this archive had never addressed. **«Dei Francesci»** is now on the Name page with the verdict it deserves: not found once in eighteen towns, and almost certainly *dei Franceschi* with the -h lost in transcription. **«Franceschini»** is now there too, with the correction that it is **not a variant of this surname at all** — it is Franceschi plus the diminutive -ino, formed independently wherever Francesco was a common name. Four people in this archive carry it, every one of them by marriage or as a mother's name.

### The Name — already here, and tested

Everything else the old page carried from plemstvo.hr is here: Niccolò and the Buda charter of 8 March 1359, the 1838 submission to the Austrian nobility commission, Heyer von Rosenfeld 1873, Zuane and Perinuša, Giovanni de Franceschi of «La Dalmazia». One claim was tested and **failed**: «Franceschi dalle Rose», Ravenna to Venice in 1040 and the Giudecca, is the origin story of the **Donà dalle Rose** — a different Venetian house entirely. That is on the Searched page so it is never repeated.

### The People — closed

**Toma de Franceschi** is now on the Namesakes page. Notary of Zadar: sworn to the city council by hereditary right in 1714, appointed public notary in 1722, forty years in the office, and — the detail worth having — running his practice in **Croatian as well as Italian**, in a city whose notarial record is otherwise Latin and Venetian. His son Ivan Krševan followed him. He matters because a notary of forty years leaves an archive, and the Zadar notarial fond is where the whole Croatian noble claim can actually be tested.

### The People — already here, and then some

The old page had eleven figures. This archive has twenty-eight, every one labelled kin or not kin, and the two the earlier reckoning listed as still owed — **Andrea dei Franceschi and Titian**, and **Francesco the painter** — have both since been written. Piero della Francesca, Girolamo, Alessandro OP, Domenico, Mariano, Carlo Francesco, and both Napoleonic Defrance / Franceschi-Delonne are all present with fuller lives than the old page gave them.

### The Coat of Arms — well ahead of it

The old page reproduced four Blasonario Giuliano blazons and linked houseofnames, heraldrysinstitute and coadb. The Arms page here carries the same four — the stork of Gianantonio 1724, the lion, Carlo's cross-arrows-and-pomegranate, and Giacomo of Pisino 1788 — **drawn**, translated, and set against three independent witnesses the old site did not have: Carlo's own letter of about 1873, Matejčić's 1979 architectural survey recording the shield on the Moncalvo façade, and the 2012 American reunion album describing the same weathered stone. It also says plainly what the old page did not: **there is no coat of arms for a surname**, and the crest vendors are selling a picture keyed to a text string.

### Not carried, on purpose — the works list

The old People page ran a long catalogue of **Piero della Francesca's paintings**, museum by museum: Arezzo, Berlin, the Gardner, the Uffizi, Lisbon, the National Gallery, Thyssen-Bornemisza, the Brera, Poldi Pezzoli, Monterchi, the Frick, the Louvre, Perugia, the Tempio Malatestiano, Sansepolcro, Urbino, the Accademia, Washington. It is a good list and it is **not family history** — no connection between the Tuscan Franceschi and this family has ever been shown, and a hundred-line museum catalogue for a man we cannot claim would be the largest single block of text on the site. He keeps his entry on Namesakes, with the diptych, and the catalogue stays in the stored HTML.

### Not carried, on purpose — the living

The old page listed the members of the Croatian Noble Corps by name, with birth years, professions and current cities. **They are living people.** This archive omits the living rather than hiding them, so they are not here and will not be. The stored HTML keeps the record for the family's own use.

## 5. And four things on the old site that this archive did not have

The comparison was supposed to be a formality. It was not.

### «Franceschi dalle Rose» — chased, and it is almost certainly a confusion

The pin read «Franceschi dalle Rose Move 1040 to Venice», with Ravenna and the Giudecca beside it. Searched: the form does not exist in the literature. What does exist, and matches the pin exactly, is the **Donà dalle Rose** — a Venetian noble house whose own origin story runs from Romagna and Altinum, which is to say Ravenna, whose «dalle Rose» is the main surviving branch, and which gave Venice two Doges. «Dalle Rose» is their byname, not this family's. The likeliest reading is that a nobiliary source was misfiled at some point and the two ran together. It is recorded here so that it does not get repeated: this archive can find no Franceschi dalle Rose anywhere.

### A German branch route this archive had no idea about

The «German Defranceski's» layer runs Ližnjan → Monheim, with «Grga dies in Zagreb», and separately «Petar Moves to Metzingen». Metzingen is four kilometres from Pfullingen, which is where the family's own wartime papers are from. Ližnjan is the third-largest cluster in the record sweep. Neither Grga nor the Monheim line appears anywhere in this archive.

### The Veneto emigration hotspots, and São Paulo

A layer of forty-four pins — Castelnuovo, Pederobba, Cornedo Vicentino, Castelgomberto, Scorzè, Moniego — all in the Veneto, all marked as places of heavy emigration, ending at «State of São Paulo». This archive's Diaspora page has the Brazilian cluster as the largest of all and has never had a departure region for it. Here is a candidate one.

### The Dalmatian narrative, laid out as a route

Ravenna → Venice 1040 → Giudecca → Niccolò to Zadar in the 1300s → Tomasso to Omiš → Francesca de Franceschi from Venice to Omiš in the 1500s → Zuane to Imotski → Antonio to Proložac → Antonia to Trsat → Pisak and Vruja. Most of it this archive now holds independently and in more detail. Two names in it are new: Tomasso, and Francesca de Franceschi of the 1500s.

## 6. The resource links from the old site, carried over

Kept because a link list a family actually used is worth preserving, and because saying which of these this archive relies on — and which it does not — is part of the point.

### Archives and registers

- Državni arhiv u Pazinu — parish registers A to K — <https://www.dapa.hr/maticne-knjige-mjesta-od-a-do-k/> — The state archive this family has actually bought certified copies from, twice.
- Portale Antenati — Italian state archives — <https://antenati.cultura.gov.it/find-the-archives-2/?lang=en> — Blocked to this project's network; recorded as not circumvented.
- FamilySearch — Udine genealogy wiki — <https://www.familysearch.org/en/wiki/Udine,_Friuli-Venezia_Giulia,_Italy_Genealogy>
- FamilySearch — Latin genealogical word list — <https://www.familysearch.org/en/wiki/Latin_Genealogical_Word_List> — Genuinely useful for reading these registers.
- Archives nationales — BB/29, First Empire letters patent — <http://chan.archivesnationales.culture.gouv.fr/> — Where the Napoleonic titles of Defrance and Franceschi-Delonne are registered.

### Regional and community

- Istra County — <https://www.istra-istria.hr/hr/>
- Istrianet — Camillo De Franceschi — <https://www.istrianet.org/istria/illustri/de_franceschi/camillo/> — The two portrait photographs of Camillo are here.
- Istria–Fiume–Dalmatia, Italian biographies — <http://istria-fiume-dalmatia.blogspot.com/p/italian-biographies-istria.html>
- Smrikve — Seget — <https://www.smrikve.com/istria/books/smrikve/places/west-istria/seget/> — On the other family's house.
- Croatian Roots — <https://croatianroots.com/services/> — Commercial research service.
- FEEFHS — Croatia — <https://feefhs.org/resource/croatia>
- DVHH — Danube Swabian Heritage — <https://dvhh.org/>

### Reference and biography

- Treccani DBI — Carlo De Franceschi — <https://www.treccani.it/enciclopedia/carlo-de-franceschi_(Dizionario-Biografico)/>
- Treccani DBI — Girolamo de Franceschi — <https://www.treccani.it/enciclopedia/girolamo-de-franceschi_(Dizionario-Biografico)/>
- Istarska enciklopedija — <http://istra.lzmk.hr/clanak.aspx?id=672>
- Hrvatska Wikipedia — Carlo De Franceschi — <https://hr.wikipedia.org/wiki/Carlo_De_Franceschi>
- Geni — Obitelj Franceschi noble family project — <https://www.geni.com/projects/Obitelj-Franceschi-de-Franceschi-Noble-family/46506>
- Catholic-Hierarchy — a Franceschi bishop — <https://www.catholic-hierarchy.org/bishop/bfrancesa.html> — Bishop of Forlì, d. 1601.
- Poskok — the De Franceschi at Imotski, 1717 to today — <https://poskok.info/obitelj-de-franceschi-u-imotskom-od-1717-do-danas/> — Now the backbone of this archive's Imotski page.
- Academia.edu — Titian's portraits of Andrea de Franceschi — <https://www.academia.edu/30396204/> — Behind a Cloudflare wall from here; not circumvented, and still owed.

### Heraldry — consulted, not relied on

- Blasonario Giuliano, letter D — <https://www.unioneistriani.it/wp-content/uploads/2021/12/Blasonario_D.pdf> — This one IS relied on: it carries the family's entry.
- Blasonario Giuliano, letter F — <https://www.unioneistriani.it/wp-content/uploads/2021/12/Blasonario_F.pdf>
- Plemstvo.hr — Franceschi — <http://www.plemstvo.hr/obitelji/franceschi>
- Heraldry's Institute — <https://www.heraldrysinstitute.com/lang/en/cognomi/Franceschi/Italia/idc/5784/idt/en/> — Commercial.
- House of Names — <https://www.houseofnames.com/au/franceschi-family-crest> — Commercial, and sells crests. Recorded because the old site used it; this archive does not.
- COADB — <https://coadb.com/surnames-rough/franceschi-coat-of-arms-family-crest> — Commercial.

## 7. The verdict

**On the evidence of a page-by-page comparison, defranceski.com can be switched off without losing anything — provided the two MyMaps are either kept alive or left as the archived KML, which they now are. Everything else it carried is either here already, in better condition, or is written down above as something still to do. Re-verified on the three pages you named — The Name, The Coat of Arms and The People — on 8 September 2026; three gaps found and closed, two omissions made deliberately and stated above.**

## Sources cited at the foot of the page

The page's source list was `dfcom`, `familysearch`, `dapa`, `blasonario`, `istrianet` (entries in `site/src/data/sources.json`, which stay; `dfcom`, "defranceski.com — the family's own site", is still cited on /name/, /namesakes/, /arms/, /liznjan/ and /lines/).

## Where else the page was listed or pointed to (all removed or reworded in the retiring PR)

- **Research menu** (`site/src/lib/research-menu.js`): `{ href: "/old-site/", label: "defranceski.com", source: "dfcom" }`, between "Findmypast, swept" and "The live tree, reconciled".
- **Book chapter** (`site/src/data/book.json`, group "Investigations"): title "defranceski.com"; blurb "The old site captured and compared with this archive page by page, and what was written down as new."
- **Menu inventory hold text** (`docs/menu-pages-hold.json`): "The old Google Site defranceski.com captured and compared with this archive page by page, and what was written down as new."
- **/mymap/** carried the link "What else was saved before the switch-off →" to this page.
- **/liznjan/** said "The pin came off defranceski.com, archived before it is switched off", linking here; it now says the pin came off the old defranceski.com Google My Map, archived in the Wayback Machine (no link).
- **Errand 21** (`site/src/data/errands.json`), "Put the twelve pages of defranceski.com on the public record before it is switched off", gave as its reference "web.archive.org/save · the URL list is on /old-site/"; it now says the list is in this record (`docs/retired-pages/old-site.md`).
- **Two Search Register rows** (`site/src/data/searched.json`, keys `src/the-wayback-machine-everythi-c3251c` and `src/david-s-google-my-map-import-04350f`, both 14 Sept 2026) listed `/old-site/` among the pages they updated; only that link was dropped (see the PR for exactly what), the rows and their text stay as research history.
- Generated or historical files that quote the page's text and are left as snapshots: `docs/menu-*-inventory*.md`, `docs/menu-*-before.json`, `docs/changes-snapshot-before.json`, `site/src/data/changes.json`, `site/src/data/worklist.json` (a 14 Sept note that the page was fixed for mobile width).

## What the Wayback / KML references amount to (index for finding them in this file)

- Twelve Wayback Machine captures, all taken 14 September 2026 (Save Page Now; 401 for anonymous POSTs, 429 twice on the first pass), listed under section 1 with their permanent addresses. Earlier captures: site root 1 January 2022, home page 11 July 2025 (<https://web.archive.org/web/20250711044602/https://sites.google.com/defranceski.com/defranceski/home>, cited in the Search Register). *drawinglight* (other Google Site on the same domain): one capture, 28 November 2021.
- Two Google My Maps, exported as KML on 8 September 2026 (1,345 + 93 placemarks), described in section 2, with their viewer addresses. As the page itself says: the eleven-page HTML capture is in the project's source library under `oldsite/html-capture-2026-09`, and both KML exports are "held with the archive's own material" (the page names no folder for them); none of those is in this repository. What this repository does hold: `docs/family-map-export.json` (an earlier JSON export of the primary map's pins, layer by layer, starting with "Family Search Books Available") and the map's content as imported into `site/src/data/mymap.json`. The map's content was imported into the archive's own data (Search Register row 14 Sept 2026: 10 layers, 1,289 pins, 56 lines, 10 polygons, 111 notes, 188 links) and is shown on /mymap/ and the Atlas (/map/).

