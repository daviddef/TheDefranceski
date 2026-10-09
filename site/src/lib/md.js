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
/* Internal AND external links. Until 29 September 2026 this regex required the
 * href to start with "/", so every markdown link to another site printed as
 * literal [text](https://…) on the page — 79 of them across the data, and
 * three of them shipped on /kalanj/ within an hour of that page going live.
 * It is the same hole the tables had, one layer down: the renderer quietly
 * handled the common case and left the other one as visible punctuation.
 * An external href is never passed through u(): it is already absolute. */
const link = (s) => s.replace(
  /\[([^\]\n]+)\]\((\/[^)\s]*|https?:\/\/[^)\s]*)\)/g,
  (_, t, href) => href.startsWith("/")
    ? `<a href="${u(href)}">${t}</a>`
    : `<a href="${href}" rel="noopener">${t}</a>`);


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
      /* Wrapped in .scroll so a wide table scrolls inside its column instead of
         pushing the page sideways. Without this the tables added on 29
         September put fifteen pages into horizontal overflow at 375px. */
      out.push(
        "<div class=\"scroll\"><table><thead><tr>" + th.map((c) => `<th>${c}</th>`).join("") +
        "</tr></thead><tbody>" +
        body.map((r) => "<tr>" + r.map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") +
        "</tbody></table></div>");
      i = j - 1;
    } else out.push(head);
  }
  return out.join("\n");
};

/* ─── One inline chain, instead of four copies of it ───────────────────────
 *
 * Added 9 October 2026. This file exists to be the archive's single renderer,
 * and it had the same three lines written out FOUR times — in md(),
 * mdUnbased(), mdHtml() and mdFlat(). Two faults therefore had to be fixed in
 * four places, so they were fixed in none:
 *
 *   ***triple***  produced  <strong><em>x</strong></em>  — tags closed in the
 *                 wrong order. 3,454 in the data, rendering as 1,391
 *                 mis-nested pairs across 146 built pages.
 *   `code`        had no rule at all. 887 in the data, every backtick
 *                 printing as a backtick.
 *
 * Order is not arbitrary: code spans first, so a ** inside backticks stays
 * literal; then *** before ** before *, or the shorter marker eats the longer
 * one's delimiters and leaves a stray asterisk behind. */
const inline = (s) => s
  .replace(/`([^`\n]+)`/g, "<code>$1</code>")
  .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>");

export const md = (x) => tables(link(inline(esc(String(x ?? "")))));

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
  /\[([^\]\n]+)\]\((\/[^)\s]*|https?:\/\/[^)\s]*)\)/g,
  (_, t, href) => href.startsWith("/")
    ? `<a href="${href}">${t}</a>`
    : `<a href="${href}" rel="noopener">${t}</a>`);

export const mdUnbased = (x) => tables(linkRaw(inline(esc(String(x ?? "")))));

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
export const mdHtml = (x) => based(tables(link(inline(String(x ?? "")))));

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
export const mdFlat = (x) => based(inline(String(x ?? "")
  .replace(/\[([^\]\n]+)\]\((?:\/|https?:\/\/)[^)\s]*\)/g, "$1")));
