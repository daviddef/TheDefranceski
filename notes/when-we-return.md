# When we come back

State at 10 September 2026. Site: https://daviddef.github.io/TheDefranceski/

## Where things stand

**Computed by `scripts/audit.py`, not typed.** 1140 people · 112 households · 1508 indexed records (335 accepted, 20 candidate, 1153 lead).

- **162** people with no place · **1** households with no place
- **763** of 1056 dossiers have no pedigree chart
- **6** places hold accepted records but appear on no lane: Kaštelir (4), Pola (2), Sovignacco (1), Pisino (1), Tar (1), Pula (1)
- **3** towns are written under more than one name in the register


---

## First, in this order

**1. ~~Test FamilySearch full-text search.~~ DONE 13 Sept 2026.** Answer: the **Croatian parish books are not in it** — the Vodnjan reading plan stands unchanged. But **US naturalisation, declarations of intention and passenger manifests are**, at full text, and searching the **village name** returns people born there under any surname. Two verified hits for *Gologorica* (Brooklyn 1929, Tacoma 1935–38), neither of them a De Franceschi. **New workstream:** sweep Gologorica, Gračišće, Crikvenica, Vodnjan, Ližnjan as *place* terms. Result counts look inflated and are untested.

**2. Retry Arolsen — STILL DOWN, verified 13 Sept.** `collections.arolsen-archives.org` times out while `arolsen-archives.org` returns 200, so the outage is theirs. `collections.arolsen-archives.org` was down for both of us. Four searches: `Defranceski`, `Defranceschi`, `Blazevic Hedviga`, `Kovacina Ursula`. **The window that matters is 1948–1951** — a failed exit leaves nothing in any Croatian register, so this is the only place it can exist. Any record of **Anton Rudolf after 1943** separately settles whether Uršula was a widow or a wife when the man called *Car* appears.

**3. Corsica — DOORS FOUND 13 Sept.** Tomino's tables décennales are **12 NUM 4186–4194**, nine volumes, unbroken 1802–1892, listed on `/corsica/`. The viewer opens in a pop-up the pane blocks — that is the next thing to solve. Original note: Nothing about it is blocked. Archives départementales de la Haute-Corse, état civil 1793–1902, all communes, free. Tomino first, exhaustively, every hit not just the two names held. Then Rogliano, Ersa, Macinaggio. Plan is on `/corsica/`.

---

## Waiting on you

- **The 101 tree-only people** — worklist sent as a file. The tree has no years for them, but places came back for 48. What's left needs your eye on citations.
- **The living-people list.** You asked for everyone we know of, name only. **The roster still has one.**
- **Ms. / Mr. / Other** — the Arolsen enquiry form needs a title before I can submit it.
- **GEDCOM** — expected around 12 Sept. Reconciled against the roster, never merged into it.

---

## Reading, when FamilySearch relents

- Vodnjan deaths. **Book pages 156–171 READ 13 Sept** — 1831 entries 20–167, **all of 1832 (1–157)**, and 1833 entries 1–3. Both pages of every frame.
  Two De Franceschi in the whole stretch: **Maddalena Francin 14 Mar 1831** and **Pasqua 19 May 1831**, both house 456. **Three** look-alike candidates examined and given up: *«q.m Francesco»* and *«di Francesco»* (image 560), *«da Francesche»* (page 164, entry 21).
  **Count by BOOK PAGE, not by frame.** Consecutive frames share a page; frame 567 is a re-shoot of 566 with cut strips laid on a blank leaf. 581 frames is not 581 pages. Page number top outer corner; entry numbers are the checksum.
  **Resume at book page 176** — 1833 read to entry 81. Pages 156–175 complete.
  Michiela De Franceschi *fu Giuseppe* at page 173 entry 41. The baptism register opens 1815/16, **too late for her own baptism** — so the test is the **marriage register** (Michiela × Domenico Giachin), which would name her father *and* mother. If the mother is **Lucia Tromba**, she is Giuseppe's daughter.
- Then images 471–545, deaths 1815–1828
- **Film 005497895**, deaths 1834–1893 — the richest unopened film; should close most of the **30 open gaps**
- Marriages vol I 217–265, then vol II — settles the two Stefani of the 1850s

