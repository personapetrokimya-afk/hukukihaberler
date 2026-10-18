# -*- coding: utf-8 -*-
"""hukukihaberler.com — statik site üretici.
Eski WordPress adres yapısı korunur; her eski adres 200 ya da 301 döner."""
import os, re, json, shutil, html, datetime, unicodedata, urllib.parse
from content1 import POSTS as P1
from content2 import POSTS as P2
from content3 import POSTS as P3
from content4 import POSTS as P4
from content5 import POSTS as P5
from content6 import POSTS as P6

SITE = "https://hukukihaberler.com"
NAME = "Hukuki Haberler"
# Gerçek kişi yazarlar. Bir yazıya "yazar" alanı YALNIZCA o kişi yazıyı kendisi yazdıysa ya da
# metni bizzat inceleyip onayladıysa eklenir; zamanlanmış görevler bu alanı asla doldurmaz.
YAZARLAR = {
    "yagmur-tahtasiz": {"ad": "Av. Yağmur Tahtasız", "kisi": "Yağmur Tahtasız", "url": "/av-yagmur-tahtasiz/",
                        "foto": "https://yagmurtahtasiz.com/assets/images/av-yagmur-tahtasiz.jpg",
                        "bio": "İzmir Barosu'na kayıtlı avukat. Anadolu Üniversitesi Hukuk Fakültesi mezunu; 2022'den bu yana aile ve boşanma hukuku ağırlıklı olarak avukatlık yapıyor. Hukuki Haberler'in hukuk danışmanlığını ve içerik denetimini yürütüyor."},
}
TAGLINE = "Hukuk, yargı ve mevzuat gündemi"
OUT = os.path.join(os.path.dirname(__file__), "site")
TARGET = "https://yagmurtahtasiz.com"   # bağlamsal link hedefi (makale başına en fazla 1-2)
PER_PAGE = 10

POSTS = P1 + P2 + P3 + P4 + P5 + P6

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

