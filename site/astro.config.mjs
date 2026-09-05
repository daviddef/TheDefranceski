import { defineConfig } from 'astro/config';

// GitHub Pages project site. If you later point defranceski.com at this repo,
// set base to '/' and site to 'https://defranceski.com'.
export default defineConfig({
  site: 'https://daviddef.github.io',
  base: '/TheDefranceski',
  build: { format: 'directory' },
});
