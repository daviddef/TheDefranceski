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
  redirects: { '/married-in': '/TheDefranceski/marriages' },
});