LOGO_SVG = open(os.path.join(os.path.dirname(__file__), "static", "logo-mark.svg"), encoding="utf-8").read().replace("<svg ", '<svg class="lmark" width="44" height="44" aria-hidden="true" focusable="false" ', 1)
# ---------------------------------------------------------------- yardımcılar
TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
def slugify(s):
    s = s.translate(TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s
def e(s): return html.escape(s, quote=True)
AYLAR = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
def kaynak_goster(p, full):
    """haberi kullanan siteler için hazır alıntı + bağlantı metni"""
    kod = f'<a href="{full}">{p["title"]}</a> (Hukuki Haberler, {trdate(p["date"])})'
    return ('<div class="cite"><b>Bu haberi kaynak gösterin</b>'
            '<p>Haberden alıntı yapıyorsanız aşağıdaki bağlantıyı kullanabilirsiniz.</p>'
            f'<textarea readonly rows="3" aria-label="Kaynak bağlantısı">{e(kod)}</textarea>'
            '<button type="button" onclick="var t=this.previousElementSibling;t.select();'
            '(navigator.clipboard?navigator.clipboard.writeText(t.value):Promise.reject()).catch(function(){document.execCommand(\'copy\')});'
            'this.textContent=\'Kopyalandı\'">Kopyala</button></div>')

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
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
from tema import CSS, ico, CATNAV, DRAWER, SITE_LINKS, JS, SEARCH_JS

def topcat(p):
    k = p["catkeys"][0]
    for c in p["catkeys"]:
        if c != "manset": k = c; break
    return k
def renk(k):
    """kategori anahtarından renk sınıfı"""
    if k in ("yargi/yargitay", "yargi/danistay", "yargi/anayasa-mahkemesi", "yargi/aihm"): return "yuksek"
    if k in ("yargi", "yargi/adalet-bakanligi", "manset"): return "yargi"
    if k == "siyaset": return "siyaset"
    if k == "diger/ekonomi": return "ekonomi"
    if k == "teknoloji": return "teknoloji"
    return "diger"
def kicker(p):
    k = topcat(p)
    return f'<a class="kicker k-{renk(k)}" href="/haber-kategorisi/{k}/">{e(CATS[k][0])}</a>'
def rtime(p): return max(1, round(p["words"] / 200))
def kisa(d): return f"{d.day} {AYLAR[d.month-1][:3]}"
def thumb(p): return p["img"].replace("/gorsel/", "/gorsel/m/")
def byline(p):
    y = YAZARLAR.get(p.get("yazar"))
    if not y: return '<a href="/yayin-ilkeleri/">Hukuki Haberler Editörlüğü</a>'
    return f'<a class="byl" href="{y["url"]}" rel="author"><img src="{y["foto"]}" alt="" width="28" height="28" loading="lazy">{e(y["ad"])}</a>'
def yazar_kutu(p):
    y = YAZARLAR.get(p.get("yazar"))
    if not y: return ""
    digr = [q for q in POSTS if q.get("yazar") == p["yazar"] and q["slug"] != p["slug"]][:5]
    li = "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a></li>' for q in digr)
    return (f'<aside class="ykutu" aria-label="Yazar"><img src="{y["foto"]}" alt="{e(y["ad"])}" width="88" height="88" loading="lazy">'
            f'<div><small>Yazar</small><a class="yad" href="{y["url"]}" rel="author">{e(y["ad"])}</a><p>{e(y["bio"])}</p>'
            + (f'<b>Yazarın diğer yazıları</b><ul>{li}</ul>' if li else "") + f'<a class="yall" href="{y["url"]}">Tüm yazıları →</a></div></aside>')
def mini(p):
    if not p.get("img"): return ""
    return f'<a class="mini" href="{p["url"]}" tabindex="-1" aria-hidden="true"><img src="{thumb(p)}" alt="" width="96" height="64" loading="lazy" decoding="async"></a>'
def save_btn(p):
    return (f'<button type="button" class="save" data-u="{p["url"]}" data-t="{e(p["title"])}" data-i="{thumb(p)}" data-k="{e(CATS[topcat(p)][0])}" '
            f'data-d="{trdate(p["date"])}" aria-pressed="false" aria-label="Bu cihazda kaydet">{ico("bookmark", 22)}</button>')
def upd(u):
    d = datetime.date.fromisoformat(u[:10]); return trdate(d) + (", " + u[11:16] if "T" in u else "")
def iso(p): return p["date"].isoformat() + (f'T{p["saat"]}:00+03:00' if p.get("saat") else "")
def when(p): return trdate(p["date"]) + (f", {p['saat']}" if p.get("saat") else "")
def meta(p, date=True, cat=False):
    s = f'<span>{ico("clock", 16)}<time datetime="{iso(p)}">{when(p)}</time></span>'
    if cat: s += f'<span class="mc">{e(CATS[topcat(p)][0])}</span>'
    return f'<div class="meta">{s}</div>'

def sidebar():
    latest = "".join(f'<li class="m">{mini(p)}<div><time datetime="{iso(p)}">{kisa(p["date"])}{(" · " + p["saat"]) if p.get("saat") else ""}</time><a href="{p["url"]}">{e(p["title"])}</a></div></li>' for p in POSTS[:6])
    cats = "".join(f'<li class="c"><a href="/haber-kategorisi/{k}/">{e(v[0])}</a><span>{cat_count[k]}</span></li>'
                   for k, v in CATS.items() if v[1] is None and cat_count[k])
    return f"""<aside aria-label="Yan sütun">
<div class="box"><h3>Son gelişmeler</h3><ul>{latest}</ul></div>
<div class="box"><h3>Bölümler</h3><ul>{cats}<li class="c"><a href="/arsiv/">Arşiv</a><span>{len(POSTS)}</span></li></ul></div>
</aside>"""

ORG_LD = {"@context": "https://schema.org", "@type": "NewsMediaOrganization", "name": NAME, "url": SITE + "/",
          "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}, "foundingDate": "2010",
          "sameAs": [], "masthead": SITE + "/kunye/", "publishingPrinciples": SITE + "/yayin-ilkeleri/", "correctionsPolicy": SITE + "/yayin-ilkeleri/#duzeltme", "email": "iletisim@hukukihaberler.com",
          "contactPoint": {"@type": "ContactPoint", "contactType": "editorial", "email": "iletisim@hukukihaberler.com", "url": SITE + "/iletisim/", "availableLanguage": "tr"}}

def _preload(main):
    m = re.search(r'<img src="([^"]+)"(?: srcset="([^"]+)")?(?: sizes="([^"]+)")?[^>]*fetchpriority=.?high', main)
    if not m: return ""
    ss = f' imagesrcset="{m.group(2)}" imagesizes="{m.group(3)}"' if m.group(2) else ""
    return f'\n<link rel="preload" as="image" href="{m.group(1)}"{ss} fetchpriority="high">'

# Google "tercih edilen kaynak" listesi siteyi tanıyınca True yapılır (google.com/preferences/source?q=hukukihaberler.com sonuç verince)
GPREF_AKTIF = False
GPREF_ALT = "Yeni haberleri Google'da ve akış okuyucunuzda kaçırmayın" if GPREF_AKTIF else "Yeni haberler akış okuyucunuzda"
GPREF_URL = "https://www.google.com/preferences/source?q=hukukihaberler.com"
STAR_SVG = '<svg viewBox="0 0 24 24" width="{s}" height="{s}" aria-hidden="true"><path fill="currentColor" d="M12 2.6l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.4l-5.8 3.1 1.1-6.5L2.6 9.4l6.5-.9z"/></svg>'
def gpref_btn(cls="gpref", label="Google'da tercih et", s=18):
    if not GPREF_AKTIF: return ""
    return f'<a class="{cls}" href="{GPREF_URL}" target="_blank" rel="noopener">{STAR_SVG.format(s=s)}{label}</a>'
def gpref_kutu():
    if not GPREF_AKTIF: return ""
    return f'<aside class="gpbox"><div class="gpt"><b>Hukuki Haberler\'i Google\'da öne çıkarın</b><span>Bizi tercih ettiğiniz kaynak olarak eklediğinizde haberlerimiz Google aramalarındaki "Öne Çıkan Haberler" bölümünde size daha sık gösterilir.</span></div>{gpref_btn("gpref gpbig", "Tercih edilen kaynak olarak ekle", 20)}</aside>'

def page(title, desc, url, main, ld=None, noindex=False, canonical=None, ogtype="website", crumbs=None, img=None, active=None, side=True, extra=""):
    act = active or url
    def on(u): return act == u or (u != "/" and act.startswith(u))
    catnav = "".join(f'<li><a href="{u}"{" class=on aria-current=page" if on(u) else ""}>{t}</a></li>' for u, t in CATNAV)
    drawer = "".join(f'<li><a href="{u}">{ico(i, 20)}<span>{t}</span></a></li>' for u, t, i in DRAWER)
    drawer2 = "".join(f'<li><a href="{u}"><span>{t}</span></a></li>' for u, t in SITE_LINKS)
    ticker = "".join(f'<li><a href="{p["url"]}">{e(p["title"])}</a></li>' for p in POSTS[:3])
    lds = []
    if ld: lds.extend(ld if isinstance(ld, list) else [ld])
    if crumbs:
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]})
    ldjson = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
    can = canonical or (SITE + url)
    full_title = f"{title} | {NAME}" if url != "/" else f"{NAME} | Hukuk, Yargı, Yargıtay, Danıştay ve Mevzuat Haberleri"
    today = datetime.date.today()
    srch = lambda i: f'<form class="hsearch" action="/arama/" method="get" role="search"><label class="sr" for="{i}">Sitede ara</label>{ico("search", 20)}<input id="{i}" name="q" type="search" placeholder="Haber, karar, mevzuat veya konu ara…" autocomplete="off"></form>'
    body = (f'<div class="hwrap"><div class="cols"><main id="icerik">{main}</main>{sidebar()}</div></div>' if side
            else f'<main id="icerik" class="hwrap">{main}</main>')
    bn = lambda u, t, i: f'<a href="{u}"{" class=on aria-current=page" if url == u else ""}>{ico(i, 22)}<span>{t}</span></a>'
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-84SWYM8295"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-84SWYM8295');</script>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{e(can)}">{_preload(main)}
<meta name="theme-color" content="#2D4054">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(can)}">
<meta property="og:locale" content="tr_TR">
<meta property="og:image" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<link rel="alternate" type="application/rss+xml" title="{NAME} RSS" href="/feed/index.xml">
<link rel="sitemap" type="application/xml" href="/sitemap.xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}</style>
{ldjson}
</head>
<body>
<a class="skip" href="#icerik">İçeriğe geç</a>
<header class="site">
<div class="hwrap htop">
<a class="brand" href="/" aria-label="{NAME} anasayfa">{ico("scale", 44)}<span><span class="bn">Hukuki Haberler</span><span class="bt">Hukuk, yargı ve mevzuat gündemi</span></span></a>
{srch("q")}
<div class="hright"><div class="hbtns">{gpref_btn()}<a class="rssbtn" href="/feed/index.xml">{ico("rss", 18)}RSS ile takip et</a></div><small>{GPREF_ALT}</small></div>
<button type="button" class="ibtn sbtn" aria-label="Sitede ara" aria-expanded="false" aria-controls="msearch">{ico("search", 22)}</button>
<button type="button" class="ibtn mbtn" aria-label="Menüyü aç" aria-expanded="false" aria-controls="drawer">{ico("menu", 24)}</button>
</div>
<div id="msearch" class="msearch" hidden><div class="hwrap">{srch("q2")}</div></div>
<nav class="cats" aria-label="Bölümler"><div class="hwrap"><ul>{catnav}</ul></div></nav>
<div class="ticker"><div class="hwrap"><span class="tk"><i></i>Güncel</span><ul>{ticker}</ul><a class="tmore" href="/arsiv/" aria-label="Tüm haberler">{ico("chev", 20)}</a><span class="tdate">{today.day} {AYLAR[today.month-1]} {today.year}, {GUNLER[today.weekday()]}</span></div></div>
</header>
<div id="drawer" class="drawer" hidden><nav class="dp" aria-label="Tüm bölümler"><div class="dh">Bölümler<button type="button" class="ibtn dclose" style="display:inline-flex" aria-label="Menüyü kapat">{ico("close", 24)}</button></div><ul>{drawer}</ul><div class="dsub">Site</div><ul>{drawer2}</ul>{"<div class=\"dgp\">" if GPREF_AKTIF else ""}{gpref_btn("gpref gpbig", "Google'da tercih edilen kaynak olarak ekle", 20)}{"</div>" if GPREF_AKTIF else ""}</nav></div>
{body}
<footer class="site"><div class="hwrap">
<div class="fcols">
<div><div class="fbrand">{ico("scale", 30)}Hukuki Haberler</div><p style="margin:0;max-width:440px">2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi. Yüksek mahkeme kararları, mevzuat değişiklikleri ve gündemin hukuki boyutu.</p></div>
<div><h4>Bölümler</h4><ul>{"".join(f'<li><a href="{u}">{t}</a></li>' for u, t in CATNAV[:7])}</ul></div>
<div><h4>Site</h4><ul>{"".join(f'<li><a href="{u}">{t}</a></li>' for u, t in SITE_LINKS)}<li><a href="/arsiv/">Arşiv</a></li><li><a href="/feed/index.xml">RSS</a></li></ul></div>
</div>
<div class="bot">© 2010–{today.year} {NAME}. Sitedeki yazılar genel bilgilendirme amaçlıdır; hukuki görüş niteliği taşımaz.</div>
</div></footer>
<nav class="bnav" aria-label="Alt menü">{bn("/", "Ana Sayfa", "home")}{bn("/kesfet/", "Keşfet", "compass")}{bn("/kaydedilenler/", "Kaydedilen", "bookmark")}<button type="button" aria-controls="drawer" aria-expanded="false">{ico("menu", 22)}<span>Menü</span></button></nav>
{JS}{extra}
</body>
</html>"""

def srcset(p): return f'srcset="{thumb(p)} 480w, {p["img"].replace("/gorsel/", "/gorsel/l/")} 800w, {p["img"]} 1200w"'
def pic(p, lazy=True, sizes="(max-width:767px) 112px, 300px"):
    return (f'<a class="pic" data-k="{renk(topcat(p))}" href="{p["url"]}" tabindex="-1" aria-hidden="true"><img src="{p["img"]}" {srcset(p)} sizes="{sizes}" alt="" width="1200" height="630"'
            f'{" loading=lazy decoding=async" if lazy else " fetchpriority=high"}></a>')
def credit_html(p):
    c = p.get("credit")
    if not c: return ""
    if c.get("kaynak") and c["kaynak"] != "Wikimedia Commons":
        lic = f', {e(c["lic"])}' if str(c.get("lic", "")).startswith("CC") else ""
        return f'<figcaption>Fotoğraf: {e(c["artist"])} / <a href="{e(c["page"])}" rel="nofollow noopener" target="_blank">{e(c["kaynak"])}</a>{lic}</figcaption>'
    return f'<figcaption>Fotoğraf: {e(c["artist"])} / <a href="{e(c["page"])}" rel="nofollow noopener" target="_blank">Wikimedia Commons</a>, {e(c["lic"])}</figcaption>'
def feat_card(p):
    return (f'<article>{pic(p, sizes="(max-width:767px) 112px, (max-width:1023px) 50vw, 420px")}<div class="ftxt">{kicker(p)}'
            f'<h3><a href="{p["url"]}">{e(p["title"])}</a></h3><p>{e(p["desc"])}</p>{meta(p)}</div></article>')
def row(p, h="h3"):
    return (f'<li class="row"><div class="rt">{kicker(p)}<{h}><a href="{p["url"]}">{e(p["title"])}</a></{h}><p>{e(p["desc"])}</p>{meta(p)}</div>'
            f'{pic(p, sizes="(max-width:767px) 112px, 160px")}</li>')
card = feat_card

def listing(title, desc, base, items, crumb="", intro="", crumbs=None, noindex=False):
    n = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
    for i in range(n):
        chunk = items[i*PER_PAGE:(i+1)*PER_PAGE]
        url = base if i == 0 else f"{base}page/{i+1}/"
        prev = (base if i == 1 else f"{base}page/{i}/") if i > 0 else None
        nxt = f"{base}page/{i+2}/" if i < n-1 else None
        pager = ('<nav class="pager" aria-label="Sayfalar">' + (f'<a href="{prev}">← Daha yeni</a>' if prev else '<span></span>') +
                 f'<span>Sayfa {i+1} / {n}</span>' + (f'<a href="{nxt}">Daha eski →</a>' if nxt else '<span></span>') + '</nav>') if n > 1 else ""
        ttl = title if i == 0 else f"{title} – Sayfa {i+1}"
        if base == "/" and i == 0:
            write(url, page(ttl, desc, url, homepage(chunk), noindex=False, ld=ORG_LD, side=False))
            continue
        head = (f'<div class="crumb">{crumb}</div>' if crumb else "") + f'<h1 class="sec">{e(title)}</h1><p class="sec-desc">{e(desc)}</p>' + intro
        main = head + '<ul class="rows one">' + "".join(row(p, "h2") for p in chunk) + "</ul>" + pager
        write(url, page(ttl, desc, url, main, noindex=(i > 0 or noindex), crumbs=crumbs if i == 0 else None))

def homepage(chunk):
    cur = [p for p in POSTS if p["date"].year >= 2026]
    photo = [p for p in cur if p.get("imgkind") in ("photo", "orig")]
    lead = (photo or cur or POSTS)[0]
    rest = [p for p in cur if p is not lead]
    side, rest = rest[:3], rest[3:]
    featp = [p for p in rest if p.get("imgkind") in ("photo", "orig")][:3]
    if len(featp) < 3: featp = rest[:3]
    rest = [p for p in rest if p not in featp]
    analiz = [p for p in cur if p.get("tur") == "Analiz"][:2]
    more = [p for p in rest if p not in analiz][:8]
    shown = {id(p) for p in [lead] + side + featp + analiz + more}
    sidel = "".join(f'<li><a class="ov" data-k="{renk(topcat(p))}" href="{p["url"]}">{f'<img src="{thumb(p)}" alt="" width="480" height="270" loading="lazy" decoding="async">' if p.get("img") else ""}<span class="ovt"><span class="ovm"><time datetime="{iso(p)}">{p["saat"] if p.get("saat") and p["date"] == lead["date"] else kisa(p["date"])}</time><span class="ovk k-{renk(topcat(p))}">{e(CATS[topcat(p)][0])}</span></span><span class="ovh">{e(p["title"])}</span></span></a></li>' for p in side)
    hero = f"""<h1 class="sr">{NAME}: hukuk, yargı ve mevzuat haberleri</h1>
