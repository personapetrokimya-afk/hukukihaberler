# -*- coding: utf-8 -*-
"""Her haber için 1200x630 kapak görseli üretir (site/gorsel/<slug>.jpg).
Orijinal arşiv küçük resmi varsa: bulanık arka plan + ortada keskin küçük resim.
Yoksa: kategori rengine göre tipografik kapak."""
import os, hashlib
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "orig")
W, H = 1200, 630
S = W / 800  # eski 800px tasarımın ölçek katsayısı
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_S = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# orijinal küçük resim → yazı
MAP = {
 "adliye-doldu-icra-mudurlukleri-kiraya-cikiyor": "adliye.jpg",
 "danistayin-ulkeye-faturasi-2-6-milyar-dolar": "basbakan.jpg",
 "cep-telefonu-faturasina-ust-limit-geliyor": "cep-telefonu.jpg",
 "mahkeme-168-davaliyi-gazete-ilaniyla-ariyor": "davali.jpg",
 "et-ve-balik-kurumu-hukuki-surec-baslatiyor": "ebk.jpg",
 "cocuklar-artik-terorist-sayilmayacak": "HABER-cocuk.jpg",
 "yargida-toplu-izin-yarin-basliyor": "toplu-izin.jpg",
 "icislerinden-valilere-nufus-cuzdani-talimati": "valilik.jpg",
 "yargitaydan-tarihi-karar": "yargıtay-karar.jpg",
 "ahtapot-paul-referandum-tahmininde-bulundu": "ahtapot-kahin-paul.jpg",
 "anayasa-mahkemesinin-anayasa-degisikligi-gerekceli-karari": "anayasa-mahkemesi.jpg",
 "hukukculardan-net-cikis-firarinin": "balyoz-davasi.jpg",
 "berberler-hafta-sonu-calisabilecek": "berber.jpg",
 "yargitaydan-iliskiye-girmeyen-kocaya-ceza": "bosanma.jpg",
 "arinctan-yas-degerlendirmesi": "bulent-arinc.jpg",
 "bulent-arinc-gundemimizde-baskanlik-sistemi-yok": "bulent-arinc.jpg",
 "elazigli-celebi-90km-yi-gecti": "celebi-otomobil.jpg",
 "tecavuz-sucu-icin-hadim-cezasi": "cezalar.jpg",
 "kadin-avukatlarin-sutyen-isyani": "cubbe.jpg",
 "aydin-doganin-vergi-davalari-nasil-sonuclandi": "dogan-yayin-holding.jpg",
 "ehliyetinizden-olmamak-icin-dikkat": "ehliyet-radar-uygulamasi.jpg",
 "facebook-artik-yerinizi-de-belli-edecek": "facebook-yerinizi-yayinliyor.jpg",
 "finansbank-hukuk-musavirligine-sebnem-karaduman-getirildi": "Finansbank-Şebnem-Karaduman.jpg",
 "halis-toprakin-vesayet-altina-alinmasi-davasi": "halis.jpg",
 "uc-il-daha-buyuksehir-olacak": "harita.jpg",
 "gozaltinda-sinava-girdi-ve-ilk-tercihi-hukuk-fakultesi": "ilktercih.jpg",
 "istanbullulara-serinleten-haber": "istanbul-kavurucu-sicaklari.jpg",
 "kadinlara-4-yil-erken-emeklilik-surprizi": "kadinlara-emeklilik.jpg",
 "key-odemelerinin-yapilacagi-tarih": "key-odemeleri.jpg",
 "keyde-3-odeme-ramazanda-yapilacak": "key-odemeleri1.jpg",
 "turk-vatandaslarina-meksika-vizesinde-kolaylik": "meksika-vizesi-kolayligi.jpg",
 "baydemir-olay-cikaran-sozlerinde-israrli": "osman-baydemir.jpg",
 "ilk-turk-hukuk-profesoru": "osman-isfen.jpg",
 "osys-tercihleri-icin-artik-son-gunler": "osys-tercihleri.jpg",
 "bir-kez-profesor-olan-derse-bile-girmiyor": "PROFESOR.jpg",
 "ese-eve-don-cagrisi-15-tl": "posta-kutusu.jpg",
 "vucudunuzu-ramazana-alistirma-yollari": "ramazan.jpg",
 "iraka-ithal-demokrasi-yaramadi": "secim-heyecani.jpg",
 "sigara-ve-alkole-yeni-zam-gelecek": "sigaraya-zam.jpg",
 "super-toto-ligi-bugun-basliyor": "superlig.jpg",
 "suudi-mahkemeden-inanilmaz-karar": "suudi-arabistan-seriat-mahkemesi.jpg",
 "temmuz-ayi-enflasyon-rakamlari-sevindirdi": "temmuz-ayi-enflasyon.jpg",
 "gelecek-hafta-da-tum-turkiyede-hava-cok-sicak-olacak": "tum-turkiyede-hava-durumu.jpg",
 "bir-kadin-5-ay-icinde-iki-dogum-yapamaz": "yargitay-karar-bozdu.jpg",
 "ahmet-turkten-demokratik-siyaset-cikisi": "ahmet-turk.jpg",
 "kayyum-nedir-saadet-partisini-simdi-kim-yonetecek": "kayyum-nedir.jpg",
}

