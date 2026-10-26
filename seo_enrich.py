#!/usr/bin/env python3
"""Structured data, alt text and image sitemap pass for AlexisAndTheTRexes.com (Oct 26, 2026).

Runs last in the build (python3 build.py && python3 seo_enrich.py) and only edits dist/. Safe to run again: it fills gaps
and rebuilds its own block each time. See the crustygoobers copy for the full description; only the settings differ.
Same shared code as the other network sites; only the settings above the line differ.
Run: python3 seo_enrich.py
"""
SITE = 'https://alexisandthetrexes.com'
DECORATIVE = None
SKIP_IMAGES = None                    # images to leave out of ImageObjects and the sitemap
ALT_OVERRIDES = {                     # file name -> alt
    'logo.webp': 'Alexis and the T-Rexes logo',
}
HOWTO = False
EXTRA = None
ISBN_LINE = None                      # (regex, html template): visible edition line on book pages, after the regex match

# ---------------------------------------------------------------------------
# Shared code below this line is the same in every site repo (Oct 25, 2026).
# ---------------------------------------------------------------------------
import glob, html as H, json, os, re, struct
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
KEVIN_ID = 'https://kevincoulston.com/#person'
FAB_ID = 'https://firstartbooks.com/#organization'
KEVIN = {'@type': 'Person', '@id': KEVIN_ID, 'name': 'Kevin Coulston', 'url': 'https://kevincoulston.com/',
         'jobTitle': 'Cartoonist and children’s book author and illustrator',
         'sameAs': ['https://nationalcartoonists.com/members/directory/member/?id=4515882', 'https://www.instagram.com/kevincoulston/',
                    'https://www.tiktok.com/@kevincoulston', 'https://www.youtube.com/@firstartbooks', 'https://kevincoulston.substack.com/',
                    'https://www.amazon.com/stores/author/B00JC406ZE', 'https://firstartbooks.com/']}
FAB = {'@type': 'Organization', '@id': FAB_ID, 'name': 'FirstArtBooks', 'url': 'https://firstartbooks.com/', 'founder': {'@id': KEVIN_ID}}
CREDIT = {'creator': {'@id': KEVIN_ID}, 'creditText': 'Kevin Coulston', 'copyrightHolder': {'@id': KEVIN_ID}, 'copyrightNotice': '© Kevin Coulston'}
IMG_EXT = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif'}
PAGE_TYPES = {'WebPage', 'CollectionPage', 'AboutPage', 'ItemPage', 'FAQPage'}
WORK_TYPES = {'Article', 'BlogPosting', 'HowTo', 'CreativeWork', 'WebApplication'}
MAX_IMAGES = 40