<section class="hero" aria-label="Manşet">
<div class="k">{kicker(lead)}</div>
<h2 class="t{" lt" if len(lead["title"]) > 60 else ""}"><a href="{lead['url']}">{e(lead['title'])}</a></h2>
<p class="d">{e(lead['desc'])}</p>
<div class="m">{meta(lead, cat=True).replace('<div class="meta">', '<div class="meta" style="flex:1">')}{save_btn(lead)}</div>
<figure class="img">{pic(lead, lazy=False, sizes="(max-width:767px) 100vw, (max-width:1023px) 50vw, 600px")}{credit_html(lead)}{('<div class="hoz"><b>Öne çıkanlar</b><ul>' + "".join(f"<li>{e(x)}</li>" for x in lead.get("ozet", [])[:3]) + '</ul><a href="' + lead["url"] + '">Haberin devamı →</a></div>') if lead.get("ozet") else ""}</figure>
<div class="side"><h2>Son gelişmeler</h2><ol>{sidel}</ol><a class="all" href="/arsiv/">Tüm son gelişmeler →</a></div>
</section>"""
    feat = (f'<section class="blk"><h2 class="sec-h"><span class="dh">Öne çıkan haberler</span><span class="mh">Son Haberler</span>'
            f'<a class="all" href="/arsiv/">Tümü</a></h2><div class="feat">{"".join(feat_card(p) for p in featp)}</div></section>')
    gun = ""
    if analiz:
        a0 = analiz[0]
        gun = f'<a class="gunluk" href="{a0["url"]}">{ico("doc", 30)}<div><b>Günün analizi</b><span>{e(a0["title"])}</span></div>{ico("chev", 22, "chev")}</a>'
    duo = ""
    if analiz:
        an = "".join(f'<article class="an"><span class="ai">{ico("pen", 22)}</span><div><h3><a href="{p["url"]}">{e(p["title"])}</a></h3><p>{e(p["desc"])}</p>'
                     f'<div class="meta"><span><b>Hukuki Haberler Editörlüğü</b></span><span>{when(p)}</span></div></div></article>' for p in analiz)
        tc = {}
        for p in cur:
            for t, s_ in zip(p["tags"], p["tagslugs"]): tc[s_] = (t, tc.get(s_, ("", 0))[1] + 1)
        top = [x for x in sorted(tc.items(), key=lambda x: (-x[1][1], x[1][0])) if x[1][1] >= 2][:5]
        topics = "".join(f'<li><a href="/haber-etiketi/{s_}/">{e(t)}</a><small>{n} haber</small></li>' for s_, (t, n) in top)
        duo = (f'<section class="blk duo tint"><div><h2 class="sec-h">Analiz</h2><div class="an-list">{an}</div></div>'
               + (f'<aside aria-label="Gündemdeki konular"><h2 class="sec-h">Gündemdeki konular</h2><ol class="topics">{topics}</ol></aside>' if topics else "") + '</section>')
    son = f'<section class="blk"><h2 class="sec-h">Diğer haberler<a class="all" href="/arsiv/">Tümü</a></h2><ul class="rows">{"".join(row(p) for p in more)}</ul></section>' if more else ""
    secs = ""
    for k, label in (("yargi", "Yargı"), ("siyaset", "Siyaset"), ("diger", "Ekonomi ve Gündem"), ("teknoloji", "Teknoloji")):
        items = [p for p in cur if (k in p["catkeys"] or any(CATS[c][1] == k for c in p["catkeys"])) and id(p) not in shown][:3]
        if len(items) >= 2:
            shown |= {id(p) for p in items}
            secs += f'<section class="blk{" tint" if secs.count("<section") % 2 else ""}"><h2 class="sec-h">{label}<a class="all" href="/haber-kategorisi/{k}/">Tümü</a></h2><div class="feat">{"".join(feat_card(p) for p in items)}</div></section>'
    return hero + feat + gun + duo + son + secs

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

# ---------------------------------------------------------------- iç bağlantı, örnek kutusu, anket
INTERNAL = [
 ("Sermaye Piyasası Kurulu'nun", "fon-skandalinda-hangi-suclar-var-usulsuz-kazanc-saglayani-hangi-ceza-bekliyor"),
 ("ceza soruşturmalarında", "fon-skandalinda-hangi-suclar-var-usulsuz-kazanc-saglayani-hangi-ceza-bekliyor"),  # (metindeki ifade, hedef slug) — yalnızca hedef haber kaynak haberden eski/aynı tarihliyse bağlanır
 ("12. Yargı Paketi", "12-yargi-paketi-resmi-gazetede-belirsiz-alacak-davasi-kaldirildi"),
 ("7589 sayılı Kanun", "12-yargi-paketi-resmi-gazetede-belirsiz-alacak-davasi-kaldirildi"),
 ("belirsiz alacak davası", "12-yargi-paketi-resmi-gazetede-belirsiz-alacak-davasi-kaldirildi"),
 ("13. Yargı Paketi", "13-yargi-paketi-ekimde-mecliste-suresiz-nafaka-ve-bosanma-davalari"),
 ("\"süresiz olarak\" ibaresini iptal", "aym-suresiz-nafaka-kararinin-gerekcesi-resmi-gazetede-yayimlandi"),
 ("süresiz nafaka", "aym-suresiz-nafaka-kararinin-gerekcesi-resmi-gazetede-yayimlandi"),
 ("Türk Kızılay Kanun Teklifi", "turk-kizilay-kanun-teklifi-genel-kurulun-ilk-gundem-maddesi"),
 ("yatırım fonlarındaki tasfiye", "fon-tasfiyesi-kanun-teklifi-mecliste-yatirimciya-1-milyon-lira"),
 ("e-Devlet üzerinden kimlik doğrulaması", "sosyal-medyada-15-yas-siniri-yonetmeligi-resmi-gazetede"),
 ("Mesafeli Sözleşmeler Yönetmeliği", "danistay-mesafeli-sozlesmeler-yonetmeligindeki-uc-hukmu-iptal-etti"),
 ("aydınlatılmış onam", "yargitay-aydinlatilmis-onam-ispat-yuku-hekim-ve-hastanede"),
 ("rücu davası", "yargitay-erken-dogan-bebekte-lazarus-fenomeni-hekime-kusur-yuklenemez"),
 ("işe iade davası", "alti-ay-kidemi-dolmadan-isten-cikarilan-bankaci-aymden-gerekceli-karar-hakki-ihlali"),
 ("pasaport tedbiri", "pasaportu-iptal-edilen-kamu-gorevlisi-doktora-yapamadi-aymden-ihlal-karari"),
 ("ısrarlı takip", "yargitay-uyarilmasina-ragmen-bir-gunde-45-mesaj-atan-sanik-cezalandirildi"),
 ("Gezi Parkı davası", "aymden-tayfun-kahramana-ikinci-ihlal-karari-yeniden-yargilama"),
 ("Akkuyu", "nukleere-hukuk-dar-geliyor"),
 ("175. maddesindeki", "aym-suresiz-nafaka-kararinin-gerekcesi-resmi-gazetede-yayimlandi"),
 ("175. maddesinin", "aym-suresiz-nafaka-kararinin-gerekcesi-resmi-gazetede-yayimlandi"),
 ("Kızılay Kanun Teklifi", "turk-kizilay-kanun-teklifi-genel-kurulun-ilk-gundem-maddesi"),
 ("Meclis araştırması", "fon-tasfiyesi-kanun-teklifi-mecliste-yatirimciya-1-milyon-lira"),
 ("hükmün açıklanmasının geri bırakılması", "12-yargi-paketi-resmi-gazetede-belirsiz-alacak-davasi-kaldirildi"),
 ("Hükmün açıklanmasının geri bırakılması", "12-yargi-paketi-resmi-gazetede-belirsiz-alacak-davasi-kaldirildi"),
 ("sosyal medya kullanıcılarının", "sosyal-medyada-15-yas-siniri-yonetmeligi-resmi-gazetede"),
 ("cayma hakkı", "danistay-mesafeli-sozlesmeler-yonetmeligindeki-uc-hukmu-iptal-etti"),
 ("Adli Tıp Kurumu", "yargitay-erken-dogan-bebekte-lazarus-fenomeni-hekime-kusur-yuklenemez"),
 ("tıben öngörülemeyen", "yargitay-erken-dogan-bebekte-lazarus-fenomeni-hekime-kusur-yuklenemez"),
 ("bireysel başvuru", "pasaportu-iptal-edilen-kamu-gorevlisi-doktora-yapamadi-aymden-ihlal-karari"),
 ("Anayasa'nın 153. maddesi", "aymden-tayfun-kahramana-ikinci-ihlal-karari-yeniden-yargilama"),
 ("haklı nedenle", "yargitay-calisma-sartlari-agirlastirilan-banka-calisanina-kidem-tazminati"),
 ("Siyasi Partiler Kanunu", "aym-26-siyasi-partinin-hesaplarini-kabul-etmedi-suc-duyurusu"),
 ("Van Valiliği", "aym-van-valiliginin-eylem-yasaklarinda-toplanti-hurriyeti-ihlali"),
 ("toplantı ve gösteri", "aym-van-valiliginin-eylem-yasaklarinda-toplanti-hurriyeti-ihlali"),
 ("ayıplı mal", "yargitay-boya-kusurlu-sifir-otomobil-ayipsiz-misliyle-degistirilecek"),
 ("e-duruşma", "12-yargi-paketinin-kalan-hukumleri-31-ekimde-yururlukte-e-durusma-vesayet"),
 ("adli tatil", "yargida-toplu-izin-yarin-basliyor"),
 ("kayyum", "kayyum-nedir-saadet-partisini-simdi-kim-yonetecek"),
 ("Booking", "dijital-konaklama-platformlarina-izin-zorunlulugu-kanun-teklifi"),
 ("kapalı alanlarda tütün", "hastane-bahcesi-ve-okul-cevresinde-sigara-yasagi-geliyor"),
 ("taksitle satış", "taksitli-alisveriste-sureleri-ticaret-bakanligi-belirleyecek-tuketici-ne-bilmeli"),
 ("veri ihlali", "ytu-fidye-yazilimi-saldirisi-verisi-etkilenen-ogrenci-ve-personelin-haklari"),
 ("seçimlerin yenilenmesi", "2028-secimi-icin-mart-nisan-takvimi-anayasa-hangi-yolu-gosteriyor-360-oy"),
 ("kamu ihalelerine", "kamu-ihalelerinde-vergi-ve-sgk-borcu-siniri-50-bin-liraya-cikti"),
 ("ortak şarj", "sarj-adaptoru-ve-usb-c-kablolarina-yeni-kurallar-2028-tuketici-ve-uretici"),
 ("kamu görevlisine hakaret", "durusmadaki-savunma-sozleri-suc-olur-mu-imamoglu-sorusturmasi-tck-128"),
]
BY_SLUG = {p["slug"]: p for p in POSTS}
def autolink(p, limit=3):
    body, n, used = p["body"], 0, set()
    for phrase, slug in INTERNAL:
        if n >= limit: break
        q = BY_SLUG.get(slug)
        if not q or q is p or slug in used: continue
        if q["date"] > p["date"] and p["date"].year < 2026: continue   # eski arşiv yeni haberlere bağlanmaz
        if q["url"] in body: continue
        # yalnızca <p> içindeki, mevcut bir <a> içinde olmayan ilk geçiş
        for m in re.finditer(re.escape(phrase), body):
            pre = body[:m.start()]
            if pre.rfind("<a ") > pre.rfind("</a>"): continue
            if pre.rfind("<h2") > pre.rfind("</h2>"): continue
            body = body[:m.start()] + f'<a href="{q["url"]}">{m.group(0)}</a>' + body[m.end():]
            n += 1; used.add(slug); break
    return body

def ozet_html(p):
    o = p.get("ozet")
    if not o: return ""
    return '<aside class="ozet"><b>Öne çıkanlar</b><ul>' + "".join(f"<li>{e(x)}</li>" for x in o) + "</ul></aside>\n"

def related_scored(p, n=2, skip=()):
    if p["date"].year >= 2026: pool = [q for q in POSTS if q["date"].year >= 2026]
    else: pool = [q for q in POSTS if q["date"] <= p["date"]]
    tg, ct = set(p["tagslugs"]), set(p["catkeys"]) - {"manset"}
    sc = []
    for q in pool:
        if q is p or q["slug"] in skip: continue
        s_ = 3 * len(tg & set(q["tagslugs"])) + len(ct & set(q["catkeys"])) - abs((p["date"] - q["date"]).days) / 400
        sc.append((s_, q["slug"], q))
    sc.sort(key=lambda x: (-x[0], x[1]))
    return [q for _, _, q in sc[:n]]

def okumadan_html(q):
    return (f'<aside class="okuma"><span>Okumadan geçme</span><a href="{q["url"]}">'
            f'<img src="{thumb(q)}" alt="" width="160" height="84" loading="lazy">'
            f'<b>{e(q["title"])}</b></a></aside>\n')

def with_okumadan(p, body):
    """2. paragraftan sonra ve (varsa) son ara başlıktan önce 'Okumadan geçme' kutusu"""
    linked = set(re.findall(r'href="/([^"#?]+)"', body))
    rel = [q for q in related_scored(p, 4) if q["slug"] not in linked][:2]
    if not rel: return body
    ends = [m.end() for m in re.finditer(r"</p>", body)]
    if len(ends) < 3: return body
    out = body[:ends[1]] + "\n" + okumadan_html(rel[0]) + body[ends[1]:]
    if len(rel) > 1:
        h2s = [m.start() for m in re.finditer(r"<h2", out)]
        if len(h2s) >= 3:
            i = h2s[-1]
            out = out[:i] + okumadan_html(rel[1]) + out[i:]
    return out

def kaynak_html(p):
    k = p.get("kaynaklar")
    if not k: return ""
    items = " · ".join(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a>' for t, u in k)
    return f'<p class="kaynak"><b>Kaynak:</b> {items}</p>'

def sss_html(p):
    s = p.get("sss")
    if not s: return ""
    items = "".join(f'<div class="sq"><h3>{e(q)}</h3><p>{e(a)}</p></div>' for q, a in s[:4])
    return f'<section class="sss" aria-labelledby="sss-h"><h2 id="sss-h">Merak edilenler</h2>{items}</section>'

def sss_ld(p, full):
    s = p.get("sss")
    if not s: return None
    return {"@context": "https://schema.org", "@type": "FAQPage", "url": full + "#sss-h", "inLanguage": "tr-TR",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in s[:4]]}

def ornek_html(p):
    o = p.get("ornek")
    if not o: return ""
    items = "".join(f"<p>{x}</p>" for x in o)
    return f'<aside class="ornek" aria-label="Örnek"><b>Örnekle açıklayalım</b>{items}</aside>'

def anket_html(p):
    a = p.get("anket")
    if not a: return ""
    opts = "".join(f'<label><input type="radio" name="o" value="{i}"> <span>{e(t)}</span></label>' for i, t in enumerate(a["secenekler"]))
    return f"""<section class="anket" data-id="{p['slug']}" data-n="{len(a['secenekler'])}"><h2>Okur anketi</h2><p class="q">{e(a['soru'])}</p>
