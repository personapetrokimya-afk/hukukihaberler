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

LOGO_SVG = open(os.path.join(os.path.dirname(__file__), "static", "favicon.svg"), encoding="utf-8").read().replace("<svg ", '<svg class="lmark" width="44" height="44" aria-hidden="true" focusable="false" ', 1)
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
.mast .logo span{color:var(--acc)}.mast .logo{display:inline-flex;align-items:center;gap:12px}.lmark{flex:none;border-radius:10px}
@media(max-width:760px){.lmark{width:34px;height:34px}.mast .logo{gap:9px}}
.mast small{display:block;margin-top:6px;color:var(--mute);font-size:13px;text-transform:uppercase;letter-spacing:.18em}
nav.main{background:#9b1c1c;border-top:3px solid #14181d}
nav.main ul{list-style:none;margin:0 auto;padding:0;max-width:1180px;display:flex;overflow-x:auto;scrollbar-width:none}
nav.main ul::-webkit-scrollbar{display:none}
nav.main a{display:block;padding:11px 13px;color:#fff;font:600 13px/1.2 var(--sans);text-transform:uppercase;letter-spacing:.03em;white-space:nowrap;border-right:1px solid rgba(255,255,255,.14)}
nav.main a:hover,nav.main a.on{background:rgba(0,0,0,.22);color:#fff}
.mbtn{display:none}
@media(max-width:760px){
 .topbar{display:none}
 header{position:sticky;top:0;z-index:50;background:var(--bg);box-shadow:0 1px 0 var(--line)}
 .mast{display:flex;align-items:center;justify-content:space-between;padding:10px 0;text-align:left}
 .mast .logo{font-size:26px!important;letter-spacing:-.5px}
 .mast small{display:none}
 .mbtn{display:flex;flex-direction:column;justify-content:center;gap:5px;width:42px;height:42px;border:1px solid var(--line);border-radius:8px;background:var(--soft);padding:0 10px;cursor:pointer}
 .mbtn span{display:block;height:2px;background:var(--ink);border-radius:2px;transition:transform .2s,opacity .2s}
 .mbtn.x span:nth-child(1){transform:translateY(7px) rotate(45deg)}.mbtn.x span:nth-child(2){opacity:0}.mbtn.x span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
 nav.main{display:none;border-top:0}
 nav.main.open{display:block;max-height:70vh;overflow:auto}
 nav.main ul{flex-direction:column;overflow:visible}
 nav.main a{border-right:0;border-bottom:1px solid rgba(255,255,255,.12);padding:14px 18px;font-size:14px}
}
.kicker{display:inline-block;white-space:nowrap;font:700 11px/1 var(--sans);text-transform:uppercase;letter-spacing:.08em;color:#fff;background:var(--acc);padding:4px 7px;border-radius:2px}
.kicker.k-yargi{background:#1e3a8a}.kicker.k-siyaset{background:#374151}.kicker.k-basindan{background:#6b4f1d}.kicker.k-diger{background:#0f766e}.kicker.k-universiteler{background:#5b21b6}.kicker.k-teknoloji{background:#0e7490}.kicker.k-barolar{background:#7c2d12}.kicker.k-hukuk-burolarindan{background:#4a044e}
time,.date{font:12px/1.4 var(--sans);color:var(--mute)}
.cols{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:36px;padding:26px 0}
@media(max-width:900px){.cols{grid-template-columns:1fr;gap:28px}}
.sec-h{display:flex;align-items:center;gap:12px;margin:0 0 14px;font:800 18px/1.2 var(--serif);text-transform:uppercase;letter-spacing:.02em}
.sec-h:after{content:"";flex:1;height:3px;background:linear-gradient(90deg,var(--acc) 0 60px,var(--line) 60px)}
.sec-h a{color:var(--ink)}
.top{display:grid;grid-template-columns:1fr;gap:26px;margin-bottom:30px}
@media(max-width:900px){.top{grid-template-columns:1fr}}
.slider{position:relative;border-radius:6px;overflow:hidden;background:#000;align-self:start}
.slides{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;scrollbar-width:none}
.slides::-webkit-scrollbar{display:none}
.slide{position:relative;flex:0 0 100%;scroll-snap-align:start;aspect-ratio:16/9;display:block;color:#fff}
.slide img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.slide:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 35%,rgba(0,0,0,.55) 62%,rgba(0,0,0,.9))}
.slide .cap{position:absolute;left:0;right:0;bottom:0;padding:22px 24px 34px;z-index:1}
.slide h2{font:800 30px/1.15 var(--serif);margin:10px 0 0;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.5)}
.slide:hover h2{text-decoration:underline;text-decoration-thickness:2px}
.dots{position:absolute;left:24px;bottom:12px;display:flex;gap:6px;z-index:2}
.dots{gap:2px!important;bottom:4px!important}.dots button{width:26px;height:24px;border:0;background:none;padding:0;cursor:pointer;position:relative}.dots button:before{content:"";position:absolute;left:2px;right:2px;top:10px;height:4px;border-radius:2px;background:rgba(255,255,255,.45)}
.dots button.on{width:38px}.dots button.on:before{background:#fff}
.sarrow{position:absolute;top:38%;transform:translateY(-50%);z-index:2;width:40px;height:40px;border-radius:50%;border:0;background:rgba(0,0,0,.45);color:#fff;font-size:22px;line-height:40px;cursor:pointer}
.sarrow.p{left:10px}.sarrow.n{right:10px}
@media(max-width:560px){.slide{aspect-ratio:4/3}.slide h2{font-size:22px}.slide .cap{padding:16px 16px 30px}.sarrow{display:none}.dots{left:16px}}
.headlines{display:grid;grid-template-columns:1fr 1fr;column-gap:24px}.headlines .sec-h{grid-column:1/-1}
@media(max-width:700px){.headlines{grid-template-columns:1fr}}
.headlines article{display:grid;grid-template-columns:84px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);align-items:start}

.headlines .pic img{width:84px;height:58px;object-fit:cover;border-radius:4px;display:block}
.headlines h3{font:700 15px/1.3 var(--serif);margin:4px 0 2px}.headlines .kicker{font-size:10px;padding:3px 6px}
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
.card .meta{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:4px 8px}
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
.card{background:var(--bg);border:1px solid var(--line);border-top:0;border-radius:6px;overflow:hidden;transition:box-shadow .2s,transform .2s}
.card:hover{box-shadow:0 6px 18px rgba(0,0,0,.08);transform:translateY(-2px)}
.card .pic{border-radius:0}
.card h3 a,.card h2 a{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card p{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
@media(max-width:560px){.grid .card{display:grid;grid-template-columns:120px 1fr;gap:0 12px;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:12px 0}
 .grid .card .pic{grid-row:1/4;border-radius:4px}.grid .card .pic img{height:84px;aspect-ratio:auto}
 .grid .card .meta,.grid .card h3,.grid .card h2{padding:0}.grid .card h3{font-size:16px;margin:2px 0}.grid .card p{display:none}
 .grid .card:hover{transform:none;box-shadow:none}.grid{gap:0}}
.kaynak{font:13px/1.6 var(--sans);color:var(--mute);border-top:1px solid var(--line);padding-top:10px;margin:0 0 18px}.kaynak b{color:var(--ink);margin-right:4px}.kaynak a{color:var(--acc)}
.pmeta .tur{background:var(--acc);color:#fff;padding:0 6px;border-radius:2px;font-weight:700}
.ozet{border:1px solid var(--line);border-top:3px solid var(--acc);padding:12px 18px 6px;margin:0 0 20px;font:15px/1.55 var(--sans)}.ozet b{display:block;text-transform:uppercase;font-size:13px;letter-spacing:.04em;color:var(--acc);margin-bottom:6px}.ozet ul{margin:0;padding-left:18px}.ozet li{margin-bottom:6px}
.okuma{margin:18px 0;border-top:2px solid var(--ink);border-bottom:1px solid var(--line);padding:10px 0;font-family:var(--sans)}.okuma span{display:block;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--acc);margin-bottom:8px}.okuma a{display:flex;gap:12px;align-items:center;color:var(--ink);text-decoration:none}.okuma img{width:160px;height:84px;object-fit:cover;flex:none;border-radius:3px}.okuma b{font-size:17px;line-height:1.35}.okuma a:hover b{color:var(--acc)}
@media(max-width:560px){.okuma img{width:110px;height:58px}.okuma b{font-size:15px}}
.tablo{width:100%;border-collapse:collapse;margin:16px 0 22px;font:14px/1.45 var(--sans)}.tablo caption{text-align:left;font-weight:700;padding-bottom:6px}.tablo th,.tablo td{border-bottom:1px solid var(--line);padding:8px 6px;text-align:left;vertical-align:top}.tablo thead th{background:var(--acc);color:#fff}
@media(max-width:560px){.tablo{font-size:12.5px}}
.liste li{margin-bottom:8px}
.kicker{min-height:24px;display:inline-flex!important;align-items:center}
footer li a,aside li a,.cats a,.fcols a{display:inline-block;min-height:24px;padding:2px 0}
@media(prefers-color-scheme:dark){.ornek b{color:#f0c36d!important}}
.ornek{background:#fff8e6;border-left:4px solid var(--gold);padding:12px 16px;margin:6px 0 20px;border-radius:0 4px 4px 0;font:15px/1.6 var(--sans)}
@media(prefers-color-scheme:dark){.ornek{background:#2a2414}}
.ornek b{display:block;font:800 12px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.08em;color:#7a5300;margin-bottom:6px}.ornek p{margin:0 0 6px}
.anket{border:1px solid var(--line);border-top:3px solid var(--acc);border-radius:4px;padding:14px 18px;margin:8px 0 20px;font:15px/1.5 var(--sans)}
.anket h2{font:800 12px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.08em;margin:0 0 6px;color:var(--acc)}.anket .q{font:700 17px/1.4 var(--serif);margin:0 0 10px}
.anket label{display:block;padding:6px 0;cursor:pointer}.anket button{margin-top:8px;background:var(--acc);color:#fff;border:0;padding:8px 18px;border-radius:3px;font:600 14px var(--sans);cursor:pointer}
.anket .r{position:relative;padding:6px 8px;margin:4px 0;background:var(--soft);border-radius:3px;overflow:hidden;display:flex;justify-content:space-between}.anket .r i{position:absolute;left:0;top:0;bottom:0;background:rgba(155,28,28,.15)}.anket .r span,.anket .r b{position:relative}
.anket small,.anket .an{display:block;color:var(--mute);font-size:12px;margin-top:6px}
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
          "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}, "foundingDate": "2010",
          "sameAs": [], "publishingPrinciples": SITE + "/yayin-ilkeleri/", "correctionsPolicy": SITE + "/yayin-ilkeleri/#duzeltme"}

def _preload(main):
    m = re.search(r'<img src="([^"]+)"(?: srcset="([^"]+)")?(?: sizes="([^"]+)")?[^>]*fetchpriority=.?high', main)
    if not m: return ""
    ss = f' imagesrcset="{m.group(2)}" imagesizes="{m.group(3)}"' if m.group(2) else ""
    return f'\n<link rel="preload" as="image" href="{m.group(1)}"{ss} fetchpriority="high">'

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
<link rel="canonical" href="{e(can)}">{_preload(main)}
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
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}</style>
{ldjson}
</head>
<body>
<a class="skip" href="#icerik">İçeriğe geç</a>
<header>
<div class="wrap"><div class="topbar"><span>{today.day} {AYLAR[today.month-1]} {today.year}, {GUNLER[today.weekday()]}</span><span class="links"><a href="/kunye/">Künye</a><a href="/iletisim/">İletişim</a><a href="/feed/index.xml">RSS</a></span></div>
<div class="mast"><a class="logo" href="/" aria-label="{NAME} anasayfa">{LOGO_SVG}Hukuki <span>Haberler</span></a><small>{TAGLINE}</small><button class="mbtn" type="button" aria-label="Menüyü aç" aria-expanded="false" aria-controls="anamenu" onclick="var n=document.getElementById('anamenu');var o=n.classList.toggle('open');this.setAttribute('aria-expanded',o);this.classList.toggle('x',o)"><span></span><span></span><span></span></button></div></div>
<nav class="main" id="anamenu" aria-label="Kategoriler"><ul>{nav}</ul></nav>
</header>
<div class="wrap"><div class="cols">
<main id="icerik">{main}</main>
{sidebar()}
</div></div>
<footer><div class="wrap">
<div class="fcols">
<div><span class="logo">Hukuki Haberler</span><p style="margin:0;max-width:420px">2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi. Yüksek mahkeme kararları, Adalet Bakanlığı duyuruları, barolar ve hukuk fakültelerinden haberler.</p></div>
<div><h4>Bölümler</h4><ul><li><a href="/haber-kategorisi/manset/">Manşet</a></li><li><a href="/haber-kategorisi/yargi/">Yargı</a></li><li><a href="/haber-kategorisi/yargi/yargitay/">Yargıtay</a></li><li><a href="/haber-kategorisi/yargi/anayasa-mahkemesi/">Anayasa Mahkemesi</a></li><li><a href="/haber-kategorisi/yargi/danistay/">Danıştay</a></li><li><a href="/haber-kategorisi/basindan/">Basından</a></li></ul></div>
<div><h4>Site</h4><ul><li><a href="/hakkinda/">Hakkında</a></li><li><a href="/kunye/">Künye</a></li><li><a href="/yayin-ilkeleri/">Yayın İlkeleri</a></li><li><a href="/iletisim/">İletişim</a></li><li><a href="/gizlilik-politikasi/">Gizlilik</a></li><li><a href="/arsiv/">Arşiv</a></li><li><a href="/sitemap.xml">Site haritası</a></li></ul></div>
</div>
<div class="bot">© 2010–{today.year} {NAME}. Sitedeki yazılar genel bilgilendirme amaçlıdır; hukuki görüş niteliği taşımaz. Haber metinleri, yayımlandıkları tarihteki mevzuat ve gelişmelere dayanır.</div>
</div></footer>
</body>
</html>"""

def srcset(p): return f'srcset="{p["img"].replace("/gorsel/", "/gorsel/m/")} 480w, {p["img"]} 800w"'
def pic(p, lazy=True, w=800, h=420):
    return f'<a class="pic" href="{p["url"]}"><img src="{p["img"]}" {srcset(p)} sizes="(max-width:560px) 120px, (max-width:900px) 50vw, 300px" alt="{e(p["title"])}" width="{w}" height="{h}"{" loading=lazy decoding=async" if lazy else " fetchpriority=high"}></a>'
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

def slider_html(items):
    sl = "".join(f'<a class="slide" href="{p["url"]}" aria-label="{e(p["title"])}"><img src="{p["img"]}" {srcset(p)} sizes="(max-width:900px) 100vw, 800px" alt="" width="800" height="420"{" fetchpriority=high" if i == 0 else " loading=lazy"}><div class="cap">{kicker(p).replace("<a ","<span ").replace("</a>","</span>").replace(" href=\"/haber-kategorisi/"+topcat(p)+"/\"","")}<h2>{e(p["title"])}</h2></div></a>' for i, p in enumerate(items))
    dots = "".join(f'<button type="button" aria-label="{i+1}. haber"{" class=on" if i == 0 else ""}></button>' for i in range(len(items)))
    return f"""<div class="slider" aria-roledescription="carousel" aria-label="Manşet"><div class="slides">{sl}</div>
<button class="sarrow p" type="button" aria-label="Önceki">‹</button><button class="sarrow n" type="button" aria-label="Sonraki">›</button><div class="dots">{dots}</div></div>
<script>(function(){{var s=document.querySelector('.slides'),d=[].slice.call(document.querySelectorAll('.dots button')),n=d.length,i=0,t;
function go(k){{i=(k+n)%n;s.scrollTo({{left:i*s.clientWidth,behavior:'smooth'}})}}
s.addEventListener('scroll',function(){{var k=Math.round(s.scrollLeft/s.clientWidth);if(k!==i)i=k;d.forEach(function(b,j){{b.classList.toggle('on',j===i)}})}},{{passive:true}});
d.forEach(function(b,j){{b.onclick=function(){{go(j);rs()}}}});
document.querySelector('.sarrow.p').onclick=function(){{go(i-1);rs()}};document.querySelector('.sarrow.n').onclick=function(){{go(i+1);rs()}};
function rs(){{clearInterval(t);t=setInterval(function(){{if(!document.hidden)go(i+1)}},6000)}}
s.addEventListener('pointerdown',function(){{clearInterval(t)}});rs();}})();</script>"""

def homepage(chunk):
    photo = [p for p in POSTS[:30] if p.get("imgkind") in ("photo", "orig")]
    slides = (photo + [p for p in POSTS if p not in photo])[:5]
    heads = [p for p in chunk if p not in slides][:5]
    rest = [p for p in POSTS if p not in slides and p not in heads and p["date"].year >= 2026][:9]
    top = f"""<section class="top" aria-label="Öne çıkan haberler">{slider_html(slides)}
<div class="headlines"><h2 class="sec-h">Son dakika</h2>{"".join(f'<article>{pic(p)}<div>{kicker(p)}<h3><a href="{p["url"]}">{e(p["title"])}</a></h3><time datetime="{p["date"].isoformat()}">{trdate(p["date"])}</time></div></article>' for p in heads)}</div></section>"""
    grid = f'<h2 class="sec-h">Son haberler</h2><div class="grid">{"".join(card(p) for p in rest)}</div>'
    secs = ""
    shown = set(id(p) for p in slides + heads + rest)
    for k, label in (("yargi", "Yargı"), ("siyaset", "Siyaset"), ("diger", "Ekonomi ve Gündem"), ("teknoloji", "Teknoloji")):
        items = [p for p in POSTS if (k in p["catkeys"] or any(CATS[c][1] == k for c in p["catkeys"])) and id(p) not in shown and p["date"].year >= 2026][:3]
        if len(items) >= 2:
            secs += f'<h2 class="sec-h"><a href="/haber-kategorisi/{k}/">{label}</a></h2><div class="grid">{"".join(card(p) for p in items)}</div>'
    return top + grid + secs

def _old_homepage(chunk):
    lead, side, rest = chunk[0], chunk[1:4], chunk[4:]
    hero = f"""<section class="hero" aria-label="Öne çıkan haberler">
<article class="lead-story">{pic(lead, lazy=False)}{kicker(lead)}<h2><a href="{lead['url']}">{e(lead['title'])}</a></h2><p>{e(lead['desc'])}</p><time datetime="{lead['date'].isoformat()}">{trdate(lead['date'])}</time></article>
<div class="side-stories">{"".join(f'<article>{pic(p)}<div>{kicker(p)}<h3><a href="{p["url"]}">{e(p["title"])}</a></h3><time datetime="{p["date"].isoformat()}">{trdate(p["date"])}</time></div></article>' for p in side)}</div>
</section>"""
    grid = f'<h2 class="sec-h">Son haberler</h2><div class="grid">{"".join(card(p) for p in rest)}</div>'
    secs = ""
    for k, label in (("yargi", "Yargı"), ("siyaset", "Siyaset"), ("diger", "Ekonomi ve Gündem"), ("teknoloji", "Teknoloji")):
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
            f'<img src="{q["img"]}" alt="" width="160" height="84" loading="lazy">'
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
    rel_html = (f'<section class="related"><h2 class="sec-h">İlgili haberler</h2><div class="grid">{"".join(card(q) for q in rel)}</div></section>') if rel else ""
    newer = POSTS[idx-1] if idx > 0 else None
    older = POSTS[idx+1] if idx < len(POSTS)-1 else None
    pn = '<nav class="pn" aria-label="Önceki / sonraki haber">' + \
         (f'<a href="{older["url"]}"><small>Önceki haber</small>{e(older["title"])}</a>' if older else "<span></span>") + \
         (f'<a class="r" href="{newer["url"]}"><small>Sonraki haber</small>{e(newer["title"])}</a>' if newer else "<span></span>") + "</nav>"
    full = SITE + p["url"]
    share = f'<div class="share"><a href="https://twitter.com/intent/tweet?url={urllib.parse.quote(full)}&text={urllib.parse.quote(p["title"])}" rel="noopener nofollow" target="_blank">X\'te paylaş</a><a href="https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(full)}" rel="noopener nofollow" target="_blank">Facebook</a><a href="https://wa.me/?text={urllib.parse.quote(p["title"] + " " + full)}" rel="noopener nofollow" target="_blank">WhatsApp</a><a href="mailto:?subject={urllib.parse.quote(p["title"])}&body={urllib.parse.quote(full)}">E-posta</a></div>'
    tur = p.get("tur", "Haber")
    ld = {"@context": "https://schema.org", "@type": "AnalysisNewsArticle" if tur == "Analiz" else "NewsArticle", "headline": p["title"], "description": p["desc"],
          "datePublished": p["date"].isoformat(), "dateModified": p.get("updated") or p["date"].isoformat(),
          "mainEntityOfPage": {"@type": "WebPage", "@id": full}, "url": full, "inLanguage": "tr-TR",
          "articleSection": p["cats"][0], "keywords": ", ".join(p["tags"]), "wordCount": p["words"],
          "isAccessibleForFree": True, "image": {"@type": "ImageObject", "url": SITE + p["img"], "width": 800, "height": 420},
          "author": {"@type": "Organization", "name": NAME + " Editörlüğü", "url": SITE + "/yayin-ilkeleri/"},
          "publisher": {"@type": "Organization", "name": NAME, "url": SITE, "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}}}
    k0 = topcat(p)
    crumbs = [("/", "Anasayfa")] + ([(f"/haber-kategorisi/{CATS[k0][1]}/", CATS[CATS[k0][1]][0])] if CATS[k0][1] else []) + [(f"/haber-kategorisi/{k0}/", CATS[k0][0]), (p["url"], p["title"])]
    crumb = " › ".join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs[:-1])
    main = f"""<article class="post"><div class="crumb">{crumb}</div>
{kicker(p)}
<h1>{e(p['title'])}</h1>
<div class="pmeta"><span><time datetime="{p['date'].isoformat()}">{trdate(p['date'])}</time></span><span>{cats_html}</span><span>{rtime(p)} dk okuma</span><span class="tur">{e(tur)}</span><span><a href="/yayin-ilkeleri/">Hukuki Haberler Editörlüğü</a></span>{('<span>Güncellendi: ' + e(p["updated"]) + '</span>') if p.get("updated") else ""}</div>
<figure class="hero-img"><img src="{p['img']}" alt="{e(p['title'])}" width="800" height="420" fetchpriority="high">{credit_html(p)}</figure>
{ozet_html(p)}<div class="body">{with_okumadan(p, autolink(p))}</div>
{ornek_html(p)}{kaynak_html(p)}{anket_html(p)}
<div class="tags"><b>Etiketler:</b>{tags_html}</div>
{share}
<div class="note">Bu {"analiz" if tur == "Analiz" else "haber"} {trdate(p['date'])} tarihinde yayımlanmıştır. Metindeki süreler, oranlar ve düzenlemeler o tarihteki mevzuatı yansıtır; sonradan değişmiş olabilir. İçerik genel bilgilendirme amaçlıdır, hukuki danışmanlık yerine geçmez. Hata bildirimi için <a href="/iletisim/">iletişim</a>.</div>
{pn}{rel_html}</article>""" + (ANKET_JS if p.get("anket") else "")
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
<p>Haberler "Hukuki Haberler Editörlüğü" imzasıyla yayımlanır. Hukuk danışmanı ve içerik denetimi: Av. Yağmur Tahtasız. Yayın ve editoryal süreçler <a href="/yayin-ilkeleri/">Yayın İlkeleri</a> sayfasında açıklanmıştır. Haberlerde yer alan görüşler, atıf yapılan kurum ve kişilere aittir; site bireysel hukuki danışmanlık vermez.</p>
<h2>Düzeltme ve tekzip</h2>
<p>Hatalı olduğu bildirilen bilgiler kaynağıyla birlikte doğrulandığında en geç üç iş günü içinde düzeltilir. Düzeltme talepleri için <a href="/iletisim/">iletişim sayfasındaki</a> yol izlenir.</p>
<h2>Telif</h2>
<p>Sitedeki metinler kaynak gösterilmek ve bağlantı verilmek şartıyla alıntılanabilir; bütün hâlinde kopyalanamaz.</p>"""
write("/kunye/", page("Künye", "Hukuki Haberler künye: yayın ilkeleri, yazı işleri, düzeltme ve telif esasları.", "/kunye/",
      f'<article class="post"><h1>Künye</h1><div class="body">{KUNYE}</div></article>'))
write("/gizlilik-politikasi/", page("Gizlilik Politikası", "Hukuki Haberler gizlilik politikası: çerez kullanılmaz, kişisel veri toplanmaz.", "/gizlilik-politikasi/",
      f'<article class="post"><h1>Gizlilik Politikası</h1><div class="body">{GIZ}</div></article>', noindex=True))

YAYIN = """<p class="lead">Hukuki Haberler'in amacı, hukuk ve yargı gündemini hukukçu olmayan okurun da anlayabileceği açıklıkta, kaynağı gösterilmiş ve tarihli biçimde aktarmaktır.</p>
<h2>Kapsam ve hedef kitle</h2>
<p>Yüksek mahkeme kararları, mevzuat değişiklikleri, Resmî Gazete, TBMM'deki kanun teklifleri, adli süreçler ve gündemdeki olayların hukuki boyutu. Hedef kitlemiz hukukçular kadar, haklarını öğrenmek isteyen her okurdur.</p>
<h2>İçerik türleri</h2>
<p>Her yazının başında türü belirtilir. <b>Haber:</b> bir karar, düzenleme veya gelişmenin doğrulanmış bilgilerle aktarılması. <b>Analiz:</b> gündemdeki bir olayın mevzuat ve içtihat üzerinden açıklanması; analizlerde editoryal değerlendirme yer alır ve bu kısımlar olgulardan ayrı yazılır. Sitede sponsorlu içerik ve görüş yazısı yayımlanmamaktadır; yayımlanırsa açıkça etiketlenir.</p>
<h2>Kaynak ve doğrulama</h2>
<p>Mümkün olan her durumda birincil kaynağa dayanırız: mevzuat metni, Resmî Gazete, mahkeme kararı, kamu kurumu açıklaması. İkincil kaynak (basın kuruluşu, ajans) kullanıldığında haberin altında bağlantısıyla belirtilir. İddia iddia olarak; soruşturma, kovuşturma, mahkûmiyet ve kesinleşme kavramları birbirinden ayrılarak yazılır. Soruşturma aşamasındaki kişiler için masumiyet karinesi esastır. Çocukların ve hassas durumdaki kişilerin kimlikleri yayımlanmaz.</p>
<h2 id="duzeltme">Düzeltme, güncelleme ve tekzip</h2>
<p>Hatalı olduğu tespit edilen bilgi kaynağıyla doğrulandığında düzeltilir; ilk yayın tarihi korunur, güncelleme tarihi ve neyin değiştiği yazının içinde belirtilir. Tekzip talepleri 5187 sayılı Basın Kanunu çerçevesinde değerlendirilir. Bildirimler için <a href="/iletisim/">iletişim</a> sayfası kullanılabilir.</p>
<h2>Doğrulama</h2>
<p>Her metindeki tarih, sayı, madde numarası ve alıntı yayımlanmadan önce kaynağına bakılarak kontrol edilir; kaynağı doğrulanamayan bilgi yayımlanmaz.</p>
<h2>Hukuki içerik denetimi ve çıkar ilişkisi</h2>
<p>Sitenin hukuk danışmanlığını ve içerik denetimini Av. Yağmur Tahtasız yürütür. Av. Tahtasız'ın avukatlık bürosuna ait <a href="https://yagmurtahtasiz.com/" rel="noopener" target="_blank">yagmurtahtasiz.com</a> sitesine, yalnızca konuyla doğrudan ilgili rehber içerikler için ve sınırlı sayıda bağlantı verilebilir. Bu bağlantılar haberlerin içeriğini veya yayın kararlarını etkilemez; sitede ücret karşılığı yayımlanmış içerik yoktur.</p>
<h2>Reklam, sponsorluk ve bağımsızlık</h2>
<p>Sitede şu an reklam ve sponsorlu içerik bulunmamaktadır. İleride reklam alınması hâlinde reklam alanları haber metninden görsel olarak ayrılacak ve "Reklam" ibaresi taşıyacaktır. Hiçbir kurum veya kişi, ödeme karşılığında bir haberin içeriğini belirleyemez. Yazılarda hukuki bilgiye kaynak olarak bağlantı verilen dış sitelerle ilişkiler bu sayfada açıklanır.</p>
<h2>Görseller</h2>
<p>Görseller lisansı uygun kaynaklardan (ör. Wikimedia Commons) alınır; fotoğrafçı, kaynak ve lisans görselin altında bağlantısıyla belirtilir. Görsellerin sağ alt köşesinde site imzası yer alır.</p>"""
write("/yayin-ilkeleri/", page("Yayın İlkeleri", "Hukuki Haberler yayın ilkeleri: kaynak ve doğrulama, düzeltme politikası, hukuki içerik denetimi, reklam ve bağımsızlık.", "/yayin-ilkeleri/",
      f'<article class="post"><h1>Yayın İlkeleri</h1><div class="body">{YAYIN}</div></article>'))

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
       [(f"/{y}/{m:02d}/", "yearly", "0.3") for (y, m) in months] + [("/arsiv/", "monthly", "0.4"), ("/hakkinda/", "yearly", "0.3"), ("/kunye/", "yearly", "0.3"), ("/yayin-ilkeleri/", "yearly", "0.3"), ("/iletisim/", "yearly", "0.2")]
lm = {p["url"]: p["date"].isoformat() for p in POSTS}
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
    f"<url><loc>{SITE}{u}</loc>{('<lastmod>'+lm[u]+'</lastmod>') if u in lm else ''}<changefreq>{c}</changefreq><priority>{pr}</priority></url>\n" for u, c, pr in urls) + "</urlset>\n"
with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f: f.write(sm)
# Google News sitemap: yalnızca son 2 günde yayımlananlar
_lim = datetime.date.today() - datetime.timedelta(days=2)
nsm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "".join(
    f"<url><loc>{SITE}{p['url']}</loc><news:news><news:publication><news:name>{NAME}</news:name><news:language>tr</news:language></news:publication><news:publication_date>{p['date'].isoformat()}</news:publication_date><news:title>{e(p['title'])}</news:title></news:news></url>\n"
    for p in POSTS if p["date"] >= _lim) + "</urlset>\n"
with open(os.path.join(OUT, "news-sitemap.xml"), "w", encoding="utf-8") as f: f.write(nsm)
with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /search/\nDisallow: /wp-admin/\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n")
for _f in os.listdir(os.path.join(os.path.dirname(__file__), "static")):
    shutil.copy(os.path.join(os.path.dirname(__file__), "static", _f), os.path.join(OUT, _f))
with open(os.path.join(OUT, "site.webmanifest"), "w", encoding="utf-8") as f:
    json.dump({"name": NAME, "short_name": NAME, "start_url": "/", "display": "standalone", "background_color": "#ffffff", "theme_color": "#9b1c1c",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, f, ensure_ascii=False)

# yönlendirmeler (Cloudflare Pages _redirects)
REDIRECTS += [("/search/*", "/"), ("/wp-login.php", "/"), ("/wp-admin/*", "/"), ("/xmlrpc.php", "/"),
              ("/cep-telefonu-faturasina-ust-limit-geliyor.html/cep-telefonu", "/cep-telefonu-faturasina-ust-limit-geliyor"),
              ("/turkcell-superlig-bugun-basliyor.html", "/super-toto-ligi-bugun-basliyor"),
              ("/ese-eve-don-cagrisi-15-tl.html", "/ese-‘eve-don’-cagrisi-15-tl"), ("/osd.xml", "/"),
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
