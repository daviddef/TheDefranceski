/* THE PULSE: what is new in this archive, and the archive in numbers. Prototype, 11 November 2026.
 *
 * Nothing here is written by hand and nothing is generated into a file that can go stale: it is computed at build time from the logs the
 * archive already keeps (searched.json: every register and source read, with its outcome; corrections.json: every claim withdrawn), and the
 * counts from the roster, the worklist and the source list. A finding that is logged and told shows up here by the next build.
 *
 * Counts only, and the text of entries that /searched/ and /corrections/ already print (clipped, never rewritten): nothing about a living
 * person that those pages do not already hold, and no person is counted by name.
 */
import searched from "../data/searched.json";
import corrections from "../data/corrections.json";
import worklist from "../data/worklist.json";
import roster from "../data/roster.json";
import sources from "../data/sources.json";

/* the card kinds of the timeline (Record Atlas's vocabulary): a day's searches fold into ONE research card, each correction is its own */
export const CARD = {
  research: { label: "Research", glyph: "⚑", note: "registers and sources read that day, with what each gave" },
  corrected: { label: "Corrected", glyph: "✓", note: "an earlier claim was withdrawn or fixed" },
};
export const KIND = {
  found: { label: "Found", glyph: "✦", note: "a register or source gave something" },
  corrected: { label: "Corrected", glyph: "✓", note: "an earlier claim was withdrawn or fixed" },
  nil: { label: "Nothing found", glyph: "○", note: "searched, in the terms named, and nothing" },
  partial: { label: "Partly", glyph: "◐", note: "some of it read, some not" },
  blocked: { label: "Blocked", glyph: "■", note: "could not be read (a block, a restriction, not on the film)" },
};
const OUT = {
  hit: "found", yield: "found", found: "found",
  nothing: "nil", nil: "nil", miss: "nil",
  partial: "partial", mixed: "partial",
  blocked: "blocked", correction: "corrected",
};
const MON = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };

