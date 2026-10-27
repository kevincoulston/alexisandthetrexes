#!/usr/bin/env python3
"""Builds alexisandthetrexes.com into dist/ (Oct 26, 2026).

Run: python3 build.py && python3 seo_enrich.py
Inputs: site_data.py (copy and book facts), src/style.css, src/site.js, art/ (Kevin's artwork), perf_assets/fonts/.
Needs Pillow. dist/ is rebuilt from scratch each time.

Page speed is built in (same rules as cg_perf.py / christmas_perf.py on the sister sites):
- Chewy and Lexend are self-hosted and preloaded, with Arial fallback faces scaled to their widths.
- The CSS is inlined; there is no other render-blocking file.
- Every image gets small WebP copies in srcset with sizes for its slot, plus width/height to stop layout shift.
- GA4 (when GA_ID is set) loads on the first scroll/tap/key or 4 s after load.
"""
import html as H
import json
import re
import shutil
from pathlib import Path

from PIL import Image

from site_data import AUTHOR_STORE, BOOKS, DINO_BOOKS, FREE_PAGES, GA_ID, GANG, SERIES_URL, SITE

P = Path(__file__).parent
ART = P / "art"
D = P / "dist"
KEVIN_ID = "https://kevincoulston.com/#person"
WIDTHS = (160, 240, 320, 480, 640, 800, 960, 1280, 1600)

LATIN = ('unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,'
         'U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}')
ARIAL = 'src:local("Arial"),local("ArialMT"),local("Liberation Sans"),local("Roboto"),local("Helvetica");'
FONT_FACE = ('@font-face{font-family:"Chewy";font-style:normal;font-weight:400;font-display:swap;'
             'src:url(/assets/fonts/chewy-latin.woff2) format("woff2");' + LATIN +
             '@font-face{font-family:"Lexend";font-style:normal;font-weight:100 900;font-display:swap;'
             'src:url(/assets/fonts/lexend-latin.woff2) format("woff2");' + LATIN +
             # Arial scaled to each font's letter width and line metrics (measured for cg_perf.py, Oct 26, 2026).
             '@font-face{font-family:"Chewy Fallback";' + ARIAL +
             'size-adjust:89.2%;ascent-override:109.9%;descent-override:34%;line-gap-override:2.7%}'
             '@font-face{font-family:"Lexend Fallback";' + ARIAL +
             'size-adjust:109.4%;ascent-override:91.4%;descent-override:22.9%;line-gap-override:0%}')
PRELOAD = ''.join(f'<link rel="preload" href="/assets/fonts/{n}" as="font" type="font/woff2" crossorigin>'
                  for n in ("chewy-latin.woff2", "lexend-latin.woff2"))
GA = ("<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());"
      "gtag('config','{id}');(function(){{var done=0,ev=['scroll','pointerdown','keydown','touchstart','mousemove'];"
      "function load(){{if(done)return;done=1;ev.forEach(function(t){{removeEventListener(t,load)}});"
      "var s=document.createElement('script');s.async=!0;s.src='https://www.googletagmanager.com/gtag/js?id={id}';document.head.appendChild(s)}}"
      "ev.forEach(function(t){{addEventListener(t,load,{{passive:!0}})}});addEventListener('load',function(){{setTimeout(load,4000)}})}})();</script>")
STAR = '<path d="M12 1l3.3 7 7.7.9-5.7 5.2 1.6 7.6L12 17.9l-6.9 3.8 1.6-7.6L1 8.9l7.7-.9z"/>'
STARS = ('<svg class="ar-stars" width="{w}" height="{h}" viewBox="0 0 120 24" role="img" aria-label="5 out of 5 stars">'
         '<g fill="{fill}" stroke="#1e2a44" stroke-width="1.5">' +
         ''.join(f'<g transform="translate({i * 24} 0)">{STAR}</g>' for i in range(5)) + '</g></svg>')

e = H.escape
_sizes = {}


def amazon(b):
    return "https://www.amazon.com/dp/" + b["asin"]


