// Tells Bing (and the other IndexNow search engines) about NEW and UPDATED pages only.
// It never sends the whole site. Run it right after a deploy:
//   node indexnow.mjs            send pages that are new or whose content changed since the last run
//   node indexnow.mjs --dry-run  show what would be sent, send nothing, save nothing
//   node indexnow.mjs --yes      also send when more pages changed than the safety limit allows
//
// How it decides (Kevin, Nov 18 2026: "only send pages that have been updated, and new pages"):
// - New page: in the live sitemap but not seen on the last run. Always sent.
// - Updated page: the page's own content changed (title, description, canonical and the text and
//   images inside <main>). Header, menu, footer, scripts and Cloudflare tokens are ignored, so a
//   site-wide menu or footer edit does not mark every page as updated.
// - Safety limit: if more than CHANGED_LIMIT pages look updated at once, that is a site-wide
//   template change, not real page updates. Those are NOT sent (new pages still are) and are marked
//   as seen, so they are not sent next time either. To send a big batch on purpose, run --dry-run
//   first, then --yes.
//   More than NEW_LIMIT new pages at once also needs --yes.
// - First run on a computer (no .indexnow-state.json yet): nothing is sent; it only records the
//   pages so the next run can tell what changed. Pages marked noindex are never sent.
// State is kept in .indexnow-state.json next to this file (ignored by Git). Needs Node 18 or newer.
import {createHash} from 'node:crypto';
import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

const HOST = 'alexisandthetrexes.com';
const KEY = '196f6339d9e200ab10aef9905222f351';
const SITE = `https://${HOST}`;
const STATE = new URL('./.indexnow-state.json', import.meta.url);
const STATE_VERSION = 2;
const CHANGED_LIMIT = 50;
const NEW_LIMIT = 300;
const args = new Set(process.argv.slice(2));
const unknown = [...args].filter(a => !['--dry-run', '--yes'].includes(a));
if (unknown.length) {
  console.error(`Unknown option ${unknown.join(' ')}. Use --dry-run or --yes. (--all was removed: the whole site is never sent.)`);
  process.exit(1);
}

