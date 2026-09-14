/* The blood graph, derived from dossiers.json at build time.

   There is deliberately no bloodline.json. Every link below already exists in
   the dossiers — 200 parent links and 765 sibling links carrying a slug, and
   535 children named on the tree records — and a second copy of them is a
   second thing to keep in step. Derive, do not duplicate.

   Every edge carries the `via` the dossier recorded for it: read from a
   register, taken from an index, from the direct line, or asserted by the
   family tree and nothing else. The chart draws each line in the colour of its
   own evidence, and an edge is always drawn at the WEAKEST grade of the two
   records that produced it. */
import d from "../data/dossiers.json";
import dl from "../data/directline.json";

const P = d.people;

/* Children named on a tree record are NOT resolved to a person by their name,
   and the first version of this file was wrong to try.

   The check that looked safe was: does a child's name match more than one
   dossier page? It almost never does. The check that matters is the other
   direction — do several different parents name a child with the SAME name? —
   and there it fails badly. Five separate women in these registers each record
   a son called "Pietro De Franceschi". Matching on the name gave that one
   dossier page five mothers, and thirty-six people came out with impossible
   parentage: precisely the kind of join this archive exists to refuse.

   So the only parent-child edges drawn are the ones the dossiers themselves
   assert, by slug, with a `via`. Children named on a tree record still appear
   beside their parent — they are real children, written down by a priest — but
   as names, unlinked, because nothing here can say which page they belong to. */

const RANK = { read: 3, line: 3, index: 2, tree: 1 };
const weakest = (a, b) => (RANK[a] ?? 1) <= (RANK[b] ?? 1) ? (a || "tree") : (b || "tree");

/* THE SPINE. The dossiers are built from register readings, so they stop where
   the parish books stop — and the last four generations of this family are not
   in a parish book at all. Building the chart from the dossiers alone left the
   archive's own direct line out of it: a reader looking for their father, or
   themselves, found nothing and was told to check the spelling.

   directline.json is the chain the archive argues page by page, eight
   generations from Gologorica to Brisbane, and consecutive generations are
   parent and child by definition. It goes in.

   Each generation keeps its OWN id rather than being matched to a dossier page
   by name, because generations 6 and 7 are both called Ivan Defranceski —
   father and son, one name — and matching on it would fold two men into one.
   That is the same mistake that gave one Pietro five mothers; it is not made
   twice.

   The living are named and nothing more, which is this archive's rule and the
   reason the last generation is here at all: a person who is alive is the one
   most likely to want to see their own line. No date is carried for them, and
   the build's own living check enforces that independently. */
function spine(people) {
  const rows = (dl.generations || []).filter((g) => g && g.name);
  const id = (g) => "line-" + g.n;
  for (const g of rows) {
    const living = g.confidence === "living";
    people[id(g)] = people[id(g)] || {
      slug: id(g), name: g.name,
      /* "2026" on its own reads as a birth year. Say which it is. */
      dt: living ? ""
        : g.born && g.died ? g.born + " – " + g.died
        : g.born ? "b. " + g.born
        : g.died ? "d. " + g.died : "",
      spine: g.n, living, place: g.place || "",
      parents: [], children: [], siblings: [], spouse: null,
    };
  }
  for (const g of rows) {
    const up = rows.find((x) => x.n === g.n - 1);
    if (!up) continue;
    const me = people[id(g)], par = people[id(up)];
    me.parents.push({ slug: id(up), name: up.name, dt: people[id(up)].dt, via: "line" });
    par.children.push({ slug: id(g), name: g.name, dt: me.dt, via: "line" });
  }
  return people;
}

export function graph() {
  const people = {};
  const put = (slug) => (people[slug] ||= {
    slug, name: P[slug]?.name || slug, dt: "",
    parents: [], children: [], siblings: [], spouse: null,
  });

  for (const [slug, r] of Object.entries(P)) {
    const pt = r.ptree || {};
    if (pt.none) continue;
    const me = put(slug);
    if (pt.self?.dt) me.dt = pt.self.dt;

    for (const p of pt.parents || []) {
      if (!p.slug || p.slug === slug) continue;
      const via = p.via || "tree";
      me.parents.push({ slug: p.slug, name: p.n, dt: p.dt, via });
      const up = put(p.slug);
      if (!up.children.some((c) => c.slug === slug))
        up.children.push({ slug, name: r.name, dt: pt.self?.dt || "", via });
    }
    for (const s of pt.siblings || []) {
      if (!s.slug || s.slug === slug) continue;
      me.siblings.push({ slug: s.slug, name: s.n, dt: s.dt, via: s.via || "tree" });
    }

    const t = r.tree || {};
    if (t.spouse) me.spouse = t.spouse;
    for (const c of t.children || []) {
      /* named, never linked — see the note at the top of this file */
      if (!me.children.some((x) => x.name === c.n && !x.slug))
        me.children.push({ slug: null, name: c.n, dt: c.d || "", via: "tree" });
    }
  }

  spine(people);

  /* A child reached both ways — asserted by a dossier with a slug, and named
     again on the parent's tree record — was appearing twice in the chart, once
     as a link and once as a bare name. Keep the link. */
  for (const p of Object.values(people)) {
    const linkedNames = new Set(p.children.filter((c) => c.slug).map((c) => c.name));
    p.children = p.children.filter((c) => c.slug || !linkedNames.has(c.name));
  }

  /* siblings are symmetric; the dossiers only record one direction */
  for (const [slug, me] of Object.entries(people))
    for (const s of me.siblings) {
      const other = people[s.slug];
      if (other && !other.siblings.some((x) => x.slug === slug))
        other.siblings.push({ slug, name: me.name, dt: me.dt, via: s.via });
    }

  /* The registers contradict themselves in places: anto-de-franceschi is
     recorded as Mattio's father in one dossier and as his brother in another.
     Drawing him in both lanes puts the same man on the chart twice in two
     incompatible roles, which is worse than either reading. A parent or child
     link is directional and comes from a ptree the archive argued over, so it
     wins; the sibling claim is dropped. The contradiction is not hidden — both
     men keep their own pages, and the dossier still records both readings. */
  for (const me of Object.values(people)) {
    const kin = new Set([...me.parents, ...me.children].map((k) => k.slug).filter(Boolean));
    me.siblings = me.siblings.filter((s) => !kin.has(s.slug));
  }

  /* and no one is their own relative */
  for (const [slug, me] of Object.entries(people)) {
    me.parents = me.parents.filter((k) => k.slug !== slug);
    me.children = me.children.filter((k) => k.slug !== slug);
    me.siblings = me.siblings.filter((k) => k.slug !== slug);
  }

  return people;
}

/* Connected components over blood links only — marriage does not make kin. */
export function components(people) {
  const seen = new Set(), out = [];
  for (const slug of Object.keys(people)) {
    if (seen.has(slug)) continue;
    const stack = [slug], comp = [];
    while (stack.length) {
      const x = stack.pop();
      if (seen.has(x) || !people[x]) continue;
      seen.add(x); comp.push(x);
      for (const k of [...people[x].parents, ...people[x].children, ...people[x].siblings])
        if (k.slug && !seen.has(k.slug)) stack.push(k.slug);
    }
    out.push(comp);
  }
  return out.sort((a, b) => b.length - a.length);
}