def variants(name):
    """[(url, width)] for art/<name>: a full-size WebP plus smaller copies, written to dist/assets/img/."""
    if name in _sizes:
        return _sizes[name]
    src = ART / name
    out_dir = D / "assets" / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    with Image.open(src) as im:
        w, h = im.size
        frame = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        full = out_dir / f"{stem}.webp"
        frame.save(full, "WEBP", quality=82, method=6)
        vs = [(f"/assets/img/{stem}.webp", w)]
        for width in WIDTHS:
            if width <= w * 0.85:
                small = frame.resize((width, round(h * width / w)), Image.LANCZOS)
                small.save(out_dir / f"{stem}-{width}.webp", "WEBP", quality=76, method=6)
                vs.append((f"/assets/img/{stem}-{width}.webp", width))
    _sizes[name] = (vs, w, h)
    return _sizes[name]


def img(name, alt, sizes, cls="", lazy=True, high=False, extra=""):
    vs, w, h = variants(name)
    srcset = ", ".join(f"{u} {wd}w" for u, wd in sorted(vs, key=lambda x: x[1]))
    src = min((v for v in vs if v[1] >= 480), key=lambda v: v[1], default=vs[0])[0]
    a = [f'src="{src}"', f'srcset="{srcset}"', f'sizes="{("auto, " if lazy else "") + sizes}"', f'width="{w}"', f'height="{h}"',
         f'alt="{e(alt)}"']
    if cls: a.append(f'class="{cls}"')
    a.append('loading="lazy" decoding="async"' if lazy else 'decoding="async"')
    if high: a.append('fetchpriority="high"')
    if extra: a.append(extra)
    return "<img " + " ".join(a) + ">"


def small_url(name, width):
    vs, _, _ = variants(name)
    return min(vs, key=lambda v: abs(v[1] - width))[0]


def stars(w=120, fill="#1e2a44"):
    return STARS.format(w=w, h=round(w / 5), fill=fill)


NAV = [("/books/", "The Books"), ("/meet-the-gang/", "Meet the Gang"), ("/free-dinosaur-pages/", "Free Pages"), ("/about/", "About Kevin")]


def header(path):
    links = "".join(f'<a href="{u}"{" aria-current=page" if path.startswith(u) else ""}>{t}</a>' for u, t in NAV)
    logo = img("logo.webp", "Alexis and the T-Rexes", "(max-width:900px) 122px, 160px", lazy=False)
    return (f'<a class="ar-skip" href="#main">Skip to the page</a><header class="ar-head"><div class="ar-in">'
            f'<a class="ar-logo" href="/" aria-label="Alexis and the T-Rexes home">{logo}</a>'
            f'<nav class="ar-nav" aria-label="Main">{links}<a class="ar-btn" href="/books/">Get the books</a></nav>'
            f'<details class="ar-menu"><summary>Menu</summary><nav aria-label="Main">{links}<a href="/books/">Get the books</a></nav></details>'
            f'</div></header>')


def footer():
    logo = img("logo.webp", "Alexis and the T-Rexes", "200px")
    links = "".join(f'<a href="{u}">{t}</a>' for u, t in [("/", "Home")] + NAV)
    return (f'<footer class="ar-foot"><div class="ar-in">{logo}<nav aria-label="Footer">{links}</nav>'
            f'<div class="ar-more"><span style="font-weight:700;color:#fff">More from Kevin</span>'
            f'<a href="https://firstartbooks.com/">FirstArtBooks.com</a><a href="https://kevincoulston.com/">KevinCoulston.com</a>'
            f'<a href="{AUTHOR_STORE}">Kevin on Amazon</a></div>'
            f'<p>© 2026 Kevin Coulston. Alexis and the T-Rexes books are paperbacks sold on Amazon.</p></div></footer>')


def page(path, title, desc, body, ld, og="og-image.jpg", js=False, preload=""):
    url = SITE + path
    css = FONT_FACE + (P / "src" / "style.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s*\n\s*", "", css)
    graph = {"@context": "https://schema.org", "@graph": ld}
    ga = GA.format(id=GA_ID) if GA_ID else ""
    script = f'<script>{(P / "src" / "site.js").read_text()}</script>' if js else ""
    og_url = SITE + "/assets/" + og
    return f"""<!doctype html>
<html lang="en" data-fonts="self">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{PRELOAD}{preload}
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#55abeb">
<link rel="icon" href="/favicon.png" type="image/png" sizes="32x32">
<link rel="icon" href="/favicon-48.png" type="image/png" sizes="48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Alexis and the T-Rexes">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_url}">
<meta name="twitter:card" content="summary_large_image">
<style>{css}</style>
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script>{ga}
</head>
<body>
{header(path)}
<main id="main">
{body}
</main>
{footer()}
{script}
</body>
</html>
"""


