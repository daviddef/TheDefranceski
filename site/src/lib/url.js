// Prefix a site-root path with the deployment base. Since 12 October 2026 this
// archive is served at the ROOT of https://archive.defranceski.com/, so BASE is
// the empty string and u() is a near no-op — but it stays, because it is what
// made the move survivable and what would make the next one survivable.
// NOTE the /TheDefranceski/ paths in the comments below: they describe bugs that
// HAPPENED, and are deliberately left as they were. Do not "correct" them to the
// new address — an archive's record of its own faults is evidence too.
const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");
/* Idempotent since 29 September 2026. u() used to prefix unconditionally, so a
   path that had already been based came back doubled —
   /TheDefranceski/TheDefranceski/corrections/. That never bit while each page
   based its links exactly once, but the moment the shared markdown renderer
   started emitting based hrefs AND a kit component also based them, seven
   links on /errands/ broke at once. A prefix function that cannot be applied
   twice safely is a trap; this one can. */
export const u = (p = "/") => {
  const path = p.startsWith("/") ? p : "/" + p;
  if (BASE && (path === BASE || path.startsWith(BASE + "/"))) return path;
  return `${BASE}${path}`;
};

/* Some prose lives in the data files as raw HTML and reaches the page through
   set:html, which means u() never sees its links. Those shipped as href="/gaps/"
   instead of href="/TheDefranceski/gaps/" and 404 on GitHub Pages. Run a prose
   string through this before setting it. Already-based, external and anchor
   links are left alone, so it is safe to apply to anything. */
export const based = (s = "") =>
  String(s).replace(/href="(\/(?!\/)[^"]*)"/g,
                    (m, h) => (h.startsWith(BASE + "/") ? m : `href="${u(h)}"`));
