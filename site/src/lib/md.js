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

export const md = (x) => link(esc(String(x ?? ""))
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"));

// Same, but turns blank lines into paragraph breaks.
export const mdp = (x) => md(x).replace(/\n\n+/g, "</p><p>");
