# Deployment

Cloudflare Worker `alexisandthetrexes` with static assets from `dist/`. `wrangler.jsonc` attaches the custom domains alexisandthetrexes.com and www.alexisandthetrexes.com (zone is on Kevin's Cloudflare account) and keeps the workers.dev address, which `src/worker.js` marks noindex.

## Build

python3 build.py && python3 seo_enrich.py

## Deploy (Windows, from D:\Claude Files\alexisandthetrexes; C:\Claude Files on the second PC)

git pull
npx.cmd wrangler deploy --config wrangler.jsonc

IndexNow is optional. If you run `node indexnow.mjs` after a deploy, it sends only new and updated pages, never the whole site (see README, IndexNow).

Account credentials are deliberately absent; use an authenticated Wrangler login. Never claim a commit is live without a successful deployment result.