def book_node(b, url=None):
    return {"@type": "Book", "@id": SITE + f"/books/{b['slug']}/#book", "name": b["full"], "url": url or SITE + f"/books/{b['slug']}/",
            "image": SITE + f"/assets/img/{Path(b['cover']).stem}.webp", "description": b["blurb"],
            "author": {"@id": KEVIN_ID}, "illustrator": {"@id": KEVIN_ID}, "publisher": {"@id": KEVIN_ID},
            "isPartOf": {"@id": SITE + "/#series"}, "position": b["num"], "typicalAgeRange": "3-8", "inLanguage": "en",
            "bookFormat": "https://schema.org/Paperback", "numberOfPages": b["pages"], "datePublished": b["date"],
            "isbn": b["isbn13"], "sameAs": [amazon(b)],
            "aggregateRating": {"@type": "AggregateRating", "ratingValue": b["stars"], "ratingCount": b["ratings"], "bestRating": "5"},
            "offers": {"@type": "Offer", "url": amazon(b), "availability": "https://schema.org/InStock",
                       "seller": {"@type": "Organization", "name": "Amazon"}}}


def site_nodes():
    return [{"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "Alexis and the T-Rexes", "inLanguage": "en",
             "publisher": {"@id": KEVIN_ID}},
            {"@type": "BookSeries", "@id": SITE + "/#series", "name": "Alexis and the T-Rexes", "url": SITE + "/",
             "author": {"@id": KEVIN_ID}, "illustrator": {"@id": KEVIN_ID}, "sameAs": [SERIES_URL], "inLanguage": "en",
             "typicalAgeRange": "3-8", "hasPart": [{"@id": SITE + f"/books/{b['slug']}/#book"} for b in BOOKS]}]


