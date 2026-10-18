"""
blog_routes.py: real, crawlable blog URLs for XeerHub.

Adds:
  GET /blog/<slug>   server-rendered article page (SEO: title, description, canonical, JSON-LD)
  GET /sitemap.xml   dynamic sitemap: home + every published article

Reads the `blogs` table from Supabase over REST using the PUBLISHABLE (anon) key.
Required env vars on the Flask Railway service:
  SUPABASE_URL        e.g. https://bhruhoqohqeaesrrhnlg.supabase.co
  SUPABASE_ANON_KEY   the same publishable key the website already uses
"""
import os, re, html, time, json
import requests
from flask import Blueprint, Response, abort

blog_bp = Blueprint('blog_bp', __name__)

SITE = 'https://xeerhub.com'
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://bhruhoqohqeaesrrhnlg.supabase.co').rstrip('/')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '').strip()

_cache = {}          # key -> (expires_at, value)
_TTL = 300           # 5 minutes


def _sb_get(path_and_query):
    """GET from Supabase REST with a small in-memory cache. Returns parsed JSON or None."""
    now = time.time()
    hit = _cache.get(path_and_query)
    if hit and hit[0] > now:
        return hit[1]
    if not SUPABASE_ANON_KEY:
        print('blog_routes: SUPABASE_ANON_KEY is not set', flush=True)
        return None
    try:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/{path_and_query}',
            headers={'apikey': SUPABASE_ANON_KEY, 'Authorization': f'Bearer {SUPABASE_ANON_KEY}'},
            timeout=10,
        )
        if r.status_code != 200:
            print('blog_routes: supabase status', r.status_code, r.text[:200], flush=True)
            return None
        data = r.json()
        _cache[path_and_query] = (now + _TTL, data)
        return data
    except Exception as e:
        print('blog_routes: supabase error', str(e), flush=True)
        return None


def _plain(body_html, n=155):
    text = re.sub(r'<[^>]+>', ' ', body_html or '')
    text = html.unescape(re.sub(r'\s+', ' ', text)).strip()
    return text if len(text) <= n else text[:n].rsplit(' ', 1)[0] + '…'


@blog_bp.route('/blog/<slug>')
def blog_post(slug):
    if not re.fullmatch(r'[a-z0-9-]{1,120}', slug):
        abort(404)
    rows = _sb_get(f'blogs?slug=eq.{slug}&select=slug,title,category,date_label,read_time,body,created_at&limit=1')
    if not rows:
        return Response(
            '<!DOCTYPE html><meta charset="utf-8"><title>Article not found | XeerHub</title>'
            '<p style="font-family:sans-serif;padding:2rem">Article not found. '
            '<a href="/#blog">See all articles</a></p>', status=404, mimetype='text/html')
    a = rows[0]
    title = html.escape(a['title'])
    desc = html.escape(_plain(a['body']))
    url = f'{SITE}/blog/{slug}'
    published = (a.get('created_at') or '')[:10]
    ld_title = json.dumps(a['title']).replace('</', '<\\/')
    meta_line = ' · '.join(x for x in [html.escape(a.get('category') or ''), html.escape(a.get('date_label') or ''), html.escape(a.get('read_time') or '')] if x)
    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | XeerHub</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="XeerHub">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":{ld_title},"datePublished":"{published}","mainEntityOfPage":"{url}","publisher":{{"@type":"Organization","name":"XeerHub","url":"{SITE}"}}}}</script>
<style>
:root{{--ink:#0B0E0D;--muted:#6B7280;--parchment:#F7F4EE;--cream:#FFFDF8;--teal-deep:#0A4A3A;--teal-mid:#1D7A5E;--teal-light:#2BAE87;--teal-pale:#E1F5EE;--gold:#C8991A;--gold-pale:#FDF6E3;--gold-border:rgba(200,153,26,.3);--border:rgba(10,74,58,.12);--border-strong:rgba(10,74,58,.25);--primary-dim:rgba(10,74,58,.07);--r:8px;--r-sm:4px;--labor:#1D7A5E;--labor-bg:rgba(29,122,94,.08);--invest:#C8991A;--invest-bg:rgba(200,153,26,.08);--env:#1A7A2E;--env-bg:rgba(26,122,46,.08);--data:#6B21A8;--data-bg:rgba(107,33,168,.08)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);font-family:'DM Sans',sans-serif;font-size:16px;line-height:1.75}}
header{{background:var(--teal-deep);padding:.9rem 1.25rem}}
header a{{color:#fff;text-decoration:none;font-family:'Playfair Display',serif;font-weight:700;font-size:1.25rem}}
main{{max-width:760px;margin:0 auto;padding:2rem 1.25rem 4rem}}
h1{{font-family:'Playfair Display',serif;font-size:clamp(1.6rem,4vw,2.3rem);line-height:1.2;margin:.5rem 0 .75rem}}
.meta{{font-size:.8rem;color:var(--muted);margin-bottom:2rem}}
.disclaimer{{font-size:.8rem;color:var(--muted);font-style:italic;border-top:1px solid var(--border);margin-top:2.5rem;padding-top:1rem}}
.cta{{display:inline-block;margin-top:1rem;background:var(--teal-deep);color:#fff;text-decoration:none;padding:.75rem 1.4rem;border-radius:var(--r-sm);font-weight:500}}
a{{color:var(--teal-mid)}}
</style>
</head>
<body>
<header><a href="/">XeerHub</a></header>
<main>
<p style="margin:0"><a href="/#blog">&larr; All articles</a></p>
<h1>{title}</h1>
<div class="meta">{meta_line}</div>
<article>{a['body']}</article>
<p class="disclaimer">This article is legal information, not legal advice. Always consult a qualified Somali lawyer for your specific situation.</p>
<a class="cta" href="/#ask">Ask XeerHub a related question &rarr;</a>
</main>
</body>
</html>'''
    return Response(page, mimetype='text/html')


@blog_bp.route('/sitemap.xml')
def sitemap():
    rows = _sb_get('blogs?select=slug,created_at&order=id.asc') or []
    today = time.strftime('%Y-%m-%d')
    urls = [f'  <url>\n    <loc>{SITE}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>']
    for r in rows:
        slug = r.get('slug')
        if not slug or not re.fullmatch(r'[a-z0-9-]{1,120}', slug):
            continue
        last = (r.get('created_at') or today)[:10]
        urls.append(f'  <url>\n    <loc>{SITE}/blog/{slug}</loc>\n    <lastmod>{last}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n'
    return Response(xml, mimetype='application/xml')
