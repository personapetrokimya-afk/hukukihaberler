# -*- coding: utf-8 -*-
"""hukukihaberler.com — statik site üretici.
Eski WordPress adres yapısı korunur; her eski adres 200 ya da 301 döner."""
import os, re, json, shutil, html, datetime, unicodedata, urllib.parse
from content1 import POSTS as P1
from content2 import POSTS as P2
from content3 import POSTS as P3
from content4 import POSTS as P4
from content5 import POSTS as P5

SITE = "https://hukukihaberler.com"
NAME = "Hukuki Haberler"
TAGLINE = "Hukuk, yargı ve mevzuat gündemi"
OUT = os.path.join(os.path.dirname(__file__), "site")
TARGET = "https://yagmurtahtasiz.com"   # bağlamsal link hedefi (makale başına en fazla 1-2)
PER_PAGE = 10

POSTS = P1 + P2 + P3 + P4 + P5

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
import images as _images
for p in POSTS: p["catname"] = CATS[p["catkeys"][0]][0] if p["catkeys"][0] != "manset" or len(p["catkeys"]) == 1 else CATS[p["catkeys"][1]][0]
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
_IMG = _images.build(POSTS, os.path.join(OUT, "gorsel"))
for p in POSTS: p["img"], p["imgkind"], p["credit"] = _IMG[p["slug"]]
for p in POSTS:
    links = re.findall(re.escape(TARGET), p["body"])
    assert len(links) <= 2, f"{p['slug']}: hedef siteye {len(links)} link (en fazla 2)"
    assert p["words"] >= 180, f"{p['slug']}: {p['words']} kelime, kısa"