<form>{opts}<button type="submit">Oy ver</button></form><div class="sonuc" hidden></div><p class="an">Anket bilimsel değildir; okur eğilimini gösterir. Kişisel veri toplanmaz.</p></section>"""

ANKET_JS = """<script>
document.querySelectorAll('.anket').forEach(function(box){
 var id=box.dataset.id,n=+box.dataset.n,form=box.querySelector('form'),res=box.querySelector('.sonuc');
 var labels=[].map.call(box.querySelectorAll('label span'),function(s){return s.textContent});
 function show(c){var t=c.reduce(function(a,b){return a+b},0)||1;res.innerHTML=labels.map(function(l,i){var pc=Math.round(c[i]*100/t);return '<div class=r><span>'+l+'</span><b>%'+pc+'</b><i style="width:'+pc+'%"></i></div>'}).join('')+'<small>'+(t===1&&!c.some(Boolean)?0:t)+' oy</small>';res.hidden=false;form.hidden=true}
 var voted=null;try{voted=localStorage.getItem('anket:'+id)}catch(e){}
 if(voted){fetch('/api/anket?id='+id).then(function(r){return r.json()}).then(function(j){show(j.c||new Array(n).fill(0))}).catch(function(){})}
 form.addEventListener('submit',function(ev){ev.preventDefault();var v=form.querySelector('input:checked');if(!v)return;
  fetch('/api/anket',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:id,o:+v.value,n:n})}).then(function(r){return r.json()}).then(function(j){try{localStorage.setItem('anket:'+id,'1')}catch(e){}show(j.c)}).catch(function(){res.textContent='Oy kaydedilemedi, lütfen daha sonra deneyin.';res.hidden=false})});
});
</script>"""

# yazılar
def related(p):
    cands = [q for q in POSTS if q is not p and (set(q["catkeys"]) & set(p["catkeys"]) or set(q["tagslugs"]) & set(p["tagslugs"]))]
    cands.sort(key=lambda q: (len(set(q["tagslugs"]) & set(p["tagslugs"])), -abs((q["date"] - p["date"]).days)), reverse=True)
    return cands[:3]
for idx, p in enumerate(POSTS):
    cats_html = " · ".join(f'<a href="/haber-kategorisi/{k}/">{e(CATS[k][0])}</a>' for k in p["catkeys"])
    tags_html = "".join(f'<a href="/haber-etiketi/{s}/" rel="tag">{e(t)}</a>' for t, s in zip(p["tags"], p["tagslugs"]))
    rel = related(p)
    rel_html = (f'<section class="related"><h2 class="sec-h">İlgili haberler</h2><ul class="rows one">{"".join(row(q) for q in rel)}</ul></section>') if rel else ""
    newer = POSTS[idx-1] if idx > 0 else None
    older = POSTS[idx+1] if idx < len(POSTS)-1 else None
    pn = '<nav class="pn" aria-label="Önceki / sonraki haber">' + \
         (f'<a href="{older["url"]}"><small>Önceki haber</small>{e(older["title"])}</a>' if older else "<span></span>") + \
         (f'<a class="r" href="{newer["url"]}"><small>Sonraki haber</small>{e(newer["title"])}</a>' if newer else "<span></span>") + "</nav>"
    full = SITE + p["url"]
    share = f'<div class="share"><a href="https://twitter.com/intent/tweet?url={urllib.parse.quote(full)}&text={urllib.parse.quote(p["title"])}" rel="noopener nofollow" target="_blank">X\'te paylaş</a><a href="https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(full)}" rel="noopener nofollow" target="_blank">Facebook</a><a href="https://wa.me/?text={urllib.parse.quote(p["title"] + " " + full)}" rel="noopener nofollow" target="_blank">WhatsApp</a><a href="mailto:?subject={urllib.parse.quote(p["title"])}&body={urllib.parse.quote(full)}">E-posta</a></div>'
    tur = p.get("tur", "Haber")
    ld = {"@context": "https://schema.org", "@type": "AnalysisNewsArticle" if tur == "Analiz" else "NewsArticle", "headline": p["title"], "description": p["desc"],
          "datePublished": iso(p), "dateModified": (p["updated"] + (":00+03:00" if "T" in p["updated"] else "")) if p.get("updated") else iso(p),
          "mainEntityOfPage": {"@type": "WebPage", "@id": full}, "url": full, "inLanguage": "tr-TR",
          "articleSection": p["cats"][0], "keywords": ", ".join(p["tags"]), "wordCount": p["words"],
          "isAccessibleForFree": True, "image": {"@type": "ImageObject", "url": SITE + p["img"], "width": 1200, "height": 630},
          "author": ({"@type": "Person", "name": YAZARLAR[p["yazar"]]["kisi"], "honorificPrefix": "Av.", "url": SITE + YAZARLAR[p["yazar"]]["url"], "@id": SITE + YAZARLAR[p["yazar"]]["url"] + "#kisi"}
                     if p.get("yazar") in YAZARLAR else {"@type": "Organization", "name": NAME + " Editörlüğü", "url": SITE + "/yayin-ilkeleri/"}),
          "publisher": {"@type": "Organization", "name": NAME, "url": SITE, "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}}}
    k0 = topcat(p)
    crumbs = [("/", "Anasayfa")] + ([(f"/haber-kategorisi/{CATS[k0][1]}/", CATS[CATS[k0][1]][0])] if CATS[k0][1] else []) + [(f"/haber-kategorisi/{k0}/", CATS[k0][0]), (p["url"], p["title"])]
    crumb = " › ".join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs[:-1])
    main = f"""<article class="post"><div class="crumb">{crumb}</div>
{kicker(p)}
<h1>{e(p['title'])}</h1>
<div class="meta pmeta"><span class="tur">{e(tur)}</span><span>{byline(p)}</span><span>{ico("clock", 16)}<time datetime="{iso(p)}">{when(p)}</time></span>{('<span>Güncellendi: ' + upd(p["updated"]) + '</span>') if p.get("updated") else ""}{save_btn(p)}</div>
<figure class="hero-img"><div class="pic"><img src="{p['img']}" {srcset(p)} sizes="(max-width:767px) 100vw, 760px" alt="{e(p['title'])}" width="1200" height="630" fetchpriority="high"></div>{credit_html(p)}</figure>
{ozet_html(p)}<div class="body">{re.sub(r'(<table[\s\S]*?</table>)', r'<div class="tscroll">\1</div>', with_okumadan(p, autolink(p)))}</div>
{ornek_html(p)}{sss_html(p)}{kaynak_html(p)}{anket_html(p)}
<div class="tags"><b>Etiketler:</b>{tags_html}</div>
{yazar_kutu(p)}{gpref_kutu()}{share}{kaynak_goster(p, full)}
<div class="note">Bu {"analiz" if tur == "Analiz" else "haber"} {trdate(p['date'])} tarihinde yayımlanmıştır. Metindeki süreler, oranlar ve düzenlemeler o tarihteki mevzuatı yansıtır; sonradan değişmiş olabilir. İçerik genel bilgilendirme amaçlıdır, hukuki danışmanlık yerine geçmez. Hata bildirimi için <a href="/iletisim/">iletişim</a>.</div>
{pn}{rel_html}</article>""" + (ANKET_JS if p.get("anket") else "")
    write(p["file"], page(p["title"], p["desc"], p["url"], main, ld=[x for x in (ld, sss_ld(p, full)) if x], ogtype="article", crumbs=crumbs, img=p["img"], active=f"/haber-kategorisi/{k0}/"))

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

# analiz, mevzuat, keşfet, kaydedilenler, arama
_an = [p for p in POSTS if p.get("tur") == "Analiz"]
if _an: listing("Analiz", "Gündemdeki hukuki gelişmelerin mevzuat ve içtihat üzerinden açıklandığı analizler.", "/analiz/", _an, crumb='<a href="/">Anasayfa</a> › Analiz')
_MZ = ("resmî gazete", "resmi gazete", "kanun", "yönetmelik", "tebliğ", "yargı paketi", "genelge", "kararname")
def _mz(p):
    h = (p["title"] + " " + " ".join(p["tags"])).replace("İ", "i").replace("I", "ı").lower()
    return any(k in h for k in _MZ)
_mv = [p for p in POSTS if _mz(p)]
listing("Mevzuat", "Kanunlar, kanun teklifleri, yönetmelikler, Resmî Gazete ve yargı paketlerine ilişkin haberler.", "/mevzuat/", _mv, crumb='<a href="/">Anasayfa</a> › Mevzuat')
_tc = {}
for p in POSTS:
    if p["date"].year >= 2026:
        for t, s_ in zip(p["tags"], p["tagslugs"]): _tc[s_] = (t, _tc.get(s_, ("", 0))[1] + 1)
_chips_c = "".join(f'<li><a href="{u}">{t}</a></li>' for u, t in [("/haber-kategorisi/manset/", "Gündem"), ("/analiz/", "Analiz"), ("/mevzuat/", "Mevzuat")]) + \
           "".join(f'<li><a href="/haber-kategorisi/{k}/">{e(v[0])}<small>{cat_count[k]}</small></a></li>' for k, v in CATS.items() if cat_count[k] and k != "manset")
_chips_t = "".join(f'<li><a href="/haber-etiketi/{s_}/">{e(t)}<small>{n}</small></a></li>' for s_, (t, n) in sorted(_tc.items(), key=lambda x: (-x[1][1], x[1][0]))[:30])
write("/kesfet/", page("Keşfet", "Hukuki Haberler bölümleri, güncel konu başlıkları ve arşiv.", "/kesfet/",
      f'<h1 class="sec">Keşfet</h1><p class="sec-desc">Bölümler, güncel konular ve arşiv.</p>'
      f'<form class="searchbox" action="/arama/" method="get" role="search"><label class="sr" for="kq">Sitede ara</label><input id="kq" name="q" type="search" placeholder="Haber, karar, mevzuat veya konu ara…"><button type="submit">Ara</button></form>'
      f'<h2 class="sec-h">Bölümler</h2><ul class="chips">{_chips_c}</ul><h2 class="sec-h">Güncel konular</h2><ul class="chips">{_chips_t}</ul>'
      f'<h2 class="sec-h">Arşiv</h2><p><a href="/arsiv/" style="color:var(--gold);text-decoration:underline">2010\'dan bugüne tüm haberler →</a></p>'))
write("/kaydedilenler/", page("Kaydedilenler", "Bu cihazda kaydettiğiniz haberler.", "/kaydedilenler/",
      '<h1 class="sec">Kaydedilenler</h1><p class="sec-desc">Kaydettiğiniz haberler yalnızca bu cihazdaki tarayıcıda saklanır; hesap veya sunucu kaydı tutulmaz.</p><div id="kayitlar"><noscript><p class="empty">Bu özellik için tarayıcınızda JavaScript açık olmalıdır.</p></noscript></div>', noindex=True))
with open(os.path.join(OUT, "arama.json"), "w", encoding="utf-8") as f:
    json.dump([{"t": p["title"], "u": p["url"], "d": p["desc"], "g": " ".join(p["tags"]), "k": CATS[topcat(p)][0], "z": trdate(p["date"]), "i": thumb(p)} for p in POSTS], f, ensure_ascii=False, separators=(",", ":"))
write("/arama/", page("Arama", "Hukuki Haberler içinde haber, karar ve mevzuat araması.", "/arama/",
      '<h1 class="sec">Arama</h1><form id="aramaform" class="searchbox" action="/arama/" method="get" role="search"><label class="sr" for="aq">Aranacak kelime</label><input id="aq" name="q" type="search" placeholder="Haber, karar, mevzuat veya konu ara…"><button type="submit">Ara</button></form><div id="sonuc" aria-live="polite"><noscript><p class="empty">Arama için tarayıcınızda JavaScript açık olmalıdır.</p></noscript></div>',
      noindex=True, extra=SEARCH_JS))

# etiketler
ETIKET_ALT_SINIR = 3   # bundan az haberi olan etiket sayfası dizine girmez, sitemap'e eklenmez
tag_posts = {}
for p in POSTS:
    for t, s in zip(p["tags"], p["tagslugs"]):
        tag_posts.setdefault(s, {"name": t, "posts": []})["posts"].append(p)
for s, d in tag_posts.items():
    items = sorted(d["posts"], key=lambda p: p["date"], reverse=True)
    crumb = f'<a href="/">Anasayfa</a> › Etiket'
    listing(f"{d['name']}", f"“{d['name']}” etiketli haberler.", f"/haber-etiketi/{s}/", items, crumb=crumb,
            noindex=len(items) < ETIKET_ALT_SINIR)   # tek-iki haberli etiket sayfaları zayıf içerik sayılır

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
      f'<article class="post static"><h1>Hakkında</h1><div class="body">{HAKKINDA}</div></article>'))
ILETISIM = """<p class="lead">Hukuki Haberler bağımsız bir yayın sitesidir; bireysel hukuki danışmanlık talebi kabul etmez.</p>
<h2>E-posta</h2>
<p>Haber ihbarı, düzeltme, tekzip ve yayınla ilgili her türlü bildirim için: <b><a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a></b>. Bildirimler yazı işleri tarafından okunur ve kural olarak üç iş günü içinde yanıtlanır.</p>
<h2>Düzeltme ve güncelleme</h2>
<p>Bir haberde eskimiş ya da hatalı bir bilgi fark ettiyseniz, haberin adresini ve doğru bilginin kaynağını belirten bir not iletebilirsiniz; doğrulanan düzeltmeler habere işlenir ve güncelleme tarihi gösterilir. Her haberin sonunda konuyla ilgili resmî kaynaklara bağlantı bulunur; güncel ve bağlayıcı bilgi için her zaman bu kaynaklar esas alınmalıdır.</p>
<h2>Hukuki danışmanlık</h2>
<p>Site, somut dosyalar hakkında görüş vermez. Bir uyuşmazlık için bulunduğunuz ildeki bir avukata ya da baroların adli yardım bürolarına başvurabilirsiniz. Baro iletişim bilgileri <a href="https://www.barobirlik.org.tr/" rel="noopener" target="_blank">Türkiye Barolar Birliği</a> sitesinde yer alır.</p>"""
write("/iletisim/", page("İletişim", "Hukuki Haberler iletişim: düzeltme bildirimi, kaynaklar ve hukuki danışmanlık için başvurulabilecek yerler.", "/iletisim/",
      f'<article class="post static"><h1>İletişim</h1><div class="body">{ILETISIM}</div></article>'))
GIZ = """<p class="lead">Bu site ziyaretçilerinden kişisel veri toplamaz.</p>
<p>Sitede üyelik, yorum ya da form bulunmaz; reklam veya takip amaçlı çerez kullanılmaz. Ziyaret sayıları, çerez kullanmayan ve bireysel ziyaretçiyi tanımlamayan Cloudflare Web Analytics ile toplu olarak ölçülür. Barındırma altyapısı, güvenlik ve performans amacıyla IP adresi ve istek zamanı gibi teknik kayıtları kısa süreli tutabilir; bu kayıtlar kimlik tespiti için kullanılmaz. Haberlerde yer alan dış bağlantılar (Resmî Gazete, mahkeme siteleri, basın kuruluşları) kendi gizlilik politikalarına tabidir.</p>"""
KUNYE = """<p class="lead">Hukuki Haberler, 2010 yılında yayına başlayan bağımsız bir hukuk haber sitesidir. Ticari bir kuruluşa, hukuk bürosuna ya da baroya bağlı değildir.</p>
<h2>Yayın ilkeleri</h2>
<p>Haberler; Resmî Gazete, yüksek mahkeme kararları, TBMM tutanakları, kamu kurumlarının açıklamaları ve ulusal basında yer alan gelişmeler esas alınarak hazırlanır. Her haberde kaynağı belli olmayan iddialara yer verilmez; karar metinleri yayımlandıkça haberler güncellenir ve güncelleme tarihi belirtilir. Kişilerin özel hayatına ilişkin bilgiler, haber değeri olan kamusal yönüyle sınırlı tutulur; adli dosyalarda taraf adları, kamuya açık karar metinlerinde geçtiği ölçüde kullanılır.</p>
<h2>Yazı işleri</h2>
<p>Haberler "Hukuki Haberler Editörlüğü" imzasıyla yayımlanır. Hukuk danışmanı ve içerik denetimi: <a href="/av-yagmur-tahtasiz/">Av. Yağmur Tahtasız</a>. Yayın ve editoryal süreçler <a href="/yayin-ilkeleri/">Yayın İlkeleri</a> sayfasında açıklanmıştır. Haberlerde yer alan görüşler, atıf yapılan kurum ve kişilere aittir; site bireysel hukuki danışmanlık vermez.</p>
<h2>Düzeltme ve tekzip</h2>
<p>Hatalı olduğu bildirilen bilgiler kaynağıyla birlikte doğrulandığında en geç üç iş günü içinde düzeltilir. Düzeltme talepleri <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine iletilebilir.</p>
<h2>İletişim</h2>
<p>E-posta: <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a></p>
<h2>Telif</h2>
<p>Sitedeki metinler kaynak gösterilmek ve bağlantı verilmek şartıyla alıntılanabilir; bütün hâlinde kopyalanamaz.</p>"""
write("/kunye/", page("Künye", "Hukuki Haberler künye: yayın ilkeleri, yazı işleri, düzeltme ve telif esasları.", "/kunye/",
      f'<article class="post static"><h1>Künye</h1><div class="body">{KUNYE}</div></article>'))
write("/gizlilik-politikasi/", page("Gizlilik Politikası", "Hukuki Haberler gizlilik politikası: çerez kullanılmaz, kişisel veri toplanmaz.", "/gizlilik-politikasi/",
      f'<article class="post static"><h1>Gizlilik Politikası</h1><div class="body">{GIZ}</div></article>', noindex=True))

YAYIN = """<p class="lead">Hukuki Haberler'in amacı, hukuk ve yargı gündemini hukukçu olmayan okurun da anlayabileceği açıklıkta, kaynağı gösterilmiş ve tarihli biçimde aktarmaktır.</p>
<h2>Kapsam ve hedef kitle</h2>
<p>Yüksek mahkeme kararları, mevzuat değişiklikleri, Resmî Gazete, TBMM'deki kanun teklifleri, adli süreçler ve gündemdeki olayların hukuki boyutu. Hedef kitlemiz hukukçular kadar, haklarını öğrenmek isteyen her okurdur.</p>
<h2>İçerik türleri</h2>
<p>Her yazının başında türü belirtilir. <b>Haber:</b> bir karar, düzenleme veya gelişmenin doğrulanmış bilgilerle aktarılması. <b>Analiz:</b> gündemdeki bir olayın mevzuat ve içtihat üzerinden açıklanması; analizlerde editoryal değerlendirme yer alır ve bu kısımlar olgulardan ayrı yazılır. Sitede sponsorlu içerik ve görüş yazısı yayımlanmamaktadır; yayımlanırsa açıkça etiketlenir.</p>
<h2>Kaynak ve doğrulama</h2>
<p>Mümkün olan her durumda birincil kaynağa dayanırız: mevzuat metni, Resmî Gazete, mahkeme kararı, kamu kurumu açıklaması. İkincil kaynak (basın kuruluşu, ajans) kullanıldığında haberin altında bağlantısıyla belirtilir. İddia iddia olarak; soruşturma, kovuşturma, mahkûmiyet ve kesinleşme kavramları birbirinden ayrılarak yazılır. Soruşturma aşamasındaki kişiler için masumiyet karinesi esastır. Çocukların ve hassas durumdaki kişilerin kimlikleri yayımlanmaz.</p>
<h2 id="duzeltme">Düzeltme, güncelleme ve tekzip</h2>
<p>Hatalı olduğu tespit edilen bilgi kaynağıyla doğrulandığında düzeltilir; ilk yayın tarihi korunur, güncelleme tarihi ve neyin değiştiği yazının içinde belirtilir. Tekzip talepleri 5187 sayılı Basın Kanunu çerçevesinde değerlendirilir. Bildirimler <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine gönderilebilir.</p>
<h2>Doğrulama</h2>
<p>Her metindeki tarih, sayı, madde numarası ve alıntı yayımlanmadan önce kaynağına bakılarak kontrol edilir; kaynağı doğrulanamayan bilgi yayımlanmaz.</p>
<h2 id="yontem">Çalışma yöntemi ve yazılım araçları</h2>
<p>Gündemi izlemek, resmî kaynaklardaki yeni duyuruları tespit etmek ve haber taslaklarını hazırlamak için yazılım araçlarından yararlanırız. Anlık gelişmelere ilişkin haberler editör onayıyla yayımlanır. Bu yolla hazırlanan tüm metinler kaynak, tarafsızlık ve doğrulama ilkelerimize göre denetlenir; dayanılan kaynak geri çekildiğinde ya da bir hata tespit edildiğinde düzeltme politikamız uygulanır.</p>
<h2>Hukuki içerik denetimi ve çıkar ilişkisi</h2>
<p>Sitenin hukuk danışmanlığını ve içerik denetimini <a href="/av-yagmur-tahtasiz/">Av. Yağmur Tahtasız</a> yürütür. Av. Tahtasız'ın avukatlık bürosuna ait <a href="https://yagmurtahtasiz.com/" rel="noopener" target="_blank">yagmurtahtasiz.com</a> sitesine, yalnızca konuyla doğrudan ilgili rehber içerikler için ve sınırlı sayıda bağlantı verilebilir. Bu bağlantılar haberlerin içeriğini veya yayın kararlarını etkilemez; sitede ücret karşılığı yayımlanmış içerik yoktur.</p>
<h2>Reklam, sponsorluk ve bağımsızlık</h2>
<p>Sitede şu an reklam ve sponsorlu içerik bulunmamaktadır. İleride reklam alınması hâlinde reklam alanları haber metninden görsel olarak ayrılacak ve "Reklam" ibaresi taşıyacaktır. Hiçbir kurum veya kişi, ödeme karşılığında bir haberin içeriğini belirleyemez. Yazılarda hukuki bilgiye kaynak olarak bağlantı verilen dış sitelerle ilişkiler bu sayfada açıklanır.</p>
<h2>Görseller</h2>
<p>Görseller lisansı uygun kaynaklardan (ör. Wikimedia Commons, Flickr, Pixabay) alınır; fotoğrafçı, kaynak ve lisans görselin altında bağlantısıyla belirtilir. Görsellerin sağ alt köşesinde site imzası yer alır.</p>"""
write("/yayin-ilkeleri/", page("Yayın İlkeleri", "Hukuki Haberler yayın ilkeleri: kaynak ve doğrulama, düzeltme politikası, hukuki içerik denetimi, reklam ve bağımsızlık.", "/yayin-ilkeleri/",
      f'<article class="post static"><h1>Yayın İlkeleri</h1><div class="body">{YAYIN}</div></article>'))

# hukuk danışmanı profil sayfası (gerçek kişi, doğrulanabilir bilgiler)
AV_URL = "/av-yagmur-tahtasiz/"
AV_FOTO = "https://yagmurtahtasiz.com/assets/images/av-yagmur-tahtasiz.jpg"
AV_LD = {"@context": "https://schema.org", "@type": "ProfilePage", "url": SITE + AV_URL, "name": "Av. Yağmur Tahtasız",
         "mainEntity": {"@type": "Person", "@id": SITE + AV_URL + "#kisi", "name": "Yağmur Tahtasız", "honorificPrefix": "Av.",
                        "jobTitle": "Avukat", "description": "İzmir Barosu'na kayıtlı avukat; Hukuki Haberler'in hukuk danışmanı ve içerik denetimi sorumlusu.",
                        "image": AV_FOTO, "url": SITE + AV_URL,
                        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Anadolu Üniversitesi Hukuk Fakültesi"},
                        "memberOf": {"@type": "Organization", "name": "İzmir Barosu", "url": "https://www.izmirbarosu.org.tr/"},
                        "worksFor": {"@type": "NewsMediaOrganization", "name": NAME, "url": SITE + "/"},
                        "knowsAbout": ["Aile hukuku", "Boşanma hukuku", "Ceza hukuku", "İcra ve iflas hukuku", "İdare hukuku"],
                        "sameAs": ["https://yagmurtahtasiz.com/", "https://yagmurtahtasiz.com/about.html", "https://www.linkedin.com/in/yagmurtahtasiz", "https://medium.com/@yagmurtahtasiz", "https://yagmurtahtasiz.substack.com", "https://yagmurtahtasiz.blogspot.com"]}}
_avp = [q for q in POSTS if q.get("yazar") == "yagmur-tahtasiz"]
AV_YAZILAR = ("<h2>Yazıları</h2><ul class=\"liste\">" + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a> <small>{trdate(q["date"])}</small></li>' for q in _avp) + "</ul>") if _avp else ""
AV = f"""<figure class="avfoto"><img src="{AV_FOTO}" alt="Av. Yağmur Tahtasız" width="240" height="240" loading="lazy" decoding="async"></figure>
<p class="lead">Av. Yağmur Tahtasız, İzmir Barosu'na kayıtlı avukattır ve Hukuki Haberler'in hukuk danışmanlığını ve içerik denetimini yürütür.</p>
<h2>Eğitim ve meslek</h2>
<ul class="liste">
<li><b>Eğitim:</b> Anadolu Üniversitesi Hukuk Fakültesi (2014-2021)</li>
<li><b>Avukatlık ruhsatı:</b> 2022</li>
<li><b>Baro:</b> İzmir Barosu</li>
<li><b>Çalışma alanı:</b> Ağırlıklı olarak aile ve boşanma hukuku; ceza, icra ve iflas ile idare hukuku dosyaları</li>
</ul>
<h2>Hukuki Haberler'deki görevi</h2>
<p>Sitede yayımlanan haber ve analizlerin hukuki çerçevesine ilişkin danışmanlık verir: mevzuat ve içtihat atıflarının, suç ve yaptırım tanımlarının ve usul bilgilerinin doğruluğuna ilişkin denetim ve düzeltme süreçlerinde görüş bildirir. Haberler "Hukuki Haberler Editörlüğü" imzasıyla yayımlanır; yayın ve düzeltme esasları <a href="/yayin-ilkeleri/">Yayın İlkeleri</a> sayfasında yer alır.</p>
<h2>Çıkar ilişkisi</h2>
<p>Av. Tahtasız'ın avukatlık bürosuna ait <a href="https://yagmurtahtasiz.com/" rel="noopener" target="_blank">yagmurtahtasiz.com</a> sitesine, yalnızca konuyla doğrudan ilgili rehber içerikler için ve sınırlı sayıda bağlantı verilebilir. Bu sitede yer alan içerikler hukuki danışmanlık niteliği taşımaz ve avukat-müvekkil ilişkisi kurmaz.</p>
{AV_YAZILAR}<h2>Bağlantılar</h2>
<ul class="liste">
<li><a href="https://yagmurtahtasiz.com/about.html" rel="noopener" target="_blank">yagmurtahtasiz.com</a></li>
<li><a href="https://www.linkedin.com/in/yagmurtahtasiz" rel="noopener" target="_blank">LinkedIn</a></li>
</ul>"""
write(AV_URL, page("Av. Yağmur Tahtasız", "Av. Yağmur Tahtasız: İzmir Barosu'na kayıtlı avukat, Hukuki Haberler hukuk danışmanı ve içerik denetimi sorumlusu.", AV_URL,
      f'<article class="post static"><h1>Av. Yağmur Tahtasız</h1><p class="sec-desc">Hukuk danışmanı ve içerik denetimi</p><div class="body">{AV}</div></article>',
      ld=AV_LD, ogtype="profile", crumbs=[("/", "Anasayfa"), ("/kunye/", "Künye"), (AV_URL, "Av. Yağmur Tahtasız")]))

# 404
write("/404.html", page("Sayfa bulunamadı", "Aradığınız sayfa bulunamadı.", "/404.html",
      '<article class="post static"><h1>Sayfa bulunamadı</h1><div class="body"><p>Aradığınız haber taşınmış ya da adresi değişmiş olabilir. <a href="/arsiv/">Arşiv</a> sayfasından tüm haberlere ulaşabilir ya da <a href="/">anasayfaya</a> dönebilirsiniz.</p></div></article>', noindex=True))

# RSS
def _rss(items, title, link):
    its = "".join(f"<item><title>{e(p['title'])}</title><link>{SITE}{p['url']}</link><guid isPermaLink=\"true\">{SITE}{p['url']}</guid><pubDate>{p['date'].strftime('%a, %d %b %Y ') + (p['saat'] + ':00' if p.get('saat') else '09:00:00') + ' +0300'}</pubDate><category>{e(p['catname'])}</category><description>{e(p['desc'])}</description><media:content url=\"{SITE}{p['img']}\" medium=\"image\" width=\"1200\" height=\"630\"/><content:encoded><![CDATA[<p><img src=\"{SITE}{p['img']}\" alt=\"\"></p>{p['body']}]]></content:encoded></item>" for p in items)
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">'
            f'<channel><title>{e(title)}</title><link>{SITE}{link}</link><atom:link rel="hub" href="https://pubsubhubbub.appspot.com/"/><atom:link rel="self" type="application/rss+xml" href="{SITE}{"/feed/index.xml" if link == "/" else "/feed/" + link.rstrip("/").split("/")[-1] + ".xml"}"/><description>{TAGLINE}</description><language>tr</language>'
            f'<image><url>{SITE}/icon-192.png</url><title>{e(title)}</title><link>{SITE}{link}</link></image>{its}</channel></rss>')
write("/feed/", _rss(POSTS[:20], NAME, "/"))
for _k in ("manset", "yargi", "siyaset", "diger", "teknoloji"):
    _it = [p for p in POSTS if _k in p["catkeys"] or any(CATS[c][1] == _k for c in p["catkeys"])][:20]
    with open(os.path.join(OUT, "feed", f"{_k}.xml"), "w", encoding="utf-8") as f: f.write(_rss(_it, f"{NAME} - {CATS[_k][0]}", f"/haber-kategorisi/{_k}/"))
os.rename(os.path.join(OUT, "feed", "index.html"), os.path.join(OUT, "feed", "index.xml"))
REDIRECTS.append(("/feed/", "/feed/index.xml")); REDIRECTS.append(("/feed", "/feed/index.xml"))
REDIRECTS.append(("/feed/atom/", "/feed/index.xml")); REDIRECTS.append(("/comments/feed/", "/feed/index.xml"))

# sitemap
urls = [("/", "weekly", "1.0")] + [(p["url"], "yearly", "0.8") for p in POSTS] + \
       [(f"/haber-kategorisi/{k}/", "monthly", "0.5") for k in CATS if cat_count[k]] + \
       [(f"/haber-etiketi/{s}/", "weekly", "0.3") for s in tag_posts if len(tag_posts[s]["posts"]) >= ETIKET_ALT_SINIR] + \
       [(f"/{y}/{m:02d}/", "yearly", "0.3") for (y, m) in months] + [("/arsiv/", "monthly", "0.4"), ("/hakkinda/", "yearly", "0.3"), ("/kunye/", "yearly", "0.3"), ("/av-yagmur-tahtasiz/", "yearly", "0.3"), ("/yayin-ilkeleri/", "yearly", "0.3"), ("/analiz/", "daily", "0.6"), ("/mevzuat/", "daily", "0.6"), ("/kesfet/", "weekly", "0.4"), ("/iletisim/", "yearly", "0.2")]
lm = {p["url"]: (iso(p) if p.get("saat") else p["date"].isoformat()) for p in POSTS}
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
    f"<url><loc>{SITE}{u}</loc>{('<lastmod>'+lm[u]+'</lastmod>') if u in lm else ''}<changefreq>{c}</changefreq><priority>{pr}</priority></url>\n" for u, c, pr in urls) + "</urlset>\n"
with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f: f.write(sm)
# Google News sitemap: yalnızca son 2 günde yayımlananlar
_lim = datetime.date.today() - datetime.timedelta(days=2)
nsm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "".join(
    f"<url><loc>{SITE}{p['url']}</loc><news:news><news:publication><news:name>{NAME}</news:name><news:language>tr</news:language></news:publication><news:publication_date>{iso(p) if p.get('saat') else p['date'].isoformat()}</news:publication_date><news:title>{e(p['title'])}</news:title></news:news></url>\n"
    for p in POSTS if p["date"] >= _lim) + "</urlset>\n"
with open(os.path.join(OUT, "news-sitemap.xml"), "w", encoding="utf-8") as f: f.write(nsm)
with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /search/\nDisallow: /wp-admin/\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n")
shutil.copytree(os.path.join(os.path.dirname(__file__), "static"), OUT, dirs_exist_ok=True)
with open(os.path.join(OUT, "site.webmanifest"), "w", encoding="utf-8") as f:
    json.dump({"name": NAME, "short_name": NAME, "start_url": "/", "display": "standalone", "background_color": "#35495E", "theme_color": "#2D4054",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, f, ensure_ascii=False)

# yönlendirmeler (Cloudflare Pages _redirects)
REDIRECTS += [("/search/*", "/"), ("/wp-login.php", "/"), ("/wp-admin/*", "/"), ("/xmlrpc.php", "/"),
              ("/cep-telefonu-faturasina-ust-limit-geliyor.html/cep-telefonu", "/cep-telefonu-faturasina-ust-limit-geliyor"),
              ("/turkcell-superlig-bugun-basliyor.html", "/super-toto-ligi-bugun-basliyor"),
              ("/ese-eve-don-cagrisi-15-tl.html", "/ese-‘eve-don’-cagrisi-15-tl"), ("/osd.xml", "/"),
              ("/halk-tv-sorusturmasi-4-tutuklama-4-ev-hapsi", "/halk-tv-sorusturmasi-4-tutuklama-surec-nasil-isler/"),
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
with open(os.path.join(OUT, "_routes.json"), "w", encoding="utf-8") as f:
    f.write('{"version":1,"include":["/api/*"],"exclude":[]}')
with open(os.path.join(OUT, "_headers"), "w", encoding="utf-8") as f:
    f.write("/*\n  X-Content-Type-Options: nosniff\n  X-Frame-Options: SAMEORIGIN\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n")

# özet
n_files = sum(len(fs) for _, _, fs in os.walk(OUT))
print(f"yazı: {len(POSTS)} | kategori: {sum(1 for k in CATS if cat_count[k])} | etiket: {len(tag_posts)} | ay: {len(months)} | dosya: {n_files} | redirect: {len(lines)}")
print("kelime min/ort:", min(p['words'] for p in POSTS), round(sum(p['words'] for p in POSTS)/len(POSTS)))
print("hedef link:", sum(len(re.findall(re.escape(TARGET), p['body'])) for p in POSTS), "yazıda",
      sum(1 for p in POSTS if TARGET in p['body']))
