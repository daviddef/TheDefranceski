/* THE RESEARCH MENU: one list, read by the header menu (layouts/Base.astro), the drawer, the hub page /research/ and the two group
   pages. 12 November 2026 (the research-menu trial): "Evidence" and "Investigations" became one "Research" menu with three groups,
   as David chose. Nothing is renamed: every item keeps the address it had. The labels of the eight pages the estate's Evidence canon
   names (kit data/evidence-menu.json) are unchanged, so the estate reads the same. `asks` is the canon's question for those pages;
   `atlas` marks the pages whose registers and places are also on the Record Atlas.
   23 November 2026 (the estate clean-up, Task C): the header menu shows ONE "Deep dives" entry, whose heading links to the hub /research/deep-dives/
   (a sub-group with `hub`); every study, deep dive and register page that used to be listed under it is on that hub, which reads this same list,
   so the menu and the hub cannot disagree. A sub-group with `menu: false` is not drawn in the menu at all and is hub-only. */
export const DEEP_DIVES_HUB = "/research/deep-dives/";
export const RESEARCH = [
  { id: "to-do", head: "To do", href: "/research/to-do/",
    dek: "What is not known yet, what has been asked of other people, and what is being worked on.",
    items: [
      { href: "/open-questions/", label: "Open Questions", asks: "What is not known, and what would settle it?" },
      { href: "/errands/", label: "Errands", asks: "What has been asked of other people, or needs someone standing in a place?" },
      { href: "/worklist/", label: "The work list", asks: "What is being done, by whom, since when?" },
    ] },
  { id: "whats-new", head: "What's new", href: "/whats-new/",
    dek: "What was read, found and taken back lately, newest first, and the same record in full.",
    items: [
      { href: "/searched/", label: "What Has Been Read", asks: "What was looked at, and what did it not turn up?" },
      { href: "/corrections/", label: "Corrections", asks: "What did this archive get wrong?" },
      { href: "/changes/", label: "What changed", asks: "What happened, most recent first?" },
    ] },
  { id: "sources-and-method", head: "Sources & method", href: "/research/sources-and-method/",
    dek: "What this archive stands on, how it reads a register, and the long studies of single sources.",
    items: [
      { href: "/sources/", label: "Sources", asks: "What does this stand on, and where do I check?" },
      { href: "/method/", label: "Method", asks: "What would make you believe or not believe this?" },
      { href: "/gallery/", label: "Gallery", asks: "What do the pages themselves look like?" },
      { sub: "Deep dives", id: "deep-dives", hub: DEEP_DIVES_HUB,
        note: "A single source studied on its own. Each is linked from its row on the Sources page.",
        items: [
          { href: "/carlos-letter/", label: "Carlo's Letter", source: "kobler" },
          { href: "/carlos-book/", label: "Carlo's Book", source: "carlo1879" },
          { href: "/the-library/", label: "The Library", source: "nsk2022" },
          { href: "/findmypast/", label: "Findmypast, swept", source: "findmypast" },
          { href: "/live-tree/", label: "The live tree, reconciled", source: "myheritage-live" },
          { href: "/dna/", label: "The DNA", source: ["ydna", "23andme"] },   /* 12 Nov 2026: left Start; the page reads these two tests */
        ] },
      { sub: "Registers and places (also on the Atlas)", id: "registers-and-places", menu: false,
        note: "The registers and places themselves are on the Record Atlas; these pages keep what only this archive holds: what has been read, what was walked, the verdicts.",
        items: [
          { href: "/archive/", label: "Archive", atlas: true },
          { href: "/parish-books/", label: "Parish Books", atlas: true },
          { href: "/map/", label: "The Map", atlas: true },
          { href: "/collections-walk/", label: "Every collection walked", atlas: true },
          { href: "/undigitised/", label: "The undigitised", atlas: true },
          { href: "/antenati/", label: "Antenati registers", atlas: true },
        ] },
    ] },
];
/* the header menu's shape: [group, ...] with { head, href, items: [[href, label] | { sub }] } */
export const navGroups = RESEARCH.map((g) => ({
  head: g.head, href: g.href,
  items: g.items.flatMap((x) => x.sub ? (x.menu === false ? [] : [{ sub: x.sub, href: x.hub }]) : [[x.href, x.label]]),
}));

/* The name's single studies, which left the "The name" menu on 23 Nov 2026 and stand on the deep-dives hub instead: [{ href, label }] (the blurbs are the book's) */
export const NAME_STUDIES = [
  { href: "/imperial/", label: "The name in imperial service" },
  { href: "/julius/", label: "Julius — a naval career" },
  { href: "/fiume-1626/", label: "Fiume, 1626" },
  { href: "/at-sea/", label: "At sea — Lloyd's List" },
  { href: "/giornaletto/", label: "The Giornaletto di Pola" },
];

/* the deep dives, by the id of the Sources row each one is linked from (one id or a list): { sourceId: [[label, href]] } */
export const deepDiveLinks = {};
for (const d of RESEARCH.flatMap((g) => g.items).filter((x) => x.id === "deep-dives").flatMap((x) => x.items)) {
  for (const id of [].concat(d.source)) (deepDiveLinks[id] ||= []).push(["Deep dive: " + d.label, d.href]);
}
