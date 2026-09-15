import { defineConfig } from 'astro/config';

// GitHub Pages project site. If you later point defranceski.com at this repo,
// set base to '/' and site to 'https://defranceski.com'.
export default defineConfig({
  site: 'https://daviddef.github.io',
  base: '/TheDefranceski',
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
  },
});