def text(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def attr(tag, name):
    m = re.search(r'\s' + name + r'\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', tag)
    return H.unescape(m.group(1) if m.group(1) is not None else m.group(2)) if m else None


def bad_alt(a):
    a = (a or '').strip()
    return (not a or re.search(r'\.(jpe?g|png|webp|gif)$|^[0-9a-f-]{16,}$|^(image|img|photo|picture)\s*\d*$', a, re.I)
            or (not re.search(r'\s', a) and re.search(r'[-_\d]', a)))


def decorative(tag):
    src = attr(tag, 'src') or ''
    return (attr(tag, 'aria-hidden') == 'true' or attr(tag, 'role') in ('presentation', 'none')
            or src.endswith('.svg') or src.startswith('data:') or bool(DECORATIVE and re.search(DECORATIVE, src)))


def page_url(f):
    rel = os.path.relpath(f, DIST).replace(os.sep, '/')
    return SITE + '/' + (rel[:-len('index.html')] if rel.endswith('index.html') else rel)


def abs_url(src, base):
    if src.startswith('//'): return 'https:' + src
    if re.match(r'https?://', src): return src
    if src.startswith('/'): return SITE + src
    return base.rsplit('/', 1)[0] + '/' + src


def local_file(url):
    if not url.startswith(SITE + '/'): return None
    p = os.path.join(DIST, url[len(SITE) + 1:].split('?')[0].split('#')[0])
    return p if os.path.isfile(p) else None


def image_size(path, cache={}):
    if path not in cache:
        try:
            from PIL import Image
            with Image.open(path) as im: cache[path] = im.size
        except Exception:
            cache[path] = None
    return cache[path]


def content_region(page):
    """(start, end) of the page body that holds content images: <main> when there is one, else <body> minus header/footer."""
    m = re.search(r'<main\b[^>]*>', page)
    if m:
        e = page.find('</main>', m.end())
        return m.end(), (e if e > 0 else len(page))
    b = re.search(r'<body\b[^>]*>', page)
    s = b.end() if b else 0
    h = re.search(r'</header>', page[s:])
    if h: s += h.end()
    f = page.rfind('<footer')
    return s, (f if f > s else len(page))


def norm_title(t):
    t = H.unescape(t or '').split(' | ')[0].lower().replace('&', 'and')
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def load_products():
    try:
        items = json.load(open(os.path.join(ROOT, 'products.json'), encoding='utf-8'))
    except FileNotFoundError:
        return {}, {}, {}
    by_url, by_name, by_slug = {}, {}, {}
    for p in items:
        if not p.get('url'): continue
        slug = p['url'].rstrip('/').rsplit('/', 1)[-1]
        by_url[p['url'].rstrip('/')] = by_slug[slug] = p
        by_name[norm_title(p['title'])] = p
    return by_url, by_name, by_slug


PRODUCTS_BY_URL, PRODUCTS_BY_NAME, PRODUCTS_BY_SLUG = load_products()


def load_isbns():
    """book-isbns.csv: ISBN-13, ASIN and edition facts for Kevin's 88 books, read from Amazon.com on Oct 25, 2026.
    All are KDP paperbacks with free 979-8 ISBNs (no ISBN-10); some older books also have a Kindle edition."""
    import csv
    try:
        rows = list(csv.DictReader(open(os.path.join(ROOT, 'book-isbns.csv'), encoding='utf-8')))
    except FileNotFoundError:
        return {}
    keys = {}
    for r in rows:
        for k in (r['amazon_short_link'], r['amazon_url'], r['asin'], r['kindle_asin'], 'fab:' + r['slug'], 'title:' + norm_title(r['title'])):
            if k: keys[k.rstrip('/')] = r
    return keys


ISBNS = load_isbns()


def isbn_for(node, p):
    """Match a Book node to its book-isbns.csv row: Amazon link or ASIN first, then FirstArtBooks URL, then title."""
    if not ISBNS: return None
    urls = [node.get('url'), (node.get('offers') or {}).get('url') if isinstance(node.get('offers'), dict) else None]
    urls += node.get('sameAs') if isinstance(node.get('sameAs'), list) else [node.get('sameAs')]
    if p: urls += [p.get('amazon'), p.get('url')]
    for u in urls:
        if not isinstance(u, str): continue
        u = u.split('?')[0].rstrip('/')
        if u in ISBNS: return ISBNS[u]
        m = re.search(r'/dp/([A-Z0-9]{10})', u) or re.search(r'firstartbooks\.com/product/([^/]+)', u)
        if m and (m.group(1) in ISBNS or 'fab:' + m.group(1) in ISBNS): return ISBNS.get(m.group(1)) or ISBNS['fab:' + m.group(1)]
    for name in (node.get('name'), p and p.get('title')):
        r = ISBNS.get('title:' + norm_title(name)) if name else None
        if r: return r
    return None


def isbn_facts(n, r):
    """Add ISBN, ASIN and one workExample per edition. Returns True if anything was added."""
    if n.get('isbn'): return False
    paperback = 'https://www.amazon.com/dp/' + r['asin']
    asin = lambda a: {'@type': 'PropertyValue', 'propertyID': 'ASIN', 'value': a}
    n['isbn'] = r['isbn13']
    n.setdefault('gtin13', r['isbn13'])
    n.setdefault('numberOfPages', int(r['pages']))
    n.setdefault('datePublished', r['publication_date'])
    n.setdefault('identifier', asin(r['asin']))
    same = n.get('sameAs')
    same = [same] if isinstance(same, str) else list(same or [])
    if paperback not in same: n['sameAs'] = same + [paperback]
    editions = [{'@type': 'Book', 'name': r['title'], 'bookFormat': 'https://schema.org/Paperback', 'isbn': r['isbn13'],
                 'numberOfPages': int(r['pages']), 'datePublished': r['publication_date'], 'inLanguage': 'en',
                 'url': paperback, 'identifier': asin(r['asin'])}]
    if r['kindle_asin']:
        editions.append({'@type': 'Book', 'name': r['title'], 'bookFormat': 'https://schema.org/EBook', 'inLanguage': 'en',
                         'url': 'https://www.amazon.com/dp/' + r['kindle_asin'], 'identifier': asin(r['kindle_asin'])})
    n.setdefault('workExample', editions)
    return True


MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def isbn_line(r):
    y, m, d = (int(x) for x in r['publication_date'].split('-'))
    fmt = 'Paperback and Kindle' if r['kindle_asin'] else 'Paperback'
    return f"{fmt} · {r['pages']} pages · Published {MONTHS[m - 1]} {d}, {y} · ISBN-13 {r['isbn13_hyphenated']} · ASIN {r['asin']}"


def product_for(node):
    for u in [node.get('url')] + (node.get('sameAs') if isinstance(node.get('sameAs'), list) else [node.get('sameAs')]):
        if isinstance(u, str) and u.rstrip('/') in PRODUCTS_BY_URL: return PRODUCTS_BY_URL[u.rstrip('/')]
    return PRODUCTS_BY_NAME.get(norm_title(node.get('name')))


def cover_alt(src):
    name = src.rsplit('/', 1)[-1]
    p = PRODUCTS_BY_SLUG.get(re.sub(r'\.[a-z]+$', '', name)) or PRODUCTS_BY_SLUG.get(re.sub(r'-(sm|lg|md|cover)\.[a-z]+$', '', name))
    return f"Cover of {H.unescape(p['title']).split(' | ')[0].strip()} by Kevin Coulston" if p else None


def context_alt(region, pos, h1):
    """Alt from the card around the image: the enclosing link, figure, list item or article, else the page heading."""
    for tag in ('a', 'figure', 'li', 'article'):
        o = region.rfind('<' + tag + ' ', 0, pos)
        o2 = region.rfind('<' + tag + '>', 0, pos)
        o = max(o, o2)
        if o < 0 or region.find('</' + tag + '>', o, pos) >= 0: continue
        c = region.find('</' + tag + '>', pos)
        if c < 0: continue
        t = text(re.sub(r'<img\b[^>]*>', ' ', region[o:c]))
        t = re.sub(r'\s*(→|›|»)\s*$', '', t)
        if 3 <= len(t):
            t = t if len(t) <= 110 else t[:107].rsplit(' ', 1)[0] + '…'
            return f'{t}: illustration by Kevin Coulston'
    return f'{h1}: illustration by Kevin Coulston' if h1 else 'Illustration by Kevin Coulston'


def ld_blocks(page):
    return list(re.finditer(r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S))


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o, list):
        for v in o: yield from walk(v)


