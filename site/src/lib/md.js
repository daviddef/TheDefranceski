// The archive's light markup, in one place.
// Data files are written with **bold**, *italic* and «quoted» — this renders it.
// Anything passed here is escaped first, so it is safe on untrusted strings.
import { u } from "./url.js";

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