*Pace it.* Incapsula blocked after roughly 400 tile requests. Tiles are at `…/image_files/{level}/{col}_{row}.jpg` — the missing `image_files` cost us most of a day.

---

## Mine, needing nobody

- ~~The Trentino cluster~~ **DONE 13 Sept** — `/trentino/` published: 49 people, no register record, plus Giubiasco and Gaillard folded in.
- The backlog, **computed not typed** — see the block at the top, refreshed by `scripts/audit.py` on every publish. The big one is **763 of 1,056 dossiers with no pedigree chart**; the old note said 55.
- ~~Switzerland and Haute-Savoie~~ **DONE 13 Sept** — both on `/trentino/`. Giubiasco is one household of four; Gaillard is one man.

---

## The strategic question, unresolved

Falco shows **10,536 records / 4,779 people** because it read a town's death registers act by act. We show **1,136 / 1,508** because we searched an index for one surname. Our `/archive/` number — **1,151 books catalogued, 997 digitised** — is not a score; it's the size of the job. We've opened a book in **7 of 14 parishes**.

Closing that gap means **reading Vodnjan whole**: ~105 images, ~4,600 entries, roughly 1,000–1,500 tool operations. Worth doing *not* for the counter but because it makes every match testable — which is exactly what those 40 name-alone joins lack.

**But test item 1 first.**

---

## Standing errands — drafted, unsent, yours to send

13 on `/errands/`, including four from your 1948 testimony: Senj births 1926 **and** marriages 1948 · Arolsen · Crikvenica deaths 1943 plus the surname **Car** · the Therapia programmes.

**Already sent:** the Hotel Kvarner Palace (ex-Therapia), 10 Sept — asking what they hold from the Therapia years and, if nothing, where it went.

---

## The Istrian round — 13 September 2026

**Method change that made it work.** Stop matching records to towns by the index's place text — in Istria it is usually «Croazia, Austria» and nothing more. Match by **image ark**: every image is bound into a parish's book, and the book is the parish. `/platform/records/waypoints/<id>?cc=2040054&count=1000&start=0` lists a parish's books, then each book's image arks. Also: **`q.fatherSurname` works** when it is the sole name term (our reference note said every `q.` but `q.surname` was ignored — wrong, and it is the only way into books where the child has no surname).

**Forty-three Istrian parishes tested against 1,768 records. Twenty-two carry the name.**

- **Svetvinčenat 1628** — Elena, daughter of Francescho di Franceschi and Eufemia, 21 Dec 1628. Read on the page. Thirty-eight years before the 1666 the archive had, and thirty-three years *before* Moncalvo, not after.
- **Pazin 1684** — Maria, daughter of Francisco de Franceschi and Marina, 24 March. 107 years earlier than our earliest Pazin record, and 56 years before Kobler's «intorno al 1740» departure for Fiume. The index drops the -i and puts a godparent in the mother's field.
- **Vižinada + Kaštelir + Tar = one family.** Giulio × Maria Ceselin → Francesco Napoleone (b. Vižinada 1818) × Maria Radojković at Kaštelir; Angelus × Lucia-Antonia Rodella, son Julius bapt. Kaštelir 1866, buried Tar 1870.
- **Krbune** — Mariana De Franceschi × Vincentius Marziol, five children 1832–43, in the County of Pazin. **She is one of the 26 lost daughters**, and she was placed by ark, not by working the row. The other 25 should go the same way.
- **Fažana 42 records, all ours** — and Natale Mattio, Vittorio, Elisabetta and Irene, listed here for a year under *Pula*, are Fažana's.
- **Pula: 38 of 85 are ours**; the other 47 are Franceschini/Franceschina, a different family.
- **Rovinj begins 1619, not 1569** (Fracischetto/Francoscheto/Franceschero are not ours). Mattio × Elisabetta baptise two sons 1722/1726; Isabetta buried 4 Dec 1728, Matto «da Dignano» on the 27th.
- **Vrsar 1670–1686** — Francesco × Giacoma, one household beginning and ending in five entries.
- **Kršan** — two De Franceschi women marrying two de Domazetovich men, 1881–94.
- **Draguč holds nothing.** Its 25 were Vižinada's, doubled by the place parameter. Tested blanks now also: Kanfanar, Tinjan, Roč, Novigrad, Marčana, Boljun, Funtana, Plomin, Rakalj, Presika, Rovinjsko Selo, Stari Pazin, Lupoglav, Nedešćina, Kringa.
- **Oprtalj 0 of 9 ours** — it was on this round's own list of fifteen and should not have been.

