import { defineConfig } from 'astro/config';

// Served at the ROOT of its own subdomain since 12 October 2026 —
// https://archive.defranceski.com/ — not as a path under daviddef.github.io.
// base must stay '/' and site must stay the bare origin: the kit's
// archives.json keys this archive on base "" (BASE_URL stripped of its
// trailing slash), and SocialHead falls back to the children's site, silently,
// if the two disagree. GitHub redirects the old /TheDefranceski/ address.
export default defineConfig({
  site: 'https://archive.defranceski.com',
  base: '/',
  /* WHY outDir IS A VARIABLE, and why the default must stay 'dist'.
     Several sessions build this estate at once, and `astro build` EMPTIES its
     outDir before it refills it — so one session's build wipes the tree
     another session's gates are reading, and the gates report a torrent of
     absences that are simply not copied yet. The kit's tools all honour
     ARCHIVE_OUT and, when they refuse a shared build, print «build to a
     directory of your own: ARCHIVE_OUT=...» as the way out. WITHOUT THIS LINE
     THAT HATCH CANNOT BE TAKEN: the variable redirected every reader and
     nothing that writes. Found 27 September 2026, after the kit had been
     printing that advice for four days.
     THE DEFAULT MUST STAY 'dist' — .github/workflows uploads `path: site/dist`,
     so changing it here would publish nothing. */
  outDir: process.env.ARCHIVE_OUT || 'dist',

  build: { format: 'directory' },
  /* The index of in-law families is now a section of /marriages/ — the essay on
     who this family married and the routing of those families to the empire
     that still holds their records were one argument split across two pages.
     The per-family detail pages under /married-in/<slug>/ stay exactly where
     they are; only the index moved, so the index address redirects rather than
     rotting. */
  /* The research map, the atlas and the graves map were three maps of the
     same ground. They are one map at /map/ now, and the three addresses that
     have been published and linked to for months land there rather than
     rotting. */
  redirects: {
    '/married-in': '/marriages',
    '/research-map': '/map',
    '/atlas': '/map',
    '/graves-map': '/map',
    /* 16 October 2026: five research notes link to /plates/ (the corrections
       log, the Gologorica line, the searched log and the Kalanj page, twice);
       the plate room has always been /gallery/, so /plates/ was a dead link.
       The prose is not edited; the address lands where the notes meant. */
    '/plates': '/gallery/',
    /* 9 October 2026: three pages folded into pages that do the same job. */
    '/research-log': '/open-questions/',
    '/gaps': '/open-questions/#gaps',
    '/photograph-these': '/errands/#photographs',
    /* The six retired /who/ addresses (a rename on 12 October 2026, four surname-first pages from the 27 September
       Trove harvest, and a rename on 21 September) used to be redirects here. On 17 October 2026 the book made every
       built page a chapter with a running head, and an Astro redirect page has no layout to carry one, so they are now
       ordinary pages at the same six addresses (src/pages/who/<old-slug>.astro, via components/Moved.astro): the same
       meta refresh, the same canonical, inside the layout. Each still lands where it did; the reasons are kept with the
       pages. */
  },
});
