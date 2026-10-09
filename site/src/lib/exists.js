/* Three pages were linking to addresses that do not exist: the changelog
   because its "where this lives" field is free text that sometimes holds two
   paths and sometimes holds a sentence, the mention pages because their place
   hrefs were slugified years ago by a routine that deleted non-ASCII letters
   instead of folding them (Österreich -> sterreich), and the namesakes page
   because not every namesake has a life written up.
   Rather than hand-correcting the data, the pages now ask whether a target
   exists before linking to it. */
import places from "../data/places.json";
import people from "../data/people.json";

export const placeSlugs = new Set(places.map(p => p.slug));
export const peopleSlugs = new Set(people.map(p => p.slug));

/* The current slug rule: fold the accent onto its base letter, never drop it. */
export const slugify = (s) =>
  String(s ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase()
    .slice(0, 60);

/* Static routes, read off the pages directory, so this can never drift from
   what the site actually builds. Dynamic [slug] routes are excluded — the
   free-text field never points at one. */
const pageFiles = import.meta.glob("../pages/**/*.astro", { eager: false });
export const staticRoutes = new Set(
  Object.keys(pageFiles)
    .filter(f => !f.includes("["))
    .map(f => f.replace("../pages", "").replace(/\/index\.astro$/, "").replace(/\.astro$/, ""))
    .map(r => (r === "" ? "/" : `${r}/`))
);

/* Split a free-text "where this lives" value into the parts that are real
   addresses and the parts that are just prose. */
export function linkParts(value) {
  return String(value ?? "")
    .split("·")
    .map(part => {
      const t = part.trim();
      /* A «where» entry may be a bare path — /gologorica-line/ — or a markdown
         link, [Joanna Defranceschi](/person/joanna-…/). Forty-nine correction
         rows had drifted to the second shape and this function only knew the
         first, so every one of them printed as literal square brackets in the
         «Corrected in place» footer: 77 on /corrections/ alone, found 9 October
         2026 by grepping the built page. A person page is a DYNAMIC route and
         is not in staticRoutes, so the markdown form is trusted as written and
         left to the gate's link checker to verify. */
      const md = /^\[([^\]]+)\]\((\/[^)\s]*)\)$/.exec(t);
      if (md) return { href: md[2], text: md[1] };
      const path = t.split("#")[0];
      const withSlash = path.endsWith("/") ? path : `${path}/`;
      return staticRoutes.has(withSlash) ? { href: t, text: t } : { text: t };
    })
    .filter(p => p.text.length > 0);
}
