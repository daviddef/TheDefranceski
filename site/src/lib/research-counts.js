/* One sentence for each Research page: what it asks, and a number the archive can state from its own data. Counted at build time, so
   it cannot go stale. 12 November 2026 (the research-menu trial). */
import questions from "../data/questions.json";
import errands from "../data/errands.json";
import worklist from "../data/worklist.json";
import searched from "../data/searched.json";
import corrections from "../data/corrections.json";
import changes from "../data/changes.json";
import sources from "../data/sources.json";
import plates from "../data/plates.json";
import book from "../data/book.json";
import { RESEARCH } from "./research-menu.js";

const rows = (x) => (Array.isArray(x) ? x : x.rows || []);
const nf = (n) => n.toLocaleString("en-GB");
const wl = rows(worklist);
const open = wl.filter((r) => r.state === "next" || r.state === "running").length;
const COUNT = {
  "/open-questions/": `${nf(questions.open.length)} open or blocked or answered, ${nf(questions.closed.length)} closed`,
  "/errands/": `${nf(rows(errands).length)} errands`,
  "/worklist/": `${nf(open)} still open, ${nf(wl.filter((r) => r.state === "done").length)} done`,
  "/searched/": `${nf(searched.rows.length)} sources examined`,
  "/corrections/": `${nf(corrections.rows.length)} claims taken back`,
  "/changes/": `${nf(changes.days.reduce((n, d) => n + d.rows.length, 0))} entries`,
  "/sources/": `${nf(sources.length)} sources`,
  "/gallery/": `${nf(plates.length)} plates`,
};
const BLURB = Object.fromEntries(
  book.parts.flatMap((p) => p.chapters).map((c) => [c.path, c.blurb]));
const ASKS = Object.fromEntries(RESEARCH.flatMap((g) => g.items).filter((x) => x.asks).map((x) => [x.href, x.asks]));

export const blurbOf = (x) => {
  const asks = ASKS[x.href] || BLURB[x.href] || "";
  const n = COUNT[x.href];
  return [asks, n ? `<em>${n}.</em>` : ""].filter(Boolean).join(" ");
};