/* "11 Nov 2026", "5 October 2026", "Sept 2026" (month only: day 1, exact false) */
export function parseWhen(s) {
  const m = /^(?:(\d{1,2})\s+)?([A-Za-z]{3,})\.?\s+(\d{4})$/.exec(String(s || "").trim());
  if (!m) return null;
  const mo = MON[m[2].slice(0, 3).toLowerCase()];
  if (mo === undefined) return null;
  const day = m[1] ? +m[1] : 1;
  return { iso: `${m[3]}-${String(mo + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`, exact: !!m[1] };
}
const clean = (s) => String(s || "").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/[*_`]/g, "").replace(/\s+/g, " ").trim();
const clip = (s, n) => {
  s = clean(s);
  if (s.length <= n) return s;
  const c = s.slice(0, n), k = c.lastIndexOf(" ");
  return c.slice(0, k > n * 0.6 ? k : n).replace(/[,;:(—\-\s]+$/, "") + "…";
};

const entries = [];
(searched.rows || []).forEach((r, i) => {
  const w = parseWhen(r.when);
  const kind = OUT[r.outcome];
  if (!w || !kind) return;
  const ev = Array.isArray(r.ev) ? r.ev.find((e) => Array.isArray(e) && typeof e[0] === "string" && e[0].startsWith("/") && e[1]) : null;
  entries.push({
    iso: w.iso, exact: w.exact, kind, order: i,
    head: ev ? clean(ev[1]) : clip(r.what, 120),
    more: ev ? clip(r.what, 240) : "",
    src: clip(r.src, 110),
    href: ev ? ev[0] : "/searched/",
    walked: r.walked === true,
    place: typeof r.dest === "string" && r.dest.length <= 32 && !/[·;]/.test(r.dest) ? r.dest.trim() : "",
    pages: typeof r.pages === "string" && r.pages.length <= 24 ? r.pages.trim() : "",
  });
});
(corrections.rows || corrections || []).forEach((r, i) => {
  const w = parseWhen(r.when);
  if (!w || !r.what) return;
  entries.push({ iso: w.iso, exact: w.exact, kind: "corrected", order: 100000 + i, head: clip(r.what, 160), more: "", src: "", href: "/corrections/", walked: false, place: "", pages: "" });
});
/* newest first; within a day, the later row of the log first */
entries.sort((a, b) => (a.iso < b.iso ? 1 : a.iso > b.iso ? -1 : b.order - a.order));

/* THE DAYS: entries of one day (month-only entries share their month), the corrections as cards of their own and the day's searches folded into one */
const days = [];
for (const e of entries) {
  const key = e.exact ? e.iso : e.iso.slice(0, 7);
  let d = days[days.length - 1];
  if (!d || d.key !== key) days.push((d = { key, iso: e.iso, exact: e.exact, corrections: [], research: [] }));
  (e.kind === "corrected" ? d.corrections : d.research).push(e);
}
const listOf = (a, max) => (a.length <= 1 ? a.join("") : a.length <= max ? a.slice(0, -1).join(", ") + " and " + a[a.length - 1] : a.slice(0, max).join(", ") + " and " + (a.length - max) + " more");
for (const d of days) {
  const r = d.research;
  d.found = r.filter((e) => e.kind === "found").length;
  const places = [...new Set(r.map((e) => e.place).filter(Boolean))];
  d.summary = r.length ? `Research: ${r.length} ${r.length === 1 ? "search" : "searches"}${places.length ? " at " + listOf(places, 3) : ""}` : "";
  d.tally = r.length ? ` · ${d.found} of ${r.length} found something` : "";
}
/* the flat list of cards, newest first, as the header panel shows it */
export const cards = [];
for (const d of days) {
  for (const c of d.corrections) cards.push({ type: "corrected", iso: d.iso, exact: d.exact, head: c.head, href: c.href });
  if (d.research.length) cards.push({ type: "research", iso: d.iso, exact: d.exact, head: d.summary + d.tally, href: "/whats-new/#d" + d.key });
}
const latest = entries.length ? entries[0].iso : "";
const weekFrom = latest ? new Date(Date.parse(latest + "T00:00:00Z") - 6 * 864e5).toISOString().slice(0, 10) : "";
const week = {};
for (const k of Object.keys(KIND)) week[k] = 0;
for (const e of entries) if (e.iso >= weekFrom) week[e.kind]++;
const total = {};
for (const k of Object.keys(KIND)) total[k] = entries.filter((e) => e.kind === k).length;

const wl = worklist.rows || [];
export const pulse = {
  entries, days, cards, latest, weekFrom, week, total,
  counts: {
    people: (roster.rows || []).length,
    logged: (searched.rows || []).length,
    walked: (searched.rows || []).filter((r) => r.walked === true).length,
    corrections: (corrections.rows || corrections || []).length,
    done: wl.filter((r) => r.state === "done").length,
    open: wl.filter((r) => r.state === "next" || r.state === "running").length,
    sources: Array.isArray(sources) ? sources.length : (sources.rows || []).length,
  },
};
export const fmtDay = (iso, exact = true) => {
  const d = new Date(iso + "T00:00:00Z");
  return exact
    ? d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    : d.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
};
export const nf = (n) => n.toLocaleString("en-GB");
/* the six numbers of the panel and of the top of /whats-new/: [figure, name, what it counts] (a vocabulary, kept here and not in a page) */
export const tiles = () => {
  const c = pulse.counts;
  return [
    [nf(c.people), "people", "in the roster"],
    [nf(c.logged), "searches", "of registers and sources logged"],
    [nf(c.walked), "books walked", "every entry of the book read"],
    [nf(c.corrections), "corrections", "claims withdrawn or fixed, in the open"],
    [nf(c.done), "tasks done", `${nf(c.open)} still open`],
    [nf(c.sources), "sources", "named and described"],
  ];
};
