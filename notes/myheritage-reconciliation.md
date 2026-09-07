# MyHeritage reconciliation — 7 September 2026

David's live tree, read directly from his logged-in session.

**The 2018 GEDCOM is superseded and must not be used again.**
`Family Trees - MyHeritage/Exports & Backups/2018-07 Defranceski.ged` — 8,286
individuals. The live tree has **15,643**. David: "really old and really wrong".

## How it was read
- Site key `OYYV7AGVV4FMSGNWXC6TO74JQDUMOYA`, six family trees, root tree ID 4.
- Name lookup: `/FP/API/individual-lookup.php?siteID=…&query=…&formatAsJSON=1`
  (errors with "Too many individuals" on a bare surname; query given+surname).
- Person detail: `/people-{SITE}/…?action=panel&s={SITE}&lang=EN&individualId={ID}`
  returns JSON with names, dates, places, relationship, photo — and the source
  citations, including FamilySearch ark URLs.

## What was harvested
- **459 individuals** carrying the surname, across 420 given-name × spelling queries.
- **211 of them carry source citations**, **262 distinct FamilySearch arks**.

## Places, by count
Mione 29 · Gologorica 21 · Telve (Assunzione di Maria SS.) 18 · Rijeka 16 ·
Ližnjan 15+4 · Crikvenica 12 · Gračišće 11+7 · Omiš 9 · Bakar 8 · Pula 7 ·
Poreč 7 · Kaštelir 6+3 · Mostacin 6 · Brescia 6 · Vitipolis 5 · Lestans 5 ·
Laives 5 · Paluzza 3 · Trieste 3 · Senj 2 · Basel 2 · São Paulo 2 · Dachau 1

## The direct line, as the live tree has it
| Generation | Live tree | Our site | Delta |
|---|---|---|---|
| 7 gens back | Johannes/Giovanni Gian Battista de Franceschi, b. 1750 Gologorica, **d. 14 Oct 1829 Gračišće**, ark 3:1:3QS7-899X-5SJM | "Giovanni 1750–1829", no page ever put in front of him | **Places and an ark we did not have** |
| 6 gens | Giovanni Battista, b. 13 Aug 1787 Gologorica, **d. 14 Sep 1846 Gračišće** | b. 13 Aug 1787, d. 1846 | **Exact death date; birthplace given as Gologorica not Gračišće** |
| 6 gens (wife) | Francisca Salamon, b. 17 Mar 1797 Gračišće | same | agrees |
| 5 gens | Antonius, b. 20 Sep 1825 Gračišće, **d. 4 Aug 1894 Gračišće**, ark 1:1:6YBR-MQ7K | b. 20 Sep 1825, d. 1894 | **Exact death date and an ark** |
| great-grandfather | Anton/Antonius Rudolph "Ante", b. 20 Jan 1890 **Ledenice / Klenovica 22**, d. circa 1943 Crikvenica, ark 1:1:XQMS-8XGZ | same | agrees |

## Things the live tree has that this archive does not
1. **Antonius Franciscus Defranceschi, b. 31 Jan 1909 Gologorica, d. 7 Aug 1945
   at DACHAU.** Nothing on this anywhere in the archive.
2. **Franciscus Antonius, b. 13 Apr 1785 Gologorica, d. 23 Feb 1842** — we read
   his baptism off the casa-31 microfilm; the death date is new.
3. **Antonius "Anthony" de Franceschi, b. 6 Aug 1856 Gračišće, d. 23 Oct 1924** —
   the Eleven's father. We had the birth; the death date is new.
4. **"SORAVITO De Franceschi" of Mione** — a byname, several individuals, one
   (Antonio Bartolomeo, 1890–1968) going Mione → Nantes.
5. **Mione is the largest single place in the tree, 29 people.** This archive
   has treated Mione as an origin, not as a populated branch.
6. A **Trentino cluster** — Telve, Strigno, Fiera di Primiero, Rovereto, Laives —
   which this site currently files under namesakes.
7. Diaspora the archive has only in aggregate: São Paulo, Uruguay (Colonia),
   Argentina (Serodino; San José del Rincón), Venezuela (Maturín), Puerto Rico,
   Basel → Manhattan, Queens NY.
8. **Maximilianus Antonius, b. 9 Jan 1828 Gologorica, d. 6 Oct 1910.**
9. **Antonius, 1742 – 17 Sep 1802, Gologorica.**

## Still to do
- Pull the full 459 with their arks to disk.
- Walk each person's Facts panel for the citation text (film, image, archive),
  not just the ark — David adds these by hand and they are the good part.
- Reconcile person by person and correct the site where the tree is better
  sourced, and flag where the site is better sourced than the tree.
- The unconnected nodes and the town classifications David mentioned.