def types(node):
    t = node.get('@type')
    return set(t if isinstance(t, list) else [t])


def is_kevin(p):
    return isinstance(p, dict) and (p.get('@id') == KEVIN_ID or p.get('name') == 'Kevin Coulston')


def enrich_node(n, primary, page, primary_is_node):
    """Fill gaps in an existing node. Only adds missing facts; never overwrites what the generator wrote."""
    t = types(n)
    changed = False

    def put(k, v):
        nonlocal changed
        if v is not None and n.get(k) in (None, '', []):
            n[k] = v; changed = True

    # Tie every mention of Kevin to the one Person node (kevincoulston.com), keeping what was written.
    for k in ('author', 'creator', 'illustrator', 'founder'):
        v = n.get(k)
        if is_kevin(v) and v.get('@id') != KEVIN_ID and not v.get('@id'):
            v['@id'] = KEVIN_ID; changed = True
    if 'Book' in t and str(n.get('url', '')).startswith('https://www.amazon.com/dp/'):
        return changed  # an edition added by isbn_facts(): already complete
    if 'Book' in t:
        put('author', {'@id': KEVIN_ID})
        put('illustrator', {'@id': KEVIN_ID})
        put('publisher', {'@id': FAB_ID})
        put('inLanguage', 'en')
        put('bookFormat', 'https://schema.org/Paperback')
        if isinstance(n.get('image'), str) and n['image'].startswith('/'): n['image'] = SITE + n['image']; changed = True
        p = product_for(n)
        if p:
            put('image', p.get('image'))
            if p.get('amazon'):
                same = n.get('sameAs')
                same = [same] if isinstance(same, str) else list(same or [])
                if p['amazon'] not in same: n['sameAs'] = same + [p['amazon']]; changed = True
                # Where to buy. No price: Amazon sets it and it changes (same rule as firstartbooks.com).
                put('offers', {'@type': 'Offer', 'url': p['amazon'], 'availability': 'https://schema.org/InStock',
                               'seller': {'@type': 'Organization', 'name': 'Amazon'}})
            if p['url'].rstrip('/') != (n.get('url') or '').rstrip('/'):
                same = n.get('sameAs') if isinstance(n.get('sameAs'), list) else ([n['sameAs']] if n.get('sameAs') else [])
                if p['url'] not in same: n['sameAs'] = same + [p['url']]; changed = True
        r = isbn_for(n, p)
        if r and isbn_facts(n, r): changed = True
    if t & WORK_TYPES and primary:
        put('image', primary)
    if t & {'Article', 'BlogPosting', 'HowTo', 'CreativeWork'}:
        put('author', {'@id': KEVIN_ID})
        put('inLanguage', 'en')
    if t & {'Article', 'BlogPosting'}:
        put('publisher', {'@id': SITE + '/#organization'} if SITE + '/#organization' in page else {'@id': FAB_ID})
    if t & PAGE_TYPES and primary and not t & {'FAQPage'}:
        put('primaryImageOfPage', {'@id': primary + '#image'} if primary_is_node else primary)
    return changed



