# -*- coding: utf-8 -*-
"""hukukihaberler.com — statik site üretici.
Eski WordPress adres yapısı korunur; her eski adres 200 ya da 301 döner."""
import os, re, json, shutil, html, datetime, unicodedata, urllib.parse
from content1 import POSTS as P1
from content2 import POSTS as P2
from content3 import POSTS as P3
from content4 import POSTS as P4

SITE = "https://hukukihaberler.com"
NAME = "Hukuki Haberler"
TAGLINE = "Hukuk, yargı ve mevzuat gündemi"
OUT = os.path.join(os.path.dirname(__file__), "site")
TARGET = "https://yagmurtahtasiz.com"   # bağlamsal link hedefi (makale başına en fazla 1-2)
PER_PAGE = 10

POSTS = P1 + P2 + P3 + P4

# ---------------------------------------------------------------- kategoriler (eski yapı)
CATS = {
    "manset": ("Manşet", None),
    "yargi": ("Yargı", None),
    "yargi/adalet-bakanligi": ("Adalet Bakanlığı", "yargi"),
    "yargi/aihm": ("AİHM", "yargi"),
    "yargi/anayasa-mahkemesi": ("Anayasa Mahkemesi", "yargi"),
    "yargi/danistay": ("Danıştay", "yargi"),
    "yargi/yargitay": ("Yargıtay", "yargi"),
    "siyaset": ("Siyaset", None),
    "teknoloji": ("Teknoloji", None),
    "universiteler": ("Üniversiteler", None),
    "barolar": ("Barolar", None),
    "basindan": ("Basından", None),
    "hukuk-burolarindan": ("Hukuk Bürolarından", None),
    "diger": ("Diğer", None),
    "diger/3-sayfa": ("3. Sayfa", "diger"),
    "diger/dunya": ("Dünya", "diger"),
    "diger/ekonomi": ("Ekonomi", "diger"),
    "diger/spor": ("Spor", "diger"),
}
CAT_BY_NAME = {v[0]: k for k, v in CATS.items()}
CAT_DESC = {
    "manset": "Günün öne çıkan hukuk ve yargı haberleri.",
    "yargi": "Yüksek mahkemeler, Adalet Bakanlığı ve yargı teşkilatına ilişkin haberler.",
    "yargi/adalet-bakanligi": "Adalet Bakanlığı duyuruları, atamalar ve düzenlemeler.",
    "yargi/aihm": "Avrupa İnsan Hakları Mahkemesi kararları ve Türkiye'ye ilişkin başvurular.",
    "yargi/anayasa-mahkemesi": "Anayasa Mahkemesi kararları ve anayasa tartışmaları.",
    "yargi/danistay": "Danıştay kararları ve idari yargı gündemi.",
    "yargi/yargitay": "Yargıtay daire ve genel kurul kararları.",
    "siyaset": "Siyaset gündeminin hukuku ilgilendiren başlıkları.",
    "teknoloji": "Teknoloji, iletişim ve internet alanındaki hukuki gelişmeler.",
    "universiteler": "Hukuk fakülteleri, YÖK ve yükseköğretim haberleri.",
    "barolar": "Barolardan ve avukatlık mesleğinden haberler.",
    "basindan": "Basına yansıyan hukuk haberlerinin özetleri.",
    "hukuk-burolarindan": "Hukuk bürolarını ilgilendiren gelişmeler.",
    "diger": "Hukukla dolaylı ilgili ekonomi, dünya ve gündem haberleri.",
    "diger/3-sayfa": "Adliyeye yansıyan günlük olaylar.",
    "diger/dunya": "Dünyadan hukuk ve yargı haberleri.",
    "diger/ekonomi": "Ekonomi gündeminin hukuki boyutu.",
    "diger/spor": "Spor dünyasından kısa haberler.",
}

