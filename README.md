# The Defranceschi Archive

An evidence-first family archive for the **Defranceschi, De Franceschi, Defranceski, de Franceski**
and **Franceschi** families of Istria, Kvarner, Carnia and Dalmatia — and the diaspora.

> *De Franceschi* means only "of the Franceschi" — the family of a man called Francesco. The name was
> therefore invented independently, many times over, wherever an Italian-speaking clerk needed to tell
> one Francesco's sons from another's. **There is no single founding Defranceschi family.** The work of
> this archive is to establish which lines are actually connected, and to say plainly where the evidence stops.

## What is here

- **1,151 parish registers** across 14 Istrian parishes, read from the State Archives in Pazin inventory
  (997 digitised). Earliest: Vodnjan 1559, Svetvinčenat 1568, Pazin 1582, Gologorica 1644, Gračišće 1667.
- **The 1945 census of the surname** — 25 families in 12 Istrian settlements on 1 October 1945, from the
  *Cadastre National de l'Istrie* (Institut Adriatique, Sušak 1946). The spaced spelling survives only in
  formerly Venetian territory; the fused form is found on both sides of the old border.
- **The 1679 Mione link** — the headmen's list of the Ovaro and Luincis parishes records
  *"Zuane De Franceschi con un suo fiolo, Zuane d'Erman: questi tre nell'Istria, luogo imperiale"* —
  a De Franceschi of Mione working in the Habsburg County of Pazin.
- **The Dalmatian line** — Omiš from 1590, Imotski from 1717, and why they are called Franceschi today.
- **388 named individuals** recovered from the FamilySearch index of the Croatian church books, 1581–1946,
  including three generations of the Fiume household of Valentino Defranceschi and his wife Elena.
- **The marriage network** — 71 in-law surnames across Venetian, Slavic and Friulian-Carnian Istria.
- Sovereignty, name-drift, migration, distribution and heraldry, all rendered from the data.

## Method

Every claim carries a confidence and a source:

| | |
|---|---|
| **Documented** | A named source with a reference, and where possible the scan. |
| **Inferred** | A reasoned conclusion from documented facts, with the reasoning written out so it can be overturned. |
| **Family lore** | Told, remembered, not corroborated. Kept because it is precious; labelled because pretending otherwise is how family myths become family history. |

**Living people are omitted from the build entirely** — not hidden, not gated, not present in the output.
A removal request is honoured within days, without argument and without requiring a reason.

On the contested history of 1943–56: report what happened to our people, with sources; use both toponyms
always; do not adjudicate between national grievances.

## Running it

```bash
cd site
npm install
npm run dev      # http://localhost:4321
npm run build    # static output in site/dist
```

Deploys to GitHub Pages on every push to `main`.
To serve from **defranceski.com** instead, set `base: '/'` and `site: 'https://defranceski.com'`
in `site/astro.config.mjs` and add the custom domain in the repository's Pages settings.

## Layout

```
data/                     dapa-registers.csv — the register inventory
site/src/data/            places, people, lines, names, sovereignty, registers
site/src/components/      the rendered SVGs: timeline, name drift, census map, routes, arms, flags
site/src/pages/           the archive itself
```

## Contributing

Corrections are the most valuable thing you can send — especially if you can read a register we cannot,
or you are one of the Vodnjan, Split or South African families. Open an issue.

## Sources

State Archives in Pazin · *Cadastre National de l'Istrie*, 1946, via istrianet.org · Dean Brhan on the
Canale di Gorto emigration · Maja Delić Peršen on the de Franceschi of Imotski · Carlo De Franceschi,
*L'Istria: note storiche* (Parenzo 1879) · Camillo De Franceschi, *Storia documentata della Contea di
Pisino* (Venice 1964) · Acta Croatica · Forebears · Portale Antenati · FamilySearch · State Archives in Rijeka.

Nothing here yet establishes descent. That is the work.

## The spine, closed (September 2026)

Two ruled rows from the *Status Animarum* of the parish of Gallignana (Gračišće),
obtained from the Državni arhiv u Pazinu in June 2021 and unread until now,
carry four generations of the direct line with wives, dates and trades:

| | |
|---|---|
| **House 5** | *Joan. Bapt. Defranceschi, agricola* — b. 13 Aug 1787, m. 1819, d. 1 Sept 1846. Wife **Francisca Salomon**, b. 17 Mar 1797. Sons Raymundus 1823, **Antonius 20 Sept 1825**, Joannes 1833, Franciscus 1840. |
| **House 19** | *† Antonius Defranceschi **q. Joannis*** — b. 20 Sept 1825, m. 25 Nov 1856, d. 4 Aug 1894, *lapicida*. Wife **Maria née Fernasar**, b. 17 Oct 1832. Children Antonius 1856, **Josephus 22 Mar 1863**, Leopolda 1865, Catharina 1869, Modestus 1875. |

*q. Joannis* — son of the late Giovanni — welds house 19 to house 5. Josephus is
the man on the certified 1863 baptism already held, and the line runs on through
Crikvenica and Senj to Brisbane. Eight generations at `/direct-line/`.

## Also new

- **`/pfullingen/`** — six Defranceskis registered in one Württemberg town between
  1939 and 1945, five born at Crikvenica; three with photographs from French-zone
  camp cards. Source: Arolsen Archives, ITS file D-1.505.
- **`/burials/`** — 99 burials, 1619–1997, found by searching the registers of the
  dead by surname rather than by parish. Includes four children buried by Carlo
  De Franceschi, one named for his own mother.
- **`/explorer/`** — 52 reconstructed households, searchable, filterable by region
  and year, with the descent links walkable.
- **`/search/`** — one index over 435 entries; press `/` anywhere on the site.
- **`/gallery/`** — 28 plates from the family's own scans, with a lightbox.
- **`/namesakes/`** — fifteen who carried the name, with public-domain art from
  Wikimedia Commons, credited.
- **`/arms/`** — the family arms redrawn. The *Blasonario Giuliano* independently
  records the achievement Carlo De Franceschi described in a private letter of
  c.1873: per fess, argent a cross issuing from the division pierced by two
  arrows in bend sinister, all gules; vert, a pomegranate proper. Two sources,
  neither quoting the other.
