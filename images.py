# -*- coding: utf-8 -*-
"""Her haber için 800x420 kapak görseli üretir (site/gorsel/<slug>.jpg).
Orijinal arşiv küçük resmi varsa: bulanık arka plan + ortada keskin küçük resim.
Yoksa: kategori rengine göre tipografik kapak."""
import os, hashlib
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "orig")
W, H = 800, 420
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

COLORS = {"manset": (155, 28, 28), "yargi": (30, 58, 138), "siyaset": (55, 65, 81), "basindan": (107, 79, 29),
          "diger": (15, 118, 110), "universiteler": (91, 33, 182), "teknoloji": (14, 116, 144), "barolar": (124, 45, 18),
          "hukuk-burolarindan": (74, 4, 78)}

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
    pad = 8
    frame = Image.new("RGB", (fg.width + pad * 2, fg.height + pad * 2), (255, 255, 255))
    frame.paste(fg, (pad, pad))
    sh = Image.new("RGBA", (frame.width + 40, frame.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((20, 24, 20 + frame.width, 24 + frame.height), fill=(0, 0, 0, 120))
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
    f_big = ImageFont.truetype(FONT_S, 230)
    d.text((W - 300, H - 290), "⚖", font=f_big, fill=tuple(min(255, v + 40) for v in c))
    # büyük kategori adı (başlık kartta ayrıca yazıldığı için tekrar edilmez)
    f_cat = ImageFont.truetype(FONT_S, 18)
    d.text((44, 44), "HUKUKİ HABERLER", font=f_cat, fill=tuple(min(255, v + 110) for v in c))
    f_t = ImageFont.truetype(FONT_B, 64 if len(catname) <= 12 else 46)
    words, lines, cur = catname.upper().split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f_t) > W - 300 and cur:
            lines.append(cur); cur = wd
        else:
            cur = t
    if cur: lines.append(cur)
    y = H // 2 - (len(lines) * 70) // 2 - 10
    for ln in lines:
        d.text((46, y + 3), ln, font=f_t, fill=(0, 0, 0))
        d.text((44, y), ln, font=f_t, fill=(255, 255, 255))
        y += 72
    d.rectangle((44, y + 8, 164, y + 13), fill=(255, 255, 255))
    f_s = ImageFont.truetype(FONT_S, 18)
    d.text((44, H - 48), "hukukihaberler.com", font=f_s, fill=(255, 255, 255))
    return im

def build(posts, outdir):
    """posts: dict list with slug/title/catkeys; returns {slug: (path, kind)}"""
    os.makedirs(outdir, exist_ok=True)
    res = {}
    for p in posts:
        slug = p["slug"]; fn = f"{slug}.jpg"; dst = os.path.join(outdir, fn)
        src = MAP.get(slug)
        if src and os.path.exists(os.path.join(ORIG, src)):
            im = with_thumb(os.path.join(ORIG, src)); kind = "orig"
        else:
            k = p["catkeys"][0]
            for c in p["catkeys"]:
                if c != "manset": k = c; break
            im = typographic(p["title"], k, p["catname"]); kind = "gen"
        im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        res[slug] = (f"/gorsel/{fn}", kind)
    typographic("Hukuk, yargı ve mevzuat gündemi", "manset", "Hukuki Haberler").save(os.path.join(outdir, "kapak.jpg"), "JPEG", quality=82, optimize=True)
    return res
