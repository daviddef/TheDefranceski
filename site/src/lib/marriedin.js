/* Which families married in, and how they are grouped — in one place, so the
   front page and /marriages/ cannot drift into two different answers. */
import mi from "../data/marriedin.json";
const ORIGIN = { venetian:"--r-venice", slavic:"--accent", carnia:"--terra",
  austrian:"--r-habsburg", maritime:"--r-italy", uskok:"--r-yugo" };
const ORD = ["hungarian-littoral","istria-austrian","dalmatia","carnia","venice"];
export const chartGroups = ORD.filter((k) => mi.routes[k]).map((k) => ({
  key: k, label: mi.routes[k].label,
  families: mi.rows.filter((r) => r.route === k)
    .map((r) => ({ surname: r.name, n: r.notindexed ? 0 : r.c, accent: ORIGIN[r.origin] })),
})).filter((g) => g.families.length);
