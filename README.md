# shaneniemeyer.com

The site for Shane Niemeyer: doctrine, library, and coaching.

## How it's built

- **Edit `src/site.html`.** It holds every page as a `<div class="view" data-view="...">`.
- **Run `python3 build.py`.** It writes one real page per view (`index.html`, `doctrine/index.html`, ...)
  with its own title, description, share tags and canonical URL, plus `sitemap.xml`, `robots.txt`, `404.html`
  and the icons and share image from `src/assets/`.
- **Commit both the source and the built files.** Netlify serves the repo as-is on every push to `main`.
- Page titles and share descriptions live in the `META` table at the top of `build.py`.
- Old `#page` links (for example `/#doctrine`) redirect to the new page addresses.
- `python3 build.py --theme ember --out /tmp/preview` builds a themed preview (`src/ember.css`) without touching the live files.
