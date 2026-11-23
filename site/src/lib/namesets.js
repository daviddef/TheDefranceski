/* WHO SHARES A NAME (23 November 2026).
 *
 * A name page, /who/<slug>/, lists its bearers: the roster rows that have a person page and either carry that name page's address in
 * `who` or, with no `who`, have a name that slugifies to the page's slug (rows added after the name join, 561 of them on 5 November
 * 2026, carry no `who`; counting only the linked rows made a page say "3 people" for five). A person's page lists the OTHER bearers of
 * the name page that lists them. Until 23 November the person page grouped rows by the raw `who` or name string instead, so a row
 * with no `who` never met the rows of its name that had one, and 316 pages left out someone the name page listed.
 *
 * This file is the one place the rule is written; both pages call it. It is pure (no imports) so a script can use it too.
 * The gate that judges the result reads the BUILT pages (tools/checknamesakes.py), not this file.
 */
export const nameSlug = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase().slice(0, 60);

/* the name page a roster row belongs to: the slug in its `who`, else the slug of its name */
export const whoSlugOf = (x) => {
  if (x.who) { const m = /^\/who\/([^/]+)\/$/.exec(x.who); return m ? m[1] : null; }
  return nameSlug(x.name);
};

/* the bearers of each name page that exists: slug -> rows with a person page, in roster order.
   `slugs` is the set of name pages (the dossiers' slugs); a row whose name page does not exist is on no list. */
export function bearersBySlug(rows, slugs) {
  const by = new Map();
  for (const x of rows) {
    if (!x.pid) continue;
    const s = whoSlugOf(x);
    if (!s || !slugs.has(s)) continue;
    if (!by.has(s)) by.set(s, []);
    by.get(s).push(x);
  }
  return by;
}

/* oldest first, by the birth the name page shows (b, else bEst); no year after those with one; roster order otherwise */
export const byBirth = (a, b) => (a.b || a.bEst || 9999) - (b.b || b.bEst || 9999);
