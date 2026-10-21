# -*- coding: utf-8 -*-
"""hukukihaberler.com — statik site üretici.
Eski WordPress adres yapısı korunur; her eski adres 200 ya da 301 döner."""
import hashlib, os, re, json, shutil, html, datetime, unicodedata, urllib.parse
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
def yerel_foto(url, ad):
    """yazar fotoğrafını sitenin kendi sunucusundan verir: yoksa bir kez indirip kare kırpar (static/yazar/), olmazsa dış adresi kullanır"""
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "yazar", ad + ".jpg")
    if not os.path.exists(yol):
        try:
            import io, urllib.request
            from PIL import Image as _Im
            veri = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
            im = _Im.open(io.BytesIO(veri)).convert("RGB")
            k = min(im.size); y0 = max(0, int((im.height - k) * 0.15))
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            im.crop(((im.width - k) // 2, y0, (im.width - k) // 2 + k, y0 + k)).resize((480, 480), _Im.LANCZOS).save(yol, "JPEG", quality=85, optimize=True, progressive=True)
        except Exception:
            return url
    return "/yazar/" + ad + ".jpg"

_YZ_VERI = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yazarlar.json"), encoding="utf-8"))
YAZAR_KAYIT = {y["kod"]: y for y in _YZ_VERI["yazarlar"]}
def _yz_ad(y): return ((y.get("unvan") or "").strip() + " " + y["kisi"]).strip()
YAZARLAR = {y["kod"]: {"ad": _yz_ad(y), "kisi": y["kisi"], "url": "/" + y["adres"] + "/",
                       "foto": y.get("foto") or "/yazar/" + y["adres"] + ".jpg", "alan": y.get("alan", ""), "bio": y.get("kisa", ""),
                       "baro": y.get("baro", ""), "rol": y.get("rol", ""), "unvan": (y.get("unvan") or "").strip(), "goster": y.get("goster", True)}
            for y in _YZ_VERI["yazarlar"]}
INCELEME = {k: v for k, v in (_YZ_VERI.get("inceleme") or {}).items() if v in YAZARLAR}
HUKUKI_DENETIM = _YZ_VERI.get("hukuki_denetim") if _YZ_VERI.get("hukuki_denetim") in YAZARLAR else None
GORUNEN_YAZARLAR = {k: y for k, y in YAZARLAR.items() if y["goster"]}
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
    "manset": "Günün öne çıkan hukuk ve yargı haberleri: yüksek mahkeme kararları, Resmî Gazete'deki düzenlemeler ve gündemdeki davaların hukuki boyutu.",
    "yargi": "Yargıtay, Danıştay, Anayasa Mahkemesi ve AİHM kararları; Adalet Bakanlığı düzenlemeleri, soruşturma ve kovuşturma süreçleri.",
    "yargi/adalet-bakanligi": "Adalet Bakanlığı duyuruları, yönetmelik değişiklikleri, yargı paketleri, hâkim ve savcı atamaları ile infaz düzenlemeleri.",
    "yargi/aihm": "Avrupa İnsan Hakları Mahkemesi'nin Türkiye'ye ilişkin kararları, ihlal tespitleri ve bireysel başvuru süreçleri.",
    "yargi/anayasa-mahkemesi": "Anayasa Mahkemesi iptal kararları, bireysel başvuruda hak ihlali kararları ve Resmî Gazete'de yayımlanan gerekçeler.",
    "yargi/danistay": "Danıştay daire ve kurul kararları, yürütmeyi durdurma kararları ve idari yargıdaki emsal uyuşmazlıklar.",
    "yargi/yargitay": "Yargıtay hukuk ve ceza dairelerinin emsal kararları, içtihadı birleştirme kararları ve genel kurul kararları.",
    "siyaset": "Siyasi gündemin hukuki boyutu: kanun teklifleri, anayasa tartışmaları, seçim mevzuatı ve siyasetçilere ilişkin yargı süreçleri.",
    "teknoloji": "Kişisel veriler, siber suçlar, erişim engelleri ve dijital platformlara ilişkin düzenlemeler ile bu alandaki yargı kararları.",
    "universiteler": "YÖK düzenlemeleri, üniversite yönetmelikleri, sınav ve öğrenci haklarına ilişkin kararlar ile hukuk fakültelerinden haberler.",
    "barolar": "Barolar ve Türkiye Barolar Birliği açıklamaları, avukatlık mevzuatı, staj ve meslek haklarına ilişkin gelişmeler.",
    "basindan": "Ulusal basına yansıyan hukuk ve yargı haberlerinin kaynak gösterilerek derlenmiş özetleri.",
    "hukuk-burolarindan": "Hukuk bürolarını ve avukatlık uygulamasını ilgilendiren mevzuat değişiklikleri ve mesleki gelişmeler.",
    "diger": "Ekonomi, dünya ve gündem haberlerinin hukukla ilgili yönleri; vergi, tüketici ve ticaret mevzuatındaki değişiklikler.",
    "diger/3-sayfa": "Adliyeye yansıyan olaylar, soruşturmalar ve davalar; masumiyet karinesi gözetilerek aktarılan gelişmeler.",
    "diger/dunya": "Dünyadan hukuk ve yargı haberleri: uluslararası mahkemeler, yabancı yüksek mahkeme kararları ve karşılaştırmalı hukuk.",
    "diger/ekonomi": "Ekonomi gündeminin hukuki boyutu: vergi, SGK, sermaye piyasası, rekabet ve tüketici mevzuatındaki değişiklikler.",
    "diger/spor": "Spor dünyasındaki hukuki uyuşmazlıklar, disiplin kararları ve spor mevzuatındaki değişiklikler.",
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

def kisalt(s, n):
    """Meta açıklaması: n karakteri aşarsa cümle ya da kelime sınırında kısaltır"""
    s = re.sub(r"\s+", " ", str(s)).strip()
    if len(s) <= n: return s
    c = s[:n]
    i = c.rfind(". ")
    if i >= n * 0.6: return c[:i + 1]
    return c[:c.rfind(" ")].rstrip(",;:–-") + "…"
def trdate(d):
    return f"{d.day} {AYLAR[d.month-1]} {d.year}"
def write(path, content):
    full = os.path.join(OUT, path.lstrip("/"))
    if path.endswith("/"): full = os.path.join(full, "index.html")
    elif not os.path.splitext(full)[1]: full = os.path.join(full, "index.html")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if full.endswith(".html") and "<picture" not in content and "resim_webp" in globals(): content = resim_webp(content)
    with open(full, "w", encoding="utf-8", newline="\n") as f: f.write(content)
def words(h): return len(re.sub(r"<[^>]+>", " ", h).split())

# ---------------------------------------------------------------- yazıları hazırla
def kart_ozeti(p, sinir=200):
    """paylaşım kartı ve liste için kısa özet: haberin ilk özet maddesi (yoksa metnin başı); tam cümlede kesilir"""
    if p.get("desc"): return p["desc"]
    kaynak = (p.get("ozet") or [""])[0] or p["body"]
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", kaynak))).strip()
    if len(t) <= sinir: return t
    k = t[:sinir]
    i = max(k.rfind(". "), k.rfind("? "), k.rfind("! "))
    return k[:i + 1] if i >= 80 else k.rsplit(" ", 1)[0] + "…"

for p in POSTS:
    p["date"] = datetime.date.fromisoformat(p["date"])
    p["file"] = p.get("path") or ("/" + p["slug"] + ".html")   # eski .html adresi (dosya)
    p["url"] = p["file"][:-5]                                   # Cloudflare Pages .html'i temiz adrese 308 yolladığı için canonical/link temiz adres
    p["catkeys"] = [CAT_BY_NAME[c] for c in p["cats"]]
    p["tagslugs"] = [slugify(t) for t in p.get("tags", [])]
    p["words"] = words(p["body"])
    p["desc"] = kart_ozeti(p)
POSTS.sort(key=lambda p: p["date"], reverse=True)
assert len({p["slug"] for p in POSTS}) == len(POSTS), "slug tekrarı"
import images as _images
for p in POSTS: p["catname"] = CATS[p["catkeys"][0]][0] if p["catkeys"][0] != "manset" or len(p["catkeys"]) == 1 else CATS[p["catkeys"][1]][0]
# önceki derlemenin WebP dosyalarını önbelleğe al (yeni sunucuda/temiz kopyada yeniden kodlama gerekmesin)
try:
    _wo = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gorsel_onbellek", "webp"); os.makedirs(_wo, exist_ok=True)
    for _dp, _, _fs in os.walk(os.path.join(OUT, "gorsel")):
        for _f in _fs:
            _j = os.path.join(_dp, _f[:-5] + ".jpg")
            if _f.endswith(".webp") and os.path.exists(_j):
                _c = os.path.join(_wo, hashlib.md5(open(_j, "rb").read()).hexdigest() + ".webp")
                if not os.path.exists(_c): shutil.copyfile(os.path.join(_dp, _f), _c)
except Exception as _e:
    print("webp önbellek uyarısı:", _e)
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
_IMG = _images.build(POSTS, os.path.join(OUT, "gorsel"))
for p in POSTS: p["img"], p["imgkind"], p["credit"] = _IMG[p["slug"]]

# ---------------------------------------------------------------- konu dosyaları (hukuk dallarına göre; mevcut adresler değişmez)
def _mz_url(no, tertip=5): return f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={no}&MevzuatTur=1&MevzuatTertip={tertip}"
KONULAR = [
 ("ceza-hukuku", "Ceza Hukuku",
  "Suçlar ve cezalar, soruşturma ve kovuşturma süreçleri, tutuklama ve adli kontrol ile ceza yargılamasındaki gelişmeler.",
  ["tck", "ceza", "tutuklama", "tutuklandı", "gözaltı", "soruşturma", "kovuşturma", "iddianame", "savcı", "başsavcılık", "dolandırıcılık", "hapis", "sulh ceza", "cmk", "suç duyurusu", "adli kontrol", "operasyon"],
  [("5237 sayılı Türk Ceza Kanunu", _mz_url(5237)), ("5271 sayılı Ceza Muhakemesi Kanunu", _mz_url(5271))]),
 ("is-hukuku", "İş Hukuku",
  "İşçi ile işveren arasındaki ilişkiler: iş sözleşmesi, ücret, kıdem ve ihbar tazminatı, işe iade, iş kazası ve sendikal haklar.",
  ["iş kanunu", "işçi", "işveren", "kıdem", "ihbar tazminatı", "sendika", "işten çıkar", "işe iade", "asgari ücret", "iş kazası", "fazla mesai", "iş hukuku", "iş sözleşmesi"],
  [("4857 sayılı İş Kanunu", _mz_url(4857)), ("5510 sayılı Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu", _mz_url(5510))]),
 ("aile-hukuku", "Aile Hukuku",
  "Boşanma, nafaka, velayet, mal rejimi ve aile içi şiddete karşı koruma tedbirlerine ilişkin düzenlemeler ve kararlar.",
  ["boşanma", "nafaka", "velayet", "aile hukuku", "evlilik", "medeni kanun", "6284", "mal rejimi", "aile mahkemesi"],
  [("4721 sayılı Türk Medeni Kanunu", _mz_url(4721)), ("6284 sayılı Ailenin Korunması ve Kadına Karşı Şiddetin Önlenmesine Dair Kanun", _mz_url(6284))]),
 ("idare-hukuku", "İdare Hukuku",
  "İdarenin işlemleri ve yargısal denetimi: iptal ve tam yargı davaları, yürütmeyi durdurma, kamu görevlileri ve disiplin hukuku.",
  ["danıştay", "idari yargı", "iptal davası", "yürütmeyi durdurma", "kamu görevlisi", "memur", "disiplin cezası", "idare mahkemesi", "tam yargı", "valilik"],
  [("2577 sayılı İdari Yargılama Usulü Kanunu", _mz_url(2577)), ("657 sayılı Devlet Memurları Kanunu", _mz_url(657))]),
 ("anayasa-ve-temel-haklar", "Anayasa ve Temel Haklar",
  "Anayasa Mahkemesi'nin iptal ve bireysel başvuru kararları, AİHM kararları ve temel hak ve özgürlüklere ilişkin gelişmeler.",
  ["anayasa mahkemesi", "bireysel başvuru", "hak ihlali", "aym", "anayasa", "ifade özgürlüğü", "toplantı hürriyeti", "aihm", "temel hak"],
  [("Türkiye Cumhuriyeti Anayasası", _mz_url(2709)), ("6216 sayılı Anayasa Mahkemesinin Kuruluşu ve Yargılama Usulleri Hakkında Kanun", _mz_url(6216))]),
 ("vergi-ve-sosyal-guvenlik", "Vergi ve Sosyal Güvenlik",
  "Vergi, harç ve prim düzenlemeleri, emeklilik ve sosyal güvenlik hakları ile bu alandaki yargı kararları.",
  ["vergi", "harç", "sgk", "emekli aylığı", "erken emeklilik", "emeklilik yaşı", "prim borcu", "gelir idaresi", "sosyal güvenlik", "sigortalılık", "eyt"],
  [("213 sayılı Vergi Usul Kanunu", _mz_url(213, 4)), ("193 sayılı Gelir Vergisi Kanunu", _mz_url(193, 4)), ("5510 sayılı Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu", _mz_url(5510))]),
 ("kisisel-veriler-ve-bilisim", "Kişisel Veriler ve Bilişim",
  "Kişisel verilerin korunması, veri ihlalleri, siber suçlar, erişim engelleri ve dijital platformlara ilişkin düzenlemeler.",
  ["kvkk", "kişisel veri", "veri ihlali", "siber", "erişim engeli", "bilişim", "yapay zeka", "sosyal medya", "5651", "fidye yazılımı"],
  [("6698 sayılı Kişisel Verilerin Korunması Kanunu", _mz_url(6698)), ("5651 sayılı İnternet Ortamında Yapılan Yayınların Düzenlenmesi Hakkında Kanun", _mz_url(5651))]),
 ("tuketici-haklari", "Tüketici Hakları",
  "Ayıplı mal ve hizmet, sigorta ve abonelik uyuşmazlıkları, tüketici hakem heyetleri ve tüketiciyi koruyan düzenlemeler.",
  ["tüketici", "kasko", "sigorta şirket", "konut sigortası", "ayıplı", "garanti belgesi", "hakem heyeti", "abonelik", "cayma hakkı", "mesafeli sözleşme"],
  [("6502 sayılı Tüketicinin Korunması Hakkında Kanun", _mz_url(6502))]),
 ("ticaret-ve-sermaye-piyasasi", "Ticaret ve Sermaye Piyasası",
  "Şirketler, sermaye piyasası, rekabet ve bankacılık alanındaki düzenlemeler, idari yaptırımlar ve yargı süreçleri.",
  ["spk", "sermaye piyasası", "anonim şirket", "limited şirket", "holding", "rekabet", "borsa", "fon", "ticaret kanunu", "konkordato", "iflas", "bankacılık", "tmsf"],
  [("6102 sayılı Türk Ticaret Kanunu", _mz_url(6102)), ("6362 sayılı Sermaye Piyasası Kanunu", _mz_url(6362)), ("4054 sayılı Rekabetin Korunması Hakkında Kanun", _mz_url(4054))]),
 ("kira-ve-tasinmaz", "Kira ve Taşınmaz",
  "Kira ilişkileri, tahliye, kira artışı, tapu ve imar uyuşmazlıkları ile kentsel dönüşüme ilişkin düzenlemeler.",
  ["kira", "kiracı", "kira artış", "kira sözleşmesi", "tahliye davası", "tapu", "imar", "kentsel dönüşüm", "kamulaştırma"],
  [("6098 sayılı Türk Borçlar Kanunu", _mz_url(6098))]),
]
KONU_ALT = 3          # bundan az haberi olan konu sayfası oluşturulmaz
KONU_DIZIN = 5        # bundan az haberi olan konu sayfası dizine girmez
def _tr_kucuk(s): return s.replace("İ", "i").replace("I", "ı").lower()
_KONU_RE = {k: re.compile("|".join((r"(?<!\w)" + re.escape(_tr_kucuk(w)) + (r"(?!\w)" if len(w) <= 4 else "")) for w in ws))
            for k, _, _, ws, _ in KONULAR}
for p in POSTS:
    h = _tr_kucuk(p["title"] + " | " + " | ".join(p.get("tags", [])))
    p["konular"] = [k for k, *_ in KONULAR if _KONU_RE[k].search(h)]
# hukuki inceleme: yalnızca ceza hukuku (suç, soruşturma, kovuşturma, ceza yargılaması) yazıları Av. Umut Tekin;
# boşanma, aile, miras, icra ve diğer özel hukuk (kira, tüketici, iş, tazminat) yazıları Av. Yağmur Tahtasız tarafından incelenir.
# Aile ve miras her durumda Yağmur Tahtasız'dadır. İdare, anayasa, vergi gibi alanlarda inceleme kartı gösterilmez.
def _kelime_re(ws): return re.compile("|".join(r"(?<!\w)" + re.escape(_tr_kucuk(w)) for w in ws))
_AILE_RE = _kelime_re(["boşan", "nafaka", "velayet", "aile hukuku", "aile mahkemesi", "evlilik", "eşler", "ziynet", "mal rejimi", "edinilmiş mal",
                       "nesep", "soybağı", "babalık davası", "evlat edin", "vesayet", "6284", "koruma kararı", "uzaklaştırma kararı",
                       "miras", "mirasçı", "veraset", "tereke", "vasiyet", "saklı pay", "tenkis", "muris"])
_ICRA_RE = _kelime_re(["icra takib", "icra müdürl", "icra dairesi", "icra ve iflas", "icra hukuku", "haciz", "iflas", "konkordato", "itirazın iptali",
                       "menfi tespit", "ihtiyati haciz", "2004 sayılı", "kambiyo"])
_OZEL_RE = _kelime_re(["manevi tazminat", "maddi tazminat", "tazminat davası", "borçlar kanunu", "aydınlatılmış onam", "hekime kusur", "tıbbi müdahale",
                       "malpraktis", "alacak davası", "kira sözleşme", "kiracı", "kira artış", "tahliye davası", "tapu iptal", "ortaklığın giderilmesi",
                       "ayıplı", "ayıpsız", "cayma hakkı", "tüketici hakem", "kıdem tazminat", "ihbar tazminat", "işe iade", "yıllık izin", "işten çıkar",
                       "hak sahipleri ne yapmalı", "hukuki haklar rehberi"])
_UT_RE = _kelime_re(["tck", "cmk", "türk ceza kanunu", "ceza muhakemesi", "tutukla", "tutuklu", "gözaltı", "iddianame", "sanık", "şüpheli",
                     "mütalaa", "beraat", "müebbet", "hapis", "cezaevi", "adli kontrol", "kovuşturma", "suç örgütü", "suç duyurusu", "suçlama",
                     "suçu", "suçlar", "suç mu", "suça", "uyuşturucu", "kara para", "aklama", "irtikap", "rüşvet", "dolandırıcı", "fetö", "deaş",
                     "terör", "kasten", "taksirle", "öldürme", "yakalandı", "gıyabi", "kırmızı bülten", "operasyon", "ağır ceza", "hagb",
                     "yasa dışı bahis", "kaçakçılı", "tefeci", "hürriyetten yoksun", "kötü muamele", "fuhuş", "silahlı saldırı"])
_CEZA_DEGIL = _kelime_re(["rekabet", "rtük", "reklam kurulu", "idari para cezası", "disiplin cezası", "kesin hesab", "adli tatil", "msci", "borsa"])
for p in POSTS:
    if p.get("denetleyen") == "yok": p.pop("denetleyen"); p["_kart_yok"] = True
    if p.get("denetleyen") and p["denetleyen"] not in YAZARLAR: p.pop("denetleyen")
    if p.get("yazar") and p["yazar"] not in YAZARLAR: p.pop("yazar")
    if p.get("denetleyen") or p.get("_kart_yok"): continue
    _t = _tr_kucuk(p["title"]); _h = _t + " | " + _tr_kucuk(" | ".join(p.get("tags", [])))
    if "adli tatil" in _t: continue
    # kural grupları ve sorumlu avukat yazarlar.json "inceleme" alanından (panelden değiştirilir); grubun avukatı yoksa kart gösterilmez
    if "aile-hukuku" in p["konular"] or _AILE_RE.search(_h):
        if INCELEME.get("aile"): p["denetleyen"] = INCELEME["aile"]
    elif _UT_RE.search(_h) and not _CEZA_DEGIL.search(_t):
        if INCELEME.get("ceza"): p["denetleyen"] = INCELEME["ceza"]
    elif _ICRA_RE.search(_h) or _OZEL_RE.search(_h):
        if INCELEME.get("ozel"): p["denetleyen"] = INCELEME["ozel"]
    if p.get("denetleyen") and p["denetleyen"] not in YAZARLAR: p.pop("denetleyen")
KONU_HABER = {k: [p for p in POSTS if k in p["konular"]] for k, *_ in KONULAR}
KONU_AD = {k: ad for k, ad, *_ in KONULAR}
KONU_VAR = [k for k, *_ in KONULAR if len(KONU_HABER[k]) >= KONU_ALT]

# WebP kopyaları: aynı görselin ~%40 daha küçük hâli; <picture> ile sunulur, desteklemeyen tarayıcı JPEG alır.
# Önbellek içerik özetine göre tutulur, yalnızca yeni/değişen görsel yeniden kodlanır.
def webp_uret(kok):
    from PIL import Image as _Im
    onb = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gorsel_onbellek", "webp")
    os.makedirs(onb, exist_ok=True)
    n = 0
    for dp, _, fs in os.walk(kok):
        for f in fs:
            if not f.endswith(".jpg"): continue
            src = os.path.join(dp, f)
            h = hashlib.md5(open(src, "rb").read()).hexdigest()
            c = os.path.join(onb, h + ".webp")
            if not os.path.exists(c):
                _Im.open(src).convert("RGB").save(c, "WEBP", quality=76, method=5); n += 1
            shutil.copyfile(c, src[:-4] + ".webp")
    return n
try:
    print("webp yeni:", webp_uret(os.path.join(OUT, "gorsel")))
except Exception as _e:   # WebP üretilemezse site JPEG ile çalışmaya devam eder
    print("webp üretilemedi:", _e)
# Discover/Google Görseller için 1:1 ve 4:3 kırpımlar (yalnızca fotoğraflı haberler; yazılı kapak görselleri kırpılınca metin kesilir)
ORAN_KIRP = {"4x3": (840, 630), "1x1": (630, 630)}
def _imza_sol():
    from PIL import ImageFont as _F, ImageDraw as _D, Image as _Im
    f = _F.truetype(_images.FONT_S, int(15 * _images.S))
    tw = _D.Draw(_Im.new("RGB", (10, 10))).textlength("hukukihaberler.com", font=f)
    return int(_images.W - int(12 * _images.S) - tw - int(10 * _images.S) * 2 - int(12 * _images.S))
def oran_kopyalari():
    from PIL import Image as _Im
    global _imza_x0
    _imza_x0 = _imza_sol()
    onb = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gorsel_onbellek", "kirp"); os.makedirs(onb, exist_ok=True)
    n = 0
    for p in POSTS:
        p["img_oran"] = {}
        if p.get("imgkind") in ("gen", "orig"): continue   # yazılı kapaklar ve çerçeveli eski görseller kırpılmaz
        src = os.path.join(OUT, p["img"].split("?")[0].lstrip("/"))
        if not os.path.exists(src): continue
        h = hashlib.md5(open(src, "rb").read()).hexdigest()
        for ad, (w, hh) in ORAN_KIRP.items():
            c = os.path.join(onb, f"{h}_{ad}.jpg")
            if not os.path.exists(c):
                im = _Im.open(src).convert("RGB"); cw = w * im.height // hh; x = (im.width - cw) // 2
                x = max(0, min(x, _imza_x0 - cw - 2))   # sağ alttaki site imzası kırpımın içine yarım girmesin
                im.crop((x, 0, x + cw, im.height)).resize((w, hh), _Im.LANCZOS).save(c, "JPEG", quality=82, optimize=True, progressive=True); n += 1
            hedef = os.path.join(OUT, "gorsel", ad, os.path.basename(src)); os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(c, hedef)
            p["img_oran"][ad] = (f"/gorsel/{ad}/{os.path.basename(src)}?v={h[:8]}", w, hh)
    return n
try:
    print("oran kırpımı yeni:", oran_kopyalari())
except Exception as _e:
    print("oran kırpımı yapılamadı:", _e)
    for p in POSTS: p.setdefault("img_oran", {})
_WEBP_RE = re.compile(r'<img src="(/gorsel/[^"?]+)\.jpg(\?v=[0-9a-f]+)?"([^>]*)>')
def _webp(u):
    return re.sub(r'(/gorsel/[^"?\s]+)\.jpg', r'\1.webp', u)
def resim_webp(h):
    """/gorsel/ JPEG'lerini <picture> içine alır: önce WebP, yedek JPEG"""
    def f(m):
        yol, v, rest = m.group(1), m.group(2) or "", m.group(3)
        if not os.path.exists(os.path.join(OUT, yol.lstrip("/") + ".webp")): return m.group(0)
        ss = re.search(r'srcset="([^"]+)"', rest); sz = re.search(r'sizes="([^"]+)"', rest)
        kaynak = _webp(ss.group(1)) if ss else f"{yol}.webp{v}"
        return (f'<picture><source type="image/webp" srcset="{kaynak}"' + (f' sizes="{sz.group(1)}"' if sz else "") + '>'
                + m.group(0) + '</picture>')
    return _WEBP_RE.sub(f, h)
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
    return f'<a class="byl" href="{y["url"]}" rel="author"><img src="{y["foto"]}" alt="" width="28" height="28" loading="lazy" referrerpolicy="no-referrer">{e(y["ad"])}</a>'
def yazar_kutu(p):
    y = YAZARLAR.get(p.get("yazar"))
    if not y: return ""
    digr = [q for q in POSTS if q.get("yazar") == p["yazar"] and q["slug"] != p["slug"]][:5]
    li = "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a></li>' for q in digr)
    return (f'<aside class="ykutu" aria-label="Yazar"><img src="{y["foto"]}" alt="{e(y["ad"])}" width="88" height="88" loading="lazy" referrerpolicy="no-referrer">'
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

def yazarlar_kutu(baslik="h2"):
    """yazarlar: fotoğraf, ad, uzmanlık alanı ve (varsa) son yazısı"""
    s = []
    for k, y in GORUNEN_YAZARLAR.items():
        son = next((q for q in POSTS if q.get("yazar") == k or q.get("denetleyen") == k), None)
        alt = (f'<a class="yz-son" href="{son["url"]}">{e(son["title"])}</a>' if son else f'<span class="yz-son">{e(y["alan"])}</span>')
        s.append(f'<li><a class="yz-f" href="{y["url"]}" tabindex="-1" aria-hidden="true"><img src="{y["foto"]}" alt="" width="64" height="64" loading="lazy" referrerpolicy="no-referrer"></a>'
                 f'<div><a class="yz-ad" href="{y["url"]}">{e(y["ad"])}</a><small>{e(y["alan"])}</small>{alt if son else ""}</div></li>')
    return (f'<div class="box yzr"><{baslik}><a href="/yazarlar/">Yazarlar</a></{baslik}><ul>{"".join(s)}</ul></div>')

def sidebar():
    latest = "".join(f'<li class="m">{mini(p)}<div><time datetime="{iso(p)}">{kisa(p["date"])}{(" · " + p["saat"]) if p.get("saat") else ""}</time><a href="{p["url"]}">{e(p["title"])}</a></div></li>' for p in POSTS[:6])
    cats = "".join(f'<li class="c"><a href="/haber-kategorisi/{k}/">{e(v[0])}</a><span>{cat_count[k]}</span></li>'
                   for k, v in CATS.items() if v[1] is None and cat_count[k])
    return f"""<aside aria-label="Yan sütun">
<div class="box"><h2>Son gelişmeler</h2><ul>{latest}</ul></div>
{yazarlar_kutu()}
<div class="box"><h2>Bölümler</h2><ul>{cats}<li class="c"><a href="/arsiv/">Arşiv</a><span>{len(POSTS)}</span></li></ul></div>
</aside>"""

ORG_LD = {"@context": "https://schema.org", "@type": "NewsMediaOrganization", "@id": SITE + "/#kurum", "name": NAME, "url": SITE + "/",
          "ethicsPolicy": SITE + "/yayin-ilkeleri/", "verificationFactCheckingPolicy": SITE + "/yayin-ilkeleri/#dogrulama",
          "actionableFeedbackPolicy": SITE + "/iletisim/",
          "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}, "foundingDate": "2010",
          "sameAs": ["https://x.com/HukukiHaberTR"], "masthead": SITE + "/kunye/", "publishingPrinciples": SITE + "/yayin-ilkeleri/", "correctionsPolicy": SITE + "/yayin-ilkeleri/#duzeltme", "email": "iletisim@hukukihaberler.com",
          "contactPoint": {"@type": "ContactPoint", "contactType": "editorial", "email": "iletisim@hukukihaberler.com", "url": SITE + "/iletisim/", "availableLanguage": "tr"}}
WEBSITE_LD = {"@context": "https://schema.org", "@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": NAME,
              "alternateName": ["HukukiHaberler", "hukukihaberler.com"], "inLanguage": "tr-TR", "publisher": {"@id": SITE + "/#kurum"}}

def _preload(main):
    m = re.search(r'<img src="([^"]+)"(?: srcset="([^"]+)")?(?: sizes="([^"]+)")?[^>]*fetchpriority=.?high', main)
    if not m: return ""
    src, ss_, sz_ = m.group(1), m.group(2), m.group(3)
    tip = ""
    if src.startswith("/gorsel/") and os.path.exists(os.path.join(OUT, src.split("?")[0].lstrip("/")[:-4] + ".webp")):
        src = _webp(src); ss_ = _webp(ss_) if ss_ else ss_; tip = ' type="image/webp"'
    ss = f' imagesrcset="{ss_}" imagesizes="{sz_}"' if ss_ else ""
    return f'\n<link rel="preload" as="image" href="{src}"{ss}{tip} fetchpriority="high">'

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

# çerezsiz ziyaret sayacı: yalnızca sayfa yolu, yönlendiren adres ve ekran genişliği gönderilir; kimlik ya da çerez yoktur
SAYAC_JS = """<script>(function(){try{if(location.hostname!=='hukukihaberler.com')return;var d=JSON.stringify({p:location.pathname,r:document.referrer,w:screen.width});var u='https://panel.hukukihaberler.com/sayac';if(navigator.sendBeacon)navigator.sendBeacon(u,d);else fetch(u,{method:'POST',body:d,keepalive:true,mode:'no-cors'});}catch(e){}})();</script>"""
def page(title, desc, url, main, ld=None, noindex=False, canonical=None, ogtype="website", crumbs=None, img=None, active=None, side=True, extra="", ogek=""):
    act = active or url
    def on(u): return act == u or (u != "/" and act.startswith(u))
    catnav = "".join(f'<li><a href="{u}"{" class=on aria-current=page" if on(u) else ""}>{t}</a></li>' for u, t in CATNAV)
    drawer = "".join(f'<li><a href="{u}">{ico(i, 20)}<span>{t}</span></a></li>' for u, t, i in DRAWER)
    drawer2 = "".join(f'<li><a href="{u}"><span>{t}</span></a></li>' for u, t in SITE_LINKS)
    _tk = POSTS[:5]
    ticker = ("".join(f'<li><a href="{p["url"]}">{e(p["title"])}</a></li>' for p in _tk)
              + "".join(f'<li aria-hidden="true"><a href="{p["url"]}" tabindex="-1">{e(p["title"])}</a></li>' for p in _tk))
    ticker_sure = max(30, int(sum(len(p["title"]) for p in _tk) * 0.16))   # okunur hız: ~6 karakter/sn
    lds = []
    if ld: lds.extend(ld if isinstance(ld, list) else [ld])
    if crumbs:
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]})
    ldjson = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
    can = canonical or (SITE + url)
    # uzun haber başlıklarında site adı eklenmez (arama sonucunda kesilmesin; site adı Google'da ayrıca gösterilir)
    full_title = (title if len(title) > 52 else f"{title} | {NAME}") if url != "/" else f"{NAME} | Hukuk, Yargı, Yargıtay, Danıştay ve Mevzuat Haberleri"
    desc = kisalt(desc, 160)
    today = datetime.date.today()
    srch = lambda i: f'<form class="hsearch" action="/arama/" method="get" role="search"><label class="sr" for="{i}">Sitede ara</label>{ico("search", 20)}<input id="{i}" name="q" type="search" placeholder="Haber, karar, mevzuat veya konu ara…" autocomplete="off"></form>'
    body = (f'<div class="hwrap"><div class="cols"><main id="icerik">{main}</main>{sidebar()}</div></div>' if side
            else f'<main id="icerik" class="hwrap">{main}</main>')
    bn = lambda u, t, i: f'<a href="{u}"{" class=on aria-current=page" if url == u else ""}>{ico(i, 22)}<span>{t}</span></a>'
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<script>(function(){{function f(i){{if(!i||i.tagName!=='IMG'||i.dataset.gy==='2')return;var p=i.parentNode;if(p&&p.tagName==='PICTURE'&&p.querySelector('source')){{i.dataset.gy=1;p.querySelectorAll('source').forEach(function(s){{s.remove()}});var u=i.getAttribute('src');i.removeAttribute('src');i.setAttribute('src',u);return}}i.dataset.gy=2;i.style.display='none';if(p&&p.tagName==='PICTURE')p.style.display='none';var c=i.closest('.okuma');if(c)c.classList.add('gyok')}}document.addEventListener('error',function(e){{f(e.target)}},true);document.addEventListener('DOMContentLoaded',function(){{document.querySelectorAll('img').forEach(function(i){{if(i.complete&&i.getAttribute('src')&&i.naturalWidth===0)f(i)}})}})}})()</script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}var _cz=null;try{{_cz=localStorage.getItem('hh:cerez')}}catch(e){{}}gtag('consent','default',{{analytics_storage:_cz==='evet'?'granted':'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'}});gtag('js',new Date());gtag('config','G-84SWYM8295');addEventListener('load',function(){{var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-84SWYM8295';document.head.appendChild(s)}});</script>
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
<meta property="og:image:secure_url" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@HukukiHaberTR">
<meta name="twitter:image" content="{SITE + (img or "/gorsel/kapak.jpg")}">
<meta name="twitter:image:alt" content="{e(title)}">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">{ogek}
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
<div class="ticker"><div class="hwrap"><span class="tk"><i></i>Güncel</span><div class="tkiz"><ul style="--tks:{ticker_sure}s">{ticker}</ul></div><a class="tmore" href="/arsiv/" aria-label="Tüm haberler">{ico("chev", 20)}</a></div></div>
<div class="hwrap htop">
<div class="hl"><span class="hdate">{today.day} {AYLAR[today.month-1]} {today.year}, {GUNLER[today.weekday()]}</span></div>
<a class="brand" href="/" aria-label="{NAME} anasayfa"><span class="brow">{ico("scale", 40, "bt1")}<span class="bn">Hukuki Haberler</span>{ico("scale", 40, "bt2")}</span><span class="balt">Hukuk <i>•</i> Yargı <i>•</i> Gündem</span></a>
<div class="hright"><div class="hbtns">{gpref_btn()}<a class="xbtn" href="https://x.com/HukukiHaberTR" rel="me noopener" target="_blank">{ico("takip", 18)}X'te takip et</a><a class="rssbtn" href="/feed/index.xml">{ico("rss", 18)}RSS ile takip et</a></div></div>
</div>
<nav class="hnav" aria-label="Bölümler"><div class="hwrap hnr">
<a class="mlogo" href="/" aria-label="{NAME} anasayfa" tabindex="-1">{ico("scale", 28)}</a>
<button type="button" class="mbtn" aria-label="Menüyü aç" aria-expanded="false" aria-controls="drawer">{ico("menu", 22)}<span>Menü</span></button>
<button type="button" class="sbtn" aria-label="Sitede ara" aria-expanded="false" aria-controls="msearch">{ico("search", 20)}</button>
<span class="hsep" aria-hidden="true"></span>
<ul class="catl">{catnav}</ul>
<a class="rssmini" href="/feed/index.xml" tabindex="-1">{ico("rss", 16)}<span>Takip et</span></a>
</div>
<div id="msearch" class="msearch" hidden><div class="hwrap">{srch("q2")}</div></div>
</nav>
</header>
<div id="drawer" class="drawer" hidden><nav class="dp" aria-label="Tüm bölümler"><div class="dh"><button type="button" class="ibtn dclose" style="display:inline-flex" aria-label="Menüyü kapat">{ico("close", 24)}</button><a class="dbrand" href="/">{ico("scale", 26)}Hukuki Haberler</a></div><div class="dsrch">{srch("q3")}</div><ul>{drawer}</ul><div class="dsub">Site</div><ul>{drawer2}</ul>{"<div class=\"dgp\">" if GPREF_AKTIF else ""}{gpref_btn("gpref gpbig", "Google'da tercih edilen kaynak olarak ekle", 20)}{"</div>" if GPREF_AKTIF else ""}</nav></div>
{body}
<footer class="site"><div class="hwrap">
<div class="fcols">
<div><div class="fbrand">{ico("scale", 30)}Hukuki Haberler</div><p style="margin:0;max-width:440px">2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi. Yüksek mahkeme kararları, mevzuat değişiklikleri ve gündemin hukuki boyutu.</p></div>
<div><h2>Bölümler</h2><ul>{"".join(f'<li><a href="{u}">{t}</a></li>' for u, t in CATNAV[:7])}<li><a href="/konular/">Konu dosyaları</a></li></ul></div>
<div><h2>Site</h2><ul>{"".join(f'<li><a href="{u}">{t}</a></li>' for u, t in SITE_LINKS)}<li><a href="/arsiv/">Arşiv</a></li><li><a href="/feed/index.xml">RSS</a></li><li><a href="https://x.com/HukukiHaberTR" rel="me noopener" target="_blank">X: @HukukiHaberTR</a></li></ul></div>
</div>
<div class="bot">© 2010–{today.year} {NAME}. Sitedeki yazılar genel bilgilendirme amaçlıdır; hukuki görüş niteliği taşımaz.</div>
</div></footer>
<nav class="bnav" aria-label="Alt menü">{bn("/", "Ana Sayfa", "home")}{bn("/kesfet/", "Keşfet", "compass")}{bn("/kaydedilenler/", "Kaydedilen", "bookmark")}<button type="button" aria-controls="drawer" aria-expanded="false">{ico("menu", 22)}<span>Menü</span></button></nav>
<div id="cerez" class="cerez" role="region" aria-label="Çerez tercihi" hidden><p>Ziyaret istatistiklerini ölçmek için Google Analytics çerezlerini kullanmak istiyoruz. İzin vermezseniz ölçüm çerezsiz ve kimliksiz yapılır. <a href="/gizlilik-politikasi/#cerezler">Ayrıntılar</a></p><div><button type="button" data-c="hayir">Reddet</button><button type="button" data-c="evet" class="ok">İzin ver</button></div></div>
{JS}{SAYAC_JS}{extra}
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
            write(url, page(ttl, desc, url, homepage(chunk), noindex=False, ld=[ORG_LD, WEBSITE_LD], side=False))
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
               + (f'<aside aria-label="Gündemdeki konular"><h2 class="sec-h">Gündemdeki konular</h2><ol class="topics">{topics}</ol>{yazarlar_kutu()}</aside>' if topics else "") + '</section>')
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
POST_URLS = {p["url"] for p in POSTS}
# yayından kalkmış ya da adresi değişmiş haberler: eski adres -> yeni adres (yönlendirme ve iç bağlantılar için)
ESKI_ADRES = {"/halk-tv-sorusturmasi-4-tutuklama-4-ev-hapsi": "/halk-tv-sorusturmasi-4-tutuklama-surec-nasil-isler",
              "/spk-baskani-gorevden-alindi-karar-ne-anlama-geliyor": "/spk-baskani-gorevden-alindi-ne-anlama-geliyor"}
_SABIT_YOL = {"arsiv", "analiz", "mevzuat", "kesfet", "hakkinda", "kunye", "iletisim", "yayin-ilkeleri", "gizlilik-politikasi",
              "kullanim-kosullari", *[y["adres"] for y in _YZ_VERI["yazarlar"]], "yazarlar", "konu", "konular", "arama", "kaydedilenler", "feed", "haber-kategorisi", "haber-etiketi"}
def ic_bag(h):
    """Metin içi site bağlantıları: yönlendirmeye düşen adresleri doğrudan hedefe çevirir, karşılığı olmayan bağlantıyı kaldırır (metin kalır)"""
    def f(m):
        href, rest, txt = m.group(1), m.group(2), m.group(3)
        yol, ek = (href.split("#", 1) + [""])[:2]
        ek = ("#" + ek) if ek else ""
        tek = yol.strip("/")
        if not tek or "/" in tek or tek.isdigit() or tek in _SABIT_YOL: return m.group(0)
        if "/" + tek in POST_URLS: return f'<a href="/{tek}{ek}"{rest}>{txt}</a>'
        if "/" + tek in ESKI_ADRES: return f'<a href="{ESKI_ADRES["/" + tek]}{ek}"{rest}>{txt}</a>'
        return txt
    return re.sub(r'<a href="(/[^"]*)"([^>]*)>(.*?)</a>', f, h, flags=re.S)
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

KARAR_ALANLARI = [("mahkeme", "Mahkeme"), ("daire", "Daire"), ("esas", "Esas no"), ("karar_no", "Karar no"), ("tarih", "Karar tarihi"),
                  ("konu", "Konu"), ("uyusmazlik", "Uyuşmazlık"), ("sonuc", "Sonuç"), ("etki", "Pratik etkisi")]
def karar_html(p):
    """Mahkeme kararı künyesi: yalnızca kaynakta açıkça yer alan alanlar yazılır, olmayan alan gösterilmez"""
    k = p.get("karar")
    if not isinstance(k, dict): return ""
    sat = "".join(f"<div><dt>{ad}</dt><dd>{e(str(k[a]))}</dd></div>" for a, ad in KARAR_ALANLARI if str(k.get(a) or "").strip())
    if not sat: return ""
    u = str(k.get("kaynak") or "")
    kay = f'<a class="kk-k" href="{e(u)}" target="_blank" rel="noopener">Karar metni (resmî kaynak)</a>' if u.startswith("https://") else ""
    return f'<aside class="karark" aria-label="Karar künyesi"><b>Karar künyesi</b><dl>{sat}</dl>{kay}</aside>\n'

_ONEK = re.compile(r"^\s*Güncelleme(?:\s*\([^)]*\))?\s*:\s*")
def _onek_sil(s): return _ONEK.sub("", s)
def govde_temiz(h):
    """metne işlenmiş güncelleme notlarında yinelenen "Güncelleme (...):" önekini kaldırır"""
    return re.sub(r"(<b>Güncelleme \([^)]*\):</b>\s*)Güncelleme(?:\s*\([^)]*\))?\s*:\s*", r"\1", h)
def gecmis_html(p):
    """Okura açık güncelleme geçmişi: ilk yayın, ardından her güncelleme/düzeltmenin tarihi ve ne değiştiği"""
    g = [x for x in (p.get("gecmis") or []) if isinstance(x, dict) and x.get("tarih")]
    if not g:   # eski haberler: metne işlenmiş "Güncelleme (gün ay yıl, SS.DD):" notlarından geçmiş çıkarılır
        for m in re.finditer(r"<b>Güncelleme \((\d{1,2}) (\w+) (\d{4}), (\d{2})\.(\d{2})\):</b>\s*(.*?)</p>", p["body"]):
            if m.group(2) in AYLAR:
                g.append({"tarih": f"{m.group(3)}-{AYLAR.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}T{m.group(4)}:{m.group(5)}", "tur": "Güncelleme",
                          "not": kisalt(_onek_sil(html.unescape(re.sub(r"<[^>]+>", "", m.group(6)))), 220)})
    u = str(p.get("updated") or "")
    if u and not g and p.get("saat") and "T" in u:   # yayından sonraki ilk bir saat içindeki teknik düzenlemeler (görsel, biçim) geçmişe yazılmaz
        try:
            if (datetime.datetime.fromisoformat(u[:16]) - datetime.datetime.fromisoformat(f'{p["date"].isoformat()}T{p["saat"]}')).total_seconds() < 3600: u = ""
        except ValueError: pass
    if not g and not u: return ""
    sat = [f'<li><time datetime="{iso(p)}">{when(p)}</time><span>İlk yayın</span></li>']
    for x in sorted(g, key=lambda x: str(x["tarih"])):
        sat.append(f'<li><time datetime="{e(str(x["tarih"]))}">{upd(str(x["tarih"]))}</time><span><b>{e(str(x.get("tur") or "Güncelleme"))}:</b> {e(kisalt(_onek_sil(str(x.get("not") or "")), 220))}</span></li>')
    if not g:
        sat.append(f'<li><time datetime="{e(u)}">{upd(u)}</time><span>Güncellendi</span></li>')
    return (f'<section class="gecmis" aria-labelledby="gecmis-{p["slug"][:40]}"><h2 id="gecmis-{p["slug"][:40]}">Güncelleme geçmişi</h2><ol>{"".join(sat)}</ol>'
            '<p>Düzeltme ilkelerimiz <a href="/yayin-ilkeleri/#duzeltme">Yayın İlkeleri</a> sayfasındadır; hata bildirimi için <a href="/iletisim/">iletişim</a>.</p></section>\n')

def inceleme_karti(p):
    """haberi yayımlanmadan önce hukuki açıdan inceleyen avukatın kartı (yalnızca kimlik ve alan bilgisi; iletişim, ücret ya da çağrı yok)"""
    y = YAZARLAR.get(p.get("denetleyen"))
    if not y: return ""
    return (f'<aside class="inceleme" aria-label="Hukuki inceleme" data-denetleyen="{p["denetleyen"]}"><a class="in-f" href="{y["url"]}" tabindex="-1" aria-hidden="true">'
            f'<img src="{y["foto"]}" alt="" width="64" height="64" loading="lazy" referrerpolicy="no-referrer"></a><div class="in-m"><span class="in-e">Hukuki inceleme</span>'
            f'<a class="in-ad" href="{y["url"]}">{e(y["ad"])}</a><span class="in-a">{e(y["alan"])}{(" · " + e(y["baro"])) if y["baro"] else ""}</span>'
            f'<p>Bu {"analiz" if p.get("tur") == "Analiz" else "haber"} {e(y["ad"])} tarafından hukuki açıdan incelenmiştir. '
            f'İçerik genel bilgilendirme amaçlıdır; somut bir dosya için hukuki danışmanlık yerine geçmez.</p></div></aside>\n')

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

def sss_temiz(p):
    """yalnızca geçerli soru-cevap çiftleri (bozuk ["q","a"] gibi maddeler gösterilmez)"""
    out = []
    for x in p.get("sss") or []:
        if isinstance(x, (list, tuple)) and len(x) >= 2:
            q, a = str(x[0]).strip(), str(x[1]).strip()
            if len(q) >= 5 and len(a) >= 5: out.append((q, a))
    return out

def sss_html(p):
    s = sss_temiz(p)
    if not s: return ""
    items = "".join(f'<div class="sq"><h3>{e(q)}</h3><p>{e(a)}</p></div>' for q, a in s[:4])
    return f'<section class="sss" aria-labelledby="sss-h"><h2 id="sss-h">Merak edilenler</h2>{items}</section>'

def sss_ld(p, full):
    s = sss_temiz(p)
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
    _q = urllib.parse.quote
    share = ('<section class="sharek" aria-label="Paylaş"><svg class="atac" viewBox="0 0 24 24" width="58" height="58" aria-hidden="true"><path d="M15 6.5v10a3 3 0 0 1-6 0V5a2 2 0 0 1 4 0v10.5a1 1 0 0 1-2 0V7.5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg><h2>Bu haberi paylaşın</h2><div class="share">'
             f'<a href="https://twitter.com/intent/tweet?url={_q(full)}&text={_q(p["title"])}" rel="noopener nofollow" target="_blank">{ico("duyur", 18)}X\'te paylaş</a>'
             f'<a href="https://www.facebook.com/sharer/sharer.php?u={_q(full)}" rel="noopener nofollow" target="_blank">{ico("topluluk", 18)}Facebook</a>'
             f'<a href="https://wa.me/?text={_q(p["title"] + " " + full)}" rel="noopener nofollow" target="_blank">{ico("sohbet", 18)}WhatsApp</a>'
             f'<a href="mailto:?subject={_q(p["title"])}&body={_q(full)}">{ico("zarf", 18)}E-posta</a>'
             f'<button type="button" data-u="{full}" onclick="var b=this;(navigator.clipboard?navigator.clipboard.writeText(b.dataset.u):Promise.reject()).then(function(){{b.lastChild.textContent=\'Kopyalandı\'}}).catch(function(){{}})">{ico("baglanti", 18)}<span>Bağlantıyı kopyala</span></button>'
             '</div></section>')
    tur = p.get("tur", "Haber")
    ld = {"@context": "https://schema.org", "@type": "AnalysisNewsArticle" if tur == "Analiz" else "NewsArticle", "headline": p["title"], "description": p["desc"],
          "datePublished": iso(p), "dateModified": (p["updated"] + (":00+03:00" if "T" in p["updated"] else "")) if p.get("updated") else iso(p),
          "mainEntityOfPage": {"@type": "WebPage", "@id": full}, "url": full, "inLanguage": "tr-TR",
          "articleSection": p["cats"][0], "keywords": ", ".join(p["tags"]), "wordCount": p["words"],
          "isAccessibleForFree": True, **({"editor": {"@type": "Person", "name": YAZARLAR[p["denetleyen"]]["kisi"], **({"honorificPrefix": YAZARLAR[p["denetleyen"]]["unvan"]} if YAZARLAR[p["denetleyen"]]["unvan"] else {}), "url": SITE + YAZARLAR[p["denetleyen"]]["url"], "@id": SITE + YAZARLAR[p["denetleyen"]]["url"] + "#kisi"}} if p.get("denetleyen") in YAZARLAR else {}), "image": [{"@type": "ImageObject", "url": SITE + p["img"], "width": 1200, "height": 630}] + [{"@type": "ImageObject", "url": SITE + u, "width": w, "height": h} for u, w, h in p.get("img_oran", {}).values()],
          "author": ({"@type": "Person", "name": YAZARLAR[p["yazar"]]["kisi"], **({"honorificPrefix": YAZARLAR[p["yazar"]]["unvan"]} if YAZARLAR[p["yazar"]]["unvan"] else {}), "url": SITE + YAZARLAR[p["yazar"]]["url"], "@id": SITE + YAZARLAR[p["yazar"]]["url"] + "#kisi"}
                     if p.get("yazar") in YAZARLAR else {"@type": "Organization", "name": NAME + " Editörlüğü", "url": SITE + "/yayin-ilkeleri/"}),
          "publisher": {"@type": "NewsMediaOrganization", "@id": SITE + "/#kurum", "name": NAME, "url": SITE + "/", "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 60}}}
    k0 = topcat(p)
    crumbs = [("/", "Anasayfa")] + ([(f"/haber-kategorisi/{CATS[k0][1]}/", CATS[CATS[k0][1]][0])] if CATS[k0][1] else []) + [(f"/haber-kategorisi/{k0}/", CATS[k0][0]), (p["url"], p["title"])]
    crumb = " › ".join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs[:-1])
    main = f"""<article class="post"><div class="crumb">{crumb}</div>
{kicker(p)}
<h1>{e(p['title'])}</h1>
<div class="meta pmeta"><span class="tur">{e(tur)}</span><span>{byline(p)}</span><span>{ico("clock", 16)}<time datetime="{iso(p)}">{when(p)}</time></span>{('<span>Güncellendi: ' + upd(p["updated"]) + '</span>') if p.get("updated") else ""}{save_btn(p)}</div>
<figure class="hero-img"><div class="pic"><img src="{p['img']}" {srcset(p)} sizes="(max-width:767px) 100vw, 760px" alt="{e(p['title'])}" width="1200" height="630" fetchpriority="high"></div>{credit_html(p)}</figure>
{inceleme_karti(p)}{ozet_html(p)}{karar_html(p)}<div class="body">{re.sub(r'(<table[\s\S]*?</table>)', r'<div class="tscroll">\1</div>', with_okumadan(p, govde_temiz(ic_bag(autolink(p)))))}</div>
{ornek_html(p)}{sss_html(p)}{kaynak_html(p)}{anket_html(p)}
{share}
{('<p class="konub"><b>Konu dosyası:</b>' + "".join(f'<a href="/konu/{k}/">{KONU_AD[k]}</a>' for k in p["konular"] if k in KONU_VAR) + '</p>') if any(k in KONU_VAR for k in p["konular"]) else ""}
<div class="tags"><b>Etiketler:</b>{tags_html}</div>
{yazar_kutu(p)}{gpref_kutu()}{kaynak_goster(p, full)}
{gecmis_html(p)}<div class="note">Bu {"analiz" if tur == "Analiz" else "haber"} {trdate(p['date'])} tarihinde yayımlanmıştır. Metindeki süreler, oranlar ve düzenlemeler o tarihteki mevzuatı yansıtır; sonradan değişmiş olabilir. İçerik genel bilgilendirme amaçlıdır, hukuki danışmanlık yerine geçmez. Hata bildirimi için <a href="/iletisim/?konu=duzeltme&amp;adres={SITE}{p['url']}#form" rel="nofollow">iletişim</a>.</div>
{pn}{rel_html}</article>""" + (ANKET_JS if p.get("anket") else "")
    write(p["file"], page(p["title"], p["desc"], p["url"], main, ld=[x for x in (ld, sss_ld(p, full)) if x], ogtype="article", crumbs=crumbs, img=p["img"], active=f"/haber-kategorisi/{k0}/",
                          ogek=f'\n<meta property="article:published_time" content="{iso(p)}">'
                               + (f'\n<meta property="article:modified_time" content="{e(str(p["updated"]))}">' if p.get("updated") else "")
                               + f'\n<meta property="article:section" content="{e(CATS[k0][0])}">'
                               + "".join(f'\n<meta property="article:tag" content="{e(t)}">' for t in p["tags"][:6])))

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
# konu dosyaları
_KARAR_KAT = {"yargi/yargitay", "yargi/danistay", "yargi/anayasa-mahkemesi", "yargi/aihm"}
for k, ad, tanim, _, mevzuat in KONULAR:
    if k not in KONU_VAR: continue
    its = KONU_HABER[k]; url = f"/konu/{k}/"
    son = its[:6]; goster = {q["slug"] for q in son}
    kararlar = [q for q in its if (set(q["catkeys"]) & _KARAR_KAT or q.get("karar")) and q["slug"] not in goster][:6]; goster |= {q["slug"] for q in kararlar}
    analizler = [q for q in its if q.get("tur") == "Analiz" and q["slug"] not in goster][:4]; goster |= {q["slug"] for q in analizler}
    kalan = [q for q in its if q["slug"] not in goster]
    diger_k = [x for x in KONU_VAR if x != k]
    blok = lambda baslik, ls: (f'<h2 class="sec-h">{baslik}</h2><ul class="rows one">' + "".join(row(q, "h3") for q in ls) + "</ul>") if ls else ""
    main = (f'<div class="crumb"><a href="/">Anasayfa</a> › <a href="/konular/">Konular</a> › {e(ad)}</div><h1 class="sec">{e(ad)}</h1>'
            f'<p class="sec-desc">{e(tanim)}</p>'
            f'<aside class="mzk"><b>Temel mevzuat</b><ul>' + "".join(f'<li><a href="{u}" target="_blank" rel="noopener">{e(t)}</a></li>' for t, u in mevzuat) +
            '</ul><small>Bağlantılar Cumhurbaşkanlığı Mevzuat Bilgi Sistemi\'ndeki güncel metne gider.</small></aside>'
            + blok("Son gelişmeler", son) + blok("Mahkeme kararları", kararlar) + blok("Analizler", analizler)
            + (f'<h2 class="sec-h">Arşivden</h2><ul class="liste">' + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a> <small>{trdate(q["date"])}</small></li>' for q in kalan[:80]) + "</ul>" if kalan else "")
            + f'<h2 class="sec-h">Diğer konu dosyaları</h2><ul class="chips">' + "".join(f'<li><a href="/konu/{x}/">{e(KONU_AD[x])}<small>{len(KONU_HABER[x])}</small></a></li>' for x in diger_k) + "</ul>")
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": ad, "description": tanim, "url": SITE + url, "inLanguage": "tr-TR",
          "isPartOf": {"@id": SITE + "/#site"}, "about": {"@type": "Thing", "name": ad},
          "mainEntity": {"@type": "ItemList", "numberOfItems": len(its), "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": SITE + q["url"]} for i, q in enumerate(its[:20])]}}
    write(url, page(f"{ad}: Haberler, Kararlar ve Mevzuat", f"{ad} konusundaki {len(its)} haber ve analiz. {tanim}", url, main, ld=ld,
                    noindex=len(its) < KONU_DIZIN, crumbs=[("/", "Anasayfa"), ("/konular/", "Konular"), (url, ad)], active="/konular/"))
write("/konular/", page("Konu Dosyaları", "Hukuk dallarına göre konu dosyaları: ceza, iş, aile, idare, vergi, ticaret hukuku ve daha fazlası; haberler, kararlar ve temel mevzuat bir arada.", "/konular/",
      '<div class="crumb"><a href="/">Anasayfa</a> › Konular</div><h1 class="sec">Konu Dosyaları</h1><p class="sec-desc">Haberler, mahkeme kararları ve temel mevzuat, hukuk dallarına göre bir arada.</p><ul class="konul">'
      + "".join(f'<li><a href="/konu/{k}/"><b>{e(KONU_AD[k])}</b><span>{e(next(t for kk, _, t, *_ in KONULAR if kk == k))}</span><small>{len(KONU_HABER[k])} haber</small></a></li>' for k in KONU_VAR) + "</ul>",
      crumbs=[("/", "Anasayfa"), ("/konular/", "Konular")]))

_tc = {}
for p in POSTS:
    if p["date"].year >= 2026:
        for t, s_ in zip(p["tags"], p["tagslugs"]): _tc[s_] = (t, _tc.get(s_, ("", 0))[1] + 1)
# keşfet: siteyi tanıtan ve bölümlere, konulara, arşive yönlendiren sayfa
_KONU_IKON = {"ceza-hukuku": "gavel", "is-hukuku": "brief", "aile-hukuku": "home", "idare-hukuku": "building", "anayasa-ve-temel-haklar": "court",
              "vergi-ve-sosyal-guvenlik": "doc", "kisisel-veriler-ve-bilisim": "laptop", "tuketici-haklari": "bookmark",
              "ticaret-ve-sermaye-piyasasi": "paper", "kira-ve-tasinmaz": "home"}
_son30 = datetime.date.today() - datetime.timedelta(days=30)
_tc30 = {}
for p in POSTS:
    if p["date"] >= _son30:
        for t, s_ in zip(p["tags"], p["tagslugs"]):
            if t.casefold() in {v[0].casefold() for v in CATS.values()}: continue
            _tc30[s_] = (t, _tc30.get(s_, ("", 0))[1] + 1)
_gundem = sorted(_tc30.items(), key=lambda x: (-x[1][1], x[1][0]))[:8]
_bolumler = [("/haber-kategorisi/manset/", "Gündem", "star", "Günün öne çıkan gelişmeleri", cat_count["manset"]),
             ("/mevzuat/", "Mevzuat", "doc", "Resmî Gazete, kanun ve yönetmelikler", len(_mv)),
             ("/analiz/", "Analiz", "pen", "Gelişmelerin hukuki çerçevesi", len(_an)),
             ("/haber-kategorisi/yargi/anayasa-mahkemesi/", "Anayasa Mahkemesi", "court", "İptal ve bireysel başvuru kararları", cat_count["yargi/anayasa-mahkemesi"]),
             ("/haber-kategorisi/yargi/yargitay/", "Yargıtay", "gavel", "Daire ve kurul kararları", cat_count["yargi/yargitay"]),
             ("/haber-kategorisi/yargi/danistay/", "Danıştay", "building", "İdari yargı kararları", cat_count["yargi/danistay"]),
             ("/haber-kategorisi/yargi/", "Yargı", "scale", "Mahkemeler ve yargı teşkilatı", cat_count["yargi"]),
             ("/haber-kategorisi/siyaset/", "Siyaset", "flag", "Siyasetin hukuki boyutu", cat_count["siyaset"]),
             ("/haber-kategorisi/barolar/", "Barolar", "brief", "Avukatlık ve meslek", cat_count["barolar"]),
             ("/haber-kategorisi/universiteler/", "Üniversiteler", "cap", "YÖK ve yükseköğretim", cat_count["universiteler"]),
             ("/haber-kategorisi/teknoloji/", "Teknoloji", "laptop", "Veri, bilişim ve internet", cat_count["teknoloji"]),
             ("/haber-kategorisi/basindan/", "Basından", "paper", "Basına yansıyanlar", cat_count["basindan"])]
_son_haber = POSTS[:3]
_kf = (
    '<div class="kf">'
    '<header class="kf-bas"><h1 class="sec">Keşfet</h1>'
    '<p class="kf-lead">Yüksek mahkeme kararlarını, mevzuat değişikliklerini ve gündemin hukuki boyutunu konuya, bölüme ve tarihe göre takip edin.</p>'
    f'<ul class="kf-say"><li><b>{len(POSTS)}</b><span>haber ve analiz</span></li><li><b>{len(KONU_VAR)}</b><span>konu dosyası</span></li>'
    f'<li><b>{sum(1 for p in POSTS if p["date"] >= datetime.date.today() - datetime.timedelta(days=7))}</b><span>son 7 günde</span></li><li><b>2010</b><span>yayında</span></li></ul></header>'
    '<form class="searchbox kf-ara" action="/arama/" method="get" role="search"><label class="sr" for="kq">Sitede ara</label>'
    '<input id="kq" name="q" type="search" placeholder="Karar, kanun, kurum veya konu ara…"><button type="submit">Ara</button></form>'
    + ('<p class="kf-oner"><span>Öne çıkan konular:</span>' + "".join(f'<a href="/arama/?q={urllib.parse.quote(t)}">{e(t)}</a>' for _, (t, n) in _gundem[:4]) + '</p>' if _gundem else "")
    + '<section class="kf-blok"><h2 class="sec-h">Şu an gündemde</h2><ol class="kf-son">'
    + "".join(f'<li><a href="{p["url"]}"><img src="{thumb(p)}" alt="" width="96" height="50" loading="lazy"><span><small>{e(p["catname"])} · {when(p)}</small><b>{e(p["title"])}</b></span></a></li>' for p in _son_haber)
    + '</ol><a class="kf-tum" href="/">Anasayfaya dön</a></section>'
    + '<section class="kf-blok"><h2 class="sec-h">Konu dosyaları</h2><p class="kf-not">Haberler, mahkeme kararları ve temel mevzuat, hukuk dallarına göre bir arada.</p><ul class="kf-konu">'
    + "".join(f'<li><a href="/konu/{k}/"><span class="kf-ik">{ico(_KONU_IKON.get(k, "doc"), 22)}</span><span class="kf-km"><b>{e(KONU_AD[k])}</b><small>Son: {e(KONU_HABER[k][0]["title"])}</small></span><em>{len(KONU_HABER[k])}</em></a></li>' for k in KONU_VAR)
    + '</ul></section>'
    + '<section class="kf-blok"><h2 class="sec-h">Bölümler</h2><ul class="kf-bol">'
    + "".join(f'<li><a href="{u}">{ico(i, 22)}<b>{t}</b><small>{a}</small><em>{n} haber</em></a></li>' for u, t, i, a, n in _bolumler if n)
    + '</ul></section>'
    + ('<section class="kf-blok"><h2 class="sec-h">Son 30 günün başlıkları</h2><ol class="kf-gun">'
       + "".join(f'<li><a href="/haber-etiketi/{s_}/"><i>{j + 1}</i><b>{e(t)}</b><small>{n} haber</small></a></li>' for j, (s_, (t, n)) in enumerate(_gundem))
       + '</ol></section>' if _gundem else "")
    + '<section class="kf-blok kf-ilke"><h2 class="sec-h">Nasıl çalışıyoruz</h2><ul>'
      '<li><b>Kaynak gösteriyoruz.</b> Her haberin altında dayanılan resmî belge ve haber kaynakları bağlantısıyla yer alır.</li>'
      '<li><b>Editör onayı.</b> Haberler yayımlanmadan önce editör tarafından kontrol edilir ve onaylanır.</li>'
      '<li><b>Açık düzeltme.</b> Bir bilgi değiştiğinde ya da hata bulunduğunda haber güncellenir; güncelleme geçmişi haberin altında görünür.</li>'
      + (f'<li><b>Hukuki denetim.</b> Hukuk danışmanlığı ve içerik denetimi <a href="{YAZARLAR[HUKUKI_DENETIM]["url"]}">{e(YAZARLAR[HUKUKI_DENETIM]["ad"])}</a> tarafından yürütülür.</li>' if HUKUKI_DENETIM else "")
      + 
      '</ul><p><a href="/yayin-ilkeleri/">Yayın ilkelerimiz</a> · <a href="/kunye/">Künye</a> · <a href="/iletisim/">Hata bildirin</a></p></section>'
    + '<section class="kf-blok"><h2 class="sec-h">Takip edin</h2><div class="kf-takip">'
      f'<a href="https://x.com/HukukiHaberTR" rel="me noopener" target="_blank">{ico("takip", 20)}<span><b>X</b><small>@HukukiHaberTR</small></span></a>'
      f'<a href="/feed/index.xml">{ico("rss", 20)}<span><b>RSS</b><small>Akış okuyucunuzda</small></span></a>'
      f'<a href="/kaydedilenler/">{ico("bookmark", 20)}<span><b>Kaydedilenler</b><small>Bu cihazda sakladıklarınız</small></span></a>'
      '</div></section>'
    + '<section class="kf-blok"><h2 class="sec-h">Arşiv</h2><p class="kf-not">2010\'dan bu yana yayımlanan tüm haberler, yıllara göre.</p><ul class="kf-yil">'
    + "".join(f'<li><a href="/{y}/">{y}</a></li>' for y in sorted({p["date"].year for p in POSTS}, reverse=True)) + '<li><a href="/arsiv/">Tüm arşiv</a></li></ul></section>'
    '</div>')
write("/kesfet/", page("Keşfet", "Hukuki Haberler'i keşfedin: konu dosyaları, bölümler, son 30 günün gündem başlıkları, yayın ilkeleri ve 2010'dan bu yana arşiv.", "/kesfet/",
      _kf, crumbs=[("/", "Anasayfa"), ("/kesfet/", "Keşfet")], side=False))
write("/kaydedilenler/", page("Kaydedilenler", "Bu cihazda kaydettiğiniz haberler.", "/kaydedilenler/",
      '<h1 class="sec">Kaydedilenler</h1><p class="sec-desc">Kaydettiğiniz haberler yalnızca bu cihazdaki tarayıcıda saklanır; hesap veya sunucu kaydı tutulmaz.</p><div id="kayitlar"><noscript><p class="empty">Bu özellik için tarayıcınızda JavaScript açık olmalıdır.</p></noscript></div>', noindex=True))
with open(os.path.join(OUT, "arama.json"), "w", encoding="utf-8") as f:
    json.dump([{"t": p["title"], "u": p["url"], "d": p["desc"], "g": " ".join(p["tags"]), "k": CATS[topcat(p)][0], "z": trdate(p["date"]), "i": thumb(p)} for p in POSTS], f, ensure_ascii=False, separators=(",", ":"))
write("/arama/", page("Arama", "Hukuki Haberler içinde haber, karar ve mevzuat araması.", "/arama/",
      '<h1 class="sec">Arama</h1><form id="aramaform" class="searchbox" action="/arama/" method="get" role="search"><label class="sr" for="aq">Aranacak kelime</label><input id="aq" name="q" type="search" placeholder="Haber, karar, mevzuat veya konu ara…"><button type="submit">Ara</button></form><div id="sonuc" aria-live="polite"><noscript><p class="empty">Arama için tarayıcınızda JavaScript açık olmalıdır.</p></noscript></div>',
      noindex=True, extra=SEARCH_JS))

# etiketler
ETIKET_ALT_SINIR = 3   # bundan az haberi olan etiket sayfası dizine girmez, sitemap'e eklenmez
_KAT_ADLARI = {v[0].casefold() for v in CATS.values()}
def etiket_dizinde(s):
    d = tag_posts[s]
    return len(d["posts"]) >= ETIKET_ALT_SINIR and d["name"].casefold() not in _KAT_ADLARI   # kategoriyle aynı adlı etiket kategori sayfasının kopyasıdır
tag_posts = {}
for p in POSTS:
    for t, s in zip(p["tags"], p["tagslugs"]):
        tag_posts.setdefault(s, {"name": t, "posts": []})["posts"].append(p)
for s, d in tag_posts.items():
    items = sorted(d["posts"], key=lambda p: p["date"], reverse=True)
    crumb = f'<a href="/">Anasayfa</a> › Etiket'
    listing(f"{d['name']}", kisalt(f"“{d['name']}” konusunda yayımlanan {len(items)} haber ve analiz. Son gelişme: {items[0]['title']}", 158), f"/haber-etiketi/{s}/", items, crumb=crumb,
            noindex=not etiket_dizinde(s))   # tek-iki haberli ya da kategoriyle aynı adlı etiket sayfaları dizine girmez

# aylık arşiv
months = {}
for p in POSTS: months.setdefault((p["date"].year, p["date"].month), []).append(p)
for (y, m), items in months.items():
    listing(f"{AYLAR[m-1]} {y}", f"{AYLAR[m-1]} {y} ayında Hukuki Haberler'de yayımlanan {len(items)} hukuk, yargı ve mevzuat haberi.", f"/{y}/{m:02d}/", items, crumb=f'<a href="/">Anasayfa</a> › <a href="/arsiv/">Arşiv</a> › {y}')
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
    listing(f"{y} yılı haberleri", f"{y} yılında Hukuki Haberler'de yayımlanan {len(items)} hukuk, yargı ve mevzuat haberi; aylara göre arşiv.", f"/{y}/", items, crumb=f'<a href="/">Anasayfa</a> › <a href="/arsiv/">Arşiv</a>')
def _ar_satir(p):
    return (f'<li data-t="{e(_tr_kucuk(p["title"]))}"><time datetime="{p["date"].strftime("%Y-%m-%d")}">{p["date"].day}<small>{AYLAR[p["date"].month-1][:3]}</small></time>'
            f'<a href="{p["url"]}">{e(p["title"])}</a><span class="ar-k">{e(CATS[topcat(p)][0])}</span></li>')
_ar_yil, _ar_bolum = [], []
_son_yil = max(years)
for y in sorted(years, reverse=True):
    yp = [p for p in POSTS if p["date"].year == y]
    _ar_yil.append(f'<li><a href="#y{y}">{y}<small>{len(yp)}</small></a></li>')
    enc = max(len(months.get((y, m), [])) for m in range(1, 13))
    hucre = ""
    for m in range(1, 13):
        n_ = len(months.get((y, m), []))
        if n_:
            hucre += (f'<li><a href="/{y}/{m:02d}/"><b>{AYLAR[m-1]}</b><small>{n_} haber</small>'
                      f'<i style="--o:{max(.06, n_ / enc):.2f}"></i></a></li>')
        else:
            _gel = (y, m) > (datetime.datetime.now().year, datetime.datetime.now().month)
            hucre += f'<li class="bos"><span><b>{AYLAR[m-1]}</b><small>{"&nbsp;" if _gel else "yayın yok"}</small></span></li>'
    liste = ""
    for m in range(12, 0, -1):
        ms = months.get((y, m))
        if not ms: continue
        liste += f'<h3 class="ar-ayb">{AYLAR[m-1]} {y}<small>{len(ms)}</small></h3><ul class="ar-l">{"".join(_ar_satir(p) for p in ms)}</ul>'
    _ar_bolum.append(f'<section class="ar-y" id="y{y}"><div class="ar-yh"><h2><a href="/{y}/">{y}</a></h2><span>{len(yp)} haber</span></div>'
                     f'<ol class="ar-takvim" aria-label="{y} ayları">{hucre}</ol>'
                     f'<details class="ar-d"{" open" if y == _son_yil else ""}><summary>{y} yılındaki tüm başlıklar</summary>{liste}</details></section>')
_ilk_yil = min(years)
AR = (f'<div class="crumb"><a href="/">Anasayfa</a> › Arşiv</div><h1 class="sec">Arşiv</h1>'
      f'<p class="sec-desc">{_ilk_yil}\'dan bu yana yayımlanan {len(POSTS)} haber ve analiz. Yıla ya da aya göre gezinebilir, başlıklar içinde arama yapabilirsiniz.</p>'
      f'<div class="ar-ust"><label class="ar-ara"><span class="sr">Arşivde ara</span>{ico("search", 18)}<input id="arq" type="search" placeholder="Başlıklarda ara, örneğin nafaka" autocomplete="off"></label>'
      f'<nav class="ar-yil" aria-label="Yıllar"><ul>{"".join(_ar_yil)}</ul></nav></div><p class="ar-sonuc" id="arn" hidden></p>'
      + "".join(_ar_bolum) +
      """<script>(function(){var q=document.getElementById('arq'),n=document.getElementById('arn');if(!q)return;
function tr(s){return s.toLocaleLowerCase('tr').normalize('NFC')}
q.addEventListener('input',function(){var v=tr(q.value.trim()),say=0;document.querySelectorAll('.ar-y').forEach(function(sec){var g=0;
sec.querySelectorAll('.ar-l li').forEach(function(li){var ok=!v||li.dataset.t.indexOf(v)>-1;li.hidden=!ok;if(ok)g++});
sec.querySelectorAll('.ar-ayb').forEach(function(h){var u=h.nextElementSibling,k=u.querySelectorAll('li:not([hidden])').length;h.hidden=!k;u.hidden=!k});
var d=sec.querySelector('details');if(v){d.open=g>0}sec.hidden=v&&!g;sec.querySelector('.ar-takvim').hidden=!!v;say+=g});
n.hidden=!v;n.textContent=v?(say?say+' başlık bulundu':'Bu aramayla eşleşen başlık yok. Farklı bir kelime deneyin.'):''})})()</script>""")
write("/arsiv/", page("Arşiv", "Hukuki Haberler arşivi: 2010'dan bu yana yayımlanan tüm hukuk, yargı ve mevzuat haberleri, yıllara ve aylara göre.", "/arsiv/", AR,
      crumbs=[("/", "Anasayfa"), ("/arsiv/", "Arşiv")]))

# sabit sayfalar
HAKKINDA = """<p class="lead">Hukuki Haberler, 2010 yılında yayına başlayan bağımsız bir hukuk haber sitesidir.</p>
<p>Sitede yüksek mahkeme kararları, Adalet Bakanlığı ve YÖK gibi kurumların duyuruları, barolar ve avukatlık mesleğine ilişkin gelişmeler ile gündemin hukuku ilgilendiren başlıkları haber diliyle aktarılır. Amaç, hukukçu olmayan okurun da takip edebileceği sadelikte, kaynağı belli ve tarihli bir kayıt tutmaktır.</p>
<h2>Yayın ilkeleri</h2>
<p>Haberler, yayımlandıkları tarihte kamuya açık kaynaklara — Resmî Gazete, kurum duyuruları, mahkeme kararları ve ulusal basın — dayanır. Her haberin altında yayın tarihi yer alır; süre, oran ve tutar gibi bilgiler o tarihin mevzuatını yansıtır ve sonradan değişmiş olabilir. Siyasi gelişmeler yalnızca hukuki boyutuyla ele alınır; site hiçbir siyasi görüşü savunmaz.</p>
<h2>Sorumluluk sınırı</h2>
<p>Sitedeki içerik genel bilgilendirme amaçlıdır; hukuki görüş, danışmanlık ya da vekâlet ilişkisi oluşturmaz. Somut bir uyuşmazlık için bir avukata başvurulmalıdır. Baroların iletişim bilgilerine <a href="https://www.barobirlik.org.tr/" rel="noopener" target="_blank">Türkiye Barolar Birliği</a> sitesinden ulaşılabilir.</p>"""
write("/hakkinda/", page("Hakkında", "Hukuki Haberler: 2010'dan bu yana hukuk, yargı ve mevzuat gündemini izleyen bağımsız haber sitesi.", "/hakkinda/",
      f'<article class="post static"><h1>Hakkında</h1><div class="body">{HAKKINDA}</div></article>'))
ILETISIM = """<p class="lead">Haber ihbarı, düzeltme ve cevap hakkı talepleri, içerikle ilgili şikâyetler ve kişisel veri başvuruları için bize e-posta ile ya da aşağıdaki formla ulaşabilirsiniz. Hukuki Haberler bağımsız bir yayın sitesidir; bireysel hukuki danışmanlık vermez.</p>
<div class="ilt-kanal">
<div><h2>E-posta</h2><p><a class="ilt-posta" href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a></p><p>Yazı işleri tarafından okunur. Ekli belge göndermeniz gerekiyorsa (karar, resmî yazı, fotoğraf) e-postayı kullanın.</p></div>
<div><h2>İletişim formu</h2><p>Formdan gelen her mesaja bir kayıt numarası verilir. Yazışmalarda bu numarayı belirtmeniz talebinizin takibini kolaylaştırır.</p><p><a href="#form">Forma git ↓</a></p></div>
</div>
<h2>Yanıt süreleri</h2>
<ul>
<li><b>Düzeltme, cevap hakkı ve içerik şikâyetleri:</b> öncelikli olarak değerlendirilir; kural olarak üç iş günü içinde yanıtlanır.</li>
<li><b>Haber ihbarları:</b> doğrulama gerektirdiğinden süre konuya göre değişir. Yayımlanmayan ihbarlara ayrıca yanıt verilmeyebilir.</li>
<li><b>Kişisel veri (KVKK) başvuruları:</b> 6698 sayılı Kanun'un 13. maddesi uyarınca en geç otuz gün içinde sonuçlandırılır.</li>
</ul>
<h2 id="kurallar">Form kuralları</h2>
<p>Talebinizin hızlı ve doğru değerlendirilebilmesi için lütfen aşağıdaki kurallara uyun.</p>
<details class="ilt-kural" open><summary>Konuya göre göndermeniz gereken bilgiler</summary>
<ul>
<li><b>Haber ihbarı:</b> olayın yeri ve zamanı ile doğrulanabilir bir kaynak (resmî duyuru, karar, belge bağlantısı). Doğrulanamayan ihbarlar yayımlanmaz. İhbarda bulunan kişinin kimliği yayımlanmaz ve üçüncü kişilerle paylaşılmaz.</li>
<li><b>Düzeltme talebi:</b> haberin adresi, hatalı olduğunu düşündüğünüz bilgi ve doğrusunu gösteren kaynak. Doğrulanan düzeltmeler habere işlenir; haberin altında düzeltme tarihi ve ne değiştiği gösterilir.</li>
<li><b>Cevap ve düzeltme hakkı:</b> haberin adresi ve yayımlanmasını istediğiniz cevap ya da düzeltme metni. Metin, haberle ilgili olmalı; hakaret, suç isnadı ya da üçüncü kişilerin haklarını ihlal eden ifade içermemelidir. Talepler mevzuattaki süre ve koşullara göre değerlendirilir.</li>
<li><b>Kişilik hakkı / içerik kaldırma talebi:</b> haberin adresi, hakkınızı ihlal ettiğini düşündüğünüz ifade ve gerekçeniz. Başkası adına başvuruyorsanız yetkinizi (vekâlet, kanuni temsil) belirtin.</li>
<li><b>KVKK başvurusu:</b> hangi hakkınızı kullanmak istediğinizi (bilgi talebi, düzeltme, silme vb.) ve ilgili sayfayı belirtin. Kimliğinizi doğrulamak için ek bilgi istenebilir.</li>
<li><b>Teknik sorun:</b> sorunun görüldüğü sayfa adresi, cihaz ve tarayıcı bilgisi.</li>
</ul></details>
<details class="ilt-kural"><summary>Form üzerinden kabul edilmeyen talepler</summary>
<ul>
<li>Bireysel hukuki danışmanlık, somut bir dosya hakkında görüş ya da dilekçe hazırlama talepleri. Bu talepler için bulunduğunuz ildeki bir avukata ya da baroların adli yardım bürolarına başvurabilirsiniz.</li>
<li>Avukat önerisi ya da avukat iletişim bilgisi talepleri. Sitede yer alan avukatlar yalnızca yayın içeriğini hukuki açıdan inceler; site aracılığıyla iş kabul etmez.</li>
<li>Reklam, sponsorlu içerik, tanıtım yazısı ve bağlantı satışı teklifleri. Sitede ücret karşılığı yayımlanan içerik yoktur.</li>
<li>Hakaret, tehdit ya da nefret söylemi içeren mesajlar. Bu tür mesajlar yanıtlanmaz.</li>
</ul></details>
<details class="ilt-kural"><summary>Mesajınızı yazarken</summary>
<ul>
<li>Başkalarına ait kişisel verileri (T.C. kimlik numarası, adres, sağlık bilgisi, dosya numarası gibi) talebiniz için zorunlu değilse paylaşmayın.</li>
<li>Kendi özel nitelikli kişisel verilerinizi (sağlık, ceza mahkûmiyeti vb.) formda paylaşmamanızı öneririz; gerekiyorsa e-posta ile iletin.</li>
<li>Mesaj en az 30, en fazla 4.000 karakter olabilir; en fazla beş bağlantı içerebilir. Aynı bağlantıdan saatte en fazla beş mesaj gönderilebilir.</li>
<li>Düzeltme, cevap hakkı ve içerik şikâyetlerinde ilgili haberin adresini yazmak zorunludur.</li>
</ul></details>
<h2 id="form">İletişim formu</h2>
<form class="ilt-form" id="ilt-form" method="post" action="/api/iletisim" novalidate>
<div class="ilt-iki"><p><label for="ilt-ad">Ad soyad <span aria-hidden="true">*</span></label><input id="ilt-ad" name="ad" type="text" autocomplete="name" required minlength="3" maxlength="80"></p>
<p><label for="ilt-eposta">E-posta <span aria-hidden="true">*</span></label><input id="ilt-eposta" name="eposta" type="email" autocomplete="email" inputmode="email" required maxlength="160"></p></div>
<div class="ilt-iki"><p><label for="ilt-konu">Konu <span aria-hidden="true">*</span></label><select id="ilt-konu" name="konu" required><option value="">Seçin</option><option value="ihbar">Haber ihbarı</option><option value="duzeltme">Düzeltme talebi</option><option value="cevap">Cevap ve düzeltme hakkı</option><option value="icerik">Kişilik hakkı / içerik kaldırma talebi</option><option value="kvkk">KVKK başvurusu</option><option value="teknik">Teknik sorun</option><option value="diger">Diğer</option></select></p>
<p><label for="ilt-tel">Telefon <small>(isteğe bağlı)</small></label><input id="ilt-tel" name="telefon" type="tel" autocomplete="tel" inputmode="tel" maxlength="30"></p></div>
<p id="ilt-adres-p"><label for="ilt-adres">İlgili haberin adresi <small id="ilt-adres-not">(düzeltme, cevap ve içerik taleplerinde zorunlu)</small></label><input id="ilt-adres" name="adres" type="url" inputmode="url" maxlength="400" placeholder="https://hukukihaberler.com/..."></p>
<p><label for="ilt-baslik">Başlık <span aria-hidden="true">*</span></label><input id="ilt-baslik" name="baslik" type="text" required minlength="5" maxlength="140"></p>
<p><label for="ilt-mesaj">Mesajınız <span aria-hidden="true">*</span></label><textarea id="ilt-mesaj" name="mesaj" rows="8" required minlength="30" maxlength="4000"></textarea><small class="ilt-sayac" id="ilt-sayac" aria-live="polite">0 / 4000</small></p>
<p class="ilt-gizli" aria-hidden="true"><label for="ilt-web">Bu alanı boş bırakın</label><input id="ilt-web" name="web" type="text" tabindex="-1" autocomplete="off"></p>
<p class="ilt-onay"><label><input type="checkbox" name="onay" value="1" required> <span>Aşağıdaki <a href="#aydinlatma">aydınlatma metnini</a> ve <a href="#kurallar">form kurallarını</a> okudum. <span aria-hidden="true">*</span></span></label></p>
<p class="ilt-hata" id="ilt-hata" role="alert" hidden></p>
<button type="submit" class="ilt-gonder">Gönder</button>
<p class="ilt-not">* ile işaretli alanlar zorunludur. Form çalışmazsa <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine yazabilirsiniz.</p>
</form>
<div class="ilt-tamam" id="ilt-tamam" tabindex="-1" hidden><h3>Mesajınız alındı</h3><p>Kayıt numaranız: <b id="ilt-no"></b></p><p>Talebiniz yazı işleri tarafından değerlendirilecek ve yanıt e-posta adresinize gönderilecektir.</p></div>
<h2 id="aydinlatma">Kişisel verilerin işlenmesine ilişkin aydınlatma metni</h2>
<p>Bu metin, 6698 sayılı Kişisel Verilerin Korunması Kanunu'nun 10. maddesi uyarınca iletişim formu ve e-posta yoluyla bize ulaşan kişileri bilgilendirmek amacıyla hazırlanmıştır.</p>
<ul>
<li><b>Veri sorumlusu:</b> Hukuki Haberler (hukukihaberler.com), iletisim@hukukihaberler.com.</li>
<li><b>İşlenen veriler:</b> ad soyad, e-posta adresi, isteğe bağlı olarak telefon numarası, konu, ilgili sayfa adresi, başlık ve mesaj içeriği, gönderim zamanı, bağlantının ülke bilgisi ve tarayıcı türü. Kötüye kullanımı önlemek için IP adresinizden geri döndürülemez bir özet üretilir ve bir saat içinde silinir; IP adresiniz saklanmaz.</li>
<li><b>Amaç:</b> talebinizi değerlendirmek ve size yanıt vermek; düzeltme, cevap hakkı ve içerik şikâyetlerine ilişkin yükümlülükleri yerine getirmek; formun kötüye kullanılmasını önlemek.</li>
<li><b>Hukuki sebep:</b> Kanun'un 5. maddesinin 2. fıkrasındaki hukuki yükümlülüğün yerine getirilmesi (ç), bir hakkın tesisi, kullanılması veya korunması (e) ve ilgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla veri sorumlusunun meşru menfaati (f).</li>
<li><b>Aktarım:</b> Veriler üçüncü kişilere satılmaz ve pazarlama amacıyla kullanılmaz. Form altyapısı ve barındırma hizmeti Cloudflare, Inc. tarafından sağlanır; veriler bu kapsamda yurt dışındaki sunucularda işlenebilir. Yasal zorunluluk hâlinde yetkili kamu kurum ve kuruluşlarıyla ya da yargı mercileriyle paylaşılabilir.</li>
<li><b>Saklama süresi:</b> Mesajlar talebin sonuçlanmasından itibaren en fazla iki yıl saklanır, ardından silinir.</li>
<li><b>Haklarınız:</b> Kanun'un 11. maddesi uyarınca verilerinizin işlenip işlenmediğini öğrenme, bilgi talep etme, düzeltilmesini ya da silinmesini isteme ve itiraz etme haklarına sahipsiniz. Başvurularınızı bu formdan "KVKK başvurusu" konusuyla ya da e-posta ile iletebilirsiniz.</li>
</ul>"""
ILETISIM_JS = r"""<script>(function(){var f=document.getElementById('ilt-form');if(!f)return;
var q=new URLSearchParams(location.search),k=document.getElementById('ilt-konu'),a=document.getElementById('ilt-adres'),m=document.getElementById('ilt-mesaj'),s=document.getElementById('ilt-sayac'),h=document.getElementById('ilt-hata');
f.dataset.t=Date.now();
if(q.get('konu')&&k.querySelector('option[value="'+q.get('konu').replace(/[^a-z]/g,'')+'"]'))k.value=q.get('konu');
if(q.get('adres')&&/^https:\/\/hukukihaberler\.com\//.test(q.get('adres')))a.value=q.get('adres');
function zor(){var z=['duzeltme','cevap','icerik'].indexOf(k.value)>=0;a.required=z;}
k.addEventListener('change',zor);zor();
m.addEventListener('input',function(){s.textContent=m.value.length+' / 4000';});
f.addEventListener('submit',function(e){e.preventDefault();h.hidden=true;
var v={};new FormData(f).forEach(function(x,y){v[y]=x;});v.onay=f.onay.checked;v.t=+f.dataset.t;
var hata=[];if((v.ad||'').trim().length<3)hata.push('Ad soyad en az 3 karakter olmalı.');
if(!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test((v.eposta||'').trim()))hata.push('Geçerli bir e-posta adresi yazın.');
if(!v.konu)hata.push('Bir konu seçin.');if(a.required&&!(v.adres||'').trim())hata.push('Bu konu için ilgili haberin adresini yazın.');
if((v.baslik||'').trim().length<5)hata.push('Başlık en az 5 karakter olmalı.');if((v.mesaj||'').trim().length<30)hata.push('Mesaj en az 30 karakter olmalı.');
if(!v.onay)hata.push('Aydınlatma metnini okuduğunuzu onaylayın.');
if(hata.length){h.textContent=hata.join(' ');h.hidden=false;h.focus&&h.scrollIntoView({block:'center'});return;}
var b=f.querySelector('button[type=submit]');b.disabled=true;b.textContent='Gönderiliyor…';
fetch('/api/iletisim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(v)}).then(function(r){return r.json().then(function(j){return[r.status,j]})}).then(function(x){
if(x[0]===200&&x[1].tamam){f.hidden=true;var t=document.getElementById('ilt-tamam');document.getElementById('ilt-no').textContent=x[1].no||'—';t.hidden=false;t.focus();t.scrollIntoView({block:'center'});}
else{h.textContent=x[1].hata||'Mesaj gönderilemedi. Lütfen e-posta ile yazın.';h.hidden=false;}}).catch(function(){h.textContent='Bağlantı hatası. Lütfen yeniden deneyin ya da e-posta ile yazın.';h.hidden=false;}).then(function(){b.disabled=false;b.textContent='Gönder';});});})();</script>"""
write("/iletisim/", page("İletişim", "Hukuki Haberler iletişim: e-posta adresi, iletişim formu, düzeltme ve cevap hakkı talepleri, KVKK başvuruları ve form kuralları.", "/iletisim/",
      f'<article class="post static"><h1>İletişim</h1><div class="body">{ILETISIM}</div></article>', extra=ILETISIM_JS))
GIZ = """<p class="lead">Bu sayfa, Hukuki Haberler'i ziyaret ettiğinizde hangi verilerin işlendiğini ve çerez tercihinizi nasıl değiştirebileceğinizi açıklar.</p>
<h2>Toplanan veriler</h2>
<p>Sitede üyelik ve yorum sistemi yoktur. Okurlar yalnızca <a href="/iletisim/">iletişim formu</a> ya da e-posta yoluyla bize ad, e-posta adresi ve mesaj iletebilir; bu bilgiler yalnızca talebi değerlendirmek ve yanıt vermek için kullanılır, en fazla iki yıl saklanır. Ayrıntılar iletişim sayfasındaki <a href="/iletisim/#aydinlatma">aydınlatma metnindedir</a>.</p>
<h2 id="cerezler">Çerezler ve ziyaret ölçümü</h2>
<ul class="liste">
<li><b>Google Analytics 4 (Google LLC):</b> Hangi haberlerin okunduğunu ve ziyaretçilerin siteye nereden geldiğini toplu olarak ölçmek için kullanılır. Analiz çerezleri (<code>_ga</code>, <code>_ga_*</code>) <b>yalnızca izin verirseniz</b> tarayıcınıza yazılır. İzin vermezseniz Google'a çerez ve tanımlayıcı içermeyen, kimliksiz ölçüm sinyalleri gönderilir. Reklam ve kişiselleştirme amaçlı izinler her durumda kapalıdır. Veriler Google tarafından yurt dışındaki sunucularda işlenebilir.</li>
<li><b>Cloudflare Web Analytics:</b> Çerez kullanmayan, bireysel ziyaretçiyi tanımlamayan toplu sayfa görüntüleme ölçümüdür.</li>
<li><b>Tarayıcı depolaması:</b> "Kaydedilenler" listesi, ankette oy verdiğiniz bilgisi ve çerez tercihiniz yalnızca kendi tarayıcınızda (localStorage) saklanır; sunucuya gönderilmez.</li>
</ul>
<p><button type="button" class="btn-cerez" id="cerezdegis">Çerez tercihimi değiştir</button></p>
<h2>Okur anketleri</h2>
<p>Bazı haberlerdeki anketlerde verilen oylar toplu sayı olarak tutulur. Aynı ankete kısa sürede tekrar oy verilmesini önlemek için IP adresinizden türetilen ve geri çevrilemeyen bir özet 24 saat saklanır; IP adresinin kendisi kaydedilmez.</p>
<h2>Barındırma ve güvenlik kayıtları</h2>
<h2>Ziyaret istatistikleri</h2>
<p>Hangi haberlerin okunduğunu ve okurların siteye nereden geldiğini toplu olarak görebilmek için kendi sunucumuzda çerezsiz bir sayaç kullanılır. Sayaç yalnızca açılan sayfanın adresini, sizi yönlendiren sitenin adını, ekran genişliğinden çıkarılan cihaz türünü ve ülke bilgisini kaydeder. IP adresiniz saklanmaz; aynı gün içindeki tekrar ziyaretleri ayırt etmek için IP adresi ve tarayıcı bilgisinden, her gün değiştirilen rastgele bir anahtarla geri döndürülemez bir özet üretilir ve ertesi gün bu anahtar silinir. Bu kayıtlarla kimliğiniz belirlenemez; kayıtlar en fazla 400 gün tutulur.</p>
<p>Site Cloudflare altyapısında barındırılır. Barındırma hizmeti, güvenlik ve performans amacıyla IP adresi ve istek zamanı gibi teknik kayıtları kısa süreli tutabilir; bu kayıtlar tarafımızca kimlik tespiti için kullanılmaz.</p>
<h2>Dış bağlantılar</h2>
<p>Haberlerde yer alan dış bağlantılar (Resmî Gazete, mahkeme siteleri, basın kuruluşları, X) ve paylaşım düğmeleri ilgili sitelerin kendi gizlilik politikalarına tabidir. Paylaşım düğmeleri siz tıklamadıkça bu sitelere veri göndermez.</p>
<h2>Haklarınız ve iletişim</h2>
<p>6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamındaki talepleriniz için <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine yazabilir ya da <a href="/iletisim/?konu=kvkk#form">iletişim formunu</a> kullanabilirsiniz.</p>"""
def _mt(x): return html.escape(str(x), quote=False)   # metin düğümü: kesme işareti olduğu gibi kalır
def _tr_kucuk_bas(t): return (t[:1].replace("I", "ı").replace("İ", "i").lower() + t[1:]) if t else t
def _tamlayan(ad):
    """özel ada ilgi eki: Tekin'in, Tahtasız'ın, Kaya'nın, Öztürk'ün"""
    sesli = [c for c in ad.lower() if c in "aeıioöuü"]
    son = sesli[-1] if sesli else "e"
    ek = {"a": "ın", "ı": "ın", "e": "in", "i": "in", "o": "un", "u": "un", "ö": "ün", "ü": "ün"}[son]
    return ad + "'" + ("n" if ad[-1:].lower() in "aeıioöuü" else "") + ek
def _yz_bag(y): return f'<a href="{y["url"]}">{html.escape(y["ad"], quote=False)}</a>'
_YZ_SIRALI = list(GORUNEN_YAZARLAR.values())
YAZI_ISLERI = "".join(f'{_mt(y["rol"] or "Yazar")}{(" (" + _mt(_tr_kucuk_bas(y["alan"])) + ")") if y["alan"] else ""}: {_yz_bag(y)}. ' for y in _YZ_SIRALI)
def _buro_parca(k):
    v = YAZAR_KAYIT[k]; b = v.get("buro_sitesi")
    if not (b and len(b) == 2 and b[1]): return ""
    return (f'{_mt(YAZARLAR[k]["unvan"] + " " if YAZARLAR[k]["unvan"] else "")}{_mt(_tamlayan(v["kisi"].split()[-1]))} '
            f'<a href="{e(b[1])}" rel="noopener" target="_blank">{_mt(b[0])}</a>')
_burolar = [x for x in (_buro_parca(k) for k in GORUNEN_YAZARLAR) if x]
_BURO_CUMLE = ((", ".join(_burolar[:-1]) + " ve " + _burolar[-1] if len(_burolar) > 1 else _burolar[0])
               + (" avukatlık bürosu sitelerine" if len(_burolar) > 1 else " avukatlık bürosu sitesine")
               + ", yalnızca konuyla doğrudan ilgili rehber içerikler için ve sınırlı sayıda bağlantı verilebilir. ") if _burolar else ""
DENETIM_PARAGRAF = (("<p>Hukuki içerik denetimini ve alanındaki yazı işlerini şu avukatlar yürütür: "
                     + "; ".join(f'{_yz_bag(y)} ({_mt(_tr_kucuk_bas(y["rol"]))}{"; " + _mt(_tr_kucuk_bas(y["alan"])) if y["alan"] else ""})' for y in _YZ_SIRALI) + ". "
                     + _BURO_CUMLE
                     + "Bu bağlantılar haberlerin içeriğini veya yayın kararlarını etkilemez; sitede ücret karşılığı yayımlanmış içerik yoktur.</p>") if _YZ_SIRALI else
                    "<p>Sitede ücret karşılığı yayımlanmış içerik yoktur.</p>")
KUNYE = """<p class="lead">Hukuki Haberler, 2010 yılında yayına başlayan bağımsız bir hukuk haber sitesidir. Ticari bir kuruluşa, hukuk bürosuna ya da baroya bağlı değildir.</p>
<h2>Yayın ilkeleri</h2>
<p>Haberler; Resmî Gazete, yüksek mahkeme kararları, TBMM tutanakları, kamu kurumlarının açıklamaları ve ulusal basında yer alan gelişmeler esas alınarak hazırlanır. Her haberde kaynağı belli olmayan iddialara yer verilmez; karar metinleri yayımlandıkça haberler güncellenir ve güncelleme tarihi belirtilir. Kişilerin özel hayatına ilişkin bilgiler, haber değeri olan kamusal yönüyle sınırlı tutulur; adli dosyalarda taraf adları, kamuya açık karar metinlerinde geçtiği ölçüde kullanılır.</p>
<h2>Yazı işleri</h2>
<p>Haberler "Hukuki Haberler Editörlüğü" imzasıyla yayımlanır. {YAZI_ISLERI}Yayın ve editoryal süreçler <a href="/yayin-ilkeleri/">Yayın İlkeleri</a> sayfasında açıklanmıştır. Haberlerde yer alan görüşler, atıf yapılan kurum ve kişilere aittir; site bireysel hukuki danışmanlık vermez.</p>
<h2>Düzeltme ve tekzip</h2>
<p>Hatalı olduğu bildirilen bilgiler kaynağıyla birlikte doğrulandığında en geç üç iş günü içinde düzeltilir. Düzeltme talepleri <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine iletilebilir.</p>
<h2>İletişim</h2>
<p>E-posta: <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a></p>
<p>X: <a href="https://x.com/HukukiHaberTR" rel="me noopener" target="_blank">@HukukiHaberTR</a></p>
<h2>Telif</h2>
<p>Sitedeki metinler kaynak gösterilmek ve bağlantı verilmek şartıyla alıntılanabilir; bütün hâlinde kopyalanamaz.</p>"""
KUNYE = KUNYE.replace("{YAZI_ISLERI}", YAZI_ISLERI)
write("/kunye/", page("Künye", "Hukuki Haberler künye: yayın ilkeleri, yazı işleri, düzeltme ve telif esasları.", "/kunye/",
      f'<article class="post static"><h1>Künye</h1><div class="body">{KUNYE}</div></article>'))
write("/gizlilik-politikasi/", page("Gizlilik ve Çerez Politikası", "Hukuki Haberler gizlilik ve çerez politikası: hangi verilerin işlendiği, Google Analytics çerezleri ve çerez tercihinin değiştirilmesi.", "/gizlilik-politikasi/",
      f'<article class="post static"><h1>Gizlilik ve Çerez Politikası</h1><div class="body">{GIZ}</div></article>'))
KOSUL = """<p class="lead">Hukuki Haberler'i kullanan herkes aşağıdaki koşulları kabul etmiş sayılır.</p>
<h2>İçeriğin niteliği</h2>
<p>Sitedeki haber ve analizler genel bilgilendirme amaçlıdır; hukuki görüş, danışmanlık ya da avukat-müvekkil ilişkisi oluşturmaz. Süre, oran ve tutar gibi bilgiler yazının yayın tarihindeki mevzuatı yansıtır ve sonradan değişmiş olabilir. Somut bir uyuşmazlıkta bir avukata başvurulmalı, güncel ve bağlayıcı bilgi için yazının altında bağlantısı verilen resmî kaynaklar esas alınmalıdır.</p>
<h2>Alıntı ve telif</h2>
<p>Metinler, kaynak gösterilmek ve ilgili habere bağlantı verilmek şartıyla kısmen alıntılanabilir; bütün hâlinde kopyalanamaz, çoğaltılamaz ve başka bir sitede yayımlanamaz. Görseller kendi lisanslarına tabidir; fotoğrafçı ve lisans bilgisi görselin altında yer alır.</p>
<h2>Dış bağlantılar</h2>
<p>Haberlerde verilen dış bağlantıların içeriğinden ilgili siteler sorumludur.</p>
<h2>Düzeltme ve iletişim</h2>
<p>Hatalı olduğunu düşündüğünüz bilgiler için <a href="/yayin-ilkeleri/#duzeltme">düzeltme politikamıza</a> bakabilir, <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine yazabilirsiniz. Kişisel verilere ilişkin esaslar <a href="/gizlilik-politikasi/">Gizlilik ve Çerez Politikası</a> sayfasındadır.</p>"""
write("/kullanim-kosullari/", page("Kullanım Koşulları", "Hukuki Haberler kullanım koşulları: içeriğin niteliği, alıntı ve telif kuralları, dış bağlantılar ve düzeltme.", "/kullanim-kosullari/",
      f'<article class="post static"><h1>Kullanım Koşulları</h1><div class="body">{KOSUL}</div></article>'))

YAYIN = """<p class="lead">Hukuki Haberler'in amacı, hukuk ve yargı gündemini hukukçu olmayan okurun da anlayabileceği açıklıkta, kaynağı gösterilmiş ve tarihli biçimde aktarmaktır.</p>
<h2>Kapsam ve hedef kitle</h2>
<p>Yüksek mahkeme kararları, mevzuat değişiklikleri, Resmî Gazete, TBMM'deki kanun teklifleri, adli süreçler ve gündemdeki olayların hukuki boyutu. Hedef kitlemiz hukukçular kadar, haklarını öğrenmek isteyen her okurdur.</p>
<h2>İçerik türleri</h2>
<p>Her yazının başında türü belirtilir. <b>Haber:</b> bir karar, düzenleme veya gelişmenin doğrulanmış bilgilerle aktarılması. <b>Analiz:</b> gündemdeki bir olayın mevzuat ve içtihat üzerinden açıklanması; analizlerde editoryal değerlendirme yer alır ve bu kısımlar olgulardan ayrı yazılır. Sitede sponsorlu içerik ve görüş yazısı yayımlanmamaktadır; yayımlanırsa açıkça etiketlenir.</p>
<h2>Kaynak ve doğrulama</h2>
<p>Mümkün olan her durumda birincil kaynağa dayanırız: mevzuat metni, Resmî Gazete, mahkeme kararı, kamu kurumu açıklaması. İkincil kaynak (basın kuruluşu, ajans) kullanıldığında haberin altında bağlantısıyla belirtilir. İddia iddia olarak; soruşturma, kovuşturma, mahkûmiyet ve kesinleşme kavramları birbirinden ayrılarak yazılır. Soruşturma aşamasındaki kişiler için masumiyet karinesi esastır. Çocukların ve hassas durumdaki kişilerin kimlikleri yayımlanmaz.</p>
<h2 id="duzeltme">Düzeltme, güncelleme ve tekzip</h2>
<p>Hatalı olduğu tespit edilen bilgi kaynağıyla doğrulandığında düzeltilir; ilk yayın tarihi korunur, güncelleme tarihi ve neyin değiştiği yazının içinde belirtilir. Tekzip talepleri 5187 sayılı Basın Kanunu çerçevesinde değerlendirilir. Bildirimler <a href="mailto:iletisim@hukukihaberler.com">iletisim@hukukihaberler.com</a> adresine gönderilebilir.</p>
<h2 id="dogrulama">Doğrulama</h2>
<p>Her metindeki tarih, sayı, madde numarası ve alıntı yayımlanmadan önce kaynağına bakılarak kontrol edilir; kaynağı doğrulanamayan bilgi yayımlanmaz.</p>
<h2 id="yontem">Çalışma yöntemi ve yazılım araçları</h2>
<p>Gündemi izlemek, resmî kaynaklardaki yeni duyuruları tespit etmek ve haber taslaklarını hazırlamak için yazılım araçlarından yararlanırız. Anlık gelişmelere ilişkin haberler editör onayıyla yayımlanır. Bu yolla hazırlanan tüm metinler kaynak, tarafsızlık ve doğrulama ilkelerimize göre denetlenir; dayanılan kaynak geri çekildiğinde ya da bir hata tespit edildiğinde düzeltme politikamız uygulanır.</p>
<h2>Hukuki içerik denetimi ve çıkar ilişkisi</h2>
{DENETIM_PARAGRAF}
<h2>Reklam, sponsorluk ve bağımsızlık</h2>
<p>Sitede şu an reklam ve sponsorlu içerik bulunmamaktadır. İleride reklam alınması hâlinde reklam alanları haber metninden görsel olarak ayrılacak ve "Reklam" ibaresi taşıyacaktır. Hiçbir kurum veya kişi, ödeme karşılığında bir haberin içeriğini belirleyemez. Yazılarda hukuki bilgiye kaynak olarak bağlantı verilen dış sitelerle ilişkiler bu sayfada açıklanır.</p>
<h2>Görseller</h2>
<p>Görseller lisansı uygun kaynaklardan (ör. Wikimedia Commons, Flickr, Pixabay) alınır; fotoğrafçı, kaynak ve lisans görselin altında bağlantısıyla belirtilir. Görsellerin sağ alt köşesinde site imzası yer alır.</p>"""
YAYIN = YAYIN.replace("{DENETIM_PARAGRAF}", DENETIM_PARAGRAF)
write("/yayin-ilkeleri/", page("Yayın İlkeleri", "Hukuki Haberler yayın ilkeleri: kaynak ve doğrulama, düzeltme politikası, hukuki içerik denetimi, reklam ve bağımsızlık.", "/yayin-ilkeleri/",
      f'<article class="post static"><h1>Yayın İlkeleri</h1><div class="body">{YAYIN}</div></article>'))

# yazar profil sayfaları (gerçek kişiler; bilgiler yazarlar.json'dan, panelden düzenlenir; iletişim, ücret ya da çağrı içermez)
_BARO_URL = {"İzmir Barosu": "https://www.izmirbarosu.org.tr/", "İstanbul Barosu": "https://www.istanbulbarosu.org.tr/",
             "Ankara Barosu": "https://www.ankarabarosu.org.tr/"}
def incelenen_listesi(k):
    ls = [q for q in POSTS if q.get("denetleyen") == k]
    if not ls: return ""
    return (f'<h2 id="incelenenler">İncelediği haberler <small style="font:600 15px var(--sans);color:var(--mute)">({len(ls)})</small></h2><ul class="liste">'
            + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a> <small>{trdate(q["date"])}</small></li>' for q in ls) + "</ul>")
def yazar_sayfasi(k):
    v, y = YAZAR_KAYIT[k], YAZARLAR[k]
    url, foto, ad = y["url"], y["foto"], y["ad"]
    yerel = foto.startswith("/")
    kisi = {"@type": "Person", "@id": SITE + url + "#kisi", "name": v["kisi"], **({"honorificPrefix": y["unvan"]} if y["unvan"] else {}),
            "jobTitle": "Avukat" if y["unvan"] == "Av." else (v.get("rol") or "Yazar"), "description": v.get("ld_aciklama") or v.get("kisa", ""),
            "image": SITE + foto if yerel else foto, "url": SITE + url}
    if v.get("mezuniyet"): kisi["alumniOf"] = {"@type": "CollegeOrUniversity", "name": v["mezuniyet"]}
    if v.get("baro"): kisi["memberOf"] = {"@type": "Organization", "name": v["baro"], **({"url": _BARO_URL[v["baro"]]} if v["baro"] in _BARO_URL else {})}
    kisi["worksFor"] = {"@type": "NewsMediaOrganization", "name": NAME, "url": SITE + "/"}
    if v.get("konum"):
        _p = [x.strip() for x in v["konum"].split(",") if x.strip()]
        kisi["workLocation"] = {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": _p[0], **({"addressRegion": _p[-1]} if len(_p) > 1 else {}), "addressCountry": "TR"}}
    if v.get("uzmanlik"): kisi["knowsAbout"] = v["uzmanlik"]
    if v.get("diller"): kisi["knowsLanguage"] = v["diller"]
    if v.get("sameas"): kisi["sameAs"] = v["sameas"]
    ld = {"@context": "https://schema.org", "@type": "ProfilePage", "url": SITE + url, "name": ad, "mainEntity": kisi}
    bol = []
    for b_ in v.get("bolumler") or []:
        if b_.get("tur") == "liste":
            sat = [x for x in b_.get("satirlar") or [] if len(x) == 2 and (x[0] or x[1])]
            if sat: bol.append(f'<h2>{_mt(b_["baslik"])}</h2>\n<ul class="liste">\n' + "".join(f'<li><b>{_mt(x[0])}:</b> {x[1]}</li>\n' if x[0] else f'<li>{x[1]}</li>\n' for x in sat) + "</ul>")
        elif (b_.get("metin") or "").strip():
            bol.append(f'<h2>{_mt(b_["baslik"])}</h2>\n' + "\n".join(f"<p>{x.strip()}</p>" for x in b_["metin"].split("\n\n") if x.strip()))
    yz = [q for q in POSTS if q.get("yazar") == k]
    yazilari = ("<h2>Yazıları</h2><ul class=\"liste\">" + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a> <small>{trdate(q["date"])}</small></li>' for q in yz) + "</ul>") if yz else ""
    bag = [x for x in v.get("baglantilar") or [] if len(x) == 2 and x[1]]
    baglar = ('<h2>Bağlantılar</h2>\n<ul class="liste">\n' + "".join(f'<li><a href="{e(x[1])}" rel="noopener" target="_blank">{_mt(x[0] or x[1])}</a></li>\n' for x in bag) + "</ul>") if bag else ""
    rp = "" if yerel else ' referrerpolicy="no-referrer"'
    govde = (f'<figure class="avfoto"><img src="{foto}" alt="{e(ad)}" width="240" height="240" loading="lazy" decoding="async"{rp}></figure>\n'
             + (f'<p class="lead">{v["giris"]}</p>\n' if v.get("giris") else "") + "\n".join(bol) + "\n" + yazilari + incelenen_listesi(k) + baglar)
    alt = " · ".join(x for x in (v.get("rol"), v.get("alan")) if x)
    write(url, page(ad, v.get("sayfa_aciklama") or f"{ad}: {v.get('rol') or 'yazar'}, Hukuki Haberler.", url,
          f'<article class="post static"><h1>{_mt(ad)}</h1>' + (f'<p class="sec-desc">{_mt(alt)}</p>' if alt else "") + f'<div class="body">{govde}</div></article>',
          ld=ld, ogtype="profile", noindex=not y["goster"], **({"img": foto} if yerel else {}), crumbs=[("/", "Anasayfa"), ("/yazarlar/", "Yazarlar"), (url, ad)]))
for _k in YAZARLAR: yazar_sayfasi(_k)

# yazarlar sayfası
def _yz_kart(k, y):
    ls = [q for q in POSTS if q.get("denetleyen") == k]
    son = ("<div class=\"yz-inc\"><b>Son incelediği haberler</b><ul>" + "".join(f'<li><a href="{q["url"]}">{e(q["title"])}</a><small>{trdate(q["date"])}</small></li>' for q in ls[:6])
           + f'</ul><a class="yz-tum" href="{y["url"]}#incelenenler">Tüm incelediği haberler ({len(ls)})</a></div>') if ls else ""
    return (f'<li><a class="yz-ust" href="{y["url"]}"><img src="{y["foto"]}" alt="{e(y["ad"])}" width="120" height="120" loading="lazy" referrerpolicy="no-referrer">'
            f'<b>{e(y["ad"])}</b><small>{e(y["alan"])}</small><span>{e(y["bio"])}</span></a>{son}</li>')
_yz = "".join(_yz_kart(k, y) for k, y in GORUNEN_YAZARLAR.items())
_yz_adlar = [f'{y["ad"]} ({_tr_kucuk_bas(y["alan"])})' if y["alan"] else y["ad"] for y in GORUNEN_YAZARLAR.values()]
_yz_aciklama = "Hukuki Haberler yazarları ve editörleri" + (": " + (", ".join(_yz_adlar[:-1]) + " ve " + _yz_adlar[-1] if len(_yz_adlar) > 1 else _yz_adlar[0]) + "." if _yz_adlar else ".")
write("/yazarlar/", page("Yazarlar", _yz_aciklama, "/yazarlar/",
      f'<div class="crumb"><a href="/">Anasayfa</a> › Yazarlar</div><h1 class="sec">Yazarlar</h1><p class="sec-desc">Haber ve analizlerin hukuki çerçevesini alanında çalışan avukatlar yazar, denetler ve düzenler.</p><ul class="yzl">{_yz}</ul>',
      crumbs=[("/", "Anasayfa"), ("/yazarlar/", "Yazarlar")]))

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
       [(f"/haber-etiketi/{s}/", "weekly", "0.3") for s in tag_posts if etiket_dizinde(s)] + \
       [(f"/{y}/", "yearly", "0.3") for y in years] + [(f"/{y}/{m:02d}/", "yearly", "0.3") for (y, m) in months] + [("/konular/", "weekly", "0.5")] + [(f"/konu/{k}/", "daily", "0.6") for k in KONU_VAR if len(KONU_HABER[k]) >= KONU_DIZIN] + [("/arsiv/", "monthly", "0.4"), ("/hakkinda/", "yearly", "0.3"), ("/kunye/", "yearly", "0.3"), *[(y["url"], "yearly", "0.3") for y in GORUNEN_YAZARLAR.values()], ("/yazarlar/", "monthly", "0.4"), ("/yayin-ilkeleri/", "yearly", "0.3"), ("/gizlilik-politikasi/", "yearly", "0.2"), ("/kullanim-kosullari/", "yearly", "0.2"), ("/analiz/", "daily", "0.6"), ("/mevzuat/", "daily", "0.6"), ("/kesfet/", "weekly", "0.4"), ("/iletisim/", "yearly", "0.2")]
def _guncel_iso(p):
    u = p.get("updated")
    if u and "T" in str(u): return str(u)[:16] + ":00+03:00"
    if u: return str(u)
    return iso(p) if p.get("saat") else p["date"].isoformat()
lm = {p["url"]: _guncel_iso(p) for p in POSTS}
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
    f"<url><loc>{SITE}{u}</loc>{('<lastmod>'+lm[u]+'</lastmod>') if u in lm else ''}<changefreq>{c}</changefreq><priority>{pr}</priority></url>\n" for u, c, pr in urls) + "</urlset>\n"
with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f: f.write(sm)
# Google News sitemap: yalnızca son 2 günde yayımlananlar
_tz = datetime.timezone(datetime.timedelta(hours=3))
_lim = datetime.datetime.now(_tz) - datetime.timedelta(hours=48)
def _yayin_an(p):
    return datetime.datetime.fromisoformat(iso(p)) if p.get("saat") else datetime.datetime.combine(p["date"], datetime.time(9, 0), _tz)
nsm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "".join(
    f"<url><loc>{SITE}{p['url']}</loc><news:news><news:publication><news:name>{NAME}</news:name><news:language>tr</news:language></news:publication><news:publication_date>{iso(p) if p.get('saat') else p['date'].isoformat()}</news:publication_date><news:title>{e(p['title'])}</news:title></news:news></url>\n"
    for p in POSTS if _yayin_an(p) >= _lim) + "</urlset>\n"
with open(os.path.join(OUT, "news-sitemap.xml"), "w", encoding="utf-8") as f: f.write(nsm)
with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /search/\nDisallow: /wp-admin/\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/news-sitemap.xml\n")
shutil.copytree(os.path.join(os.path.dirname(__file__), "static"), OUT, dirs_exist_ok=True)
with open(os.path.join(OUT, "site.webmanifest"), "w", encoding="utf-8") as f:
    json.dump({"name": NAME, "short_name": NAME, "start_url": "/", "display": "standalone", "background_color": "#35495E", "theme_color": "#2D4054",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, f, ensure_ascii=False)

# yönlendirmeler (Cloudflare Pages _redirects)
# yönetim panelinden kaldırılan eski (arşiv) yazıların adresleri 404 yerine arşive yönlenir (eski adres denetimi bozulmasın)
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaldirilanlar.json")):
    for _k in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaldirilanlar.json"), encoding="utf-8")):
        if any(q["slug"] == _k["slug"] for q in POSTS): continue
        _h = _k.get("hedef") or "/arsiv/"
        REDIRECTS += [(f"/{_k['slug']}.html", _h), (f"/{_k['slug']}", _h), (f"/{_k['slug']}/", _h)]
# panelden kaldırılan yazarların profil adresleri yazarlar sayfasına yönlenir
for _a in _YZ_VERI.get("kaldirilan_adresler") or []:
    if any(y["adres"] == _a for y in _YZ_VERI["yazarlar"]): continue
    REDIRECTS += [(f"/{_a}", "/yazarlar/"), (f"/{_a}/", "/yazarlar/")]
REDIRECTS += [("/search/*", "/"), ("/wp-login.php", "/"), ("/wp-admin/*", "/"), ("/xmlrpc.php", "/"),
              ("/cep-telefonu-faturasina-ust-limit-geliyor.html/cep-telefonu", "/cep-telefonu-faturasina-ust-limit-geliyor"),
              ("/turkcell-superlig-bugun-basliyor.html", "/super-toto-ligi-bugun-basliyor"),
              ("/ese-eve-don-cagrisi-15-tl.html", "/ese-‘eve-don’-cagrisi-15-tl"), ("/osd.xml", "/"),
              *ESKI_ADRES.items(),
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
    if b.endswith("/") and b.rstrip("/") in POST_URLS: b = b.rstrip("/")
    seen.add(a); lines.append(f"{enc(a)} {enc(b)} 301")
with open(os.path.join(OUT, "_redirects"), "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
with open(os.path.join(OUT, "_routes.json"), "w", encoding="utf-8") as f:
    f.write('{"version":1,"include":["/api/*"],"exclude":[]}')
with open(os.path.join(OUT, "_headers"), "w", encoding="utf-8") as f:
    f.write("/*\n  X-Content-Type-Options: nosniff\n  X-Frame-Options: SAMEORIGIN\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
            "  Strict-Transport-Security: max-age=31536000\n  Cross-Origin-Opener-Policy: same-origin\n"
            "/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
            "/gorsel/*\n  Cache-Control: public, max-age=604800, stale-while-revalidate=86400\n")

# özet
n_files = sum(len(fs) for _, _, fs in os.walk(OUT))
print(f"yazı: {len(POSTS)} | kategori: {sum(1 for k in CATS if cat_count[k])} | etiket: {len(tag_posts)} | ay: {len(months)} | dosya: {n_files} | redirect: {len(lines)}")
print("kelime min/ort:", min(p['words'] for p in POSTS), round(sum(p['words'] for p in POSTS)/len(POSTS)))
print("hedef link:", sum(len(re.findall(re.escape(TARGET), p['body'])) for p in POSTS), "yazıda",
      sum(1 for p in POSTS if TARGET in p['body']))
