/* The rivers drawing's derived words and names, for every page that draws it (the home page and /lines/).
   The counts are the drawing's own ledger (kit lib/lines.js), never typed; the member names are the roster's. */
import { ledger, pensOf } from "@daviddef/archive-kit/lib/lines.js";
import rivers from "../data/rivers.json";
import roster from "../data/roster.json";

const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen"];
export const word = (n) => WORDS[n] ?? String(n);
export const Cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
export const L = ledger(rivers);
export const lanes = word(L.lanes);
export const households = word(L.households);
/* the people in the pens, by display name: the roster's names for the ids scripts/build-rivers-members.py listed */
const byPid = Object.fromEntries(roster.rows.filter((r) => r.pid).map((r) => [r.pid, r.name]));
export const names = Object.fromEntries(pensOf(rivers).flatMap((p) => (p.members || []).map((m) => [m.person || m, byPid[m.person || m] || m])));
/* the person pages live under /person/ in this archive (the kit's default is /people/) */
export const personBase = "/person/";
