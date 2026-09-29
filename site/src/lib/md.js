// The archive's light markup, in one place.
// Data files are written with **bold**, *italic* and «quoted» — this renders it.
// Anything passed here is escaped first, so it is safe on untrusted strings.
import { u, based } from "./url.js";

const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// And internal links, which this renderer refused for a year.
//
// Data files were being written with [text](/path/) in them anyway — eighteen
// roster notes on 16 September alone — and every one of them printed as
// literal square brackets on a person's own page. The research map worked
// round it with a private resolver of its own, which is the shape of a problem
// that belongs here instead. Only ABSOLUTE INTERNAL paths are linked: the
// base prefix is applied through the same helper every other link uses, and
// anything that is not a /path/ is left as the brackets somebody typed.
const link = (s) => s.replace(
  /\[([^\]\n]+)\]\((\/[^)\s]*)\)/g,
  (_, t, href) => `<a href="${u(href)}">${t}</a>`);


/* Markdown tables — added 29 September 2026.
 *
 * This renderer handled bold, italic, «quotes» and internal links, and had no
 * table support at all. Meanwhile 152 pipe-tables had been written into the
 * data across many sessions, and every one of them printed as literal |---|
 * on the page: /searched/, /worklist/, /corrections/, /lines/, /method/ and a
 * dozen person pages. It is the same hole the link renderer had for a year.
 *
 * Deliberately conservative. A block qualifies only if a row of |cells| is
 * followed immediately by a |---|---| separator. Anything else — a stray pipe
 * in prose, a table without a separator — is left exactly as it was written. */
const cells = (line) =>
  line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());

const tables = (src) => {
  const out = [];
  const lines = String(src).split("\n");
  for (let i = 0; i < lines.length; i++) {
    const head = lines[i], sep = lines[i + 1];
    const isRow = (l) => /^\s*\|.*\|\s*$/.test(l || "");
    const isSep = (l) => /^\s*\|[\s:|-]+\|\s*$/.test(l || "") && /-/.test(l || "");
    if (isRow(head) && isSep(sep)) {
      const th = cells(head);
      let j = i + 2;
      const body = [];
      while (isRow(lines[j]) && !isSep(lines[j])) body.push(cells(lines[j++]));
      out.push(
        "<table><thead><tr>" + th.map((c) => `<th>${c}</th>`).join("") +
        "</tr></thead><tbody>" +
        body.map((r) => "<tr>" + r.map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") +
        "</tbody></table>");
      i = j - 1;
    } else out.push(head);
  }
  return out.join("\n");
};

export const md = (x) => tables(link(esc(String(x ?? ""))
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>")));

// Same, but turns blank lines into paragraph breaks.
export const mdp = (x) => md(x).replace(/\n\n+/g, "</p><p>");

/* Same again, but the paragraph break carries a style. Four pages — carlo,
   vodnjan, errands, photograph-these — had their own renderer purely to get
   `</p><p style='margin-top:12px'>`, and that was not worth a private copy of
   the whole thing. Added 29 September 2026 while unifying twenty-five
   renderers into one. */
export const mdps = (x, style = "margin-top:12px") =>
  md(x).replace(/\n\n+/g, `</p><p style="${style}">`);

/* And the same renderer with links left EXACTLY as written, no base prefix.
   Added 29 September 2026. Some kit components base the hrefs themselves —
   Errands does it with an unguarded `href="/` → `href="/TheDefranceski/`
   replace — so prose handed to them must arrive unbased or it comes out
   doubled. Seven links on /errands/ broke this way the moment the shared
   renderer started basing its own links. Use this ONLY where a component
   downstream is going to do the basing. */
const linkRaw = (s) => s.replace(
  /\[([^\]\n]+)\]\((\/[^)\s]*)\)/g,
  (_, t, href) => `<a href="${href}">${t}</a>`);

export const mdUnbased = (x) => tables(linkRaw(esc(String(x ?? ""))
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>")));

export const mdpsUnbased = (x, style = "margin-top:12px") =>
  mdUnbased(x).replace(/\n\n+/g, `</p><p style="${style}">`);

/* The same renderer that does NOT escape, for data this archive wrote itself.
 *
 * Added 29 September 2026. Twenty data files carry deliberate HTML — the
 * evidence chips, a handful of anchors, the odd <em> — and it renders because
 * the pages showing it never escaped. That is why eleven pages could not move
 * to md(): escaping would have turned their own markup into visible tag text.
 *
 * So the fork is made explicit instead of copied eleven times. md() escapes
 * and is the right default for anything a stranger could have written;
 * mdHtml() trusts the string and is for this archive's own data files, which
 * are written by its own sessions and reviewed in git. Both get the links, the
 * «quotes» and the tables, so a fix reaches every page either way. */
export const mdHtml = (x) => based(tables(link(String(x ?? "")
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"))));

export const mdpHtml = (x) => mdHtml(x).replace(/\n\n+/g, "</p><p>");
export const mdpsHtml = (x, style = "margin-top:12px") =>
  mdHtml(x).replace(/\n\n+/g, `</p><p style="${style}">`);

/* And one more, for table cells. Added 29 September 2026.
 *
 * /people/ puts a truncated roster note inside a cell that ALREADY contains a
 * link, and the note itself is full of markdown links — 477 of them were
 * printing as [text](/who/x/) because that cell had its own bold-only
 * renderer. Rendering them properly would nest an <a> inside an <a>, which is
 * invalid. So here the link is FLATTENED to its own text: the words survive,
 * the anchor does not. Use this wherever a rendered link would be illegal or
 * merely noise. */
export const mdFlat = (x) => based(String(x ?? "")
  .replace(/\[([^\]\n]+)\]\(\/[^)\s]*\)/g, "$1")
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"));
