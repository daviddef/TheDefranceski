// The archive's light markup, in one place.
// Data files are written with **bold**, *italic* and «quoted» — this renders it.
// Anything passed here is escaped first, so it is safe on untrusted strings.
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

export const md = (x) => esc(String(x ?? ""))
  .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  .replace(/«(.+?)»/g, "<em>«$1»</em>")
  .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>");

// Same, but turns blank lines into paragraph breaks.
export const mdp = (x) => md(x).replace(/\n\n+/g, "</p><p>");