# ---------------------------------------------------------------- şablon (haber teması)
CSS = """
:root{--ink:#14181d;--mute:#5f6973;--line:#e3e6ea;--bg:#fff;--soft:#f4f5f7;--acc:#9b1c1c;--acc2:#c62828;--gold:#b8860b;--sans:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--serif:Georgia,"Times New Roman",serif}
@media(prefers-color-scheme:dark){:root{--ink:#e8eaed;--mute:#9aa3ad;--line:#2a3036;--bg:#121518;--soft:#1b1f24;--acc:#e57373;--acc2:#ef9a9a}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans)}
a{color:var(--ink);text-decoration:none}a:hover{color:var(--acc)}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;color:#000;padding:6px 10px;z-index:99}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
.topbar{font:12px/1.4 var(--sans);color:var(--mute);border-bottom:1px solid var(--line);padding:6px 0;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.topbar a{color:var(--mute)}.topbar .links a{margin-left:14px}
.mast{padding:20px 0 14px;text-align:center}
.mast .logo{font:800 44px/1 var(--serif);letter-spacing:-1px;color:var(--ink)}
.mast .logo span{color:var(--acc)}
.mast small{display:block;margin-top:6px;color:var(--mute);font-size:13px;text-transform:uppercase;letter-spacing:.18em}
nav.main{background:var(--acc);border-top:3px solid var(--ink)}
nav.main ul{list-style:none;margin:0 auto;padding:0;max-width:1180px;display:flex;overflow-x:auto;scrollbar-width:none}
nav.main ul::-webkit-scrollbar{display:none}
nav.main a{display:block;padding:11px 16px;color:#fff;font:600 13px/1.2 var(--sans);text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;border-right:1px solid rgba(255,255,255,.14)}
nav.main a:hover,nav.main a.on{background:rgba(0,0,0,.22);color:#fff}
.kicker{display:inline-block;white-space:nowrap;font:700 11px/1 var(--sans);text-transform:uppercase;letter-spacing:.08em;color:#fff;background:var(--acc);padding:4px 7px;border-radius:2px}
.kicker.k-yargi{background:#1e3a8a}.kicker.k-siyaset{background:#374151}.kicker.k-basindan{background:#6b4f1d}.kicker.k-diger{background:#0f766e}.kicker.k-universiteler{background:#5b21b6}.kicker.k-teknoloji{background:#0e7490}.kicker.k-barolar{background:#7c2d12}.kicker.k-hukuk-burolarindan{background:#4a044e}
time,.date{font:12px/1.4 var(--sans);color:var(--mute)}
.cols{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:36px;padding:26px 0}
@media(max-width:900px){.cols{grid-template-columns:1fr;gap:28px}}
.sec-h{display:flex;align-items:center;gap:12px;margin:0 0 14px;font:800 18px/1.2 var(--serif);text-transform:uppercase;letter-spacing:.02em}
.sec-h:after{content:"";flex:1;height:3px;background:linear-gradient(90deg,var(--acc) 0 60px,var(--line) 60px)}
.sec-h a{color:var(--ink)}
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:22px;margin-bottom:30px}
@media(max-width:760px){.hero{grid-template-columns:1fr}}
.lead-story{border-top:4px solid var(--acc);padding-top:14px}
.lead-story h2{font:800 32px/1.15 var(--serif);margin:10px 0 8px}
.lead-story p{margin:0;color:var(--mute);font-size:16px}
.side-stories{display:flex;flex-direction:column;gap:14px;border-left:1px solid var(--line);padding-left:22px}
@media(max-width:760px){.side-stories{border-left:0;padding-left:0}}
.side-stories article{padding-bottom:14px;border-bottom:1px solid var(--line)}.side-stories article:last-child{border:0}
.side-stories h3{font:700 18px/1.3 var(--serif);margin:6px 0 2px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-bottom:30px}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.grid{grid-template-columns:1fr}}
.card{background:var(--soft);border-radius:4px;padding:16px 16px 18px;display:flex;flex-direction:column;gap:6px;border-top:3px solid var(--line)}
.card h3,.card h2{font:700 18px/1.3 var(--serif);margin:4px 0}
.card p{margin:0;color:var(--mute);font-size:14px;line-height:1.55}
.card .meta{display:flex;justify-content:space-between;align-items:center;gap:8px}
.rows article{display:grid;grid-template-columns:110px 1fr;gap:16px;padding:16px 0;border-bottom:1px solid var(--line)}
@media(max-width:560px){.rows article{grid-template-columns:1fr;gap:6px}}
.rows .d{font:12px/1.5 var(--sans);color:var(--mute)}.rows .d b{display:block;font:800 26px/1 var(--serif);color:var(--ink)}
.rows h2{font:700 21px/1.3 var(--serif);margin:2px 0 4px}.rows p{margin:0;color:var(--mute);font-size:15px}
aside .box{background:var(--soft);padding:16px 18px;margin-bottom:22px;border-radius:4px;border-top:3px solid var(--acc)}
aside h3{margin:0 0 10px;font:800 13px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.08em}
aside ul{list-style:none;margin:0;padding:0;font-size:14px}aside li{padding:7px 0;border-top:1px solid var(--line)}aside li:first-child{border-top:0;padding-top:0}
aside ol{margin:0;padding:0;list-style:none;counter-reset:n}aside ol li{counter-increment:n;display:flex;gap:12px;padding:8px 0;border-top:1px solid var(--line)}aside ol li:first-child{border-top:0;padding-top:0}
aside ol li:before{content:counter(n);font:800 22px/1 var(--serif);color:var(--acc);min-width:22px}
aside .cnt{float:right;color:var(--mute);font-size:12px}
.cloud a{display:inline-block;font-size:12px;background:var(--bg);border:1px solid var(--line);padding:2px 8px;border-radius:12px;margin:0 4px 6px 0;color:var(--mute)}.cloud a:hover{border-color:var(--acc);color:var(--acc)}
.crumb{font:12px/1.4 var(--sans);color:var(--mute);margin-bottom:12px}.crumb a{color:var(--mute)}
.post h1{font:800 36px/1.15 var(--serif);margin:8px 0 10px;letter-spacing:-.3px}
@media(max-width:560px){.post h1{font-size:28px}.mast .logo{font-size:32px}}
.post .pmeta{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-bottom:18px;font:13px/1.4 var(--sans);color:var(--mute)}
.post .lead{font:italic 20px/1.5 var(--serif);color:var(--ink);margin:0 0 16px}
.post .body{font:17px/1.75 var(--serif)}
.post .body p{margin:0 0 1.15em}.post .body h2{font:800 22px/1.3 var(--serif);margin:1.5em 0 .5em;padding-left:12px;border-left:4px solid var(--acc)}
.post .body a{color:var(--acc);text-decoration:underline;text-underline-offset:2px}
.post .body blockquote{margin:1em 0;padding:4px 18px;border-left:3px solid var(--acc);color:var(--mute);font-style:italic}
.post .body table{border-collapse:collapse;width:100%;font:15px/1.5 var(--sans);margin:1em 0}.post .body td,.post .body th{border:1px solid var(--line);padding:6px 10px;text-align:left}
.tags{margin:22px 0 12px;font:13px/2 var(--sans)}.tags b{color:var(--mute);margin-right:6px}.tags a{display:inline-block;background:var(--soft);padding:0 10px;margin:0 6px 4px 0;border-radius:12px;color:var(--mute)}
.share{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 20px;font:13px/1 var(--sans)}.share a{border:1px solid var(--line);padding:8px 12px;border-radius:3px;color:var(--mute)}.share a:hover{border-color:var(--acc);color:var(--acc)}
.note{background:var(--soft);padding:12px 16px;font:13px/1.5 var(--sans);color:var(--mute);border-radius:4px;margin-top:8px}
.related{margin-top:30px}
.pn{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px;font:14px/1.4 var(--sans)}.pn a{background:var(--soft);padding:12px 14px;border-radius:4px;display:block}.pn small{display:block;color:var(--mute);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}.pn .r{text-align:right}
@media(max-width:560px){.pn{grid-template-columns:1fr}}
.pager{display:flex;justify-content:space-between;align-items:center;padding:18px 0;font:14px/1.4 var(--sans)}.pager a{border:1px solid var(--line);padding:8px 14px;border-radius:3px}
h1.sec{font:800 30px/1.2 var(--serif);margin:0 0 4px}.sec-desc{color:var(--mute);margin:0 0 18px;font-size:15px}
footer{background:var(--ink);color:#c9ced4;margin-top:20px;padding:34px 0 26px;font:13px/1.7 var(--sans)}
@media(prefers-color-scheme:dark){footer{background:#0b0d10}}
footer a{color:#e8eaed}footer .fcols{display:grid;grid-template-columns:2fr 1fr 1fr;gap:28px;margin-bottom:22px}
@media(max-width:700px){footer .fcols{grid-template-columns:1fr}}
footer h4{margin:0 0 8px;font:800 12px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.1em;color:#fff}
footer ul{list-style:none;margin:0;padding:0}footer .logo{font:800 26px/1 var(--serif);color:#fff;display:inline-block;margin-bottom:8px}
footer .bot{border-top:1px solid rgba(255,255,255,.12);padding-top:14px;font-size:12px;color:#9aa3ad}
.pic{display:block;overflow:hidden;border-radius:3px;background:var(--soft)}.pic img{display:block;width:100%;height:auto;aspect-ratio:800/420;object-fit:cover;transition:transform .3s}.pic:hover img{transform:scale(1.03)}
.card{padding:0 0 16px}.card .pic{border-radius:4px 4px 0 0;margin-bottom:4px}.card .meta,.card h3,.card h2,.card p{padding:0 14px}
.lead-story .pic{margin-bottom:12px}
.side-stories article{display:grid;grid-template-columns:150px 1fr;gap:12px;align-items:start}.side-stories .pic{margin:0}
.rows article{grid-template-columns:220px 1fr}@media(max-width:560px){.rows article{grid-template-columns:1fr}}
.rows .meta{display:flex;gap:10px;align-items:center;margin-bottom:4px}
.hero-img{margin:0 0 20px}.hero-img figcaption{font:12px/1.4 var(--sans);color:var(--mute);margin-top:6px}.hero-img figcaption a{color:var(--mute)}.hero-img img{width:100%;height:auto;border-radius:4px;display:block}
.related .card .pic{margin-bottom:4px}
.arch{columns:3;column-gap:24px;font:15px/1.9 var(--sans)}@media(max-width:700px){.arch{columns:2}}
.arch ul{list-style:none;margin:0 0 12px;padding:0;break-inside:avoid}.arch b{display:block;font-size:13px;text-transform:uppercase;color:var(--mute)}
"""