def webpage(path, name, kind="WebPage", crumbs=None):
    n = {"@type": kind, "@id": SITE + path + "#webpage", "url": SITE + path, "name": name, "isPartOf": {"@id": SITE + "/#website"}, "inLanguage": "en"}
    if crumbs:
        n["breadcrumb"] = {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": t, "item": SITE + u} for i, (u, t) in enumerate(crumbs)]}
    return n


def crumbs_html(items):
    return '<nav class="ar-crumbs" aria-label="Breadcrumb">' + " › ".join(
        f'<a href="{u}">{e(t)}</a>' if i < len(items) - 1 else f'<span aria-current="page">{e(t)}</span>' for i, (u, t) in enumerate(items)) + "</nav>"


def book_card(b, h="h3"):
    return (f'<article class="ar-card ar-book">'
            f'<a href="/books/{b["slug"]}/" tabindex="-1" aria-hidden="true">{img(b["cover"], b["cover_alt"], "(max-width:900px) 92vw, 380px", "ar-cover")}</a>'
            f'<p class="ar-kick">Book {b["num"]}</p><{h}><a href="/books/{b["slug"]}/">{e(b["title"])}</a></{h}><p>{e(b["blurb"])}</p>'
            f'<div class="ar-chips"><span class="ar-chip">{e(b["theme"])}</span><span class="ar-chip">{b["pages"]} pages</span>'
            f'<span class="ar-chip">{b["stars"]} stars ({b["ratings"]})</span></div>'
            f'<div class="ar-btns"><a class="ar-btn" href="{amazon(b)}">See it on Amazon</a><a href="/books/{b["slug"]}/" style="font-weight:600">More about it</a></div></article>')


def books_section(h2="Three books, one very silly dino family", intro=True):
    cards = "".join(book_card(b) for b in BOOKS)
    lead = ('<p class="ar-lede">Each story is a 24 to 30 page square paperback for ages 3 to 8, made for reading out loud and laughing together.</p>' if intro else "")
    return (f'<section class="ar-sec" id="books"><div class="ar-in ar-stack" style="gap:40px"><div class="ar-center"><p class="ar-kick">The series</p>'
            f'<h2>{h2}</h2>{lead}</div><div class="ar-grid3">{cards}</div>'
            f'<div class="ar-center"><a class="ar-btn alt" href="{SERIES_URL}">See the whole series on Amazon</a></div></div></section>')


def gang_section():
    cards = ""
    for g in GANG:
        cls = "ar-round" if g.get("round") else ""
        cards += (f'<div class="ar-card ar-pal"><div class="ar-pic">{img(g["img"], g["alt"], "(max-width:900px) 40vw, 220px", cls)}</div>'
                  f'<h3>{g["name"]}</h3><p>{e(g["short"])}</p></div>')
    return (f'<section class="ar-sec ar-skyband" id="gang"><div class="ar-in ar-stack" style="gap:36px"><div class="ar-center">'
            f'<h2>Meet the gang</h2><p class="ar-lede" style="font-weight:600">They wear diapers, they giggle a lot, and they are still learning how everything works.</p></div>'
            f'<div class="ar-grid4">{cards}</div><div class="ar-center"><a class="ar-btn alt" href="/meet-the-gang/">Meet everyone</a></div></div></section>')


def count_section():
    dinos = [("snap.webp", 160), ("daisy.webp", 160)]
    data = []
    for n, w in dinos:
        vs, W, Hh = variants(n)
        data.append({"src": small_url(n, w), "w": w, "h": round(Hh * w / W)})
    start = [(6, 44, 0), (44, 46, 1), (82, 44, 0), (20, 14, 1), (60, 12, 0)]
    first = "".join(f'<img class="ar-d" src="{data[k]["src"]}" width="{data[k]["w"]}" height="{data[k]["h"]}" alt="" aria-hidden="true" '
                    f'style="left:{x}%;bottom:{y}%" loading="lazy">' for x, y, k in start)
    nums = "".join(f'<button class="ar-num" type="button">{i}</button>' for i in range(1, 11))
    bg = img("hero-wide.webp", "", "(max-width:900px) 92vw, 600px", "ar-yard-bg", extra='aria-hidden="true"')
    return (f'<section class="ar-sec ar-green" id="play"><div class="ar-in ar-play" id="ar-count">'
            f'<div class="ar-stack"><p class="ar-kick">Play along</p><h2>Can you count the T-Rexes?</h2>'
            f'<p>Count the dinosaurs in the yard, then tap the matching number. A little game straight out of Count to Ten.</p>'
            f'<div class="ar-nums" role="group" aria-label="How many T-Rexes?">{nums}</div><p class="ar-say" aria-live="polite"></p></div>'
            f'<div class="ar-card ar-yard" role="img" aria-label="A yard with five baby T-Rexes in it. How many can you count?" '
            f'data-dinos="{e(json.dumps(data))}">{bg}{first}</div></div></section>')


def free_cards(h="h3"):
    out = ""
    for f in FREE_PAGES:
        out += (f'<article class="ar-card ar-page">{img(f["img"], "Free " + f["title"].lower() + " activity page from " + f["book"], "(max-width:900px) 92vw, 380px")}'
                f'<{h}>{e(f["title"])}</{h}><p>{e(f["kind"])} from {e(f["book"])}.</p>'
                f'<div class="ar-btns"><a class="ar-btn sun" href="{f["url"]}">Get the free page</a><a href="{f["book_url"]}" style="font-weight:600">See the book</a></div></article>')
    return out


def free_section():
    return (f'<section class="ar-sec" id="printables"><div class="ar-in ar-stack" style="gap:36px"><div class="ar-center"><p class="ar-kick">Free printables</p>'
            f'<h2>Free dinosaur pages to print</h2><p class="ar-lede">Snap and Daisy\'s favorite thing after story time? Drawing more dinosaurs. '
            f'These free pages come from Kevin\'s dinosaur drawing and tracing books.</p></div><div class="ar-grid3">{free_cards()}</div>'
            f'<div class="ar-center"><a class="ar-btn alt" href="/free-dinosaur-pages/">More about the free pages</a></div></div></section>')


def draw_section():
    pic = img("room.webp", "Alexis showing off a T-Rex drawing on an easel in her bedroom while Snap and Daisy watch", "(max-width:900px) 92vw, 700px")
    return (f'<section class="ar-sec"><div class="ar-in ar-split"><div class="ar-card">{pic}</div><div class="ar-stack">'
            f'<p class="ar-kick">Little artists welcome</p><h2 style="font-size:clamp(32px,3.6vw,48px)">Love drawing dinosaurs too?</h2>'
            f'<p>Kevin also makes step-by-step How to Draw books for kids. You\'ll find them, plus free drawing lessons, at FirstArtBooks.com.</p>'
            f'<div><a class="ar-btn leaf" href="https://firstartbooks.com/">Visit FirstArtBooks.com</a></div></div></div></section>')


def tips_section():
    tips = "".join(f'<div class="ar-tip"><h3>{t}</h3><p>{e(x)}</p></div>' for t, x in [
        ("Count out loud", BOOKS[0]["tip"]), ("Make a gift", BOOKS[1]["tip"]), ("Play hide-and-seek", BOOKS[2]["tip"])])
    return (f'<section class="ar-sec ar-white" id="parents"><div class="ar-in ar-stack" style="gap:30px"><div class="ar-stack" style="gap:8px">'
            f'<p class="ar-kick">For parents and teachers</p><h2 style="font-size:clamp(32px,3.8vw,50px)">Made for read-aloud time</h2></div>'
            f'<div class="ar-grid3">{tips}</div><div class="ar-chips"><span class="ar-chip">Ages 3 to 8</span><span class="ar-chip">Pre-K to grade 3</span>'
            f'<span class="ar-chip">8.5 x 8.5 inch paperbacks</span><span class="ar-chip">24 to 30 pages each</span></div></div></section>')


def kevin_section(h="h2"):
    pic = img("kevin.webp", "Kevin Coulston, author and illustrator of Alexis and the T-Rexes", "(max-width:760px) 130px, 220px")
    return (f'<section class="ar-sec ar-purple" id="kevin"><div class="ar-in ar-kevin">{pic}<div class="ar-stack" style="max-width:70ch">'
            f'<{h} style="color:#fff">Meet the author and illustrator</{h}><p>Kevin Coulston is a cartoonist and children\'s book author and illustrator. '
            f'He wrote and drew all three Alexis and the T-Rexes books, and he has made more than 80 books for kids, including the How to Draw series from FirstArtBooks.</p>'
            f'<div class="ar-btns"><a class="ar-btn alt" href="/about/">About Kevin</a></div></div></div></section>')


def home():
    wide = variants("hero-wide.webp")
    phone = variants("hero-phone.webp")
    ss = lambda v: ", ".join(f"{u} {w}w" for u, w in sorted(v[0], key=lambda x: x[1]))
    bg = (f'<picture class="ar-hero-bg"><source media="(min-width:600px)" srcset="{ss(wide)}" sizes="100vw">'
          f'<img src="{small_url("hero-phone.webp", 640)}" srcset="{ss(phone)}" sizes="100vw" width="{phone[1]}" height="{phone[2]}" alt="" aria-hidden="true" '
          f'fetchpriority="high" decoding="async"></picture>')
    logo_sizes = "(max-width:1179px) min(520px, 82vw), 35vw"
    hero = (f'<section class="ar-hero"><div class="ar-hero-top">{img("logo.webp", "Alexis and the T-Rexes", logo_sizes, lazy=False)}</div>'
            f'<div class="ar-scene">{bg}<div class="ar-stage">{img("logo.webp", "", logo_sizes, "ar-hero-logo", lazy=False, extra="aria-hidden=\"true\"")}'
            f'<div class="ar-trio">{img("snap.webp", "Snap, the orange baby T-Rex, smiling with his arms out", "(max-width:599px) 32vw, (max-width:1179px) 22vw, 260px", "ar-c ar-c-snap", lazy=False)}'
            f'{img("alexis.webp", "Alexis, a five-year-old girl with long brown hair and a cupcake apron, arms open wide", "(max-width:599px) 60vw, (max-width:1179px) 40vw, 430px", "ar-c ar-c-alexis", lazy=False)}'
            f'{img("daisy.webp", "Daisy, the blue baby T-Rex with a red bow, giggling", "(max-width:599px) 32vw, (max-width:1179px) 22vw, 260px", "ar-c ar-c-daisy", lazy=False)}</div>'
            f'<div class="ar-badge">{stars(120)}<b>5.0 stars<br>on Amazon</b><small>all 3 books</small></div></div></div>'
            f'<div class="ar-hero-under"><div class="ar-card ar-hero-card"><p class="ar-kick">Picture books for ages 3 to 8</p>'
            f'<h1>A five-year-old, two baby <span class="ar-nw">T-Rexes</span>, and a whole lot of giggles</h1>'
            f'<p>Count to ten, throw a birthday party and play hide-and-seek with Alexis and her silly dinosaur friends, Snap and Daisy.</p>'
            f'<div class="ar-rating">{stars(90, "#f7941d")}5.0 on Amazon, all 3 books</div>'
            f'<div class="ar-btns"><a class="ar-btn" href="#books">View the books</a><a class="ar-btn alt" href="#play">Play along</a></div></div></div></section>')
    body = hero + books_section() + gang_section() + count_section() + free_section() + draw_section() + tips_section() + kevin_section()
    ld = site_nodes() + [webpage("/", "Alexis and the T-Rexes picture books")] + [book_node(b) for b in BOOKS]
    preload = (f'<link rel="preload" as="image" href="{small_url("hero-phone.webp", 640)}" imagesrcset="{ss(phone)}" imagesizes="100vw" media="(max-width:599px)">'
               f'<link rel="preload" as="image" imagesrcset="{ss(wide)}" imagesizes="100vw" media="(min-width:600px)">')
    return page("/", "Alexis and the T-Rexes | Dinosaur picture books for kids by Kevin Coulston",
                "Count to Ten, Birthday Surprise and Hide and Seek: three funny picture books about five-year-old Alexis and her baby T-Rexes, Snap and Daisy. Ages 3 to 8.",
                body, ld, js=True, preload=preload)


def books_index():
    head = (f'<section class="ar-pagehead"><div class="ar-in ar-stack">{crumbs_html([("/", "Home"), ("/books/", "The Books")])}'
            f'<h1>The Alexis and the T-Rexes books</h1><p class="ar-lede">Three picture books about Alexis and her baby T-Rexes, Snap and Daisy. '
            f'Read them in order, or start anywhere.</p></div></section>')
    ld = site_nodes() + [webpage("/books/", "The Alexis and the T-Rexes books", "CollectionPage", [("/", "Home"), ("/books/", "The Books")]),
                         {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": b["num"], "url": SITE + f"/books/{b['slug']}/", "name": b["full"]} for b in BOOKS]}]
    return page("/books/", "The Books | Alexis and the T-Rexes picture books",
                "All three Alexis and the T-Rexes picture books: Count to Ten, Birthday Surprise and Hide and Seek, for ages 3 to 8.",
                head + books_section("Pick a story", intro=False) + tips_section(), ld)


def book_page(b):
    others = [o for o in BOOKS if o is not b]
    learn = "".join(f"<li>{e(x)}</li>" for x in b["learn"])
    isbn10 = f'<dt>ISBN-10</dt><dd>{b["isbn10"]}</dd>' if b["isbn10"] else ""
    asin = f'<dt>ASIN</dt><dd>{b["asin"]}</dd>' if not b["isbn10"] else ""
    path = f"/books/{b['slug']}/"
    trail = [("/", "Home"), ("/books/", "The Books"), (path, b["title"])]
    body = (f'<div class="ar-in">{crumbs_html(trail)}<div class="ar-bookpage">'
            f'<div>{img(b["cover"], b["cover_alt"], "(max-width:820px) 92vw, 520px", "ar-cover", lazy=False, high=True)}</div>'
            f'<div class="ar-stack"><p class="ar-kick">Book {b["num"]} of 3</p><h1>{e(b["full"]).replace("T-Rexes", "<span class=\"ar-nw\">T-Rexes</span>")}</h1>'
            f'<div class="ar-rating">{stars(100, "#f7941d")}{b["stars"]} out of 5 on Amazon ({b["ratings"]} ratings)</div>'
            f'<p style="font-size:19px">{e(b["blurb"])}</p>'
            f'<div class="ar-btns"><a class="ar-btn" href="{amazon(b)}">Get it on Amazon</a><a class="ar-btn alt" href="{SERIES_URL}">See all 3 books</a></div>'
            f'<h2 style="font-size:30px;margin-top:10px">What kids get from it</h2><ul class="ar-list">{learn}</ul>'
            f'<h2 style="font-size:30px;margin-top:10px">Try this after reading</h2><p>{e(b["tip"])}</p>'
            f'<h2 style="font-size:30px;margin-top:10px">Book details</h2><dl class="ar-facts"><dt>Author and illustrator</dt><dd>Kevin Coulston</dd>'
            f'<dt>Format</dt><dd>Paperback, 8.5 x 8.5 inches</dd><dt>Pages</dt><dd>{b["pages"]}</dd><dt>Reading age</dt><dd>3 to 8 years</dd>'
            f'<dt>Published</dt><dd>{b["date_text"]}</dd><dt>ISBN-13</dt><dd>{b["isbn13_h"]}</dd>{isbn10}{asin}<dt>Series</dt><dd>Alexis and the T-Rexes, book {b["num"]}</dd></dl>'
            f'</div></div></div>'
            f'<section class="ar-sec ar-white"><div class="ar-in ar-stack" style="gap:30px"><h2>More Alexis and the T-Rexes</h2>'
            f'<div class="ar-grid3" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr))">{"".join(book_card(o) for o in others)}</div></div></section>'
            + free_section())
    ld = site_nodes() + [webpage(path, b["full"], "ItemPage", trail), book_node(b)]
    return page(path, f"{b['full']} | Picture book by Kevin Coulston",
                f"{b['blurb']} A {b['pages']}-page picture book for ages 3 to 8 by Kevin Coulston.", body, ld,
                preload=f'<link rel="preload" as="image" imagesrcset="{", ".join(f"{u} {w}w" for u, w in sorted(variants(b["cover"])[0], key=lambda x: x[1]))}" imagesizes="(max-width:820px) 92vw, 520px">')


def gang_page():
    rows = ""
    for g in GANG:
        cls = "ar-round" if g.get("round") else ""
        rows += (f'<div class="ar-gang-row"><div class="ar-gang-pic">{img(g["img"], g["alt"], "(max-width:760px) 80vw, 400px", cls)}</div>'
                 f'<div class="ar-stack"><h2>{g["name"]}</h2><p style="font-size:19px">{e(g["long"])}</p></div></div>')
    scenes = (img("backyard.webp", "Alexis, Snap and Daisy in the backyard by the sandbox, next to two cracked dinosaur eggs", "(max-width:760px) 92vw, 600px")
              + img("garden.webp", "Alexis, Snap and Daisy in a garden full of flowers and lettuce, saying hello to a boy walking his dog", "(max-width:760px) 92vw, 600px"))
    trail = [("/", "Home"), ("/meet-the-gang/", "Meet the Gang")]
    body = (f'<section class="ar-pagehead"><div class="ar-in ar-stack">{crumbs_html(trail)}<h1>Meet the gang</h1>'
            f'<p class="ar-lede">Alexis, her baby T-Rexes Snap and Daisy, and her best friend Abigail.</p></div></section>'
            f'<section class="ar-sec"><div class="ar-in ar-stack" style="gap:56px">{rows}</div></section>'
            f'<section class="ar-sec ar-white"><div class="ar-in ar-stack" style="gap:28px"><h2>Out and about</h2><div class="ar-scenes">{scenes}</div></div></section>'
            + books_section("Read their stories", intro=False))
    ld = site_nodes() + [webpage("/meet-the-gang/", "Meet the gang", "WebPage", trail)]
    return page("/meet-the-gang/", "Meet the Gang | Alexis, Snap and Daisy | Alexis and the T-Rexes",
                "Meet Alexis, her baby T-Rexes Snap and Daisy, and her best friend Abigail, from the Alexis and the T-Rexes picture books.", body, ld)


def free_page():
    minis = "".join(f'<a class="ar-card ar-mini" href="{d["url"]}" style="text-decoration:none">{img(d["img"], "Cover of " + d["title"] + " by Kevin Coulston", "92px")}'
                    f'<span class="ar-stack" style="gap:4px"><h3>{e(d["title"])}</h3><p>{e(d["what"])}. See it on Amazon.</p></span></a>' for d in DINO_BOOKS)
    trail = [("/", "Home"), ("/free-dinosaur-pages/", "Free Pages")]
    body = (f'<section class="ar-pagehead"><div class="ar-in ar-stack">{crumbs_html(trail)}<h1>Free dinosaur pages to print</h1>'
            f'<p class="ar-lede">Free drawing, grid and tracing pages from Kevin\'s Cartoon Dinosaurs books. Each one opens on FirstArtBooks.com, where you can print it.</p></div></section>'
            f'<section class="ar-sec"><div class="ar-in ar-stack" style="gap:44px"><div class="ar-grid3">{free_cards("h2")}</div>'
            f'<div class="ar-stack"><h2 style="font-size:clamp(28px,3vw,40px)">Want more? These pages come from three books</h2>'
            f'<div class="ar-grid3">{minis}</div></div></div></section>' + count_section() + draw_section())
    ld = site_nodes() + [webpage("/free-dinosaur-pages/", "Free dinosaur pages to print", "CollectionPage", trail)]
    return page("/free-dinosaur-pages/", "Free Dinosaur Pages to Print | Alexis and the T-Rexes",
                "Free printable dinosaur drawing, grid and tracing pages for kids from Kevin Coulston's Cartoon Dinosaurs books, plus a count-the-T-Rexes game.",
                body, ld, js=True)


def about_page():
    trail = [("/", "Home"), ("/about/", "About Kevin")]
    pic = img("kevin.webp", "Kevin Coulston, author and illustrator of Alexis and the T-Rexes", "(max-width:760px) 130px, 220px", lazy=False)
    body = (f'<section class="ar-pagehead"><div class="ar-in ar-stack">{crumbs_html(trail)}<h1>About Kevin Coulston</h1></div></section>'
            f'<section class="ar-sec"><div class="ar-in ar-kevin">{pic}<div class="ar-stack" style="max-width:70ch">'
            f'<p style="font-size:19px">Kevin Coulston is a cartoonist and children\'s book author and illustrator. He wrote and drew all three Alexis and the T-Rexes books.</p>'
            f'<p>He has made more than 80 books for kids, including the How to Draw, Trace Then Color and Draw by Grid books from FirstArtBooks, '
            f'and he shares free drawing lessons for kids at FirstArtBooks.com.</p>'
            f'<div class="ar-btns"><a class="ar-btn" href="https://kevincoulston.com/">KevinCoulston.com</a><a class="ar-btn leaf" href="https://firstartbooks.com/">FirstArtBooks.com</a>'
            f'<a class="ar-btn alt" href="{AUTHOR_STORE}">Kevin\'s books on Amazon</a></div></div></div></section>' + draw_section() + books_section("Kevin's Alexis and the T-Rexes books", intro=False))
    ld = site_nodes() + [webpage("/about/", "About Kevin Coulston", "AboutPage", trail)]
    return page("/about/", "About Kevin Coulston | Alexis and the T-Rexes",
                "Kevin Coulston is the cartoonist, author and illustrator of the Alexis and the T-Rexes picture books and more than 80 books for kids.", body, ld)


def not_found():
    pic = img("snap-sleepy.webp", "Snap the T-Rex dozing next to a big letter Z", "260px", lazy=False)
    body = (f'<section class="ar-sec"><div class="ar-in ar-center" style="gap:18px">{pic}<h1>This page is taking a nap</h1>'
            f'<p class="ar-lede">We couldn\'t find that page. Try the books, or head back home.</p>'
            f'<div class="ar-btns" style="justify-content:center"><a class="ar-btn" href="/">Back home</a><a class="ar-btn alt" href="/books/">The books</a></div></div></section>')
    html = page("/404.html", "Page not found | Alexis and the T-Rexes", "That page could not be found.", body, site_nodes())
    return html.replace('<meta name="viewport"', '<meta name="robots" content="noindex">\n<meta name="viewport"', 1)


def main():
    if D.exists():
        shutil.rmtree(D)
    (D / "assets" / "fonts").mkdir(parents=True)
    for f in (P / "perf_assets" / "fonts").iterdir():
        shutil.copy(f, D / "assets" / "fonts" / f.name)
    for n in ("favicon.png", "favicon-48.png", "apple-touch-icon.png"):
        shutil.copy(ART / n, D / n)
    shutil.copy(ART / "og-image.jpg", D / "assets" / "og-image.jpg")
    pages = {"index.html": home(), "books/index.html": books_index(), "meet-the-gang/index.html": gang_page(),
             "free-dinosaur-pages/index.html": free_page(), "about/index.html": about_page(), "404.html": not_found()}
    for b in BOOKS:
        pages[f"books/{b['slug']}/index.html"] = book_page(b)
    for rel, html in pages.items():
        f = D / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html)
    urls = [u for u in ["/", "/books/"] + [f"/books/{b['slug']}/" for b in BOOKS] + ["/meet-the-gang/", "/free-dinosaur-pages/", "/about/"]]
    (D / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                                   'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
                                   "".join(f"<url><loc>{SITE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (D / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    (D / "_headers").write_text("/assets/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                                "/assets/img/*\n  Cache-Control: public, max-age=2592000\n")
    print(f"build: {len(pages)} pages, {sum(len(v[0]) for v in _sizes.values())} image files")


if __name__ == "__main__":
    main()
