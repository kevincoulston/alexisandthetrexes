// Tells Bing (and the other IndexNow search engines) which pages changed.
// Run it right after a deploy:
//   node indexnow.mjs            pages whose live HTML changed since the last run on this computer
//   node indexnow.mjs --all      every page in the sitemap
//   node indexnow.mjs --dry-run  show what would be sent, send nothing
// The first run on a computer sends every page. Page hashes are kept in
// .indexnow-state.json next to this file (ignored by Git). Needs Node 18 or newer.
import {createHash} from 'node:crypto';
import {existsSync, readFileSync, writeFileSync} from 'node:fs';

const HOST = 'alexisandthetrexes.com';
const KEY = '196f6339d9e200ab10aef9905222f351';
const SITE = `https://${HOST}`;
const STATE = new URL('./.indexnow-state.json', import.meta.url);
const args = new Set(process.argv.slice(2));

// Cloudflare adds per-request tokens (bot check, email protection); drop them so
// an unchanged page hashes the same on every run.
const clean = html => html
  .replace(/<script\b[^>]*>[^<]*__CF\$cv\$params[\s\S]*?<\/script>/g, '')
  .replace(/\/cdn-cgi\/l\/email-protection#[0-9a-f]+/g, '')
  .replace(/data-cfemail="[0-9a-f]+"/g, '')
  .replace(/\snonce="[^"]*"/g, '');

async function get(url, tries = 3) {
  for (let i = 1; ; i++) {
    try {
      return await fetch(url, {redirect: 'manual', headers: {'User-Agent': 'indexnow-deploy-check'}});
    } catch (e) {
      if (i >= tries) throw e;
      await new Promise(r => setTimeout(r, 1000 * i));
    }
  }
}

const keyRes = await get(`${SITE}/${KEY}.txt`);
if (!keyRes.ok || (await keyRes.text()).trim() !== KEY) {
  console.error(`${SITE}/${KEY}.txt is not live (status ${keyRes.status}). Deploy first, then run this again.`);
  process.exit(1);
}

const sitemap = await (await get(`${SITE}/sitemap.xml`)).text();
const urls = [...new Set([...sitemap.matchAll(/<url>\s*<loc>([^<]+)<\/loc>/g)]
  .map(m => m[1].trim().replace(/&amp;/g, '&'))
  .filter(u => new URL(u).host === HOST))];
if (!urls.length) {
  console.error(`No pages found in ${SITE}/sitemap.xml.`);
  process.exit(1);
}

const old = existsSync(STATE) ? JSON.parse(readFileSync(STATE, 'utf8')) : {};
const hashes = {}, skipped = [];
let next = 0;
await Promise.all(Array.from({length: 6}, async () => {
  while (next < urls.length) {
    const url = urls[next++];
    try {
      const r = await get(url);
      if (r.status !== 200) { skipped.push(`${url} (${r.status})`); continue; }
      hashes[url] = createHash('sha256').update(clean(await r.text())).digest('hex');
    } catch (e) {
      skipped.push(`${url} (${e.message})`);
    }
  }
}));

const send = urls.filter(u => hashes[u] && (args.has('--all') || old[u] !== hashes[u]));
console.log(`${HOST}: ${urls.length} pages in the sitemap, ${send.length} to send` +
  (Object.keys(old).length ? '' : ' (first run on this computer, so every page)'));
for (const s of skipped) console.log(`  not sent, did not load: ${s}`);
if (args.has('--dry-run')) {
  for (const u of send) console.log(`  ${u}`);
  process.exit(0);
}

for (let i = 0; i < send.length; i += 10000) {
  const r = await fetch('https://api.indexnow.org/indexnow', {
    method: 'POST',
    headers: {'Content-Type': 'application/json; charset=utf-8'},
    body: JSON.stringify({host: HOST, key: KEY, keyLocation: `${SITE}/${KEY}.txt`, urlList: send.slice(i, i + 10000)}),
  });
  if (r.status !== 200 && r.status !== 202) {
    console.error(`IndexNow refused the list (status ${r.status}): ${await r.text()}`);
    process.exit(1);
  }
}
// Keep the old hash for pages that did not load, so they are retried next time.
for (const s of skipped) { const u = s.split(' ')[0]; if (old[u]) hashes[u] = old[u]; }
writeFileSync(STATE, JSON.stringify(hashes, null, 1) + '\n');
console.log(send.length ? `Sent ${send.length} page(s) to IndexNow.` : 'Nothing changed, nothing sent.');