MENU = [("/", "Anasayfa"), ("/haber-kategorisi/manset/", "Manşet"), ("/haber-kategorisi/yargi/", "Yargı"),
        ("/haber-kategorisi/yargi/yargitay/", "Yargıtay"), ("/haber-kategorisi/yargi/anayasa-mahkemesi/", "AYM"),
        ("/haber-kategorisi/yargi/danistay/", "Danıştay"),
        ("/haber-kategorisi/siyaset/", "Siyaset"), ("/haber-kategorisi/barolar/", "Barolar"),
        ("/haber-kategorisi/universiteler/", "Üniversiteler"), ("/haber-kategorisi/teknoloji/", "Teknoloji"),
        ("/haber-kategorisi/basindan/", "Basından"), ("/haber-kategorisi/diger/", "Diğer"), ("/arsiv/", "Arşiv")]
GUNLER = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]

def topcat(p):
    k = p["catkeys"][0]
    for c in p["catkeys"]:
        if c != "manset": k = c; break
    return k
def kicker(p):
    k = topcat(p); root = CATS[k][1] or k
    return f'<a class="kicker k-{root}" href="/haber-kategorisi/{k}/">{e(CATS[k][0])}</a>'
def rtime(p): return max(1, round(p["words"] / 200))

def sidebar():
    latest = "".join(f'<li><a href="{p["url"]}">{e(p["title"])}</a><br><time datetime="{p["date"].isoformat()}">{trdate(p["date"])}</time></li>' for p in POSTS[:6])
    yargi = [p for p in POSTS if "yargi" in p["catkeys"] or any(CATS[c][1] == "yargi" for c in p["catkeys"])][:5]
    yargi_html = "".join(f'<li><a href="{p["url"]}">{e(p["title"])}</a></li>' for p in yargi)
    cats = "".join(f'<li><a href="/haber-kategorisi/{k}/">{e(v[0])}</a><span class="cnt">{cat_count[k]}</span></li>'
                   for k, v in CATS.items() if v[1] is None and cat_count[k])
    tagc = {}
    for p in POSTS:
        for t, s_ in zip(p["tags"], p["tagslugs"]): tagc[s_] = (t, tagc.get(s_, ("", 0))[1] + 1)
    top = sorted(tagc.items(), key=lambda x: -x[1][1])[:24]
    cloud = "".join(f'<a href="/haber-etiketi/{s_}/">{e(t)}</a>' for s_, (t, n) in top)
    months = {}
    for p in POSTS: months[(p["date"].year, p["date"].month)] = months.get((p["date"].year, p["date"].month), 0) + 1
    arch = "".join(f'<li><a href="/{y}/{m:02d}/">{AYLAR[m-1]} {y}</a><span class="cnt">{n}</span></li>'
                   for (y, m), n in sorted(months.items(), reverse=True)[:8])
    return f"""<aside>
<div class="box"><h3>Son haberler</h3><ul>{latest}</ul></div>
<div class="box"><h3>Yargı kararları</h3><ol>{yargi_html}</ol></div>
<div class="box"><h3>Kategoriler</h3><ul>{cats}</ul></div>
<div class="box"><h3>Konular</h3><div class="cloud">{cloud}</div></div>
<div class="box"><h3>Arşiv</h3><ul>{arch}</ul><p style="margin:10px 0 0;font-size:13px"><a href="/arsiv/">Tüm arşiv →</a></p></div>
</aside>"""