**Then the same key was turned on the whole pool, and the number reframes everything**

- **`q.motherSurname` works too** — the field the married-out daughters live in. 218 records the surname search had never seen.
- Every record carries **`FS_DIGITAL_FILM_NBR`**. The place is optional; the film never is.
- **727 of 1,619 records — 45% — have no town at all.** Every place-based table on this site was built from the other 55%.
- **396 of the 727 resolve to one parish from the film alone**: Svetvinčenat 102 · Pula 83 · **Dubrovnik-Grad 47** · Sv. Dujam Split 46 · Rijeka 31 · Split-Veli Varoš 15 · Labin 10 · Nerežišća 10 · Dubrovnik-Pile 9 · Rovinj 7 · Barban 6 · Kastav 6 · Vižinada 5 · Split-Stari Grad 5 · Imotski-Glavina 4 · Split-Bol 4 · Vrsar 3 · Poreč 3. **Dubrovnik (56) and Split (~70) are on no lane of the branch chart.**
- **331 sit on reels carrying more than one parish.** 005497884 = Svetvinčenat + Petar u Šumi. 005497893 = Vižinada + the unnamed State Archive item. 005494037 carries seven parishes. **The film number is a fast first pass, not an answer; the ark is the answer.**
- **Proof of that, measured:** film 005497893 holds 112 town-less records and its catalogue creator is «Župa Vižinada». **Two of the 112 are Vižinada's.** The other 110 are the Vodnjan books bound onto the same reel. Attribution by film creator would have misfiled 110 records by forty kilometres — the same reel and the same mistake as the withdrawn «Vižinada, five households 1816–1844».
- **Šterna has a film: 005497888** — shared with Šumber. One ark test settles it. **Run this first.**

**THROTTLED.** After roughly 200 catalogue and waypoint calls in a few minutes FamilySearch returned **403**. Not a wall — a throttle. The archive's own note has said *pace it* since the Vodnjan tiles, and today it was ignored.

**Next, and cheap, because the machinery now exists**
1. **Šterna vs Šumber on film 005497888** — one ark test, five records.
2. Resolve the remaining **331** multi-parish-reel records by ark, worst reels first (005494037 has seven parishes on it).
3. ~~Run the ark test on the 25 lost daughters~~ **DONE 13 Sept — 137 of 155 rows placed.** ~49 are on film 005497893 = **Vodnjan** (not the Vižinada its catalogue names). **Francisca** (9 children) and **Veneranda** (9) are **Svetvinčenat**. **Marietta → Dubrovnik**, **Antonia → Rijeka**, **Dominica/Domenica → Labin**, **Catharina → Barban**. Still unnamed: films 005494789 (9 rows of a Maria), 005494797, 005494798, 005494788, 005497818, 005497822 (5 rows of Mariana, expect Krbune), 005497825, 005497835; and 005497826 carries Pazin+Pomer+Plomin and needs the ark test. 18 rows matched nothing and need re-fetching.
   **Method note:** each search result carries THREE persona ids (child + both parents). Indexing only the principal's matched 1 row of 155; indexing all three matched 137.
4. **Dubrovnik and Split** — 126 town-less records between them, and neither city is on the chart.
2. **Fažana**, 42 records and never read by eye. Two households, books from 1810.
3. **Svetvinčenat marriages 1762–1858** — 19 records found by ark, unread on the page.
4. **Rovinj**, 29 volumes from 1553, 21 records, nothing read.
5. Šterna and Sovinjak are **not in this filmed collection** — they need a different route.
6. The **Labin 1615 Aloysius** is not in the pool; our Labin records run 1826–1866. Worth re-testing.

