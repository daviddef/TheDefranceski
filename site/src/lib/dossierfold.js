/* WHAT A NAME PAGE HOLDS FOR ONE PERSON, AND THE PERSON'S OWN PAGE DID NOT SAY (23 November 2026).
 *
 * /who/<name>/ is a research dossier on a NAME and stays exactly as it is. Two of the things it shows are about ONE bearer, not about the
 * name, and can be told apart from the name-level rest (every mention across the site, the records matched by name, the household drawn
 * from it) without any guess, because the data says whose they are:
 *
 *  1. "What the archive knows" is the roster rows' own `note` fields, strung together (scripts/build-dossiers.py: `known` is the first
 *     row's note, `more` the others', in roster order). A paragraph there is a row's note, and the row is one person. A person page tells
 *     its row's note in the story (chaptersOf / storyOf cut it into cards, so the words are all there, re-ordered under the life's
 *     headings, and the check measures that). The exception is a duplicate's pointer page ("the same person as another page"): the kit
 *     draws no story on it, so its row's note is on /who/ and nowhere on any person page (25 rows). Those paragraphs are shown, verbatim.
 *
 *  2. "The record itself" (the `rec` strip): the one FamilySearch index entry the archive holds for a name it has not placed in a
 *     household. It is built from a bearer's own `ark`. It is the person's when the row was read from THAT record (the row's primary
 *     `ark` is the entry's id) and the entry is about someone of the same given name (the register's name for the entry; an entry whose
 *     subject is a relative named on the record, or whose given name differs, is not this person's and stays on the name page).
 *
 * Nothing here is written by hand: the words are the dossier's, passed through unchanged. Nothing is shown on a living person's page. The
 * gate that judges the BUILT pages is tools/checkdossierfold.py.
 */
import register from "../data/register.json";

const REG = new Map((register.rows || []).map((x) => [x.id, x]));
const stripAcc = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "");
/* the words of a name without a parenthesised qualifier, lower case, letters only */
export const nameWords = (s) => stripAcc(String(s || "").replace(/\s*\(.*?\)\s*/g, " ")).toLowerCase().match(/[a-z]+/g) || [];

/* a note's paragraphs, as the name page's text is made of them (blank-line separated) */
export const paragraphs = (note) => String(note || "").split(/\n\n+/).map((x) => x.trim()).filter(Boolean);

/* the words of a paragraph with the markup taken off, to compare two texts by their letters and digits only */
const plain = (t) => String(t || "").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/<[^>]+>/g, "").replace(/[*`]/g, "");
const squash = (t) => stripAcc(String(t || "").normalize("NFKC")).toLowerCase().replace(/[\W_]+/g, "");

/* the FamilySearch index id a row was read from: its primary `ark` ("1:1:6BKV-845N" -> "6BKV-845N") */
export const arkId = (r) => { const m = /([0-9A-Z]{4}-[0-9A-Z]{3,4})/.exec(String((r && r.ark) || "")); return m ? m[1] : null; };

/* the entry's subject carries the row's given name: first word equal, or one begins with the other (four letters or more), which takes
   Latin cases (Catharinam / Catharina) and clerks' short forms (Felice Anto / Felice Antonio) and nothing else */
export function sameGiven(entryName, rowName) {
  const a = nameWords(entryName)[0], b = nameWords(rowName)[0];
  if (!a || !b) return false;
  return a === b || (a.length >= 4 && b.startsWith(a)) || (b.length >= 4 && a.startsWith(b));
}

/* Is this paragraph of the dossier one of THIS ROW's note? (the provenance test: the name page's text is the rows' notes) */
export const dossierHolds = (d, note) => !!d && !!note && (d.known === note || (d.more || []).includes(note));

/* WHAT TO SHOW ON ONE PERSON'S PAGE.
 *   r        the roster row
 *   d        the name page's dossier (dossiers.json people[slug]) for the name page that LISTS this person, or undefined
 *   told     true when this page already tells the row's note itself (story mode); false for a duplicate's pointer
 *   idShown  true when the page already shows the index id somewhere else (so the entry is not told twice)
 *   lede     the words the page already prints under the name (its lede, drawn from the note's first sentences): a paragraph that is
 *            only that line is not said again
 * A paragraph with no letter or digit in it (the "---" rule lines the notes put between findings) says nothing and is not shown; nor is a
 * paragraph that is only the lede line.
 * Returns null, or { notes: [paragraph…], rec: {…} | null }. The living are never passed in by the page. */
export function dossierFold({ r, d, told, idShown, lede = "" }) {
  if (!r || !d || r.living) return null;
  const said = squash(lede);
  const notes = !told && dossierHolds(d, r.note) ? paragraphs(r.note).filter((p) => { const q = squash(plain(p)); return q && !(said && said.includes(q)); }) : [];
  /* the name page draws the strip only where no household is drawn for the name (!ptree); a duplicate's pointer says nothing of its own */
  const id = arkId(r);
  const e = id ? REG.get(id) : null;
  const rec = d.rec && !d.ptree && !r.sameAs && id && d.rec.id === id && e && sameGiven(e.n, r.name) && !idShown ? d.rec : null;
  return notes.length || rec ? { notes, rec } : null;
}