const decode = s => s.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const attr = (tag, name) => (tag.match(new RegExp(`\\s${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, 'i')) || [])[2] ?? '';
const metaContent = (html, key, val) => {
  for (const tag of html.match(/<(meta|link)\b[^>]*>/gi) || []) {
    if (attr(tag, key).toLowerCase() === val) return attr(tag, tag.toLowerCase().startsWith('<link') ? 'href' : 'content');
  }
  return '';
};

// The part of a page that is its own content. Everything that is the same on every page
// (header, menu, footer) or changes on every request (Cloudflare tokens, scripts) is left out.
export function fingerprint(html) {
  html = html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<(script|style|noscript|template|svg|iframe)\b[\s\S]*?<\/\1>/gi, '')
    .replace(/\/cdn-cgi\/l\/email-protection#[0-9a-f]+/g, '')
    .replace(/data-cfemail="[0-9a-f]+"/g, '')
    .replace(/\snonce="[^"]*"/g, '');
  const title = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '';
  const head = [title, metaContent(html, 'name', 'description'), metaContent(html, 'rel', 'canonical')];
  const start = html.search(/<main\b/i), end = html.lastIndexOf('</main>');
  let body = start >= 0 && end > start ? html.slice(start, end) : (html.match(/<body\b[\s\S]*<\/body>/i) || [html])[0];
  body = body.replace(/<(header|footer|nav)\b[\s\S]*?<\/\1>/gi, '');
  const images = [...body.matchAll(/<img\b[^>]*>/gi)].map(m => attr(m[0], 'src').split('?')[0]);
  const text = decode(body.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
  return createHash('sha256').update(JSON.stringify([...head.map(s => decode(s).trim()), text, images])).digest('hex');
}

const noindex = html => /<meta\b[^>]*name\s*=\s*["']robots["'][^>]*content\s*=\s*["'][^"']*noindex/i.test(html);

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

async function main() {
  const keyRes = await get(`${SITE}/${KEY}.txt`);
  if (!keyRes.ok || (await keyRes.text()).trim() !== KEY) {
    console.error(`${SITE}/${KEY}.txt is not live (status ${keyRes.status}). Deploy first, then run this again.`);
    process.exit(1);
  }

  const sitemap = await (await get(`${SITE}/sitemap.xml`)).text();
  const urls = [...new Set([...sitemap.matchAll(/<url>\s*<loc>([^<]+)<\/loc>/g)]
    .map(m => decode(m[1].trim()))
    .filter(u => new URL(u).host === HOST))];
  if (!urls.length) {
    console.error(`No pages found in ${SITE}/sitemap.xml.`);
    process.exit(1);
  }

  // Old state files (from the version that hashed the whole page) still tell us which pages
  // existed, so new pages are found, but their hashes cannot be compared and are not used.
  const raw = existsSync(STATE) ? JSON.parse(readFileSync(STATE, 'utf8')) : null;
  const current = raw && raw.version === STATE_VERSION;
  const oldPages = !raw ? {} : current ? raw.pages : Object.fromEntries(Object.keys(raw).map(u => [u, null]));

  const hashes = {}, skipped = [], hidden = [];
  let next = 0;
  await Promise.all(Array.from({length: 6}, async () => {
    while (next < urls.length) {
      const url = urls[next++];
      try {
        const r = await get(url);
        if (r.status !== 200) { skipped.push(`${url} (${r.status})`); continue; }
        const html = await r.text();
        if (noindex(html)) { hidden.push(url); continue; }
        hashes[url] = fingerprint(html);
      } catch (e) {
        skipped.push(`${url} (${e.message})`);
      }
    }
  }));

  const loaded = urls.filter(u => hashes[u]);
  const added = raw ? loaded.filter(u => !(u in oldPages)) : [];
  const changed = current ? loaded.filter(u => u in oldPages && oldPages[u] !== hashes[u]) : [];
  const yes = args.has('--yes');
  const tooManyChanged = changed.length > CHANGED_LIMIT && !yes;
  const tooManyNew = added.length > NEW_LIMIT && !yes;
  const send = [...(tooManyNew ? [] : added), ...(tooManyChanged ? [] : changed)];

  console.log(`${HOST}: ${urls.length} pages in the sitemap, ${added.length} new, ${changed.length} updated, ${send.length} to send.`);
  if (!raw) console.log('  First run on this computer: nothing sent. Pages recorded, so the next run sends only new and updated pages.');
  else if (!current) console.log('  State file is from the old version: only new pages can be found this time. Updated pages are tracked from now on.');
  if (tooManyChanged) console.log(`  ${changed.length} pages look updated at once (limit ${CHANGED_LIMIT}). That is a site-wide change, so they were NOT sent${args.has('--dry-run') ? '' : ' and are now marked as seen'}. If every one of them really has new content, check with --dry-run and send them with --yes before the next normal run.`);
  if (tooManyNew) console.log(`  ${added.length} new pages at once (limit ${NEW_LIMIT}), so they were NOT sent and will be offered again next run. Rerun with --yes to send them.`);
  for (const s of skipped) console.log(`  not checked, did not load: ${s}`);
  if (hidden.length) console.log(`  ${hidden.length} page(s) marked noindex, never sent.`);
  if (args.has('--dry-run')) {
    for (const u of send) console.log(`  ${u}`);
    console.log('Dry run: nothing sent, nothing saved.');
    return;
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
  for (const u of send) console.log(`  sent ${u}`);

  // Pages that did not load keep their old hash so they are checked again next time.
  // New pages held back by the limit are left out, so they still count as new next time.
  const pages = {...hashes};
  for (const s of skipped) { const u = s.split(' ')[0]; if (oldPages[u]) pages[u] = oldPages[u]; }
  if (tooManyNew) for (const u of added) delete pages[u];
  writeFileSync(STATE, JSON.stringify({version: STATE_VERSION, pages}, null, 1) + '\n');
  console.log(send.length ? `Sent ${send.length} page(s) to IndexNow.` : 'Nothing new or updated, nothing sent.');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