COLORS = {k: (53, 73, 94) for k in ("manset","yargi","siyaset","basindan","diger","universiteler","teknoloji","barolar","hukuk-burolarindan")}

def _cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r) + 1, round(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def _fit(im, w, h):
    r = min(w / im.width, h / im.height)
    return im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)

def with_thumb(src):
    im = Image.open(src).convert("RGB")
    bg = _cover(im, W, H).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.6)
    fg = _fit(im, int(W * 0.62), int(H * 0.8))
    fg = fg.filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
    pad = 0
    frame = Image.new("RGB", (fg.width + pad * 2, fg.height + pad * 2), (20, 20, 20))
    frame.paste(fg, (pad, pad))
    sh = Image.new("RGBA", (frame.width + 40, frame.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((20, 24, 20 + frame.width, 24 + frame.height), fill=(29, 42, 55, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    x, y = (W - frame.width) // 2, (H - frame.height) // 2
    out = bg.convert("RGBA")
    out.alpha_composite(sh, (x - 20, y - 20))
    out.paste(frame, (x, y))
    return out.convert("RGB")

def typographic(title, catkey, catname):
    root = catkey.split("/")[0]
    c = COLORS.get(root, COLORS["manset"])
    im = Image.new("RGB", (W, H), c)
    d = ImageDraw.Draw(im)
    # köşegen açık bant
    dark = tuple(max(0, v - 28) for v in c)
    d.polygon([(0, H), (W, 0), (W, H)], fill=dark)
    # büyük terazi glifi
    f_big = ImageFont.truetype(FONT_S, int(230 * S))
    d.text((W - int(300 * S), H - int(290 * S)), "⚖", font=f_big, fill=(80, 100, 122))
    # büyük kategori adı (başlık kartta ayrıca yazıldığı için tekrar edilmez)
    f_cat = ImageFont.truetype(FONT_S, int(18 * S))
    d.text((int(44 * S), int(44 * S)), "HUKUKİ HABERLER", font=f_cat, fill=tuple(min(255, v + 110) for v in c))
    f_t = ImageFont.truetype(FONT_B, int((64 if len(catname) <= 12 else 46) * S))
    words, lines, cur = catname.upper().split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f_t) > W - int(300 * S) and cur:
            lines.append(cur); cur = wd
        else:
            cur = t
    if cur: lines.append(cur)
    lh = int(72 * S); x0 = int(44 * S)
    y = H // 2 - (len(lines) * int(70 * S)) // 2 - int(10 * S)
    for ln in lines:
        d.text((x0 + 2, y + 3), ln, font=f_t, fill=(0, 0, 0))
        d.text((x0, y), ln, font=f_t, fill=(255, 255, 255))
        y += lh
    d.rectangle((x0, y + int(8 * S), x0 + int(120 * S), y + int(13 * S)), fill=(241, 210, 147))
    f_s = ImageFont.truetype(FONT_S, int(18 * S))
    d.text((x0, H - int(48 * S)), "hukukihaberler.com", font=f_s, fill=(255, 255, 255))
    return im

COMMONS = os.path.join(HERE, "commons")
ALIAS = {  # aynı fotoğrafı paylaşan haberler
 "anayasa-mahkemesi-ve-uluslararasi-anlasmalar": "nukleere-hukuk-dar-geliyor",
 "aymden-tayfun-kahramana-ikinci-ihlal-karari-yeniden-yargilama": "aym-26-siyasi-partinin-hesaplarini-kabul-etmedi-suc-duyurusu",
 "hizmetli-memurun-13-yillik-hukuk-mucadelesi": "hizmetli-memurun-13-yillik-hukuk-mucadelesi",
}
def photo(src):
    im = Image.open(src).convert("RGB")
    up = max(W / im.width, H / im.height) > 1
    im = _cover(im, W, H)
    if up: im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
    return ImageEnhance.Sharpness(im).enhance(1.1)

def imza(im):
    """sağ alt köşeye site imzası"""
    im = im.convert("RGBA")
    f = ImageFont.truetype(FONT_S, int(15 * S))
    txt = "hukukihaberler.com"
    d0 = ImageDraw.Draw(im)
    tw = d0.textlength(txt, font=f)
    pad_x, h = int(10 * S), int(26 * S)
    x1, y1 = W - int(12 * S), H - int(12 * S)
    x0, y0 = x1 - tw - pad_x * 2 - int(12 * S), y1 - h
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((x0, y0, x1, y1), radius=int(4 * S), fill=(29, 42, 55, 150))
    d.rectangle((x0, y0, x0 + int(4 * S), y1), fill=(241, 210, 147, 235))
    d.text((x0 + pad_x + int(6 * S), y0 + int(4 * S)), txt, font=f, fill=(255, 255, 255, 235))
    return Image.alpha_composite(im, ov).convert("RGB")

def build(posts, outdir):
    """returns {slug: (url, kind, credit)}"""
    import json
    os.makedirs(outdir, exist_ok=True)
    meta = {}
    mp = os.path.join(COMMONS, "meta.json")
    if os.path.exists(mp): meta = json.load(open(mp, encoding="utf-8"))
    res = {}
    for p in posts:
        slug = p["slug"]; fn = f"{slug}.jpg"; dst = os.path.join(outdir, fn)
        key = ALIAS.get(slug, slug)
        cpath = os.path.join(COMMONS, key + ".jpg")
        src = MAP.get(slug)
        credit = None
        if src and os.path.exists(os.path.join(ORIG, src)):
            im = with_thumb(os.path.join(ORIG, src)); kind = "orig"
        elif os.path.exists(cpath) and key in meta:
            im = photo(cpath); kind = "photo"; m = meta[key]
            credit = {"artist": m.get("artist") or "Wikimedia Commons", "lic": m.get("lic", ""), "page": m.get("page", "")}
        else:
            k = p["catkeys"][0]
            for c in p["catkeys"]:
                if c != "manset": k = c; break
            im = typographic(p["title"], k, p["catname"]); kind = "gen"
        if kind != "gen": im = imza(im)
        im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)
        for sub, size, q in (("m", (480, 252), 78), ("l", (800, 420), 80)):
            os.makedirs(os.path.join(outdir, sub), exist_ok=True)
            im.resize(size, Image.LANCZOS).save(os.path.join(outdir, sub, fn), "JPEG", quality=q, optimize=True, progressive=True)
        _v = hashlib.md5(open(dst, "rb").read()).hexdigest()[:8]
        res[slug] = (f"/gorsel/{fn}?v={_v}", kind, credit)
    typographic("Hukuk, yargı ve mevzuat gündemi", "manset", "Hukuki Haberler").save(os.path.join(outdir, "kapak.jpg"), "JPEG", quality=82, optimize=True)
    return res