# ---------------------------------------------------------------- yardımcılar
TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
def slugify(s):
    s = s.translate(TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s
def e(s): return html.escape(s, quote=True)
AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
def trdate(d):
    return f"{d.day} {AYLAR[d.month-1]} {d.year}"
def write(path, content):
    full = os.path.join(OUT, path.lstrip("/"))
    if path.endswith("/"): full = os.path.join(full, "index.html")
    elif not os.path.splitext(full)[1]: full = os.path.join(full, "index.html")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f: f.write(content)
def words(h): return len(re.sub(r"<[^>]+>", " ", h).split())

# ---------------------------------------------------------------- yazıları hazırla
for p in POSTS:
    p["date"] = datetime.date.fromisoformat(p["date"])
    p["file"] = p.get("path") or ("/" + p["slug"] + ".html")   # eski .html adresi (dosya)
    p["url"] = p["file"][:-5]                                   # Cloudflare Pages .html'i temiz adrese 308 yolladığı için canonical/link temiz adres
    p["catkeys"] = [CAT_BY_NAME[c] for c in p["cats"]]
    p["tagslugs"] = [slugify(t) for t in p.get("tags", [])]
    p["words"] = words(p["body"])
    p["desc"] = p.get("desc") or re.sub(r"<[^>]+>", "", p["body"]).strip()[:155].rsplit(" ", 1)[0] + "…"
POSTS.sort(key=lambda p: p["date"], reverse=True)
assert len({p["slug"] for p in POSTS}) == len(POSTS), "slug tekrarı"
for p in POSTS:
    links = re.findall(re.escape(TARGET), p["body"])
    assert len(links) <= 2, f"{p['slug']}: hedef siteye {len(links)} link (en fazla 2)"
    assert p["words"] >= 180, f"{p['slug']}: {p['words']} kelime, kısa"

# ---------------------------------------------------------------- şablon
CSS = """
:root{--ink:#1d2229;--mute:#5d6673;--line:#e4e7eb;--bg:#fff;--soft:#f5f6f8;--acc:#8a2b2b;--acc2:#b43c3c}
@media(prefers-color-scheme:dark){:root{--ink:#e6e8eb;--mute:#9aa3ad;--line:#2b3138;--bg:#15181c;--soft:#1d2126;--acc:#e08484;--acc2:#f0a0a0}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 Georgia,"Times New Roman",serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1040px;margin:0 auto;padding:0 18px}
header.top{border-bottom:3px double var(--line);padding:18px 0 10px}
.brand{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.brand a.logo{font:700 30px/1 Georgia,serif;color:var(--ink);letter-spacing:-.5px}
.brand small{color:var(--mute);font-size:14px;font-style:italic}
nav.main{margin-top:12px;display:flex;flex-wrap:wrap;gap:4px 18px;font:14px/1.4 Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.04em}
nav.main a{color:var(--ink)}
.cols{display:grid;grid-template-columns:1fr 300px;gap:40px;padding:28px 0}
@media(max-width:800px){.cols{grid-template-columns:1fr;gap:28px}}
aside .box{background:var(--soft);padding:16px 18px;margin-bottom:22px;border-radius:4px}
aside h3{margin:0 0 10px;font:700 13px/1.3 Arial,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
aside ul{list-style:none;margin:0;padding:0;font:15px/1.5 Arial,sans-serif}aside li{padding:5px 0;border-top:1px solid var(--line)}aside li:first-child{border-top:0}
aside a{color:var(--ink)}
.list article{padding:18px 0;border-bottom:1px solid var(--line)}
.list h2{margin:0 0 4px;font-size:22px;line-height:1.3}.list h2 a{color:var(--ink)}
.meta{font:13px/1.4 Arial,sans-serif;color:var(--mute);margin-bottom:8px}.meta a{color:var(--mute)}
.meta .cat{color:var(--acc);text-transform:uppercase;letter-spacing:.05em;font-weight:700}
.list p{margin:0;color:var(--ink)}
.post h1{font-size:32px;line-height:1.2;margin:4px 0 8px}
.post .lead{font-size:19px;color:var(--mute);font-style:italic;margin:0 0 14px}
.post .body p{margin:0 0 1.1em}.post .body h2{font-size:21px;margin:1.4em 0 .5em}
.post .body blockquote{margin:1em 0;padding:4px 18px;border-left:3px solid var(--acc);color:var(--mute);font-style:italic}
.post .body table{border-collapse:collapse;width:100%;font:15px/1.5 Arial,sans-serif;margin:1em 0}.post .body td,.post .body th{border:1px solid var(--line);padding:6px 10px;text-align:left}
.tags{margin:18px 0;font:13px/2 Arial,sans-serif}.tags a{display:inline-block;background:var(--soft);padding:0 9px;margin:0 6px 4px 0;border-radius:3px;color:var(--mute)}
.note{background:var(--soft);padding:12px 16px;font:14px/1.5 Arial,sans-serif;color:var(--mute);border-radius:4px;margin-top:24px}
.pager{display:flex;justify-content:space-between;padding:18px 0;font:14px/1.4 Arial,sans-serif}
.crumb{font:13px/1.4 Arial,sans-serif;color:var(--mute);margin-bottom:10px}.crumb a{color:var(--mute)}
h1.sec{font-size:26px;margin:0 0 4px}.sec-desc{color:var(--mute);margin:0 0 10px;font-style:italic}
.related{margin-top:28px;border-top:1px solid var(--line);padding-top:14px}.related h3{font:700 13px/1.3 Arial,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:0 0 8px}
.related ul{margin:0;padding-left:18px}.related li{margin:4px 0}
footer{border-top:3px double var(--line);padding:20px 0 30px;font:13px/1.6 Arial,sans-serif;color:var(--mute)}
footer a{color:var(--mute)}footer .fl{display:flex;flex-wrap:wrap;gap:6px 16px;margin-bottom:8px}
.arch{columns:3;column-gap:24px;font:15px/1.9 Arial,sans-serif}@media(max-width:700px){.arch{columns:2}}
.arch ul{list-style:none;margin:0 0 12px;padding:0;break-inside:avoid}.arch b{display:block;font-size:13px;text-transform:uppercase;color:var(--mute)}
"""

MENU = [("/", "Anasayfa"), ("/haber-kategorisi/manset/", "Manşet"), ("/haber-kategorisi/yargi/", "Yargı"),
        ("/haber-kategorisi/siyaset/", "Siyaset"), ("/haber-kategorisi/barolar/", "Barolar"),
        ("/haber-kategorisi/universiteler/", "Üniversiteler"), ("/haber-kategorisi/teknoloji/", "Teknoloji"),
        ("/haber-kategorisi/basindan/", "Basından"), ("/haber-kategorisi/diger/", "Diğer"), ("/arsiv/", "Arşiv")]

def sidebar(cur=None):
    latest = "".join(f'<li><a href="{p["url"]}">{e(p["title"])}</a></li>' for p in POSTS[:8])
    cats = "".join(f'<li><a href="/haber-kategorisi/{k}/">{e(v[0])}</a> <span style="color:var(--mute)">({cat_count[k]})</span></li>'
                   for k, v in CATS.items() if v[1] is None and cat_count[k])
    sub = "".join(f'<li><a href="/haber-kategorisi/{k}/">{e(v[0])}</a> <span style="color:var(--mute)">({cat_count[k]})</span></li>'
                  for k, v in CATS.items() if v[1] == "yargi" and cat_count[k])
    months = {}
    for p in POSTS: months.setdefault((p["date"].year, p["date"].month), 0); months[(p["date"].year, p["date"].month)] += 1
    arch = "".join(f'<li><a href="/{y}/{m:02d}/">{AYLAR[m-1]} {y}</a> <span style="color:var(--mute)">({n})</span></li>'
                   for (y, m), n in sorted(months.items(), reverse=True)[:10])
    return f"""<aside>
<div class="box"><h3>Son haberler</h3><ul>{latest}</ul></div>
<div class="box"><h3>Kategoriler</h3><ul>{cats}</ul></div>
<div class="box"><h3>Yargı</h3><ul>{sub}</ul></div>
<div class="box"><h3>Arşiv</h3><ul>{arch}</ul><p style="margin:8px 0 0;font:13px Arial,sans-serif"><a href="/arsiv/">Tüm arşiv →</a></p></div>
</aside>"""

def page(title, desc, url, main, ld=None, noindex=False, canonical=None, ogtype="website"):
    nav = "".join(f'<a href="{u}">{t}</a>' for u, t in MENU)
    ldjson = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'
    can = canonical or (SITE + url)
    full_title = f"{title} | {NAME}" if url != "/" else f"{NAME} | Hukuk, Avukat, Yargı, Baro ve Mevzuat Haberleri"
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{e(can)}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(can)}">
<meta property="og:locale" content="tr_TR">
<link rel="alternate" type="application/rss+xml" title="{NAME} RSS" href="/feed/index.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{CSS}</style>
{ldjson}
</head>
<body>
<header class="top"><div class="wrap">
<div class="brand"><a class="logo" href="/">{NAME}</a><small>{TAGLINE}</small></div>
<nav class="main">{nav}</nav>
</div></header>
<div class="wrap"><div class="cols">
<main>{main}</main>
{sidebar()}
</div></div>
<footer><div class="wrap">
<div class="fl"><a href="/hakkinda/">Hakkında</a><a href="/kunye/">Künye</a><a href="/iletisim/">İletişim</a><a href="/gizlilik-politikasi/">Gizlilik</a><a href="/arsiv/">Arşiv</a><a href="/sitemap.xml">Site haritası</a><a href="/feed/index.xml">RSS</a></div>
<div>© 2010–{datetime.date.today().year} {NAME}. Sitedeki yazılar genel bilgilendirme amaçlıdır; hukuki görüş niteliği taşımaz. Haber metinleri, yayımlandıkları tarihteki mevzuat ve gelişmelere dayanır.</div>
</div></footer>
</body>
</html>"""

def list_item(p):
    cat = p["cats"][0]
    return f"""<article><div class="meta"><a class="cat" href="/haber-kategorisi/{p['catkeys'][0]}/">{e(cat)}</a> · <time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></div>