**Letters out, awaiting reply:** Arolsen (sent 13 Sept) · **HAZU Library, Zagreb — scan of Klen's 1425 Petrapilosa tax roll, Starine 58 pp. 85–124 (sent 13 Sept, thread 1a099eeac2779c13)**.

**Unchanged and still open:** Vodnjan deaths from book page 176; film 005497895; Corsica 12 NUM 4186–4194; Arolsen (enquiry sent 13 Sept, awaiting reply).

### Later on 13 September — the corrections the round produced

- **131 register rows written back with a resolved town** (`pl` + `plsrc:"film"`): Vodnjan 47 · Svetvinčenat 20 · Fažana 10 · Ližnjan 8 · Pula 7 · Labin 7 · Pomer 7 · Krbune 6 · Vižinada 4 · Dubrovnik 4 · Barban 3 · Medulin 3 · Pazin, Rovinj, Rijeka, Galižana, Split 1 each.
- **audit.py** now separates *unlocated* from *located but unread*: «of 40 rows, 20 carry a parish resolved from the film».
- **Six new atlas pages**: Pomer, Krbune, Dubrovnik, Labin, Medulin, Galižana. Two new chart entries: Dubrovnik, and «The daughters' villages».
- **The Labin 1615 is under correction.** Three later measurements cannot find it (rebuilt sweep 1789, by-image 1826, and the register holds no such row). Earliest in Istria that can actually be produced: **Rovinj 1619, then Svetvinčenat 1628**.
- **The head-of-page cluster table now carries a by-image column beside every row.** Oprtalj, Roč and Hum hold none of this family. Šterna 1→11, Rovinj 3→21, Kaštelir 4→17, Ližnjan 18→95, Svetvinčenat 11→118.

### Stopped on a hard block
FamilySearch returned **403 on everything** — search, catalogue, waypoints *and* the Deep Zoom tile service — after a day of heavy use. Earlier 403s cleared in tens of minutes; this one did not within the session. **Resume with light, spaced calls and check `/service/search/hr/v2/personas?...&count=1` before doing anything bulk.**

### First three things when it lifts
1. **Zanetta Gravisi.** Two Šterna marriage entries, arks `3:1:3QS7-L99X-LH9T` and `3:1:3QSQ-G99X-L4BY`, film 005497888, book «Marriages (Vjenčani) 1723-1820». Two *different* images, both naming Bortolo De Franceschi, son of Gio Batta and Zanetta Gravisi/Granisi — one with «Nazario», one with «Zorzi Marchege». Two marriages of Bortolo, or one entry indexed twice? The pages will say. Gravisi is a Capodistrian marquisal name.
2. **Francisca Defranceschi × Antonius Cerneca**, nine children 1831–1846, film 005497886 = **Svetvinčenat**. The head of the lost-daughters queue, now located and still unread.
3. **Fažana**, 42 records and never read by eye: Vittorio × Stella Tamborin and Giuseppe × Giovanna Beluzzi, plus **Maria Defranceschi × Giovanni Moscarda**, six children 1835–1849.

---

## 13 September, late — the find the project was built to get

**«Alli 12 9bre 1777. Cepich. Cargna. — Bortolo figlio del q. Gio: Batta de Franceschi *dalla Cargna*, Diocese d'Udine, ha contratto legitimo Matrimonio coll'Ill.ma Sig.a Zanetta Gravisi figlia dell'Ill.mo Sig.r Marchese Nazario della Villa di Cepich di questa Pieve…»**

Šterna marriage book, page 39, film **005497888**, ark `3:1:3QS7-L99X-LH9T`. **The first entry this archive has found that states where an Istrian De Franceschi came from.** Confirmed word-for-word by an archivist's pencil finding-aid slip filmed with the book (ark `3:1:3QSQ-G99X-L4BY`), which the index counted as a second marriage.

Corrections it forced, same day: Zanetta Gravisi is Bortolo's **wife**, not his mother; there was never a second marriage.

**Open from it:**
1. **Gio: Batta de Franceschi of Carnia** — dead before 1777, in no Istrian register. Now look for him in Carnia: Ovaro/Mione, Paluzza, and the Udine diocesan books.
2. **Marchese Nazario Gravisi of Cepich** — the slip also records «Nazario Gravisi 29/5 1737», presumably his own marriage, in the same book.
3. Šterna's books run **1723–1836** and only this one page has been read.

