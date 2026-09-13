/* Resolve a name as the tree writes it to the dossier page that holds that person.
   Deliberately conservative, and twice over:
     - a match is only returned when exactly one candidate survives, and
     - if both sides carry a year, the years must agree.
   Without the second test "Ivan Defranceski, 1925-1995" resolves to an Ivan de
   Franceschi of Omis who died in 1895, and "Antonio Defranceschi, 1825-1894" to
   an Antonio of Svetvincenat of 1704. Both were caught only by checking. */
export function norm(x) {
  let s = String(x ?? "")
    .replace(/\s*\(.*?\)\s*/g, " ")
    .replace(/\s*\/.*$/, " ")
    .replace(/\b(?:née|nee|born|q\.?m|fu|detta|detto)\b/gi, " ")
    .replace(/\bq\.\s*/gi, " ");
  s = s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  s = s.replace(/defranceschi/g, "de franceschi").replace(/defranceski/g, "de franceschi");
  return s.replace(/[^a-z ]+/g, " ").split(/\s+/).filter(Boolean).join(" ");
}

const years = (s) => (String(s ?? "").match(/\b(1[3-9]\d\d|20\d\d)\b/g) || []).map(Number);

function agrees(want, have) {
  if (!want.length || !have.length) return true;        // one side undated: cannot test
  return Math.abs(Math.min(...want) - Math.min(...have)) <= 6;   // birth against birth
}

export function makeResolver(people) {
  const rows = [];
  for (const p of people) {
    const k = norm(p.name);
    if (!k) continue;
    const f = Object.fromEntries((p.facts || []).filter(a => a.length > 1).map(a => [a[0], a[1]]));
    rows.push({ k, slug: p.slug, y: years(f.Years) });
  }
  return function resolve(name, dates) {
    const q = norm(name);
    if (!q) return null;
    const want = years(dates);
    const qt = q.split(" ");
    if (qt.length < 2) return null;                     // a bare forename names nobody
    /* Gather from all three tests at once and rank, rather than stopping at the
       first that yields anything: "Milka Papic" starts a page called "Milka Papic
       marries Zvonimir Vukelic", which is an event and not the person. */
    const seen = new Set(), hitsAll = [];
    for (const r of rows) {
      const s = new Set(r.k.split(" "));
      if (r.k === q || r.k.startsWith(q + " ") || qt.every(t => s.has(t))) {
        if (!seen.has(r.slug)) { seen.add(r.slug); hitsAll.push(r); }
      }
    }
    let hits = hitsAll;
    hits = hits.filter(r => agrees(want, r.y));
    /* If the tree knows this person's dates, only trust a dossier that also carries
       dates and agrees with them. An undated page cannot confirm anything, and twice
       today an unverified name match has put the wrong person on the page. */
    if (want.length) {
      const dated = hits.filter(r => r.y.length);
      if (dated.length) hits = dated; else return null;
    }
    if (!hits.length) return null;
    /* Several dossiers can hold near-identical names for one person, and some of
       them are thin pages with no facts at all. Prefer the one whose dates actually
       confirm the match, then the exact form, then the plainest. */
    const dated = r => (want.length && r.y.length) ? 0 : 1;
    hits.sort((a, b) => dated(a) - dated(b)
                     || (a.k === q ? 0 : 1) - (b.k === q ? 0 : 1)
                     || a.k.split(" ").length - b.k.split(" ").length
                     || a.slug.length - b.slug.length);
    return hits[0].slug;
  };
}
