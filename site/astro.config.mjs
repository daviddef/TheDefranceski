import { defineConfig } from 'astro/config';

// GitHub Pages project site. If you later point defranceski.com at this repo,
// set base to '/' and site to 'https://defranceski.com'.
export default defineConfig({
  site: 'https://daviddef.github.io',
  base: '/TheDefranceski',
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
    '/married-in': '/TheDefranceski/marriages',
    '/research-map': '/TheDefranceski/map',
    '/atlas': '/TheDefranceski/map',
    '/graves-map': '/TheDefranceski/map',
    /* 9 October 2026: three pages folded into pages that do the same job. */
    '/research-log': '/TheDefranceski/open-questions/',
    '/gaps': '/TheDefranceski/open-questions/#gaps',
    '/photograph-these': '/TheDefranceski/errands/#photographs',
  },
});