## VPN was the cause — and the rate limit is separate

Turning the VPN off cleared Error 15 immediately. **But with the VPN off it still returned after ~25 calls.** Two different limits. Budget bursts of ~20 calls, pause, and spend them on images rather than index rows.

## Since the VPN came off
- **Francisca Defranceschi married JOANNES BERGAMO**, not Antonius Cerneca, and the "nine children 1831–1846" are the **weddings of four sons**. The Svetvinčenat marriage book is a ruled table with printed GENITORES SPONSI / GENITORES SPONSAE columns; the index flattens all four parents into one list. **Every husband inferred from an `o` list on a post-1815 marriage row is suspect** — birth rows are safe. The 19 husbands placed earlier were re-checked: 17 rest only on birth rows, the other two have birth rows too. They stand.
- Bergamo is on Kandler's list of Carnian families at Sanvincenti, beside Defranceschi. With *Vittorio De Franceschi × Eufemia Bergamo* in the same book, that is two Carnian houses intermarrying twice, a generation apart.

## Still to read, in this order when the limit allows
1. **Vodnjan book page 173** — the Michiela/Domenica Giachin conflict. Film 005497894; book page 164 ≈ image 560, so try images 565–572. Note the Giachin rows are all **birth** rows, so Domenica and Michiela really are the mothers; the conflict with the death-register reading stands.
2. **Nazario Gravisi, 29/5 1737**, recorded on the Šterna finding-aid slip — same book as the Cargna entry.
3. **The rest of Šterna's marriage book, 1723–1820.** This priest wrote origins in the margin. One page gave «Cargna»; there may be more.
4. Vodnjan deaths from book page 176; film 005497895.

## Blocked again, harder
FamilySearch returned **Access Denied Error 15** on every endpoint — search, catalogue, waypoints *and* tiles — in **both** browsers, after ~40 calls. It reports `clientIp 168.140.255.212 / proxyIp 45.223.168.251`. **That looks like a VPN exit: ask David to turn a VPN off before anything else.** Signing in does not help; the block is above authentication.

## Local work finished while blocked
- Suppressed charts **55 → 46**, and the audit now bands them: only the ≤25-year ones are work.
- **75 charts** drawn from a single indexed birth row (Colotta and Fioretta of 1666 among them), with three guards: two-word keys, birth rows only, and the date gate.
- **Twenty false birth years** corrected — first-appearance dates carried in as births. Rule: parent in a household, same place, year inside the childbearing span.
- **Kršan** given a page; Anna Maria Francisca's dates fixed from this site's own Gologorica page (b. 1860, d. Trieste 1941), which links the Kršan Domazetović marriages back to Gologorica.

---

## 13 September, evening — Vodnjan film structure, and a numbering question

**The Vodnjan film is filed under the ORTHODOX branch of the waypoint tree**, which is why it never appeared in the Roman Catholic parish list and why earlier attempts to find its waypoint failed. Working ids:
- Film 005497894, 581 images: `9R2D-927:391644701,391690101,391807401`
- Its parent: `9R2H-GPX:391644701,391690101` («Vodnjan»), under `9RKB-BZ7:391644701` («Orthodox (Pravoslavna crkva)»).

**A numbering question to settle before resuming.** Image 573 of that film is a *Liber Defunctorum* opening of **1832**, entries roughly 85–118, and the printed page number in the top outer corner appeared to read **76** — not 173. Read at low magnification only, and the block hit before it could be confirmed.

If that is right, this archive's «book page 156–175» and «resume at book page 176» are **its own running count, not the book's printed numbers**, and the resume instruction is ambiguous for anyone else. **First job next session: open image 573, read the printed page number at full magnification, and either confirm the archive's numbering or restate the resume point in image numbers.**

**Forebears town sweep, started.** Gračišće and Vodnjan done (see `/places/vodnjan/` for the result — the esodo visible in a surname list). Ližnjan's slug does not resolve as `liznjan` or `ližnjan`; find the right one. Gologorica has no page.
