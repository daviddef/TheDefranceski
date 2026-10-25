/* THE LIVING-PEOPLE CUTOFF, once, for the pages (25 October 2026).

   A person is living if they are 80 or younger this year (this year minus the birth year) and no
   death or burial is recorded. The 80 is the kit's (kit/lib/person.js LIVING_YEARS, the same number
   scripts/living_v2.py reads from the kit's living_rule.py), and the cutoff is DERIVED from it:

       LIVING_CUTOFF = this year - LIVING_YEARS        (1946 in 2026)

   A birth year >= LIVING_CUTOFF with no death beside it is a living person's year. Every page that
   needs the boundary imports it from here. households.astro used to carry its own «NOW - by < 80»,
   which is 79: a man born in 1946 was not withheld there. Nothing else may spell the number 80
   out in code; scripts/check-living-v2.py fails the build if a page does.

   Citations are deliberately NOT a parameter. A public source cannot make a dated person under 81
   «not living» (see scripts/living_v2.py). */
import { LIVING_YEARS } from "@daviddef/archive-kit/lib/person.js";

export { LIVING_YEARS };
export const THIS_YEAR = new Date().getFullYear();
export const LIVING_CUTOFF = THIS_YEAR - LIVING_YEARS;

/* True if a birth year puts a person at 80 or younger now. */
export function bornInLivingWindow(y, now = THIS_YEAR) {
  const n = Number(y);
  return Number.isFinite(n) && n >= now - LIVING_YEARS && n <= now;
}