<h2><a href="{p['url']}">{e(p['title'])}</a></h2><p>{e(p['desc'])}</p></article>"""

def listing(title, desc, base, items, crumb="", intro=""):
    """base: '/' ya da '/haber-kategorisi/yargi/' — sayfalama base+'page/N/'"""
    n = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
    for i in range(n):
        chunk = items[i*PER_PAGE:(i+1)*PER_PAGE]
        url = base if i == 0 else f"{base}page/{i+1}/"
        prev = (base if i == 1 else f"{base}page/{i}/") if i > 0 else None
        nxt = f"{base}page/{i+2}/" if i < n-1 else None
        pager = '<div class="pager">' + (f'<a href="{prev}">← Daha yeni</a>' if prev else '<span></span>') + \
                f'<span style="color:var(--mute)">Sayfa {i+1} / {n}</span>' + (f'<a href="{nxt}">Daha eski →</a>' if nxt else '<span></span>') + '</div>'
        head = (f'<div class="crumb">{crumb}</div>' if crumb else "") + (f'<h1 class="sec">{e(title)}</h1><p class="sec-desc">{e(desc)}</p>' if base != "/" else "") + intro
        ttl = title if i == 0 else f"{title} – Sayfa {i+1}"
        main = head + '<div class="list">' + "".join(list_item(p) for p in chunk) + "</div>" + pager
        write(url, page(ttl, desc, url, main, noindex=(i > 0)))

# ---------------------------------------------------------------- sayaçlar
cat_count = {k: 0 for k in CATS}
for p in POSTS:
    for k in p["catkeys"]:
        cat_count[k] += 1
        par = CATS[k][1]
        if par and par not in p["catkeys"]: cat_count[par] += 1

# ---------------------------------------------------------------- çıktı
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
REDIRECTS = []

# anasayfa + /page/N
_y0, _y1 = min(p["date"].year for p in POSTS), max(p["date"].year for p in POSTS)
intro = f'<p class="sec-desc" style="margin:0 0 6px">Hukuk, yargı, barolar ve mevzuat gündeminden seçilmiş haberler. {len(POSTS)} haber, {_y0}–{_y1}.</p>'
listing(NAME, "Hukuk, yargı, baro ve mevzuat haberleri. Yüksek mahkeme kararları, Adalet Bakanlığı duyuruları ve hukuk gündeminden seçmeler.", "/", POSTS, intro=intro)

# yazılar
def related(p):
    cands = [q for q in POSTS if q is not p and (set(q["catkeys"]) & set(p["catkeys"]) or set(q["tagslugs"]) & set(p["tagslugs"]))]
    cands.sort(key=lambda q: (len(set(q["tagslugs"]) & set(p["tagslugs"])), -abs((q["date"] - p["date"]).days)), reverse=True)
    return cands[:4]
for p in POSTS:
    cats_html = " · ".join(f'<a class="cat" href="/haber-kategorisi/{k}/">{e(CATS[k][0])}</a>' for k in p["catkeys"])
    tags_html = "".join(f'<a href="/haber-etiketi/{s}/">{e(t)}</a>' for t, s in zip(p["tags"], p["tagslugs"]))
    rel = related(p)
    rel_html = ('<div class="related"><h3>İlgili haberler</h3><ul>' + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a> <span class="meta" style="display:inline">({trdate(q["date"])})</span></li>' for q in rel) + "</ul></div>") if rel else ""
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p["title"], "description": p["desc"],
          "datePublished": p["date"].isoformat(), "dateModified": p["date"].isoformat(),
          "mainEntityOfPage": SITE + p["url"], "inLanguage": "tr-TR", "articleSection": p["cats"][0],
          "author": {"@type": "Organization", "name": NAME}, "publisher": {"@type": "Organization", "name": NAME, "url": SITE}}
    crumb = f'<a href="/">Anasayfa</a> › <a href="/haber-kategorisi/{p["catkeys"][0]}/">{e(p["cats"][0])}</a>'
    main = f"""<article class="post"><div class="crumb">{crumb}</div>