ORG_LD = {"@context": "https://schema.org", "@type": "NewsMediaOrganization", "name": NAME, "url": SITE + "/",
          "logo": {"@type": "ImageObject", "url": SITE + "/favicon.svg"}, "foundingDate": "2010",
          "sameAs": [], "publishingPrinciples": SITE + "/kunye/", "correctionsPolicy": SITE + "/kunye/"}

def page(title, desc, url, main, ld=None, noindex=False, canonical=None, ogtype="website", crumbs=None, img=None):
    nav = "".join(f'<li><a href="{u}"{" class=on" if u == url else ""}>{t}</a></li>' for u, t in MENU)
    lds = []
    if ld: lds.append(ld)
    if crumbs:
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]})
    ldjson = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
    can = canonical or (SITE + url)
    full_title = f"{title} | {NAME}" if url != "/" else f"{NAME} | Hukuk, Yargı, Yargıtay, Danıştay ve Mevzuat Haberleri"
    today = datetime.date.today()
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{e(can)}">
<meta name="theme-color" content="#9b1c1c">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(can)}">
<meta property="og:locale" content="tr_TR">
<meta property="og:image" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta property="og:image:width" content="800">
<meta property="og:image:height" content="420">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<link rel="alternate" type="application/rss+xml" title="{NAME} RSS" href="/feed/index.xml">
<link rel="sitemap" type="application/xml" href="/sitemap.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{CSS}</style>
{ldjson}
</head>
<body>
<a class="skip" href="#icerik">İçeriğe geç</a>
<header>
<div class="wrap"><div class="topbar"><span>{today.day} {AYLAR[today.month-1]} {today.year}, {GUNLER[today.weekday()]}</span><span class="links"><a href="/kunye/">Künye</a><a href="/iletisim/">İletişim</a><a href="/feed/index.xml">RSS</a></span></div>
<div class="mast"><a class="logo" href="/" aria-label="{NAME} anasayfa">Hukuki <span>Haberler</span></a><small>{TAGLINE}</small></div></div>
<nav class="main" aria-label="Kategoriler"><ul>{nav}</ul></nav>
</header>
<div class="wrap"><div class="cols">
<main id="icerik">{main}</main>
{sidebar()}
</div></div>
<footer><div class="wrap">
<div class="fcols">
<div><span class="logo">Hukuki Haberler</span><p style="margin:0;max-width:420px">2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi. Yüksek mahkeme kararları, Adalet Bakanlığı duyuruları, barolar ve hukuk fakültelerinden haberler.</p></div>
<div><h4>Bölümler</h4><ul><li><a href="/haber-kategorisi/manset/">Manşet</a></li><li><a href="/haber-kategorisi/yargi/">Yargı</a></li><li><a href="/haber-kategorisi/yargi/yargitay/">Yargıtay</a></li><li><a href="/haber-kategorisi/yargi/anayasa-mahkemesi/">Anayasa Mahkemesi</a></li><li><a href="/haber-kategorisi/yargi/danistay/">Danıştay</a></li><li><a href="/haber-kategorisi/basindan/">Basından</a></li></ul></div>
<div><h4>Site</h4><ul><li><a href="/hakkinda/">Hakkında</a></li><li><a href="/kunye/">Künye</a></li><li><a href="/iletisim/">İletişim</a></li><li><a href="/gizlilik-politikasi/">Gizlilik</a></li><li><a href="/arsiv/">Arşiv</a></li><li><a href="/sitemap.xml">Site haritası</a></li></ul></div>
</div>
<div class="bot">© 2010–{today.year} {NAME}. Sitedeki yazılar genel bilgilendirme amaçlıdır; hukuki görüş niteliği taşımaz. Haber metinleri, yayımlandıkları tarihteki mevzuat ve gelişmelere dayanır.</div>
</div></footer>
</body>
</html>"""

def pic(p, lazy=True, w=800, h=420):
    return f'<a class="pic" href="{p["url"]}"><img src="{p["img"]}" alt="{e(p["title"])}" width="{w}" height="{h}"{" loading=lazy decoding=async" if lazy else " fetchpriority=high"}></a>'
def credit_html(p):
    c = p.get("credit")
    if not c: return ""
    return f'<figcaption>Fotoğraf: {e(c["artist"])} / <a href="{e(c["page"])}" rel="nofollow noopener" target="_blank">Wikimedia Commons</a>, {e(c["lic"])}</figcaption>'
def card(p, h="h3"):
    return f"""<article class="card">{pic(p)}<div class="meta">{kicker(p)}<time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></div>