def jdump(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def howto_from_page(region, h1, url, primary):
    """HowTo for a 'How to draw …' page whose steps are a visible numbered list on the page."""
    if not re.match(r'how to draw', h1, re.I): return None
    best = None
    for m in re.finditer(r'<ol\b[^>]*>(.*?)</ol>', region, re.S):
        items = [text(li) for li in re.findall(r'<li\b[^>]*>(.*?)</li>', m.group(1), re.S)]
        items = [i for i in items if len(i) > 8]
        if len(items) >= 3 and (best is None or len(items) > len(best)): best = items
    if not best: return None
    node = {'@type': 'HowTo', '@id': url + '#howto', 'name': h1, 'url': url, 'author': {'@id': KEVIN_ID}, 'inLanguage': 'en',
            'tool': [{'@type': 'HowToTool', 'name': 'Pencil'}, {'@type': 'HowToTool', 'name': 'Paper'}],
            'step': [{'@type': 'HowToStep', 'position': i + 1, 'name': s if len(s) <= 80 else s[:77].rsplit(' ', 1)[0] + '…', 'text': s} for i, s in enumerate(best)]}
    if primary: node['image'] = primary
    return node


INDEXNOW_KEY = '196f6339d9e200ab10aef9905222f351'


def process():
    files = sorted(f for f in glob.glob(os.path.join(DIST, '**', '*.html'), recursive=True))
    pages = {}
    for f in files:
        s = open(f, encoding='utf-8').read()
        if re.search(r'http-equiv="refresh"', s, re.I) or os.path.basename(f) == '404.html': continue
        pages[f] = s

    # Pass 1: the best alt each image already has somewhere on the site.
    known = defaultdict(Counter)
    for s in pages.values():
        for tag in re.findall(r'<img\b[^>]*>', s):
            a, src = attr(tag, 'alt'), attr(tag, 'src')
            if src and not bad_alt(a): known[src][a.strip()] += 1

    def best_known(src):
        if src in known: return known[src].most_common(1)[0][0]
        base = re.sub(r'-(sm|lg|md)(\.[a-z]+)$', r'\2', src)
        for k, c in known.items():
            if re.sub(r'-(sm|lg|md)(\.[a-z]+)$', r'\2', k) == base: return c.most_common(1)[0][0]
        return None

    stats = Counter()
    sitemap_images = {}
    for f, page in pages.items():
        canon = re.search(r'<link\b[^>]*rel="canonical"[^>]*>', page)
        url = attr(canon.group(0), 'href') if canon else page_url(f)
        if not url.startswith(SITE): url = page_url(f)
        h1m = re.search(r'<h1\b[^>]*>(.*?)</h1>', page, re.S)
        h1 = text(h1m.group(1)) if h1m else ''
        s0, e0 = content_region(page)
        region = page[s0:e0]

        # Alt text: fill empty, missing or filename-style alts on content images; decorative art keeps alt="".
        def fix(m):
            tag = m.group(0)
            a, src = attr(tag, 'alt'), attr(tag, 'src') or ''
            if decorative(tag) or not src or not bad_alt(a): return tag
            name = os.path.basename(src.split('?')[0])
            v = ALT_OVERRIDES.get(name) or best_known(src) or cover_alt(src) or context_alt(region, m.start(), h1)
            stats['alts'] += 1
            v = H.escape(v, quote=True)
            return re.sub(r'\salt\s*=\s*(?:"[^"]*"|\'[^\']*\')', f' alt="{v}"', tag) if a is not None else re.sub(r'^<img\b', f'<img alt="{v}"', tag)

        region = re.sub(r'<img\b[^>]*>', fix, region)
        page = page[:s0] + region + page[e0:]

        # Content images on this page, in order.
        imgs, seen = [], set()
        for tag in re.findall(r'<img\b[^>]*>', region):
            src = attr(tag, 'src') or ''
            if decorative(tag) or not src: continue
            u = abs_url(src, url)
            lf = local_file(u)
            if not lf or u in seen or (SKIP_IMAGES and re.search(SKIP_IMAGES, u)): continue
            w, h = attr(tag, 'width'), attr(tag, 'height')
            size = image_size(lf)
            if size: w, h = size
            if w and int(w) < 100: continue
            seen.add(u)
            imgs.append({'url': u, 'alt': (attr(tag, 'alt') or '').strip(), 'w': int(w) if w else None, 'h': int(h) if h else None})
        page = re.sub(r'<meta\b[^>]*data-seo-enrich[^>]*>', '', page)
        og = re.search(r'<meta\b[^>]*property="og:image"[^>]*>', page)
        og_url = attr(og.group(0), 'content') if og else None
        primary = imgs[0]['url'] if imgs else (og_url if og_url and local_file(og_url) else None)
        sitemap_images[url] = [i['url'] for i in imgs]

        # Existing JSON-LD: fill gaps in place.
        page = re.sub(r'<script\b[^>]*data-seo-enrich[^>]*>.*?</script>', '', page, flags=re.S)
        has = set()
        page_isbn, page_books = None, {}
        for m in reversed(ld_blocks(page)):
            try: data = json.loads(m.group(1))
            except ValueError: continue
            changed = False
            for n in walk(data):
                if '@type' in n:
                    has |= types(n)
                    changed |= enrich_node(n, primary, page, bool(imgs))
                    if 'Book' in types(n) and not str(n.get('url', '')).startswith('https://www.amazon.com/dp/'):
                        r = isbn_for(n, product_for(n))
                        if r: page_books[r['asin']] = r
                        if r and (n.get('url') or '').rstrip('/') == url.rstrip('/'): page_isbn = r
            if changed:
                page = page[:m.start(1)] + jdump(data) + page[m.end(1):]
                stats['nodes'] += 1

        # A /books/<slug>/ page about one book whose Book node points elsewhere (e.g. at firstartbooks.com).
        if not page_isbn and len(page_books) == 1 and re.search(r'/books/[^/]+/?$', url): page_isbn = next(iter(page_books.values()))

        # The book's own page: show its edition facts (ISBN-13, ASIN) where the site setting says.
        page = re.sub(r'<(\w+)\b[^>]*data-seo-isbn[^>]*>.*?</\1>', '', page, flags=re.S)
        if ISBN_LINE and page_isbn:
            at = re.search(ISBN_LINE[0], page, re.S)
            if at:
                line = ISBN_LINE[1].format(H.escape(isbn_line(page_isbn))).replace('>', ' data-seo-isbn>', 1)
                page = page[:at.end()] + line + page[at.end():]
                stats['isbn'] += 1

        # New block: Kevin, the publisher, ImageObjects for the page's artwork, and a HowTo where the page shows steps.
        graph = [KEVIN]
        if 'Book' in has or 'Article' in has or 'BlogPosting' in has: graph.append(FAB)
        for i, im in enumerate(imgs[:MAX_IMAGES]):
            o = {'@type': 'ImageObject', '@id': im['url'] + '#image', 'contentUrl': im['url'], 'url': im['url']}
            if im['alt']: o['name'] = o['caption'] = im['alt']
            if im['w'] and im['h']: o['width'], o['height'] = im['w'], im['h']
            ext = os.path.splitext(im['url'])[1].lower()
            if ext in IMG_EXT: o['encodingFormat'] = IMG_EXT[ext]
            o.update(CREDIT)
            if i == 0: o['representativeOfPage'] = True
            graph.append(o)
            stats['images'] += 1
        if HOWTO and 'HowTo' not in has:
            ht = howto_from_page(region, h1, url, primary)
            if ht: graph.append(ht); stats['howto'] += 1
        if EXTRA: graph += [g for g in EXTRA(url, page, region, h1, has, primary) or [] if g]
        block = '<script type="application/ld+json" data-seo-enrich>' + jdump({'@context': 'https://schema.org', '@graph': graph}) + '</script>'
        if not og and primary:
            block = f'<meta property="og:image" content="{H.escape(primary)}" data-seo-enrich>' + block
            stats['og'] += 1
        page = page.replace('</head>', block + '</head>', 1)
        open(f, 'w', encoding='utf-8').write(page)

    # Image sitemap: every page's content images, merged with any image entries already there.
    sm = os.path.join(DIST, 'sitemap.xml')
    xml = open(sm, encoding='utf-8').read()
    if 'xmlns:image=' not in xml:
        xml = re.sub(r'<urlset\b', '<urlset xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"', xml, count=1)

    def add(m):
        block = m.group(0)
        loc = H.unescape(re.search(r'<loc>(.*?)</loc>', block, re.S).group(1).strip())
        have = [H.unescape(x) for x in re.findall(r'<image:loc>(.*?)</image:loc>', block)]
        want = have + [u for u in sitemap_images.get(loc, []) if u not in have]
        body = re.sub(r'\s*<image:image>.*?</image:image>', '', block, flags=re.S)
        imgs = ''.join(f'<image:image><image:loc>{H.escape(u)}</image:loc></image:image>' for u in want[:1000])
        stats['sitemap_images'] += len(want)
        return body.replace('</url>', imgs + '</url>')

    xml = re.sub(r'<url>.*?</url>', add, xml, flags=re.S)
    open(sm, 'w', encoding='utf-8').write(xml)

    # IndexNow key file, so indexnow.mjs can tell Bing which pages changed after a deploy.
    open(os.path.join(DIST, INDEXNOW_KEY + '.txt'), 'w', encoding='utf-8').write(INDEXNOW_KEY)
    print(f"seo_enrich: {len(pages)} pages, {stats['alts']} alts filled, {stats['nodes']} JSON-LD blocks enriched, "
          f"{stats['images']} ImageObjects, {stats['howto']} HowTo, {stats['og']} og:image, {stats['sitemap_images']} sitemap images, {stats['isbn']} ISBN lines")


if __name__ == '__main__':
    process()
