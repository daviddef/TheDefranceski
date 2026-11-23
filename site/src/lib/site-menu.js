/* THE WHOLE MENU, one list. 12 November 2026 (the menu regroup, PR A): the seven groups other than Research became five, and Research
   (lib/research-menu.js, unchanged in shape) is the sixth. The header menu, the drawer and anything else that needs "where is this page
   in the menu" read THIS list (layouts/Base.astro does), so there is one place to change a label or move a page. No page was renamed and
   no address changed: every href below is a page that was already built, only its group moved.
     a menu is  [label, items]
     items     either a flat list of [href, label]            (a short menu: one column)
               or a list of groups { head, href?, items }   (a group is a column; `href` makes its heading a link; an item is [href, label])
   The addresses a menu used to carry and no longer shows by name: /whats-new/ left Start (it is the "What's new" group of Research),
   /dna/ left Start (a deep dive under Sources), /senj-line/ was in two menus (chapter 5 of Our line; "Blažević — Hedviga" is the same page),
   /burials/ moved from Go there to People.
   23 November 2026 (the estate clean-up, Task C), what left the menu by name and where it is reached from instead:
     People / Drawn (Our line, drawn; The trees; Blood relatives, drawn; Household Explorer; The Timeline)  ->  the hub /drawn/, which reads DRAWN below.
     Places & families / The families (Svetvinčenat, Omiš, Imotski, Seget, Ližnjan, Rijeka, Dubrovnik, Corsica, Trentino, and "Bakar, Fiume & the unplaced")
       ->  the hub /families/ ("All the families"), which lists them and every family of the book (the mothers' families, the 21 /married-in/ pages);
       four stay named (NAMED_FAMILIES). "Bakar, Fiume & the unplaced" is a section of /lines/ (#regions), which stays in Places.
     The name / In the records (imperial, Julius, Fiume 1626, At sea, the Giornaletto)  ->  the deep-dives hub /research/deep-dives/ (NAME_STUDIES).
     Research / Deep dives (six studies) and Registers and places (six)  ->  the deep-dives hub, whose heading is the one "Deep dives" entry of the menu. */
import { navGroups } from "./research-menu.js";

/* THE HUB OF DRAWN PAGES (/drawn/): one line each on what it shows. The menu carries ONE link, "Drawn"; the page reads this list.
   No page was renamed or moved. */
export const DRAWN = [
  { href: "/tree/", label: "Our line, drawn", blurb: "Eight generations of the one descent, each as the couple it actually was, with every child listed." },
  { href: "/tree/#trees", label: "The trees", blurb: "The families of the book drawn one by one, each in the form its evidence supports." },
  { href: "/direct-line/", label: "The Spine", blurb: "The direct line as eight generations, and for four of them the parish-book page that names the household." },
  { href: "/bloodline/", label: "Blood relatives, drawn", blurb: "Choose a person and see their parents, brothers and sisters and children round them; every line is coloured by the evidence behind it." },
  { href: "/bloodline/#households", label: "Household Explorer", blurb: "The households of the register, one at a time, with who lived in each." },
  { href: "/timeline/", label: "The Timeline", blurb: "Lives against history: sovereignty, pressure and family events on one scale." },
  { href: "/lives/", label: "Lives on one scale", blurb: "One bar to a person, birth to death, down the whole of a line; solid where a record gives the date, hollow where only a family tree does." },
  { href: "/lines/", label: "The Lines", blurb: "The families as lines on a river: where each came from, the stations it passed and the households not yet placed." },
];

/* THE FAMILIES: four family pages stay named in the menu (David's 12 Nov rule: the archive's own line first, then A to Z). The own line, Gologorica, is
   in "Our line", so here it is A to Z, and the four are the families with the most people on record (Svetvinčenat, Ližnjan, Omiš, Rijeka). Every other
   family is reached through the hub /families/ ("All the families"). */
export const NAMED_FAMILIES = [
  ["/liznjan/", "Ližnjan"], ["/omis-line/", "Omiš"], ["/rijeka/", "Rijeka"], ["/places/svetvincenat/", "Svetvinčenat"],
];

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
    { head: "Drawn", href: "/drawn/", items: [] },
  ]],
  ["Places & families", [
    { head: "Places", href: "/places/", items: [
      ["/lines/", "The Lines"], ["/map/", "The Map"], ["/istria-sweep/", "Every town"], ["/diaspora/", "Where the name went"],
      ["/diaspora/#leaving", "Leaving"],
    ] },
    { head: "The families", items: [
      ["/families/", "All the families"], ...NAMED_FAMILIES,
    ] },
    { head: "Walking it", items: [
      ["/walk/", "Walk the line, and the journeys"], ["/walk/carnia/", "Carnia — Val Degano"], ["/walk/gologorica/", "Gologorica & Gračišće"],
    ] },
  ]],
  /* THE NAME: its own group, one column. "In the records" (five single studies) moved to the deep-dives hub. */
  ["The name", [
    ["/name/", "The Name"], ["/your-name/", "Say Your Name"], ["/namesakes/", "Namesakes"], ["/arms/", "Arms & Flags"],
  ]],
  ["Research", navGroups],
];
