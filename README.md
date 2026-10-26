# alexisandthetrexes

Source for https://alexisandthetrexes.com, the home of Kevin Coulston's Alexis and the T-Rexes picture books (Count to Ten, Birthday Surprise, Hide and Seek).

Shared source for ChatGPT/Codex and Claude. Read [AGENTS.md](AGENTS.md) and [DEPLOYMENT.md](DEPLOYMENT.md) before editing or deploying.

## Layout

- `site_data.py`: all book facts (from the Amazon listings, Oct 26 2026), characters, free pages and the GA4 ID (`GA_ID`, G-FEWWZYTBCV, loaded on first interaction or after 4 s; no tag is written when it is empty).
- `build.py`: writes `dist/` from `site_data.py`, `src/style.css`, `src/site.js` and `art/` (WebP srcset variants, inline CSS, self-hosted Chewy and Lexend with size-matched fallbacks, JSON-LD, sitemap, robots, headers).
- `seo_enrich.py`: the network's shared structured data, alt text and image sitemap pass (uses `products.json` and `book-isbns.csv`). Also writes the IndexNow key file.
- `src/worker.js`: serves `dist/`, redirects www to the bare domain, and marks the temporary workers.dev address noindex.
- `indexnow.mjs`: tells Bing which pages changed after a deploy.

Build: `python3 build.py && python3 seo_enrich.py` (needs Pillow). Commit `dist/` with the source.

## Pages

`/`, `/books/`, `/books/count-to-ten/`, `/books/birthday-surprise/`, `/books/hide-and-seek/`, `/meet-the-gang/`, `/free-dinosaur-pages/`, `/about/`, plus `404.html`.

## IndexNow (Bing)

After each deploy, run `node indexnow.mjs` from this folder (Node 18 or newer). It checks that `/196f6339d9e200ab10aef9905222f351.txt` is live and sends the pages whose HTML changed since its last run on that computer. `--all` resends every page, `--dry-run` sends nothing. Page hashes are kept in `.indexnow-state.json`, which Git ignores.
