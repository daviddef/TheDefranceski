/* THE WHOLE MENU, one list. 12 November 2026 (the menu regroup, PR A): the seven groups other than Research became five, and Research
   (lib/research-menu.js, unchanged in shape) is the sixth. The header menu, the drawer and anything else that needs "where is this page
   in the menu" read THIS list (layouts/Base.astro does), so there is one place to change a label or move a page. No page was renamed and
   no address changed: every href below is a page that was already built, only its group moved.
     a menu is  [label, items]
     items     either a flat list of [href, label]            (a short menu: one column)
               or a list of groups { head, href?, items }   (a group is a column; `href` makes its heading a link; an item is [href, label])
   The addresses a menu used to carry and no longer shows by name: /whats-new/ left Start (it is the "What's new" group of Research),
   /dna/ left Start (a deep dive under Sources), /senj-line/ was in two menus (chapter 5 of Our line; "Blažević — Hedviga" is the same page),
   /burials/ moved from Go there to People. */
import { navGroups } from "./research-menu.js";

export const MENU = [
  ["Start", [
    ["/", "Home"], ["/story/", "Start with the story"], ["/about/", "About"],
  ]],
  ["Our line", [
    { head: "The line", items: [
      ["/direct-line/", "The Spine"], ["/carnia/", "1 · Carnia"], ["/gologorica-line/", "2 · Gologorica"],
      ["/the-eleven/", "3 · Gračišće — the Eleven"], ["/crikvenica-house/", "4 · Crikvenica"], ["/senj-line/", "5 · Senj"],
      ["/pfullingen/", "6 · Pfullingen"],
    ] },
    { head: "Maternal lines", items: [
      ["/maternal/salomon/", "Salomon — Francisca"], ["/maternal/fernasar/", "Fernasar — Maria"], ["/kalanj/", "Kalanj — Anna"],
      ["/maternal/kovacina/", "Kovačina — Uršula"],
    ] },
    { head: "People and stories", items: [
      ["/carlo/", "Carlo De Franceschi"], ["/cheryl-lerena/", "Cheryl Lerena — the poems"], ["/1948/", "Nineteen forty-eight"],
      ["/vodnjan/", "Vodnjan"],
    ] },
  ]],
  ["People", [
    { head: "Lists", items: [
      ["/people/", "The People"], ["/who/", "Every Name"], ["/register/", "The Register"], ["/households/", "Households"],
      ["/marriages/", "The Marriages"], ["/graves/", "Graves"], ["/burials/", "Burials"],
    ] },
    { head: "Drawn", items: [
      ["/tree/", "Our line, drawn"], ["/trees/", "The trees"], ["/roots/", "Roots & Routes"], ["/timeline/", "The Timeline"],
      ["/bloodline/", "Blood relatives, drawn"], ["/explorer/", "Explorer"],
    ] },
  ]],
  ["Places & families", [
    { head: "The families", items: [
      ["/lines/", "The Lines"], ["/lines/#regions", "Bakar, Fiume & the unplaced"], ["/places/svetvincenat/", "Svetvinčenat — the castle"],
      ["/omis-line/", "Out of Venice — Omiš"], ["/imotski/", "…and Imotski"], ["/seget/", "Out of Crete — Seget"],
      ["/liznjan/", "Southern Istria — Ližnjan"], ["/rijeka/", "The Kvarner — Rijeka and Bakar"], ["/dubrovnik/", "Ragusa — Dubrovnik"],
      ["/corsica/", "Corsica — a parallel"], ["/trentino/", "Trentino — a blind spot"],
    ] },
    { head: "Places", items: [
      ["/places/", "Places"], ["/istria-sweep/", "Every town"], ["/diaspora/", "Where the name went"], ["/emigration/", "Leaving"],
      ["/journeys/", "Journeys"],
    ] },
    { head: "Walking it", items: [
      ["/walk/", "Walk the line"], ["/walk/carnia/", "Carnia — Val Degano"], ["/walk/gologorica/", "Gologorica & Gračišće"],
    ] },
  ]],
  ["The name", [
    { head: "The name", items: [
      ["/name/", "The Name"], ["/your-name/", "Say Your Name"], ["/arms/", "Arms & Flags"], ["/namesakes/", "Namesakes"],
    ] },
    { head: "In the records", items: [
      ["/imperial/", "The name in imperial service"], ["/julius/", "Julius — a naval career"], ["/fiume-1626/", "Fiume, 1626"],
      ["/at-sea/", "At sea — Lloyd's List"], ["/giornaletto/", "The Giornaletto di Pola"],
    ] },
  ]],
  ["Research", navGroups],
];