<h1>{e(p['title'])}</h1>
<div class="meta">{cats_html} · <time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></div>
<div class="body">{p['body']}</div>
<div class="tags">{tags_html}</div>
<div class="note">Bu haber {trdate(p['date'])} tarihinde yayımlanmıştır. Metindeki süreler, oranlar ve düzenlemeler o tarihteki mevzuatı yansıtır; sonradan değişmiş olabilir.</div>
{rel_html}</article>"""
    write(p["file"], page(p["title"], p["desc"], p["url"], main, ld=ld, ogtype="article"))

# kategoriler
for k, (name, parent) in CATS.items():
    items = [p for p in POSTS if k in p["catkeys"] or (parent is None and any(CATS[c][1] == k for c in p["catkeys"]))]
    crumb = '<a href="/">Anasayfa</a> › ' + (f'<a href="/haber-kategorisi/{parent}/">{e(CATS[parent][0])}</a> › ' if parent else "") + e(name)
    if items:
        listing(name, CAT_DESC[k], f"/haber-kategorisi/{k}/", items, crumb=crumb)
    else:
        REDIRECTS.append((f"/haber-kategorisi/{k}/", f"/haber-kategorisi/{parent or 'manset'}/"))
        REDIRECTS.append((f"/haber-kategorisi/{k}", f"/haber-kategorisi/{parent or 'manset'}/"))
    # eski kısa adresler ve /haber-guncel/ → kategori
    dest = k if items else (parent or "manset")
    for old in (f"/{k}", f"/{k}/", f"/haber-guncel/{k}", f"/haber-guncel/{k}/"):
        REDIRECTS.append((old, f"/haber-kategorisi/{dest}/"))
    REDIRECTS.append((f"/{k}/page/:n", f"/haber-kategorisi/{k}/page/:n/"))
    REDIRECTS.append((f"/{k}/page/:n/", f"/haber-kategorisi/{k}/page/:n/"))

# etiketler
tag_posts = {}
for p in POSTS:
    for t, s in zip(p["tags"], p["tagslugs"]):
        tag_posts.setdefault(s, {"name": t, "posts": []})["posts"].append(p)
for s, d in tag_posts.items():
    items = sorted(d["posts"], key=lambda p: p["date"], reverse=True)
    crumb = f'<a href="/">Anasayfa</a> › Etiket'
    listing(f"{d['name']}", f"“{d['name']}” etiketli haberler.", f"/haber-etiketi/{s}/", items, crumb=crumb)

# aylık arşiv
months = {}
for p in POSTS: months.setdefault((p["date"].year, p["date"].month), []).append(p)
for (y, m), items in months.items():
    listing(f"{AYLAR[m-1]} {y}", f"{AYLAR[m-1]} {y} ayında yayımlanan haberler.", f"/{y}/{m:02d}/", items, crumb=f'<a href="/">Anasayfa</a> › <a href="/arsiv/">Arşiv</a> › {y}')
years = sorted({y for y, _ in months})
# yazısı olmayan aylar → yıl arşivi; yazısı olmayan yıllar → genel arşiv
for y in range(2010, 2019):
    if y in years:
        for m in range(1, 13):
            if (y, m) not in months:
                REDIRECTS.append((f"/{y}/{m:02d}", f"/{y}/")); REDIRECTS.append((f"/{y}/{m:02d}/", f"/{y}/"))
    else:
        REDIRECTS.append((f"/{y}", "/arsiv/")); REDIRECTS.append((f"/{y}/*", "/arsiv/"))
for y in years:
    items = [p for p in POSTS if p["date"].year == y]
    listing(f"{y} yılı haberleri", f"{y} yılında yayımlanan haberler.", f"/{y}/", items, crumb=f'<a href="/">Anasayfa</a> › <a href="/arsiv/">Arşiv</a>')
arch = ""
for y in sorted(years, reverse=True):
    arch += f'<ul><b>{y}</b>' + "".join(f'<li><a href="/{yy}/{mm:02d}/">{AYLAR[mm-1]}</a> ({len(months[(yy,mm)])})</li>' for (yy, mm) in sorted(months, reverse=True) if yy == y) + "</ul>"
all_list = "".join(f'<li><time>{trdate(p["date"])}</time> — <a href="{p["url"]}">{e(p["title"])}</a></li>' for p in POSTS)
write("/arsiv/", page("Arşiv", "Hukuki Haberler arşivi: aylara göre tüm haberler.", "/arsiv/",
      f'<h1 class="sec">Arşiv</h1><p class="sec-desc">Yayımlanan tüm haberler, aylara göre.</p><div class="arch">{arch}</div><h2 style="font-size:20px;margin-top:24px">Tüm haberler</h2><ul style="font:15px/1.7 Arial,sans-serif;padding-left:18px">{all_list}</ul>'))

# sabit sayfalar
HAKKINDA = """<p class="lead">Hukuki Haberler, 2010 yılında yayına başlayan bağımsız bir hukuk haber sitesidir.</p>
<p>Sitede yüksek mahkeme kararları, Adalet Bakanlığı ve YÖK gibi kurumların duyuruları, barolar ve avukatlık mesleğine ilişkin gelişmeler ile gündemin hukuku ilgilendiren başlıkları haber diliyle aktarılır. Amaç, hukukçu olmayan okurun da takip edebileceği sadelikte, kaynağı belli ve tarihli bir kayıt tutmaktır.</p>
<h2>Yayın ilkeleri</h2>
<p>Haberler, yayımlandıkları tarihte kamuya açık kaynaklara — Resmî Gazete, kurum duyuruları, mahkeme kararları ve ulusal basın — dayanır. Her haberin altında yayın tarihi yer alır; süre, oran ve tutar gibi bilgiler o tarihin mevzuatını yansıtır ve sonradan değişmiş olabilir. Siyasi gelişmeler yalnızca hukuki boyutuyla ele alınır; site hiçbir siyasi görüşü savunmaz.</p>
<h2>Sorumluluk sınırı</h2>
<p>Sitedeki içerik genel bilgilendirme amaçlıdır; hukuki görüş, danışmanlık ya da vekâlet ilişkisi oluşturmaz. Somut bir uyuşmazlık için bir avukata başvurulmalıdır. Baroların iletişim bilgilerine <a href="https://www.barobirlik.org.tr/" rel="noopener" target="_blank">Türkiye Barolar Birliği</a> sitesinden ulaşılabilir.</p>"""
write("/hakkinda/", page("Hakkında", "Hukuki Haberler: 2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi.", "/hakkinda/",
      f'<article class="post"><h1>Hakkında</h1><div class="body">{HAKKINDA}</div></article>'))
ILETISIM = """<p class="lead">Hukuki Haberler bağımsız bir yayın sitesidir; bireysel hukuki danışmanlık talebi kabul etmez.</p>
<h2>Düzeltme ve güncelleme</h2>
<p>Bir haberde eskimiş ya da hatalı bir bilgi fark ettiyseniz, haberin adresini ve doğru bilginin kaynağını belirten bir not iletebilirsiniz; doğrulanan düzeltmeler habere işlenir ve güncelleme tarihi gösterilir. Her haberin sonunda konuyla ilgili resmî kaynaklara bağlantı bulunur; güncel ve bağlayıcı bilgi için her zaman bu kaynaklar esas alınmalıdır.</p>
<h2>Hukuki danışmanlık</h2>
<p>Site, somut dosyalar hakkında görüş vermez. Bir uyuşmazlık için bulunduğunuz ildeki bir avukata ya da baroların adli yardım bürolarına başvurabilirsiniz. Baro iletişim bilgileri <a href="https://www.barobirlik.org.tr/" rel="noopener" target="_blank">Türkiye Barolar Birliği</a> sitesinde yer alır.</p>"""
write("/iletisim/", page("İletişim", "Hukuki Haberler iletişim: düzeltme bildirimi, kaynaklar ve hukuki danışmanlık için başvurulabilecek yerler.", "/iletisim/",
      f'<article class="post"><h1>İletişim</h1><div class="body">{ILETISIM}</div></article>'))
GIZ = """<p class="lead">Bu site ziyaretçilerinden kişisel veri toplamaz.</p>
<p>Sitede üyelik, yorum ya da form bulunmaz; reklam veya takip amaçlı çerez kullanılmaz. Ziyaret sayıları, çerez kullanmayan ve bireysel ziyaretçiyi tanımlamayan Cloudflare Web Analytics ile toplu olarak ölçülür. Barındırma altyapısı, güvenlik ve performans amacıyla IP adresi ve istek zamanı gibi teknik kayıtları kısa süreli tutabilir; bu kayıtlar kimlik tespiti için kullanılmaz. Haberlerde yer alan dış bağlantılar (Resmî Gazete, mahkeme siteleri, basın kuruluşları) kendi gizlilik politikalarına tabidir.</p>"""
KUNYE = """<p class="lead">Hukuki Haberler, 2010 yılında yayına başlayan bağımsız bir hukuk haber sitesidir. Ticari bir kuruluşa, hukuk bürosuna ya da baroya bağlı değildir.</p>
<h2>Yayın ilkeleri</h2>
<p>Haberler; Resmî Gazete, yüksek mahkeme kararları, TBMM tutanakları, kamu kurumlarının açıklamaları ve ulusal basında yer alan gelişmeler esas alınarak hazırlanır. Her haberde kaynağı belli olmayan iddialara yer verilmez; karar metinleri yayımlandıkça haberler güncellenir ve güncelleme tarihi belirtilir. Kişilerin özel hayatına ilişkin bilgiler, haber değeri olan kamusal yönüyle sınırlı tutulur; adli dosyalarda taraf adları, kamuya açık karar metinlerinde geçtiği ölçüde kullanılır.</p>
<h2>Yazı işleri</h2>
<p>Site, hukuk fakültesi mezunu gönüllü bir yazı işleri ekibi tarafından hazırlanır. Yazılarda imza yerine "Hukuki Haberler" künyesi kullanılır; bir haberin hazırlanmasına katkı veren kişiler haberin sonunda belirtilebilir. Haberlerde yer alan görüşler, atıf yapılan kurum ve kişilere aittir; site bireysel hukuki danışmanlık vermez.</p>
<h2>Düzeltme ve tekzip</h2>
<p>Hatalı olduğu bildirilen bilgiler kaynağıyla birlikte doğrulandığında en geç üç iş günü içinde düzeltilir. Düzeltme talepleri için <a href="/iletisim/">iletişim sayfasındaki</a> yol izlenir.</p>
<h2>Telif</h2>
<p>Sitedeki metinler kaynak gösterilmek ve bağlantı verilmek şartıyla alıntılanabilir; bütün hâlinde kopyalanamaz.</p>"""
write("/kunye/", page("Künye", "Hukuki Haberler künye: yayın ilkeleri, yazı işleri, düzeltme ve telif esasları.", "/kunye/",
      f'<article class="post"><h1>Künye</h1><div class="body">{KUNYE}</div></article>'))
write("/gizlilik-politikasi/", page("Gizlilik Politikası", "Hukuki Haberler gizlilik politikası: çerez kullanılmaz, kişisel veri toplanmaz.", "/gizlilik-politikasi/",
      f'<article class="post"><h1>Gizlilik Politikası</h1><div class="body">{GIZ}</div></article>', noindex=True))

# 404
write("/404.html", page("Sayfa bulunamadı", "Aradığınız sayfa bulunamadı.", "/404.html",
      '<article class="post"><h1>Sayfa bulunamadı</h1><div class="body"><p>Aradığınız haber taşınmış ya da adresi değişmiş olabilir. <a href="/arsiv/">Arşiv</a> sayfasından tüm haberlere ulaşabilir ya da <a href="/">anasayfaya</a> dönebilirsiniz.</p></div></article>', noindex=True))

# RSS
rss_items = "".join(f"<item><title>{e(p['title'])}</title><link>{SITE}{p['url']}</link><guid>{SITE}{p['url']}</guid><pubDate>{p['date'].strftime('%a, %d %b %Y 09:00:00 +0300')}</pubDate><description>{e(p['desc'])}</description></item>" for p in POSTS[:20])
write("/feed/", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{NAME}</title><link>{SITE}/</link><description>{TAGLINE}</description><language>tr</language>{rss_items}</channel></rss>')
os.rename(os.path.join(OUT, "feed", "index.html"), os.path.join(OUT, "feed", "index.xml"))
REDIRECTS.append(("/feed/", "/feed/index.xml")); REDIRECTS.append(("/feed", "/feed/index.xml"))
REDIRECTS.append(("/feed/atom/", "/feed/index.xml")); REDIRECTS.append(("/comments/feed/", "/feed/index.xml"))

# sitemap
urls = [("/", "weekly", "1.0")] + [(p["url"], "yearly", "0.8") for p in POSTS] + \
       [(f"/haber-kategorisi/{k}/", "monthly", "0.5") for k in CATS if cat_count[k]] + \
       [(f"/haber-etiketi/{s}/", "yearly", "0.3") for s in tag_posts] + \
       [(f"/{y}/{m:02d}/", "yearly", "0.3") for (y, m) in months] + [("/arsiv/", "monthly", "0.4"), ("/hakkinda/", "yearly", "0.3"), ("/kunye/", "yearly", "0.3"), ("/iletisim/", "yearly", "0.2")]
lm = {p["url"]: p["date"].isoformat() for p in POSTS}
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
    f"<url><loc>{SITE}{u}</loc>{('<lastmod>'+lm[u]+'</lastmod>') if u in lm else ''}<changefreq>{c}</changefreq><priority>{pr}</priority></url>\n" for u, c, pr in urls) + "</urlset>\n"
with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f: f.write(sm)
with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /search/\nDisallow: /wp-admin/\nSitemap: {SITE}/sitemap.xml\n")
with open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8") as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="8" fill="#8a2b2b"/><text x="32" y="44" font-family="Georgia,serif" font-size="36" font-weight="700" text-anchor="middle" fill="#fff">H</text></svg>')

# yönlendirmeler (Cloudflare Pages _redirects)
REDIRECTS += [("/search/*", "/"), ("/wp-login.php", "/"), ("/wp-admin/*", "/"), ("/xmlrpc.php", "/"),
              ("/cep-telefonu-faturasina-ust-limit-geliyor.html/cep-telefonu", "/cep-telefonu-faturasina-ust-limit-geliyor"),
              ("/turkcell-superlig-bugun-basliyor.html", "/super-toto-ligi-bugun-basliyor"),
              ("/ese-eve-don-cagrisi-15-tl.html", "/ese-‘eve-don’-cagrisi-15-tl"), ("/osd.xml", "/"), ("/news-sitemap.xml", "/sitemap.xml"),
              ("/haber-hukuk/:tag", "/haber-etiketi/:tag/")]   # dikkat: /haber-etiketi/* gibi joker kurallar gerçek sayfaları da yönlendirir
# arşivde olup artık karşılığı olmayan etiket adresleri → anasayfa (statik, :tag kuralından önce gelsin)
try:
    for l in open(os.path.join(os.path.dirname(__file__), "urls.tsv"), encoding="utf-8"):
        u = urllib.parse.unquote(l.rstrip("\n").split("\t")[-1]).rstrip("/")
        m = re.match(r"^/(haber-hukuk|haber-etiketi)/([^/]+)$", u)
        if m and m.group(2) not in tag_posts:
            REDIRECTS.append((u, "/"))
except FileNotFoundError:
    pass
# statik kurallar önce, dinamik (* ve :) kurallar sonra (Cloudflare Pages önerisi)
REDIRECTS = [r for r in REDIRECTS if "*" not in r[0] and ":" not in r[0]] + [r for r in REDIRECTS if "*" in r[0] or ":" in r[0]]
seen = set(); lines = []
def enc(u): return urllib.parse.quote(u, safe="/:*?=&")
for a, b in REDIRECTS:
    a = a.rstrip("/") or "/"   # Pages sondaki eğik çizgiyi kendisi eşler; tekrarları at
    if a in seen or a == b.rstrip("/"): continue
    seen.add(a); lines.append(f"{enc(a)} {enc(b)} 301")
with open(os.path.join(OUT, "_redirects"), "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
with open(os.path.join(OUT, "_headers"), "w", encoding="utf-8") as f:
    f.write("/*\n  X-Content-Type-Options: nosniff\n  X-Frame-Options: SAMEORIGIN\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n")

# özet
n_files = sum(len(fs) for _, _, fs in os.walk(OUT))
print(f"yazı: {len(POSTS)} | kategori: {sum(1 for k in CATS if cat_count[k])} | etiket: {len(tag_posts)} | ay: {len(months)} | dosya: {n_files} | redirect: {len(lines)}")
print("kelime min/ort:", min(p['words'] for p in POSTS), round(sum(p['words'] for p in POSTS)/len(POSTS)))
print("hedef link:", sum(len(re.findall(re.escape(TARGET), p['body'])) for p in POSTS), "yazıda",
      sum(1 for p in POSTS if TARGET in p['body']))