<{h}><a href="{p['url']}">{e(p['title'])}</a></{h}><p>{e(p['desc'])}</p></article>"""

def row_item(p):
    return f"""<article>{pic(p)}
<div><div class="meta">{kicker(p)}<time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></div><h2><a href="{p['url']}">{e(p['title'])}</a></h2><p>{e(p['desc'])}</p></div></article>"""

def listing(title, desc, base, items, crumb="", intro="", crumbs=None):
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
        if base == "/" and i == 0:
            main = head + homepage(chunk)
        else:
            main = head + '<div class="rows">' + "".join(row_item(p) for p in chunk) + "</div>"
        write(url, page(ttl, desc, url, main + pager, noindex=(i > 0), crumbs=crumbs if i == 0 else None,
                        ld=(ORG_LD if (base == "/" and i == 0) else None)))

def homepage(chunk):
    lead, side, rest = chunk[0], chunk[1:4], chunk[4:]
    hero = f"""<section class="hero" aria-label="Öne çıkan haberler">
<article class="lead-story">{pic(lead, lazy=False)}{kicker(lead)}<h2><a href="{lead['url']}">{e(lead['title'])}</a></h2><p>{e(lead['desc'])}</p><time datetime="{lead['date'].isoformat()}">{trdate(lead['date'])}</time></article>
<div class="side-stories">{"".join(f'<article>{pic(p)}<div>{kicker(p)}<h3><a href="{p["url"]}">{e(p["title"])}</a></h3><time datetime="{p["date"].isoformat()}">{trdate(p["date"])}</time></div></article>' for p in side)}</div>
</section>"""
    grid = f'<h2 class="sec-h">Son haberler</h2><div class="grid">{"".join(card(p) for p in rest)}</div>'
    secs = ""
    for k, label in (("yargi", "Yargı"), ("basindan", "Basından"), ("diger", "Ekonomi ve Gündem")):
        items = [p for p in POSTS if (k in p["catkeys"] or any(CATS[c][1] == k for c in p["catkeys"])) and p not in chunk][:3]
        if items:
            secs += f'<h2 class="sec-h"><a href="/haber-kategorisi/{k}/">{label}</a></h2><div class="grid">{"".join(card(p) for p in items)}</div>'
    return hero + grid + secs

# ---------------------------------------------------------------- sayaçlar
cat_count = {k: 0 for k in CATS}
for p in POSTS:
    for k in p["catkeys"]:
        cat_count[k] += 1
        par = CATS[k][1]
        if par and par not in p["catkeys"]: cat_count[par] += 1

# ---------------------------------------------------------------- çıktı
REDIRECTS = []

# anasayfa + /page/N
listing(NAME, "Hukuk, yargı, baro ve mevzuat haberleri. Yargıtay, Danıştay ve Anayasa Mahkemesi kararları, Adalet Bakanlığı duyuruları ve hukuk gündeminden seçmeler.", "/", POSTS)

# yazılar
def related(p):
    cands = [q for q in POSTS if q is not p and (set(q["catkeys"]) & set(p["catkeys"]) or set(q["tagslugs"]) & set(p["tagslugs"]))]
    cands.sort(key=lambda q: (len(set(q["tagslugs"]) & set(p["tagslugs"])), -abs((q["date"] - p["date"]).days)), reverse=True)
    return cands[:3]
for idx, p in enumerate(POSTS):
    cats_html = " · ".join(f'<a href="/haber-kategorisi/{k}/">{e(CATS[k][0])}</a>' for k in p["catkeys"])
    tags_html = "".join(f'<a href="/haber-etiketi/{s}/" rel="tag">{e(t)}</a>' for t, s in zip(p["tags"], p["tagslugs"]))
    rel = related(p)
    rel_html = (f'<section class="related"><h2 class="sec-h">İlgili haberler</h2><div class="grid">{"".join(card(q) for q in rel)}</div></section>') if rel else ""
    newer = POSTS[idx-1] if idx > 0 else None
    older = POSTS[idx+1] if idx < len(POSTS)-1 else None
    pn = '<nav class="pn" aria-label="Önceki / sonraki haber">' + \
         (f'<a href="{older["url"]}"><small>Önceki haber</small>{e(older["title"])}</a>' if older else "<span></span>") + \
         (f'<a class="r" href="{newer["url"]}"><small>Sonraki haber</small>{e(newer["title"])}</a>' if newer else "<span></span>") + "</nav>"
    full = SITE + p["url"]
    share = f'<div class="share"><a href="https://twitter.com/intent/tweet?url={urllib.parse.quote(full)}&text={urllib.parse.quote(p["title"])}" rel="noopener nofollow" target="_blank">X\'te paylaş</a><a href="https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(full)}" rel="noopener nofollow" target="_blank">Facebook</a><a href="https://wa.me/?text={urllib.parse.quote(p["title"] + " " + full)}" rel="noopener nofollow" target="_blank">WhatsApp</a><a href="mailto:?subject={urllib.parse.quote(p["title"])}&body={urllib.parse.quote(full)}">E-posta</a></div>'
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p["title"], "description": p["desc"],
          "datePublished": p["date"].isoformat(), "dateModified": p["date"].isoformat(),
          "mainEntityOfPage": {"@type": "WebPage", "@id": full}, "url": full, "inLanguage": "tr-TR",
          "articleSection": p["cats"][0], "keywords": ", ".join(p["tags"]), "wordCount": p["words"],
          "isAccessibleForFree": True, "image": {"@type": "ImageObject", "url": SITE + p["img"], "width": 800, "height": 420},
          "author": {"@type": "Organization", "name": NAME, "url": SITE + "/kunye/"},
          "publisher": {"@type": "Organization", "name": NAME, "url": SITE, "logo": {"@type": "ImageObject", "url": SITE + "/favicon.svg"}}}
    k0 = topcat(p)
    crumbs = [("/", "Anasayfa")] + ([(f"/haber-kategorisi/{CATS[k0][1]}/", CATS[CATS[k0][1]][0])] if CATS[k0][1] else []) + [(f"/haber-kategorisi/{k0}/", CATS[k0][0]), (p["url"], p["title"])]
    crumb = " › ".join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs[:-1])
    main = f"""<article class="post"><div class="crumb">{crumb}</div>
{kicker(p)}
<h1>{e(p['title'])}</h1>
<div class="pmeta"><span><time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></span><span>{cats_html}</span><span>{rtime(p)} dk okuma</span><span>Hukuki Haberler</span></div>
<figure class="hero-img"><img src="{p['img']}" alt="{e(p['title'])}" width="800" height="420" fetchpriority="high">{credit_html(p)}</figure>
<div class="body">{p['body']}</div>
<div class="tags"><b>Etiketler:</b>{tags_html}</div>
{share}
<div class="note">Bu haber {trdate(p['date'])} tarihinde yayımlanmıştır. Metindeki süreler, oranlar ve düzenlemeler o tarihteki mevzuatı yansıtır; sonradan değişmiş olabilir.</div>
{pn}{rel_html}</article>"""
    write(p["file"], page(p["title"], p["desc"], p["url"], main, ld=ld, ogtype="article", crumbs=crumbs, img=p["img"]))

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
