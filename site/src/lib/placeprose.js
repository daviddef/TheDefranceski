/* Place names in running prose, linked to the archive's place page with the flag that flew over the place in the year the sentence names.

   The kit's placeIndex/linkPlaces (the ones the Corrections page uses) do the work; this file builds the index once for the whole build and hands pages two
   functions. `inPlaces(html, seen?)` links the first mention of each place in the html it is given (a `seen` Set carries "already linked" across several
   pieces of one entry, so a place is linked once per entry, not once per paragraph). Only places this archive has a page for (src/data/places.json) are
   linked; a place with no page is left as written. The flag table is src/data/place-flags.json (scripts/build-place-flags.py); the flag art is the kit's own.
   Pages that go through a kit component which bases its own hrefs (Errands) pass `unbased: true`.

   Typography: the kit's Corrections component draws .pl-flag itself; pages that use this helper call `placeCss` once in a <style is:global>. */
import { placeIndex, linkPlaces } from "@daviddef/archive-kit/lib/placelinks.js";
import placeRows from "../data/places.json";
import placeFlags from "../data/place-flags.json";
import { u } from "./url.js";

const FLAG_ART = import.meta.glob("../../node_modules/@daviddef/archive-kit/kit/data/flags/*.svg", { eager: true, query: "?url", import: "default" });
const flagUrl = (svg) => { const k = Object.keys(FLAG_ART).find((p) => p.endsWith("/" + svg)); return k ? FLAG_ART[k] : ""; };
const index = (base) => placeIndex(placeRows.map((p) => ({ name: p.name, aliases: Object.values(p.alt || {}), href: base ? u(`/places/${p.slug}/`) : `/places/${p.slug}/` })), placeFlags, flagUrl);
const based = index(true), unbased = index(false);

export const inPlaces = (html, o = {}) => linkPlaces(html, o.unbased ? unbased : based, { seen: o.seen });
export const placeCss = `.lk-place{text-decoration-style:dotted}.pl-flag{height:.8em;width:auto;margin-right:.3em;vertical-align:-.04em;border:1px solid var(--rule,#ccc);border-radius:1px}`;
