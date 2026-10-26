# -*- coding: utf-8 -*-
"""Tweet -> eleme -> (web taraması + yazım) -> denetim -> yayın -> arama motoru bildirimi.

Yayın politikası (yalnızca hukuki KONULAR; kişi haberleri -gözaltı, tutuklama, iddia- alınmaz):
  resmi      : resmî kurum hesabının duyurduğu düzenleme/karar -> otomatik yayın
  iddia      : resmî olmayan hesabın aktardığı hukuki gelişme -> yalnızca resmî kaynak ya da 2 bağımsız kaynakla
               teyitte otomatik; aksi halde bekler ve bildirim gider
Dayanılan tweet silinirse haber yayından kaldırılır (bkz. takip.py).
"""
import hashlib, os, re, json, time, datetime, shutil, subprocess, runpy, unicodedata, threading, urllib.request, urllib.parse, io, html
from ortak import (gemini, GEMINI_KEY, TR, log, ekle_jsonl, sayac, saatlik_yazi, claude, json_ayikla, simdi, SITE_DEPO, VERI, SITE,
                   MODEL_ELEME, MODEL_YAZIM, WEB_ARAMA_ARACI, GUNLUK_ELEME_SINIRI, GUNLUK_YAZI_SINIRI,
                   SAATLIK_YAZI_SINIRI, YAYIN_ACIK, sinir_doldu, bildirim, arama_motorlarina_bildir)

KATEGORILER = ["Yargı", "Yargıtay", "Anayasa Mahkemesi", "Danıştay", "Adalet Bakanlığı", "AİHM", "Siyaset",
               "Teknoloji", "Ekonomi", "Dünya", "3. Sayfa", "Barolar", "Manşet"]

# kişi hesapları için ön süzgeç: bunlardan biri yoksa modele gönderilmez
_KOKLER = ["gözaltı", "tutukla", "tutuklan", "tutuklu", "tahliye", "serbest bırak", "adli kontrol", "ev hapsi",
           "iddianame", "dava", "duruşma", "mahkeme", "hâkim", "hakim", "savcı", "soruşturma", "kovuşturma",
           "yargıtay", "danıştay", "anayasa mahkemesi", "aym", "hsk", "karar", "beraat", "mahkûm", "mahkum", "ceza",
           "hapis", "kanun", "teklif", "resmî gazete", "resmi gazete", "yönetmelik", "kayyum", "kayyım", "operasyon",
           "ifade", "avukat", "baro", "dokunulmazlık", "fezleke", "suç duyurusu", "şikâyet", "şikayet", "itiraz",
           "istinaf", "temyiz", "cezaevi", "infaz", "rtük", "kvkk", "rekabet kurulu", "erişim engeli", "el konul",
           "müsadere", "iade", "kırmızı bülten", "aihm", "ihlal", "polis", "jandarma", "baskın", "ihraç"]

def on_suzgec(metin):
    m = metin.lower()
    return any(k in m for k in _KOKLER)

# ------------------------------------------------------------------ site verisi
def _posts():
    try:
        return runpy.run_path(os.path.join(SITE_DEPO, "content6.py"))["POSTS"]
    except Exception as e:
        log("content6 okunamadı:", e); return []

def site_yazilari(n=60):
    return [(p.get("date", ""), p.get("saat", ""), p["title"]) for p in _posts()[:n]]

def site_listesi(n=50):
    """eleme ve yazım için: tarih saat | /slug/ | başlık; editör onayı bekleyen taslaklar da yayımlanmış sayılır
    (aynı olay onay beklerken ikinci bir kaynaktan gelince ikinci kez yazılmasın)"""
    bekleyen = []
    try:
        import glob
        for f in sorted(glob.glob(os.path.join(VERI, "taslak", "*.json")), key=os.path.getmtime)[-40:]:
            d = json.load(open(f, encoding="utf-8"))
            if d.get("durum") in ("bekliyor", "yayınlanıyor") and time.time() - d.get("ts", 0) < 86400:
                bekleyen.append(f"- (onay bekliyor, yayımlanmış say) | /{d['post']['slug']}/ | {d['post']['title']}")
    except Exception:
        pass
    return "\n".join(bekleyen + [f"- {p.get('date','')} {p.get('saat','')} | /{p['slug']}/ | {p['title']}" for p in _posts()[:n]])

def _eski_adresler():
    """sitede birleştirilip yönlendirilen yazılar (build.py ESKI_ADRES): eski slug -> yeni slug"""
    try:
        m = re.search(r"ESKI_ADRES = \{(.*?)\}\n", open(os.path.join(SITE_DEPO, "build.py"), encoding="utf-8").read(), re.S)
        return {a.strip("/"): b.strip("/") for a, b in re.findall(r'"(/[a-z0-9-]+)":\s*"(/[a-z0-9-]+)"', m.group(1))} if m else {}
    except Exception: return {}

def post_bul(slug):
    p = next((p for p in _posts() if p["slug"] == slug), None)
    if p is None and slug:
        hedef = _eski_adresler().get(slug)
        if hedef: p = next((x for x in _posts() if x["slug"] == hedef), None)
    return p

def site_sluglari():
    return {p["slug"] for p in _posts()}

def gorsel_listesi():
    try:
        meta = json.load(open(os.path.join(SITE_DEPO, "commons", "meta.json"), encoding="utf-8"))
    except Exception:
        return {}
    gor, sec = set(), {}
    for k, v in meta.items():
        t = v.get("title", "")
        if t in gor or not os.path.exists(os.path.join(SITE_DEPO, "commons", k + ".jpg")): continue
        gor.add(t); sec[k] = t.replace("File:", "")
    return sec

_KONU = os.path.join(VERI, "konular.json")
_konu_kilit = threading.Lock()
def son_konular(saat=24):
    try:
        d = json.load(open(_KONU, encoding="utf-8"))
    except Exception:
        d = []
    sinir = time.time() - saat * 3600
    return [x for x in d if x["ts"] > sinir]

_ACILIS = time.time()   # tekrar sınırı yalnızca bu açılıştan sonraki başarısızlıkları sayar (eski hatalı denetim kayıtları engellemesin)
_DOLGU = set("ve ile için ilişkin hakkında kapsamında bir bu da de ki mi olan yeni ile ilgili sonrası öncesi tarafından".split())

def _kelimeler(t):
    return {w for w in re.findall(r"[a-zçğıöşü0-9]{3,}", t.lower().replace("İ", "i")) if w not in _DOLGU}

def _kokler(t):
    return {w[:5] for w in _kelimeler(t)}

def yakinda_yazildi(konu, saat=6):
    """aynı gelişme son saatlerde zaten yazıldıysa (taslak hazır ya da şu an yazılıyor) True: aynı haber ikinci kez ücretli yazılmasın"""
    k = _kokler(konu)
    if len(k) < 3: return None
    for x in son_konular(saat):
        if x["durum"] not in ("onay bekliyor", "yazılıyor"): continue
        w = _kokler(x["konu"])
        ortak = k & w
        if len(ortak) >= 4 and len(ortak) / len(k | w) >= 0.33: return x["konu"]
    return None

def basarisiz_tekrar(konu, saat=12, esik=2):
    """aynı konu son saatlerde 'esik' kez yazılıp denetimden/yazımdan dönmüşse True (boşa ücretli yazımı önler)"""
    k = _kelimeler(konu)
    if len(k) < 2: return False
    say = 0
    for x in son_konular(saat):
        if x["durum"] not in ("denetim", "yazılmadı", "hata") or x["ts"] < _ACILIS: continue
        w = _kelimeler(x["konu"])
        if w and len(k & w) / len(k | w) >= 0.3: say += 1
    return say >= esik

def sss_duzelt(liste):
    """modelin SSS biçimini [["soru","cevap"], ...] haline getirir: liste/demet, {"q","a"} / {"soru","cevap"} sözlükleri kabul edilir;
    soru ya da cevabı boş/anahtar adı olan maddeler atılır"""
    out = []
    for x in liste or []:
        if isinstance(x, dict):
            q = next((x[k] for k in ("q", "soru", "question", "s") if x.get(k)), "")
            a = next((x[k] for k in ("a", "cevap", "answer", "c", "yanit", "yanıt") if x.get(k)), "")
        elif isinstance(x, (list, tuple)) and len(x) >= 2:
            q, a = x[0], x[1]
        else:
            continue
        q, a = str(q).strip(), str(a).strip()
        if len(q) < 5 or len(a) < 5 or q.lower() in ("q", "soru", "question") or a.lower() in ("a", "cevap", "answer"):
            continue
        out.append([q, a])
    return out

SSS_SISTEM = """Bir hukuk haberinin altına "Merak edilenler" bölümü yazıyorsun. Yalnızca verilen haber metnindeki bilgiye dayan, yeni bilgi ekleme.
4 soru-cevap yaz: soru en fazla 45 karakter, insanların arayacağı kısa kalıpta ("Ceza ne kadar?"); cevap 1-2 cümle, tarafsız.
Yalnızca JSON: {"sss": [["soru", "cevap"], ...]}"""

def sss_hazirla(p):
    """yayın öncesi son kontrol: SSS geçerliyse temizlenmiş halini, bozuksa haber metninden yeniden üretilmişini döndürür"""
    ham = p.get("sss") or []
    temiz = [[q, a] for q, a in sss_duzelt(ham) if len(q) <= 60][:4]
    if len(temiz) >= 2 or not ham: return temiz
    try:
        metin = html.unescape(re.sub(r"<[^>]+>", " ", p.get("body", "")))
        yeni = sss_duzelt(json_ayikla(kucuk_model(SSS_SISTEM, f"Başlık: {p.get('title','')}\nMetin: {metin[:6000]}", 1500)).get("sss"))
        yeni = [[q, a] for q, a in yeni if len(q) <= 60][:4]
        log("SSS bozuktu, yeniden üretildi:", p.get("title", "")[:60], len(yeni))
        return yeni
    except Exception as e:
        log("SSS yeniden üretilemedi:", repr(e)); return temiz

def yarim_yayinlari_duzelt():
    """servis açılışında: yeniden başlatma yüzünden 'yayınlanıyor'/'kaldırılıyor' durumunda takılan taslakları düzeltir"""
    try:
        sluglar = site_sluglari()
    except Exception:
        return
    for f in os.listdir(TASLAK_DIR):
        if not f.endswith(".json"): continue
        d = taslak_oku(f[:-5])
        if not d or d.get("durum") not in ("yayınlanıyor", "kaldırılıyor"): continue
        slug = d["post"].get("slug")
        if d["durum"] == "yayınlanıyor":
            if slug in sluglar:
                d["durum"] = "yayınlandı"; d["url"] = d.get("url") or f"{SITE}/{slug}/"
            else:
                d["durum"] = "bekliyor"; d["hata"] = "Servis yeniden başladığı için yayın tamamlanmadı; tekrar Yayınla'ya basın"
        else:
            d["durum"] = "yayından kaldırıldı" if slug not in sluglar else "yayınlandı"
        taslak_yaz(d); log("takılı taslak düzeltildi:", d["post"]["title"], "->", d["durum"])

def yarim_konulari_temizle():
    """servis açılışında: yarıda kalmış 'yazılıyor' kayıtlarını siler (o paylaşımlar kuyruktan yeniden işlenecek)"""
    with _konu_kilit:
        d = [x for x in son_konular(72) if x["durum"] != "yazılıyor"]
        json.dump(d, open(_KONU, "w", encoding="utf-8"), ensure_ascii=False)

# --- her paylaşımın akıbeti (panelde "Elenen haberler"): hangi aşamada neden elendi ya da taslak oldu ---
_akis_tl = threading.local()

def akibet_kaydet(durum, neden=None, tw=None, el=None, **ek):
    tw = tw or getattr(_akis_tl, "tw", None)
    if not tw: return
    el = el if el is not None else (getattr(_akis_tl, "el", None) or {})
    try:
        ekle_jsonl("akibet.jsonl", {"ts": time.time(), "durum": durum, "neden": (str(neden)[:400] if neden else None),
                                    "url": tw.get("url"), "id": str(tw.get("id") or ""), "kullanici": tw.get("kullanici"), "ad": tw.get("ad"),
                                    "grup": tw.get("grup"), "tarih": tw.get("tarih"), "saat": tw.get("saat"), "tw_ts": tw.get("ts"),
                                    "metin": (tw.get("metin") or "")[:900], "konu": el.get("konu"), "tur": el.get("tur"), "oncelik": el.get("oncelik"),
                                    "zorla": bool(getattr(_akis_tl, "zorla", False)), "tid": getattr(_akis_tl, "tid", None), **ek})
    except Exception as e:
        log("akıbet kaydı yazılamadı:", e)

def konu_ekle(konu, durum, neden=None):
    if durum != "yazılıyor": akibet_kaydet(durum, neden)
    try:
        import ortak as _om
        if durum != "yazılıyor": _om.maliyet_bilgi(sonuc=durum)
    except Exception: pass
    with _konu_kilit:
        d = son_konular(72)
        # "yazılıyor" kaydı sonuçla değiştirilir (aynı konu ikinci bir işçide eş zamanlı yazılmasın diye önce bu kayıt düşülür)
        d = [x for x in d if not (x["konu"] == konu and x["durum"] == "yazılıyor")]
        d.append({"ts": time.time(), "konu": konu, "durum": durum})
        json.dump(d, open(_KONU, "w", encoding="utf-8"), ensure_ascii=False)

# ------------------------------------------------------------------ 1) eleme
ELEME_SISTEM = """Türkiye'de hukuk haberleri yayımlayan tarafsız bir haber sitesi için gelen X paylaşımlarını eleyen editörsün.
Ölçüt GERÇEK HABER DEĞERİDİR: kamuyu ilgilendiren hukuki gelişme. Kişisel sorunlar, polemikler, kişisel iddialar ciddiye alınmaz.
Kural, paylaşan hesabın grubuna göre değişir (mesajdaki "hesap grubu"):
A) resmi (bakanlık, başsavcılık, mahkeme, HSK, baro, TBMM): kurumun duyurduğu YENİ hukuki işlem/karar/düzenleme haberdir.
B) siyasi (cumhurbaşkanı, parti genel başkanları): hukuk, yargı, mevzuat ya da kamuyu ilgilendiren bir dosyaya dair YENİ açıklama,
   kanun teklifi, yasal girişim haberdir (ör. "fon skandalında kim olursa olsun hesap soracağız" -> fon skandalının hukuki boyutu haberi).
   Belirli bir kişiyi suçlayan/itham eden iddia ya da kişisel polemik haber DEĞİLDİR.
C0) kisi (ÖZGÜN GAZETECİLER: adliye muhabirleri, araştırmacı gazeteciler): bu hesaplar haberi çoğu zaman İLK veren kaynaktır.
   Paylaşım YENİ ve SOMUT bir hukuki gelişmeyi ilk kez duyuruyorsa (gözaltı/tutuklama/yakalama kararı, iddianame, dava açıldı,
   soruşturma başlatıldı, karar çıktı, erişim engeli, kayyım, ifadeye çağrı) başka sitede henüz olmasa da "haber": true;
   gazetecinin yorumu, polemiği, kişisel görüşü ya da kaynağı belirsiz söylentisi haber değildir. Aşağıdaki C kuralları da geçerlidir.
C) kisi / haberci (gazeteciler, haber hesapları): kamuyu ilgilendiren hukuki gelişme haberdir:
   - kanun, Resmî Gazete, yüksek mahkeme kararı, kurum kararı ya da kurumun suç duyurusu;
   - KAMU DOSYALARI: belediye ya da kamu kurumu soruşturmaları, kamu görevlilerine yönelik soruşturmalar, büyük operasyonlar
     (organize suç, yasa dışı bahis, rüşvet, ihaleye fesat, dolandırıcılık ağları), toplu mağduriyet yaratan dosyalar (fon, kripto),
     kamuoyunun izlediği büyük davalardaki yasal adımlar (iddianame kabulü, duruşma, karar, tahliye, re'sen soruşturma).
     Bunlar kişi haberi değil dosya haberidir: haber, sürecin hukuki boyutunu (hangi suç, hangi madde, sonraki adımlar) anlatır.
   - KAMUOYUNUN TANIDIĞI KİŞİLER: gazeteci, medya sahibi, siyasetçi, belediye başkanı, iş insanı, sanatçı, sporcu, akademisyen
     hakkında gözaltı, tutuklama, adli kontrol, tahliye, iddianame, dava ya da karar HABERDİR; kamuoyu izler. Haber kişiyi suçlamaz,
     hangi suçlama, hangi kanun maddesi, masumiyet karinesi ve sonraki adımlarla hukuki süreci anlatır.
   Haber DEĞİLDİR: tanınmayan tek bir sıradan kişinin gözaltı/tutuklama/ifade haberi, yerel asayiş olayı (tek kavga, kaza, küçük hırsızlık),
   özel kişiler arasındaki kişisel uyuşmazlık, kişisel polemik, kişinin kendisi hakkındaki paylaşımı, Türkiye hukukuyla ilgisi olmayan yurt dışı olayları.
Her grupta "haber": false: tebrik, anma, taziye, kutlama, polemik, slogan, tanıtım, eski olay, tahmin, belirsiz ima, şaka/ironi,
kişisel sorun, listede zaten işlenmiş konu (yeni gelişme yoksa).
"tur" alanı: "resmi" = A; "siyasi" = B; "gazeteci" = C0; "iddia" = C.
GÜNCELLEME: Konu sitede ZATEN işlenmişse ve paylaşım o konuda YENİ ve SOMUT bir gelişme bildiriyorsa "haber": true, "islem": "guncelleme"
ve "guncellenecek" alanına listedeki yazının slug'ını (/ işaretleri olmadan) yaz. Yeni gelişme yoksa "haber": false.
ANALİZ: Konu geniş kesimi etkileyen bir hukuki değişiklikse (yeni kanun, yürürlüğe giren önemli düzenleme, genel etkili yüksek mahkeme
kararı, büyük bir kamu dosyasının hukuki boyutu) "analiz": true; sıradan duyurularda false.
Yalnızca JSON döndür: {"haber": true|false, "islem": "yeni|guncelleme", "guncellenecek": "slug ya da null", "analiz": true|false,
"tur": "resmi|siyasi|iddia", "konu": "en fazla 12 kelime, kişi adı değil konu", "oncelik": 1|2|3, "neden": "kısa",
"ilgili": "paylaşımın konusu sitede (listede) işlenmişse o yazının slug'ı, yoksa null (haber false olsa da doldur)"}
oncelik 1 = yeni yürürlüğe giren düzenleme ya da yüksek mahkeme kararı; 2 = önemli; 3 = sıradan.
ÖNCELİK: Resmî Gazete'de ya da resmi kurum duyurusunda geniş kesimi doğrudan etkileyen düzenlemeler (kamu personeli, sözleşmeli personel,
sınav/atama: KPSS, AGS, YKS, ÖSYM; vergi, harç, SGK, emeklilik, asgari ücret, kira, ehliyet/pasaport işlemleri) her zaman "haber": true,
"oncelik": 1 ve "analiz": true olsun; bunlar insanların en çok aradığı konulardır, atlama."""

def ele(tw):
    if sinir_doldu(sayac("eleme"), GUNLUK_ELEME_SINIRI):
        return {"haber": False, "neden": "günlük eleme sınırı"}
    sayac("eleme", 1)
    liste = site_listesi(50)
    # yazımı başarısız olan (denetim, hata, sınır) konular "işlendi" sayılmaz; yeni kaynaktan gelince tekrar denenir
    # "yazılıyor" kaydı 10 dakikadan eskiyse yarıda kalmış sayılır (servis yeniden başlamış ya da hata olmuş)
    konular = "\n".join(f"- {x['konu']} ({x['durum']})" for x in [k for k in son_konular(24)
                         if k.get("durum") not in ("denetim", "hata", "sınır", "teyit bekliyor")
                         and not (k.get("durum") == "yazılıyor" and time.time() - k["ts"] > 600)][-40:])
    mesaj = (f"Paylaşan: {tw['ad']} (@{tw['kullanici']}), hesap grubu: {tw['grup']}\nSaat: {tw['saat']}\n"
             f"Metin:\n{tw['metin']}\n\nSitede son yayımlananlar:\n{liste}\n\nSon 24 saatte işlenen konular:\n{konular or '-'}")
    metin = kucuk_model(ELEME_SISTEM, mesaj, max_tokens=2000, timeout=90)
    el = json_ayikla(metin)
    el["tur"] = {"resmi": "resmi", "siyasi": "siyasi", "kisi": "gazeteci"}.get(tw["grup"], "iddia")  # tür hesabın grubundan gelir
    return el

# ------------------------------------------------------------------ 2) yazım
YAZIM_SISTEM = """Sen tarafsız bir hukuk haber sitesinin deneyimli adliye muhabirisin. Sana az önce atılmış bir X paylaşımı veriliyor.
Önce webde tarama yap, sonra teyitli, tarafsız ve özgün bir haber yaz. Doğruluk hızdan önce gelir.

1) WEB TARAMASI (web_search aracı, en fazla 5 arama):
- Olayı haber sitelerinde ara. Başka sitede çıkmışsa adresini ve saatini "diger_siteler"e yaz; çıkmamışsa "ilk": true.
- Başka sitelerin cümlelerini, başlığını, yapısını KULLANMA; olguları kendi cümlelerinle yaz ve kendi hukuki açını kat.
- Haberin hukuki çerçevesi için resmî/mevzuat kaynağı bul (mevzuat.gov.tr, resmigazete.gov.tr, anayasa.gov.tr, yargitay.gov.tr, kurumun kendi sitesi vb.).
- Kaynak listesine ve metne başka avukatların, hukuk bürolarının ya da kişisel hukuk bloglarının sitelerini KOYMA ve onlara atıf yapma
  ("bir avukat sitesinde..." gibi); yalnızca resmî kurumlar, mevzuat siteleri ve haber kuruluşları kaynak olur.

2) HABER TÜRÜNE GÖRE ÇERÇEVE (editör notundaki "tur"):
- resmi: Kurumun açıklaması birincil kaynaktır; "... açıkladı", "... duyurdu" diye aktar, ne anlama geldiğini ve sonraki usul adımını anlat.
- siyasi: Açıklamayı "... açıkladı", "... dedi" diye kısaca aktar; haberin ağırlığı KONUNUN hukuki boyutu olsun (ilgili kanun maddeleri,
  hangi suçlar/hükümler gündeme gelebilir, süreç nasıl işler). Örnek: "fon skandalında hesap soracağız" -> fon dosyasında gündeme gelen
  suç tiplerinin TCK/SPK maddeleri, yaptırımlar ve yatırımcının yolları. Belirli kişileri suçlayan iddia konu olamaz.
- gazeteci (özgün gazeteci hesabı, haberi İLK veren kaynak olabilir): Resmî kaynak ya da ikinci bir haber kaynağıyla teyit
  edilebiliyorsa normal yaz. Edilemiyorsa da YAZ ("yayinla": true, "teyit": false, "tek_kaynak": true): bilgiyi açıkça gazeteciye
  dayandır ("Gazeteci Ad Soyad'ın X hesabından aktardığına göre ..."), koşullu ve temkinli dil kullan, kesinleşmiş olgu gibi sunma;
  resmî açıklama yapılmadığını belirt; kişileri suçlama, masumiyet karinesini hatırlat; haberin ağırlığı sürecin hukuki boyutu olsun
  (hangi kanun maddesi, sonraki usul adımları). Başlıkta da kaynak belli olsun ya da koşullu dil kullan (ör. "... İddiası", "... İddia Edildi").
- iddia (haber hesabı): Konu, YALNIZCA resmî bir kaynak (kurum sitesi, Resmî Gazete, TBMM, mahkeme) ya da iki bağımsız haber
  kaynağıyla teyit edildiyse yazılır ("teyit": true); teyit yoksa "yayinla": false, "teyit": false.

3) KİŞİ KURALI (KESİN): Haber bir KONU haberidir, kişi haberi değildir.
- Tek bir sıradan kişinin gözaltısı, tutuklanması, ifadesi ya da kişisel davası haberin konusu olamaz; paylaşım buysa "yayinla": false.
- KAMU DOSYALARI (belediye/kamu kurumu soruşturması, büyük operasyon, toplu mağduriyet, kamuoyunun izlediği büyük dava) yazılabilir;
  haber dosyanın hukuki sürecini anlatır: resmî açıklamaya göre ne yapıldı, hangi suçlamalar ve TCK maddeleri, kaç kişi, hangi tedbir
  (tutuklama, adli kontrol, ev hapsi), süreç bundan sonra nasıl işler, şüphelilerin hakları. Masumiyet karinesi açıkça korunur.
- İSİM KURALI (KIRMIZI ÇİZGİ): Bir gerçek kişinin adı YALNIZCA şu şartların HEPSİ sağlanırsa yazılır:
  (a) kamuoyunca tanınan kişi: gazeteci, siyasetçi, kamu görevlisi ya da tanınmış kişi (sanatçı, sporcu, iş insanı gibi kamusal figür);
  (b) isim kaynak paylaşımında AÇIKÇA geçiyor (tanınmış kişi paylaşımda yalnız soyadıyla anılıyorsa, ör. "İmamoğlu", bu da yeterli;
  tam adı (c) şartındaki kaynaklardan yaz); (c) aynı kişiyi ve aynı olayı en az İKİ BAĞIMSIZ haber kuruluşu ya da bir resmî kaynak
  doğruluyor (web aramasında açıp gördüğün sayfalar; aynı ajans metnini kullanan siteler tek kaynak sayılır); (d) yayın yasağı yok.
  Tahminle, çağrışımla, "büyük ihtimalle" diye isim YAZMA. Özel kişi, çocuk, mağdur, tanık ve şüphelinin yakınlarının adı ASLA yazılmaz
  (sayı ve unvan yeterli: "belediyede görevli 7 kişi"). Bir şart bile eksikse ya da emin değilsen isim yazma, unvan kullan ("bir gazeteci").
  İsmi yazılan kişi tarafsız anlatılır: suçlama iddia olarak ve kaynağıyla verilir, kişinin ya da avukatının açıklaması varsa ona da yer verilir.
  ŞARTLAR SAĞLANIYORSA İSMİ YAZ: haberin ASIL ÖZNESİ şartları sağlayan bir siyasetçi ya da kamu görevlisiyse (belediye başkanı, milletvekili,
  bakan, vali, hâkim/savcı gibi) adı BAŞLIKTA ve ilk paragrafta yazılır ("Çukurova Belediye Başkanı Emrah Kozay Tutuklandı");
  şartlar sağlanmışken ismi saklayıp yalnızca unvan kullanma, bu okura eksik haber verir.
  Yazdığın HER gerçek kişi adını "post.isimler" alanında bildir: [{"ad": "Ad Soyad", "nitelik": "gazeteci|siyasetci|kamu_gorevlisi|taninmis_kisi",
  "kaynaklar": ["birinci bağımsız haber/resmî kaynak url", "ikinci url"]}] ve bu adresleri "kaynaklar" listesine de ekle. Bildirilmeyen
  bir isim metinde geçerse haber reddedilir.
- Kamu kurumları, görevlileri ve siyasetçiler yalnızca kendi açıklama ve resmî işlemleriyle anılır.
- Görsel aramalarında kişi adı kullanılmaz; kurum binası, mekân ya da konuyu anlatan genel fotoğraf aranır.

4) KESİN KURALLAR:
- Tarafsızlık: taraf tutan, yorum katan, sıfatla yargılayan ifade yok; siyasi aktörlere eşit mesafe.
- İtham yok: kimse suçlu diye nitelenmez; "iddia edildi", "belirtti", "açıkladı" kullanılır. Masumiyet karinesi korunur.
  Gözaltı, tutuklama, dava, mahkûmiyet ve kesinleşme birbirinden ayrı tutulur. Çocuk ve mağdur kimliği yazılmaz.
- Telif: başka sitelerin metni kopyalanmaz; tweetten doğrudan alıntı en fazla iki kısa cümle ve tırnak içinde.
- Doğrulayamadığın isim, sayı, tarih, madde numarası, ceza miktarı YAZILMAZ.
- Değişiklik metinlerindeki ibare değişikliklerini ("... ibaresi ... olarak değiştirilmiştir", bent/fıkra ekleme) madde madde aktarma;
  okurun anlayacağı biçimde neyin değiştiğini özetle. Anlamından tam emin olmadığın madde, bent ya da numarayı hiç yazma.
- Kategori, işlemi yapan kuruma ve konuya göre seçilir: "Adalet Bakanlığı" yalnızca Adalet Bakanlığı'nın işlemleri; "Anayasa Mahkemesi",
  "Yargıtay", "Danıştay" yalnızca o mahkemenin kararları; diğer bakanlıkların ekonomi, ticaret, ulaştırma düzenlemeleri "Ekonomi";
  yargı süreçleri "Yargı"; siyasi süreç ve TBMM "Siyaset"; bilişim ve veri "Teknoloji".
- Dil: sade, somut Türkçe; 5N1K ile başla; cümle uzunlukları değişken. Uzun tire (—) yok. "Sonuç olarak", "özetle",
  "önemle belirtmek gerekir", "dikkat çekici", "kritik", "unutmamak gerekir", "kesinlikle", "bu bağlamda", "merakla bekleniyor" yok.
- Paylaşım şaka, ironi, eski olay, belirsiz ima ise ya da olay sitede zaten varsa ve yeni gelişme yoksa yayınlama.
- İÇ BAĞLANTI: "Sitede son yayımlananlar" listesinde konuyla DOĞRUDAN ilgili yazı varsa metne 1-2 doğal bağlantı ver:
  <a href="/slug/">cümlenin parçası olan anlamlı ifade</a> ("buraya tıklayın" gibi değil). İlgili yazı yoksa bağlantı koyma.
- Avukat büro sitelerine (yagmurtahtasiz.com, umuttekin.av.tr) hizmet sayfası bağlantısı ("izmir-ceza-avukati" gibi) VERME.
  Yalnızca haberin konusunu BİREBİR anlatan bir rehber yazısı (https://yagmurtahtasiz.com/blog/... ya da /araclar/...) varsa en fazla
  1 bağlantı ver: rehberin konusu haberin başlığındaki konuyla aynı olmalı (ör. süresiz nafaka haberi -> "süresiz nafaka kaldırıldı mı"
  rehberi; kıdem tazminatı haberi -> kıdem tazminatı hesaplama aracı). Operasyon, gözaltı, tutuklama, siyaset ve genel gündem
  haberlerinde hiç bağlantı verme. Emin değilsen verme.

USUL VE KAYNAK DOĞRULUĞU (KESİN):
- Tutuklama ve adli kontrol kararına itiraz: süre kararın öğrenilmesinden itibaren İKİ HAFTA (CMK 268/1, 7499 s.K. ile 1.6.2024'ten beri);
  dilekçe kararı veren sulh ceza hâkimliğine verilir; itirazı yargı çevresindeki ASLİYE CEZA MAHKEMESİ HÂKİMİ inceler (CMK 268/3-b, 7331 s.K.,
  1.1.2022). Tutuklama/adli kontrol için "bir sonraki/sıradaki sulh ceza hâkimliği" ESKİ usuldür, YAZMA. El koyma, kayyım, arama gibi diğer
  sulh ceza kararlarına itirazı ise numara olarak izleyen sulh ceza hâkimliği inceler (CMK 268/3-a); süre yine iki haftadır.
  Gözaltına itiraz sulh ceza hâkimliğine yapılır (CMK 91/5).
- Usul süresini, merciini ya da madde numarasını yalnızca güncel mevzuat metninden (mevzuat.gov.tr, Resmî Gazete) doğruladıysan yaz;
  emin değilsen "kanunda öngörülen süre içinde" gibi genel ifade kullan.
- Kanun TEKLİFİ ya da tasarısı yürürlükteki kanun gibi anlatılmaz: "teklif edildi", "kabul edilirse", "Genel Kurul'da görüşülecek" denir;
  yürürlük ancak Resmî Gazete'de yayımla başlar ve tarihi belirtilir.
- Ajansların aynı metnini kullanan haber siteleri BAĞIMSIZ teyit sayılmaz; birincil kaynak (kurum açıklaması, Resmî Gazete, karar metni)
  ile ikincil kaynağı (haber sitesi) ayır ve metinde hangisine dayandığını belli et.
- Olay haberlerinde (gözaltı, operasyon, tutuklama, dava) başlık "... Ne Demek?", "... Nedir?" kalıbında olmaz; olayı söyleyen haber başlığı kullanılır.

4b) UZUNLUK VE YAPI: Her taslak haberi ve hukuki değerlendirmeyi AYNI yazıda verir (ayrı analiz yazılmaz).
- 600-1000 kelime, 4-6 <h2>. Sıra: spotta 5N1K; ardından olgular (kendi cümlelerinle); sonra hukuki çerçeve ve ilgili maddeler
  (yalnızca doğrulanmış), uygulamada ne değişir, vatandaş/kurum ne yapmalı, süreç bundan sonra nasıl işler.
- ARAMA VE YAPAY ZEKÂ ÖZETLERİ İÇİN: spotun İLK cümlesi tek başına okunduğunda haberin tamamını anlatan kesin bir olgu cümlesidir:
  kim (kurum/kişi adıyla), ne oldu, ne zaman (gün ay yıl) ve varsa hukuki dayanak (ör. "5651 sayılı Kanun'un 8/A maddesi"). "Haberlere
  göre" gibi belirsiz girişle ya da soruyla başlama. Ara başlıklar (<h2>) genel kalıp olmasın ("Haberlerde neler aktarıldı?" YANLIŞ);
  konunun öznesini taşısın ("Cafer Mahiroğlu'nun hesabına erişim engeli nasıl verildi?" DOĞRU). Her <h2>'nin altındaki ilk cümle o
  başlığın sorusunu doğrudan cevaplar. Rakam, tarih, madde numarası ve kurum adlarını açık yaz.
- "sss": en fazla 4 kısa soru (en fazla 45 karakter, insanların arayacağı kalıpta) ve 1-2 cümlelik cevap; yalnızca metindeki bilgiye dayanır.
- "post" içine "kapsamli": true ekle.

BAŞLIK (ARAMA KALIBI): Konu geniş kesimi etkileyen bir düzenleme ise (kamu personeli, sınav/atama, vergi, harç, SGK, emeklilik,
asgari ücret, kira vb.) başlığı insanların Google'da arayacağı soru kalıbında yaz: "... Ne Anlama Geliyor?", "... Kimleri Kapsıyor?",
"... Ne Zaman?", "... Başvuru Nasıl Yapılır?", "... Ne Değişti?". Anahtar terim (düzenlemenin adı, sınav adı, karar numarası) başta olsun;
en fazla 75 karakter, doğal ve abartısız, tık tuzağı yok. Diğer haberlerde olağan haber başlığı kullan.

5) ÇIKTI: yalnızca tek JSON nesnesi.
Yayınlanmayacaksa: {"yayinla": false, "teyit": true|false, "neden": "kısa", "diger_siteler": [...]}
Yayınlanacaksa:
{"yayinla": true, "teyit": true|false, "tek_kaynak": true|false, "ilk": true|false, "diger_siteler": [["site adı", "url", "saat varsa"]],
 "post": {
  "slug": "en fazla 8 kelime, küçük harf, Türkçe karakter yok, tireli",
  "title": "EN FAZLA 75 KARAKTER, tarafsız, tek fikir",
  "tur": "Haber",
  "cats": ["listeden 1-2 kategori"],
  "tags": ["5-8 etiket"],
  "ozet": ["3 madde, her biri tek cümle"],
  "body": "<p class=\\"lead\\">spot, 2-3 cümle</p> + <h2>...</h2><p>...</p> bölümleri; uzunluk 4b maddesine göre",
  "kaynaklar": [["dayanılan kaynak: X paylaşımıysa 'X paylaşımı: Ad (@kullanici), gün ay yıl SS.DD', web sayfasıysa 'Kurum, gün ay yıl: belge başlığı'", "bağlantı"], ["resmî/mevzuat kaynağının başlığı", "url"], ...],
  "karar": "YALNIZCA haber bir mahkeme kararını konu alıyorsa ve bilgiler kaynakta AÇIKÇA yazıyorsa: {\"mahkeme\": \"Yargıtay\", \"daire\": \"9. Hukuk Dairesi\", \"esas\": \"2025/1234\", \"karar_no\": \"2026/567\", \"tarih\": \"12 Mart 2026\", \"konu\": \"kısa\", \"sonuc\": \"kısa\", \"kaynak\": \"resmî karar metni https bağlantısı\"}; kaynakta olmayan alanı YAZMA (tahmin etme, uydurma), hiçbiri yoksa ya da konu karar değilse null",
  "gorsel_aramalari": ["FOTOĞRAF için 3 kısa İngilizce arama; ÖNCE haberin KONUSUNU gösteren nesne/sahne (ör. yasa dışı bahis -> \"online betting smartphone\", \"Turkish lira banknotes\"; uyuşturucu -> \"seized drugs police evidence\"; kira -> \"apartment building keys\"; görüntü paylaşımı -> \"smartphone recording video\"). Bina, adliye ya da kurum binası araması YAZMA; kişi adı yok"],
  "gorsel": null
 }}
Kategori listesi: """ + ", ".join(KATEGORILER)

ANALIZ_EK = """

BU BİR ANALİZ YAZISIDIR (yukarıdaki kuralların hepsi geçerli, şu farklarla):
- post.tur = "Analiz". Başlık en fazla 75 karakter, açıklayıcı ve aynı konudaki kısa haberden farklı olsun (ör. "... Ne Değiştiriyor?").
- body 600-1000 kelime, 4-6 <h2>: düzenlemenin/kararın hukuki çerçevesi, ilgili maddeler (yalnızca doğrulanmış), uygulamada ne değişir,
  vatandaş ve kurumlar ne yapmalı, süreç bundan sonra nasıl işler.
- post.sss: en fazla 4 soru, YALNIZCA iki elemanlı listeler halinde: [["soru metni", "cevap metni"], ...] (sözlük ya da "q"/"a" anahtarı kullanma). Soru en fazla 45 karakter, insanların arayacağı kısa kalıp ("Yeni ceza ne kadar?");
  cevap 1-2 cümle, yalnızca metindeki doğrulanmış bilgiye dayanır.
- Bu bir haber değil açıklayıcı yazı olduğu için "ilk" alanını false bırakabilirsin."""

ARASTIRMA_SISTEM = """Bir hukuk haber sitesinin araştırmacısısın. Bir X paylaşımı veriliyor; habercinin yazabilmesi için web_search ile
(en fazla 5 arama) araştır ve NOT çıkar. Haber yazma, yalnızca doğrulanmış bilgileri topla:
- Olay: ne oldu, kim (kurum), nerede, ne zaman; sayılar ve tarihler. Kişi suçlaması yok, iddiaları "iddia" diye işaretle.
- Teyit için en az 3 FARKLI haber sitesini ve varsa resmî kaynağı (kurum sitesi, Resmî Gazete, başsavcılık, mahkeme) bul;
  bulduğun her siteyi "diger_siteler"e yaz. Teyit kararını sen verme, yalnızca bulduklarını listele.
- Hukuki çerçeve: ilgili kanun ve madde numaraları, maddelerin KISA özeti (mevzuat.gov.tr, resmigazete.gov.tr vb. üzerinden doğrula),
  usulde sonraki adımlar, varsa emsal karar.
- Kaynaklar: her biri için başlık, kurum/site, tarih-saat ve tam URL. Avukat, hukuk bürosu ve kişisel hukuk blogu sitelerini kaynak alma.
- Başka sitelerde çıkmış mı: site adı, URL, saat.
Yalnızca JSON: {"olgular": ["..."], "hukuki": ["..."], "ilk": true|false,
 "kaynaklar": [["Kurum/Site, gün ay yıl: başlık", "url"]], "diger_siteler": [["site", "url", "saat"]], "eksik": "bulunamayan önemli bilgi"}"""

from ortak import ENV as _ENV
ENV_YAZIM_MODU = _ENV.get("YAZIM_MODU", "iki")

def arastir(mesaj, azami_arama=5):
    """Ucuz araştırma: önce Google aramalı Gemini (ücretsiz), olmazsa web aramalı Haiku. Not metni (JSON ya da düz) döndürür.
    Pahalı yazım modeli (Sonnet) bu notları okur; kendisi web araması yapmaz (arama sonuçlarını tekrar tekrar okumak maliyetin çoğuydu)."""
    from ortak import gemini_arastir
    try:
        yazi, kay = gemini_arastir(ARASTIRMA_SISTEM + "\nNot: Kaynak adreslerini metne yazma; kaynak listesi aramadan ayrıca alınır. "
                                   "Notları JSON olarak ver.", mesaj)
        if kay and len(yazi) > 200:
            try: notlar = json_ayikla(yazi)
            except Exception: notlar = {"notlar": yazi}
            notlar["kaynaklar"] = kay   # yalnızca aramanın gerçekten açtığı adresler
            return json.dumps(notlar, ensure_ascii=False)
        log("gemini araştırması yetersiz, Haiku'ya geçiliyor")
    except Exception as e:
        log("gemini araştırması olmadı:", str(e)[:160])
    arac = [{"type": WEB_ARAMA_ARACI, "name": "web_search", "max_uses": azami_arama}]
    notlar, _ = claude(MODEL_ELEME, ARASTIRMA_SISTEM, mesaj, max_tokens=6000, araclar=arac, timeout=300)
    try: notlar = json.dumps(json_ayikla(notlar), ensure_ascii=False)
    except Exception: pass
    return notlar

NOT_EKI = ("\n\nARAŞTIRMA NOTLARI (web taraması yapıldı; web_search aracın YOK. Yalnızca bu notlardaki doğrulanmış "
           "bilgileri ve kaynakları kullan; notlarda olmayan madde numarası, sayı ya da bilgi uydurma; kaynak bağlantısı olarak yalnızca "
           "notlardaki 'kaynaklar' adreslerini kullan):\n")

def yaz(tw, eleme, analiz=False, haber=None, mod=None):
    """mod: "sonnet" (Sonnet + web araması; eski yöntem), "iki" (Haiku araştırır, Sonnet aramasız yazar), "haiku" (Haiku + arama)"""
    mod = mod or ENV_YAZIM_MODU
    gorseller = gorsel_listesi()
    liste = site_listesi(20)
    mesaj = (f"Paylaşan: {tw['ad']} (@{tw['kullanici']}) [{tw['grup']} hesabı]\nPaylaşım (TSİ): {tw['tarih']} {tw['saat']}\n"
             f"Bağlantı: {tw['url']}\nMetin:\n{tw['metin']}\n\nEditör notu: tur={eleme.get('tur')} | {eleme.get('konu','')}\n"
             f"Bugün: {simdi().strftime('%d.%m.%Y %H.%M')}\n\nSitede son yayımlananlar:\n{liste}")
    if analiz:
        mesaj += ANALIZ_EK
        if haber:
            hm = html.unescape(re.sub(r"<[^>]+>", " ", haber["body"]))
            mesaj += (f"\n\nBU KONUDA YAYINDAKİ KISA HABERİMİZ (/{haber['slug']}/): {haber['title']}\n{hm}\n\n"
                      f"Analiz bu haberi TEKRAR ETMEZ. Spotun hemen arkasındaki paragrafta <a href=\"/{haber['slug']}/\">...</a> ile habere "
                      "bağlantı ver. Haberde anlatılan olguları en fazla 1-2 cümleyle hatırlat; yazının geri kalanı haberde OLMAYAN konulara "
                      "ayrılsın: vatandaşın/yatırımcının/kurumun yapması gerekenler, başvuru yolları ve süreler, emsal kararlar ve uygulama, "
                      "mevzuatın arka planı, sık karşılaşılacak sorunlar. Ara başlıklar haberdekilerden farklı olsun. Haberin ötesinde "
                      "gerçekten yeni ve doğrulanmış bilgi katamıyorsan \"yayinla\": false ve \"neden\": \"ayrı değer yok\" döndür.")
    if eleme.get("capraz_teyit"):
        mesaj += ("\n\nÇAPRAZ TEYİT: Aynı gelişmeyi kısa süre içinde şu bağımsız hesaplar da paylaştı: "
                  + "; ".join(f"@{k} ({u})" for k, u, _ in eleme["capraz_teyit"])
                  + ". Bunları paylaşan hesap dışındaki bağımsız kaynaklar olarak say (teyit vardır); haber sitelerinde karşılıklarını bulursan kaynak listesine ekle.")
    # maliyet: web araması sonuçları girdinin büyük kısmı. Resmî Gazete metni tam geldiği için aramasız;
    # düşük öncelikli (3) haberlerde en fazla 2 arama; diğerlerinde 5.
    arama = int(os.environ.get("YAZIM_ARAMA", "5"))
    if tw.get("kullanici") == "Resmî Gazete" and not analiz:
        arama = 0
        mesaj += ("\n\nNOT: Yukarıdaki metin Resmî Gazete'de yayımlanan düzenlemenin kendisidir; web_search aracın yok. "
                  "Yalnızca bu metne dayan; metinde olmayan sayı, tarih ya da madde ekleme. Kaynak olarak Resmî Gazete bağlantısını göster.")
    elif str(eleme.get("oncelik")) == "3" and not analiz:
        arama = min(arama, 2)
    arac = [{"type": WEB_ARAMA_ARACI, "name": "web_search", "max_uses": arama}] if arama else None
    if mod == "iki" and arac:
        # 1) ucuz model web'de araştırır ve not çıkarır; 2) Sonnet bu notlardan, arama yapmadan yazar (pahalı model az girdi okur)
        notlar = arastir(mesaj, arama)
        mesaj2 = (mesaj + "\n\nARAŞTIRMA NOTLARI (web taraması yapıldı; web_search aracın YOK. Yalnızca bu notlardaki doğrulanmış "
                  "bilgileri ve kaynakları kullan; notlarda olmayan madde numarası, sayı ya da bilgi uydurma; 'ilk' ve 'diger_siteler' "
                  "alanlarını notlardan al. TEYİT kararını sen ver: notlarda resmî bir kaynak ya da paylaşan hesap dışında en az iki "
                  "bağımsız haber sitesi varsa teyit vardır):\n" + notlar)
        metin, u = claude(MODEL_YAZIM, YAZIM_SISTEM, mesaj2, max_tokens=12000, timeout=300)
    elif mod == "haiku":
        metin, u = claude(MODEL_ELEME, YAZIM_SISTEM, mesaj, max_tokens=12000, araclar=arac, timeout=400)
    else:
        metin, u = claude(MODEL_YAZIM, YAZIM_SISTEM, mesaj, max_tokens=12000, araclar=arac, timeout=400)
    return json_ayikla(metin), gorseller

# ------------------------------------------------------------------ görsel (Wikimedia Commons, serbest lisans)
_UA = {"User-Agent": "HukukiHaberler/1.0 (https://hukukihaberler.com; iletisim@hukukihaberler.com)"}
_LISANS = ("cc by", "cc-by", "cc0", "public domain", "pd", "kamu malı")

def _temiz(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

_KOTU_BASLIK = r"(?i)chart|diagram|logo|map|flag|seal|emblem|icon|graph|organi[sz]ation|scheme|plan\b|şema|harita|inside|interior|poster|screenshot"

def commons_adaylar(aramalar, azami=20):
    """birkaç aramadan serbest lisanslı fotoğraf adaylarını toplar (indirmez)"""
    out, gor = [], set()
    for q in (aramalar or [])[:4]:
        try:
            u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6"
                 "&gsrlimit=10&prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=1280&gsrsearch="
                 + urllib.parse.quote("filetype:bitmap " + q))
            js = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=_UA), timeout=20).read())
            for pg in sorted(js.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
                if pg["title"] in gor: continue
                ii = (pg.get("imageinfo") or [{}])[0]
                if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1000: continue
                if re.search(_KOTU_BASLIK, pg["title"]): continue
                em = ii.get("extmetadata", {})
                lic = _temiz(em.get("LicenseShortName", {}).get("value"))
                if not lic.lower().startswith(_LISANS): continue
                gor.add(pg["title"])
                out.append({"url": ii.get("thumburl") or ii["url"], "title": pg["title"], "page": ii.get("descriptionurl", ""),
                            "lic": lic, "artist": _temiz(em.get("Artist", {}).get("value"))[:120] or "Wikimedia Commons",
                            "aciklama": _temiz(em.get("ImageDescription", {}).get("value"))[:220],
                            "tarih": _temiz(em.get("DateTimeOriginal", {}).get("value"))[:20], "arama": q})
                if len(out) >= azami: return out
        except Exception as e:
            log("commons araması hata:", q, e)
    return out

def pexels_adaylar(aramalar, azami=15):
    """Pexels'ten gerçek fotoğraf adayları (PEXELS_KEY tanımlıysa). Pexels lisansı ticari kullanıma serbesttir."""
    from ortak import ENV
    anahtar = ENV.get("PEXELS_KEY", "")
    if not anahtar: return []
    out, gor = [], set()
    for q in (aramalar or [])[:3]:
        try:
            u = "https://api.pexels.com/v1/search?per_page=10&orientation=landscape&query=" + urllib.parse.quote(q)
            js = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"Authorization": anahtar, **_UA}), timeout=20).read())
            for f in js.get("photos", []):
                if f["id"] in gor or f.get("width", 0) < 1200: continue
                gor.add(f["id"])
                out.append({"url": f["src"].get("landscape") or f["src"]["large"], "kucuk": f["src"].get("medium"),
                            "title": f"Pexels {f['id']}: {f.get('alt') or q}", "page": f.get("url", ""), "lic": "Pexels Lisansı",
                            "artist": (f.get("photographer") or "Pexels")[:120], "aciklama": (f.get("alt") or "")[:220],
                            "tarih": "", "arama": q, "kaynak": "Pexels"})
                if len(out) >= azami: return out
        except Exception as e:
            log("pexels araması hata:", q, e)
    return out

_OV_LISANS = {"by": "CC BY", "by-sa": "CC BY-SA", "cc0": "CC0", "pdm": "Kamu malı"}

def openverse_adaylar(aramalar, azami=15):
    """Openverse (Flickr vb.) üzerinden ticari kullanıma uygun lisanslı gerçek fotoğraflar; anahtar gerekmez"""
    out, gor = [], set()
    for q in (aramalar or [])[:3]:
        try:
            u = ("https://api.openverse.org/v1/images/?page_size=20&license_type=commercial&mature=false&category=photograph"
                 "&q=" + urllib.parse.quote(q))
            js = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=_UA), timeout=25).read())
            for f in js.get("results", []):
                lic = _OV_LISANS.get((f.get("license") or "").lower())
                if not lic or f.get("source") == "wikimedia" or f["id"] in gor: continue  # Commons zaten ayrıca aranıyor
                g_, y_ = f.get("width") or 0, f.get("height") or 0
                if (g_ and g_ < 800) or (g_ and y_ and y_ > g_ * 1.1): continue  # boyutu bilinmeyen kabul; küçük ve dikey olan alınmaz
                if str(f.get("url", "")).lower().split("?")[0].endswith((".png", ".gif", ".svg", ".webp")): continue
                gor.add(f["id"])
                surum = f" {f['license_version']}" if f.get("license_version") and lic not in ("CC0", "Kamu malı") else ""
                kaynak = (f.get("source") or "Openverse").replace("flickr", "Flickr")
                out.append({"url": f["url"], "kucuk": f.get("thumbnail") or f["url"], "title": f"{kaynak} {f['id'][:8]}: {f.get('title') or q}",
                            "page": f.get("foreign_landing_url") or "", "lic": lic + surum, "artist": (f.get("creator") or kaynak)[:120],
                            "aciklama": ((f.get("title") or "") + " " + " ".join(t.get("name", "") for t in (f.get("tags") or [])[:8]))[:220],
                            "tarih": "", "arama": q, "kaynak": kaynak})
                if len(out) >= azami: return out
        except Exception as e:
            log("openverse araması hata:", q, e)
    return out

def pixabay_adaylar(aramalar, azami=12):
    """Pixabay (PIXABAY_KEY tanımlıysa); Pixabay içerik lisansı ticari kullanıma serbesttir"""
    from ortak import ENV
    anahtar = ENV.get("PIXABAY_KEY", "")
    if not anahtar: return []
    out = []
    for q in (aramalar or [])[:3]:
        try:
            u = (f"https://pixabay.com/api/?key={anahtar}&image_type=photo&orientation=horizontal&min_width=1200&per_page=12"
                 "&safesearch=true&q=" + urllib.parse.quote(q))
            js = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=_UA), timeout=20).read())
            for f in js.get("hits", []):
                out.append({"url": f["largeImageURL"], "kucuk": f.get("webformatURL"), "title": f"Pixabay {f['id']}: {f.get('tags', q)}",
                            "page": f.get("pageURL", ""), "lic": "Pixabay Lisansı", "artist": (f.get("user") or "Pixabay")[:120],
                            "aciklama": f.get("tags", "")[:220], "tarih": "", "arama": q, "kaynak": "Pixabay"})
                if len(out) >= azami: return out
        except Exception as e:
            log("pixabay araması hata:", q, e.__class__.__name__)  # adres anahtar içerdiği için ayrıntı yazılmaz
    return out

def tum_adaylar(aramalar):
    """kaynakları sırayla karıştırır; böylece kısa listeye her kaynaktan aday girer"""
    listeler = [commons_adaylar(aramalar), openverse_adaylar(aramalar), pixabay_adaylar(aramalar), pexels_adaylar(aramalar)]
    out = []
    for i in range(max(len(l) for l in listeler)):
        out += [l[i] for l in listeler if i < len(l)]
    return out[:40]

GORSEL_SISTEM = """Bir hukuk haber sitesinin foto editörüsün. Haberin konusunu DOĞRUDAN gösteren fotoğrafları seç.
Kurallar:
- Fotoğraf haberin asıl konusunu göstermeli: sağlık haberinde hastane/sağlık çalışanı/tıbbi ortam; demiryolunda tren/istasyon;
  mahkeme kararında o mahkemenin KENDİ binası (genel adliye değil); haberin konusu olan kurumun (TV kanalı, büyükelçilik) kendi binası; TBMM'de Meclis; ekonomi düzenlemesinde ilgili sektör (ör. kredi kartı, banka, borsa).
- Haber Türkiye ile ilgiliyse başka ülkenin askeri, polisi, bayrağı ya da tabelası öne çıkan fotoğrafı SEÇME; haber askerî değilse askerî fotoğraf SEÇME.
- Yalnızca bir şehir ya da ülke adı geçtiği için alakasız sokak, manzara, eski tarihli (2000 öncesi) fotoğraf SEÇME.
- Tanınabilir özel kişilerin yüzünü öne çıkaran fotoğraf, çocuk fotoğrafı, iç mekân planı, grafik SEÇME.
En uygun en fazla 8 adayı ("c<numara>" ya da arşiv "a:<anahtar>") EN İYİDEN başlayarak sırala; uygun olmayanı listeye koyma.
Yabancı plaka, kurum adı ya da yazısı öne çıkacağı belli olan adayı (ör. "Chicago Fire Department", "Summit County") listeye alma.
Pixabay/Flickr adaylarının başlığı etiket listesidir; etiketler konuyu karşılıyorsa (ör. "tanker, truck, hazardous") listeye al.
Fotoğrafın Türkiye'de çekilmemiş olması tek başına eleme nedeni değildir; son karar fotoğrafa bakılarak verilir.
Hiçbiri uygun değilse boş liste ver; uygunsuz fotoğraf koymaktansa yazılı kapak daha iyidir.
Yalnızca JSON döndür: {"sirali": ["c3", "a:anahtar", ...], "neden": "liste boşsa kısa gerekçe"}"""

GORSEL_DENETIM_SISTEM = """Bir hukuk haber sitesinin foto editörüsün. Sana bir haber ve bir aday fotoğraf gösteriliyor; fotoğrafa BAKARAK
bu haberin kapak görseli olarak uygun olup olmadığını puanla.
5: haberin KONUSUNU doğrudan gösteriyor (üniversite/eğitim yönetmeliğinde öğrenciler, amfi, kampüs, mezuniyet; bahis haberinde bahis/telefon/para, uyuşturucu haberinde ele geçirilen madde, kira haberinde
   konut ve anahtar, vergi haberinde belgeler ve hesap makinesi); BİNA fotoğrafı yalnızca aşağıdaki KURUM BİNASI istisnasıyla 4-5 alır
4: konuyla açık ve doğrudan ilişkili genel bir fotoğraf; okuyucu yadırgamaz
3: dolaylı ya da zorlama ilişki
1-2: alakasız ya da yanıltıcı
Fotoğrafın Türkiye'de çekilmemiş olması TEK BAŞINA puan düşürmez: konuyu doğrudan gösteren, ülkesi belli olmayan bir sahne
(ör. otoyolda tanker, ADR levhası yakın planı, banka kartları) 4-5 alabilir.
Puanı EN FAZLA 2 ver:
- haber Türkiye ile ilgiliyken başka ülkenin askeri, polisi, bayrağı ya da üniforması ya da OKUNUR yabancı plaka, tabela, kurum adı öne çıkıyorsa
- haber askerî değilken askerî araç ya da personel varsa
- bir kişinin yüzü net seçilip fotoğrafın odağıysa (poz veren stok fotoğraf modeli de dahil; eller, arkadan ya da uzaktan kişiler sorun değil) ya da çocuk varsa
- şema, grafik, harita, logo, ekran görüntüsü ya da belge taramasıysa
- haberi olduğundan farklı gösteriyorsa (ör. kaza olmayan haberde kaza, şiddet olmayan haberde şiddet)
- hâkim tokmağı (gavel) öne çıkıyorsa: Türk mahkemelerinde tokmak kullanılmaz, yanıltıcıdır
- kelepçe, parmaklık, hücre, kelepçeli el, sorgu odası gibi SUÇLULUK çağrıştıran bir sahne gösteriyorsa (masumiyet karinesi;
  haber doğrudan cezaevi koşulları ya da infaz düzenlemesi değilse)
- fotoğrafın ana konusu bir BİNA ya da cephe ise EN FAZLA 2. TEK İSTİSNA (KURUM BİNASI): haberin DOĞRUDAN konusu belirli bir kurumsa
  ve fotoğraf O KURUMUN KENDİ binasıysa (Halk TV soruşturmasında Halk TV binası, Yargıtay kararında Yargıtay binası, ATV haberinde ATV
  binası, bir büyükelçilikle ilgili haberde o büyükelçiliğin binası, bir üniversitenin yönetmeliğinde O ÜNİVERSİTENİN binası ya da
  kampüsü) 4-5 verilebilir. Hangi bina olduğunu fotoğraftaki tabela/yazıdan
  ya da sana verilen "Fotoğraf künyesi"nden anla; künye ve görüntü o kurumu açıkça göstermiyorsa istisna uygulanmaz. Genel adliye,
  başka bir kurumun binası ya da kimliği belirsiz bina her durumda EN FAZLA 2
- eski model/antika araç, siyah-beyaz ya da açıkça eski tarihli bir sahne gösteriyorsa (haber tarihî bir konu değilse)
- müze, fuar, klasik araç sergisi gibi haberle ilgisiz bir ortamdaysa
"alt": görme engelli okur ve Google Görseller için fotoğrafı anlatan Türkçe alt metni; 6-14 kelimelik tek cümle, yalnızca
fotoğrafta GÖRÜNENİ anlatır, kişi adı ve yorum içermez, "fotoğraf"/"görsel" sözüyle başlamaz (ör. "Gün batımında kep fırlatan mezun öğrencilerin silüeti").
Yalnızca JSON: {"puan": 1-5, "goruluyor": "fotoğrafta ne var (kısa)", "neden": "kısa", "alt": "..."}"""

GORSEL_ESIK = 4

GORSEL_GENEL_SISTEM = """Bir hukuk haber sitesinin foto editörüsün. Bu haber için konuya özgü fotoğraf bulunamadı; şimdi SON ÇARE olarak
genel bir hukuk/yargı/mevzuat fotoğrafı seçiyorsun (adalet heykeli, kanun kitapları, imzalanan belge, dosya ve evrak, Türk lirası gibi).
Bina ya da cephe fotoğrafı (adliye, bakanlık, kurum binası) KULLANILMIYOR: bunlara en fazla 2 ver.
Fotoğrafa BAKARAK genel kapak görseli olarak uygunluğunu puanla:
5: evrensel hukuk simgesini ya da konuya yakın bir nesneyi (belge, para, telefon) temiz biçimde gösteriyor; haberle çelişmiyor
4: genel hukuk teması açık, okuyucuyu yanıltmaz
3 ve altı: bulanık, ilgisiz, yanıltıcı
Puanı EN FAZLA 2 ver: kelepçe, parmaklık, hücre gibi suçluluk çağrıştıran sahne varsa; başka ülkenin bayrağı/tabelası/üniforması öne çıkıyorsa; yüzü net seçilen ve fotoğrafın odağı olan bir kişi (poz veren stok model dahil) ya da çocuk varsa; şiddet,
kaza, gözaltı sahnesi varsa; şema, logo, ekran görüntüsüyse; Türk mahkemelerinde kullanılmayan tokmak (gavel) öne çıkıyorsa.
"alt": görme engelli okur ve Google Görseller için fotoğrafı anlatan Türkçe alt metni; 6-14 kelimelik tek cümle, yalnızca
fotoğrafta GÖRÜNENİ anlatır, kişi adı ve yorum içermez, "fotoğraf"/"görsel" sözüyle başlamaz (ör. "Gün batımında kep fırlatan mezun öğrencilerin silüeti").
Yalnızca JSON: {"puan": 1-5, "goruluyor": "fotoğrafta ne var (kısa)", "neden": "kısa", "alt": "..."}"""

def _duz_rgb(im):
    """saydam (dekupe) görselleri sitenin koyu zeminine oturtur; saydam alan JPEG'de bozuk renk vermesin"""
    from PIL import Image
    if im.mode == "P" and "transparency" in im.info: im = im.convert("RGBA")
    if im.mode in ("RGBA", "LA", "PA"):
        im = im.convert("RGBA")
        zemin = Image.new("RGBA", im.size, (23, 36, 47, 255))
        return Image.alpha_composite(zemin, im).convert("RGB")
    return im.convert("RGB")

def _kucuk_jpeg(veri, en=768):
    from PIL import Image
    im = _duz_rgb(Image.open(io.BytesIO(veri)))
    if im.width > en: im = im.resize((en, round(im.height * en / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=80); return b.getvalue()

def commons_kucuk_url(url, en=500):  # Wikimedia standart küçük resim genişlikleri: 330, 500, 960, 1280
    return re.sub(r"/\d+px-", f"/{en}px-", url) if "/thumb/" in url else url

def _gorsel_baytlari(secim):
    """('c', commons bilgisi) ya da ('a', arşiv anahtarı) için küçültülmüş JPEG baytları"""
    tur, deger = secim
    if tur == "c":
        adres = deger.get("kucuk") if deger.get("kaynak") else commons_kucuk_url(deger["url"], 960)
        veri = urllib.request.urlopen(urllib.request.Request(adres or deger["url"], headers=_UA), timeout=30).read()
    else:
        veri = open(os.path.join(SITE_DEPO, "commons", deger + ".jpg"), "rb").read()
    return _kucuk_jpeg(veri)

def kucuk_model(sistem, mesaj, max_tokens=2000, timeout=90):
    """görsel hattının metin adımları: önce ücretsiz Gemini, hata/kota olursa Claude Haiku"""
    if GEMINI_KEY:
        try:
            return gemini(sistem, mesaj, timeout=timeout)
        except Exception as e:
            log("gemini olmadı, Claude kullanılıyor:", str(e)[:120])
    return claude(MODEL_ELEME, sistem, mesaj, max_tokens=max_tokens, timeout=timeout)[0]

def gorsel_dogrula(p, jpeg, genel=False, kunye=""):
    """fotoğrafa bakarak uygunluk puanı verir: {'puan', 'goruluyor', 'neden'}; genel=True son çare (genel hukuk fotoğrafı) ölçütü"""
    import base64
    icerik = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
              {"type": "text", "text": f"Haber başlığı: {p['title']}\nKategori: {', '.join(p.get('cats', []))}\nÖne çıkanlar: {' '.join(p.get('ozet', []))}"
              + (f"\nFotoğraf künyesi (dosya adı/etiketler): {kunye[:200]}" if kunye else "")}]
    sistem = GORSEL_GENEL_SISTEM if genel else GORSEL_DENETIM_SISTEM
    metin = None
    if GEMINI_KEY:  # ücretsiz katman; olmazsa (kota/hata) Claude'a düşer
        try:
            metin = gemini(sistem, icerik[1]["text"], jpeg=jpeg)
        except Exception as e:
            log("gemini görsel denetimi olmadı, Claude kullanılıyor:", str(e)[:120])
    if metin is None:
        metin, _ = claude(MODEL_ELEME, sistem, icerik, max_tokens=1500, timeout=90)
    js = json_ayikla(metin)
    try: puan = int(js.get("puan", 0))
    except Exception: puan = 0
    return {"puan": puan, "goruluyor": str(js.get("goruluyor", ""))[:160], "neden": str(js.get("neden", ""))[:200],
            "alt": alt_temizle(js.get("alt", ""))}

def alt_temizle(a):
    a = re.sub(r"\s+", " ", str(a or "")).strip().strip('"').strip()
    a = re.sub(r"^(fotoğraf|görsel|resim)(ta|te|de|da)?\s*[:,-]?\s*", "", a, flags=re.I).strip()
    if a: a = a[0].upper() + a[1:]
    return a.rstrip(".")[:150]

GENEL_ARAMA_SISTEM = """Bir hukuk haber sitesinin foto editörüsün. Haberin konusuna özgü fotoğraf bulunamadı. Wikimedia Commons'ta
haberin konusunu GENEL ama DOĞRUDAN anlatan fotoğraf için 4 kısa İngilizce arama yaz (Türkiye bağlamı tercih edilir).
Ülke belli olmayan YAKIN PLAN aramaları tercih et (plaka, tabela, yazı görünmeyen): tehlikeli madde -> "orange hazard plate tanker",
"hazard placard closeup", "fuel tanker truck side"; vergi -> "tax documents calculator"; kira -> "apartment keys".
Diğer örnekler: tehlikeli madde taşımacılığı -> "tanker truck highway Turkey"; vergi düzenlemesi ->
"tax documents calculator", "Turkish lira banknotes"; belediye soruşturması -> "public tender documents", "Turkish lira banknotes".
Bina, adliye ya da kurum binası araması YAZMA.
Kişi adı yok. Yalnızca JSON: {"aramalar": ["...", "...", "...", "..."]}"""

# her kategoride son çare olarak denenecek genel aramalar
KATEGORI_ARAMALARI = {
    "Ekonomi": ["Turkish lira banknotes", "financial documents calculator"], "Siyaset": ["ballot box voting"],
    "Mevzuat": ["legal documents signing"], "Yargı": ["scales of justice statue"],
}
GENEL_HUKUK_ARAMALARI = ["scales of justice statue", "law books library", "signing legal documents", "Turkish lira banknotes"]
# haberin konusuna göre son çare aramaları: adalet heykelinden ÖNCE denenir (üniversite yönetmeliğine adalet heykeli düşmesin)
KONU_ARAMALARI = [
    (r"üniversite|yükseköğretim|yök\b|öğrenci|lisans|fakülte|akademik|mezun", ["university students campus", "lecture hall students", "graduation caps"]),
    (r"okul|öğretmen|milli eğitim|meb\b|eğitim-öğretim|sınav", ["classroom desks", "school corridor", "exam paper pencil"]),
    (r"hastane|sağlık|hekim|doktor|ilaç|eczane|hemşire", ["hospital corridor", "medicine pills pharmacy", "stethoscope desk"]),
    (r"vergi|gümrük|maliye|stopaj|kdv|harç|tebliğ", ["tax documents calculator", "Turkish lira banknotes"]),
    (r"banka|kredi|faiz|borsa|sermaye piyasası|emisyon|tahvil|spk|bddk", ["bank cards payment", "stock market screen"]),
    (r"enerji|elektrik|doğalgaz|yakıt|petrol|maden", ["power lines electricity", "gas station fuel pump"]),
    (r"tarım|süt|hayvancılık|çiftçi|gıda", ["farm field tractor", "dairy cows farm"]),
    (r"trafik|araç|sürücü|ehliyet|otoyol|karayolu|muayene", ["traffic highway cars", "car dashboard driving"]),
    (r"işçi|çalışan|memur|maaş|sgk|emekli|istihdam|kıdem", ["office workers desk", "factory workers safety"]),
    (r"kira|konut|tapu|imar|kentsel dönüşüm|emlak", ["apartment keys", "residential buildings city"]),
    (r"internet|sosyal medya|dijital|yapay zekâ|yapay zeka|siber|veri", ["smartphone social media", "laptop keyboard data"]),
]
_ADALET_SIMGE = re.compile(r"lady justice|justitia|themis|scales of justice|justice statue|statue of justice|adalet heykel", re.I)

def konu_aramalari(p):
    metin = (p.get("title", "") + " " + " ".join(p.get("tags", [])) + " " + " ".join(p.get("ozet", []))).replace("İ", "i").lower()
    out = []
    for rx, qs in KONU_ARAMALARI:
        if re.search(rx, metin): out += [q for q in qs if q not in out]
    return out

def _adalet_simgesi_bol():
    """son 8 yazının 2'sinde adalet heykeli/terazi varsa yeni haberde kullanılmaz (ana sayfa hep aynı görünmesin)"""
    try:
        meta = json.load(open(os.path.join(SITE_DEPO, "commons", "meta.json"), encoding="utf-8"))
        return sum(1 for x in _posts()[:8] if _ADALET_SIMGE.search((meta.get(x["slug"]) or {}).get("title") or "")) >= 2
    except Exception:
        return False

GORSEL_FIKIR_SISTEM = """Usta bir haber foto editörüsün. Bir hukuk haberi için çarpıcı, profesyonel ve DOĞRU bir kapak fotoğrafı fikri bulacaksın.
Haberin özünü anlatan 3 FARKLI görsel fikir üret; düz ve sıkıcı değil, dergi kapağı kalitesinde ama haberi yanlış göstermeyen.
Örnek, yasa dışı bahis para trafiği: "karanlık odada laptop ekranında bahis oranları", "telefonda mobil bankacılık ile para transferi",
"klavye üzerinde kredi kartı ve nakit". Örnek, kira artışı: "apartman kapısında anahtar teslimi", "kira sözleşmesi imzalanırken kalem".
Kurallar: genel bina/cephe/adliye yok. İSTİSNA: haberin doğrudan konusu belirli bir kurumsa (Halk TV, ATV, Yargıtay, Danıştay,
Anayasa Mahkemesi, bir büyükelçilik, bir belediye, BİR ÜNİVERSİTE) İLK fikir MUTLAKA o kurumun KENDİ binası/kampüsü olsun; aramada
kurum adını yaz ("Halk TV building Istanbul", "Yargitay building Ankara", "German embassy Ankara", "Piri Reis University campus").
Kurum, haberin KONUSU olan kurumdur; yayımlayan değil: Resmî Gazete'de çıkan bir üniversite yönetmeliğinde kurum o ÜNİVERSİTEDİR
(Resmî Gazete, bakanlık ya da YÖK değil). Üniversite/okul/eğitim haberinde diğer fikirler öğrenci, kampüs, amfi, mezuniyet gibi eğitim sahneleri olsun. Kelepçe, parmaklık, tokmak yok; tanınabilir yüz yok (eller, nesneler, arkadan siluet olabilir);
şiddet ve kan yok; fikir, stok fotoğraf arşivlerinde (Pixabay, Flickr) bulunabilecek gerçekçi bir sahne olmalı.
Her fikir için 2 kısa İngilizce arama yaz (2-4 kelime, etiket gibi: "online betting laptop", "mobile banking transfer").
Yalnızca JSON: {"fikirler": [{"fikir": "kısa Türkçe tarif", "aramalar": ["...", "..."]}, ...]}"""

def gorsel_fikirleri(p):
    """haber için 3 görsel fikir ve arama kelimeleri"""
    try:
        metin = kucuk_model(GORSEL_FIKIR_SISTEM,
                          f"Haber başlığı: {p['title']}\nKategori: {', '.join(p.get('cats', []))}\nÖne çıkanlar: {' '.join(p.get('ozet', []))}",
                          max_tokens=1500, timeout=60)
        fk = json_ayikla(metin).get("fikirler", [])[:3]
        log("görsel fikirleri:", " | ".join(f.get("fikir", "") for f in fk))
        return fk
    except Exception as e:
        log("görsel fikri üretilemedi:", e); return []

_RAPOR = None  # gorsel_dene çalışırken değerlendirilen adaylar buraya yazılır
_OTURUM_SECILEN = set()
_GORSEL_ISLENIYOR = set()   # görsel seçimi sürmekte olan haberler (bekçi aynı habere ikinci kez girmesin)
_YEDEK_GENEL = re.compile(r"lady justice|justitia|themis|scales of justice|law books|lawyer, office|advocacy|law, justice", re.I)
_YEDEK_KURUM = [("anayasa mahkemesi", re.compile(r"Constitutional Court of Turkey", re.I)),
                ("aym", re.compile(r"Constitutional Court of Turkey", re.I)),
                ("yargıtay", re.compile(r"Court of Cassation", re.I)),
                ("danıştay", re.compile(r"Danıştay Binası", re.I))]

def yedek_gorsel(p):
    """konuya özgü fotoğraf bulunamadığında: sitede daha önce denetimden geçmiş genel hukuk fotoğraflarından birini seçer
    (kurum haberiyse o kurumun binası). Son haberlerde kullanılanlar seçilmez; aynı haber hep aynı fotoğrafı alır."""
    try:
        meta = json.load(open(os.path.join(SITE_DEPO, "commons", "meta.json"), encoding="utf-8"))
    except Exception:
        return None
    var = lambda k: os.path.exists(os.path.join(SITE_DEPO, "commons", k + ".jpg"))
    son = {(meta.get(x["slug"]) or {}).get("title") for x in _posts()[:12]}
    metin = (p.get("title", "") + " " + " ".join(p.get("tags", [])) + " " + " ".join(p.get("cats", []))).replace("İ", "i").lower()
    havuz = []
    for ad, rx in _YEDEK_KURUM:
        if ad in metin:
            havuz = [k for k, v in meta.items() if rx.search(v.get("title", "")) and k != p.get("slug") and var(k)]
            if havuz: break
    if not havuz:
        havuz = [k for k, v in meta.items() if _YEDEK_GENEL.search(v.get("title", "")) and "gavel" not in v.get("title", "").lower()
                 and k != p.get("slug") and var(k)]
    if havuz and _adalet_simgesi_bol():
        diger = [k for k in havuz if not _ADALET_SIMGE.search(meta[k].get("title", ""))]
        if diger: havuz = diger
    tekil = {}
    for k in sorted(havuz): tekil.setdefault(meta[k]["title"], k)
    aday = sorted(k for t, k in tekil.items() if t not in son) or sorted(tekil.values())
    if not aday: return None
    return aday[int(hashlib.md5(p.get("slug", p.get("title", "")).encode()).hexdigest(), 16) % len(aday)]  # bu çalışmada seçilen fotoğraflar (aynı toplu işte iki habere aynı görsel gitmesin)

def gorsel_sec(p, gorseller):
    """1) haberin kendi aramalarından metinle kısa liste, her adayın FOTOĞRAFINA bakarak doğrulama;
    2) olmazsa konuyu genel ama doğrudan anlatan aramalarla ikinci tur; 3) olmazsa kategori/hukuk genel fotoğrafları.
    Dönüş: {'foto': ...} | {'gorsel': ...} | {} ve her durumda 'denetim'"""
    denenen, reddedilen = set(), []
    # son yayınlanan haberlerde kullanılan fotoğraflar tekrar seçilmez (ana sayfada aynı görsel yan yana görünmesin)
    try:
        _meta = json.load(open(os.path.join(SITE_DEPO, "commons", "meta.json"), encoding="utf-8"))
        son_kullanilan = {(_meta.get(x["slug"]) or {}).get("title") for x in _posts()[:20]} - {None}
    except Exception:
        son_kullanilan = set()
    denenen |= son_kullanilan | _OTURUM_SECILEN
    # maliyet sınırı: haber başına en fazla 9 konuya özgü + 3 genel fotoğraf denetimi; günlük toplam da sınırlı
    butce = {"ozgul": 9, "genel": 3}
    if sinir_doldu(sayac("gorsel_denetim"), int(os.environ.get("GUNLUK_GORSEL_DENETIM", "600"))):
        _y = yedek_gorsel(p)
        if _y:
            log("günlük görsel denetimi sınırı doldu, genel hukuk fotoğrafı kullanılacak:", _y)
            return {"gorsel": _y, "denetim": {"puan": 4, "goruluyor": "genel hukuk fotoğrafı", "neden": "Günlük görsel denetimi sınırı doldu; daha önce onaylanmış genel fotoğraf", "kaynak": "otomatik"}}
        log("günlük görsel denetimi sınırı doldu, yazılı kapak kullanılacak")
        return {"denetim": {"puan": 0, "goruluyor": "yazılı kapak", "neden": "Günlük görsel denetimi sınırı doldu", "kaynak": "otomatik"}}
    gorseller = {k: v for k, v in gorseller.items()
                 if ("File:" + v) not in son_kullanilan and v not in son_kullanilan and k not in _OTURUM_SECILEN}

    def tur(aramalar, arsiv_dahil, genel=False):
        kaynaklar = tum_adaylar(aramalar)
        adaylar = [a for a in kaynaklar if a["title"] not in denenen]
        satirlar = [f"c{i}: {a['title'].replace('File:', '')} | {a['aciklama']} | tarih: {a['tarih']} | {a.get('kaynak', 'Commons')}"
                    for i, a in enumerate(adaylar)]
        arsiv = [f"a:{k}: {v}" for k, v in gorseller.items()] if arsiv_dahil else []
        if not satirlar and not arsiv: return None
        mesaj = (f"Haber başlığı: {p['title']}\nÖzet: {' '.join(p.get('ozet', []))}\n\nCommons adayları:\n" + ("\n".join(satirlar) or "-")
                 + "\n\nArşiv:\n" + ("\n".join(arsiv) or "-"))
        if genel:
            mesaj += ("\n\nNOT: Bu son tur. Konuyu doğrudan göstermesi GEREKMEZ; temiz, yanıltıcı olmayan genel bir hukuk/yargı/devlet "
                      "kurumu fotoğrafı yeterli. Şema, logo, yabancı bayrak/tabela ve tanınabilir yüz yine seçilmez.")
        try:
            metin = kucuk_model(GORSEL_SISTEM, mesaj, max_tokens=2000, timeout=90)
            js = json_ayikla(metin)
            sirali = js.get("sirali")
            if sirali is None and js.get("secim"): sirali = [js["secim"]]
            sirali = [str(x).strip() for x in (sirali or [])][:8]
        except Exception as e:
            log("görsel seçimi hatası:", e); return None
        # stok kaynaklarının (Pixabay/Flickr/Pexels) ilk adayları, ön seçim etiketlere bakıp elese de fotoğraf denetimine girer
        if not genel:
            stok = [f"c{i}" for i, x in enumerate(adaylar) if x.get("kaynak")][:4]
            sirali = (sirali + [x for x in stok if x not in sirali])[:10]
        kaynak_say = {}
        for x in adaylar: kaynak_say[x.get("kaynak", "Commons")] = kaynak_say.get(x.get("kaynak", "Commons"), 0) + 1
        log(f"görsel turu: {len(adaylar)} aday {kaynak_say}, ön seçim: {sirali or 'yok'}"
            + ("" if sirali else f" | gerekçe: {str(js.get('neden', ''))[:150]}"))
        if genel and _adalet_bol:
            sirali = [x for x in sirali if not (x.startswith("c") and x[1:].isdigit() and int(x[1:]) < len(adaylar)
                      and _ADALET_SIMGE.search(adaylar[int(x[1:])]["title"] + " " + adaylar[int(x[1:])].get("aciklama", "")))]
        _YASAK_ETIKET = ("gavel", "handcuff", "hammer", "judge's", "auction", "prison", "jail", "mugshot", "portrait", "model, pose",
                         "selfie", "vintage", "retro", "antique", "child", "kid", "baby")
        for s_ in sirali:
            anahtar = "genel" if genel else "ozgul"
            if s_.startswith("c") and s_[1:].isdigit() and int(s_[1:]) < len(adaylar):
                _et = (adaylar[int(s_[1:])]["title"] + " " + adaylar[int(s_[1:])].get("aciklama", "")).lower()
                if any(y in _et for y in _YASAK_ETIKET):
                    denenen.add(adaylar[int(s_[1:])]["title"]); continue
            if butce[anahtar] <= 0:
                log(f"görsel denetimi bütçesi bitti ({anahtar})"); break
            if s_.startswith("c") and s_[1:].isdigit() and int(s_[1:]) < len(adaylar):
                secim = ("c", adaylar[int(s_[1:])]); ad = adaylar[int(s_[1:])]["title"]; denenen.add(ad)
            elif s_.startswith("a:") and s_[2:] in gorseller and arsiv_dahil:
                secim = ("a", s_[2:]); ad = "arşiv " + s_[2:]
            else:
                continue
            butce[anahtar] -= 1; sayac("gorsel_denetim", 1)
            try:
                dn = gorsel_dogrula(p, _gorsel_baytlari(secim), genel=genel, kunye=ad)
            except Exception as e:
                log("görsel denetimi yapılamadı:", ad, e); continue
            log(f"görsel denetimi{' (genel)' if genel else ''} {dn['puan']}/5: {ad} — {dn['goruluyor']} ({dn['neden']})")
            if _RAPOR is not None:
                kucuk = (secim[1].get("kucuk") or commons_kucuk_url(secim[1]["url"], 500)) if secim[0] == "c" else f"{SITE}/gorsel/{secim[1]}.jpg"
                _RAPOR.append({"ad": ad, "kucuk": kucuk, "puan": dn["puan"], "goruluyor": dn["goruluyor"], "neden": dn["neden"],
                               "tur": "genel" if genel else "özgül"})
            if dn["puan"] >= GORSEL_ESIK:
                _OTURUM_SECILEN.add(ad if secim[0] == "c" else secim[1])
                dn["kaynak"] = "otomatik"
                if genel: dn["neden"] = "Genel hukuk fotoğrafı (konuya özgü uygun fotoğraf bulunamadı). " + dn["neden"]
                return ({"foto": dict(secim[1], alt=dn.get("alt", ""))} if secim[0] == "c" else {"gorsel": secim[1], "alt": dn.get("alt", "")}) | {"denetim": dn}
            reddedilen.append(f"{dn['goruluyor']} ({dn['puan']}/5)")
        return None

    _adalet_bol = _adalet_simgesi_bol()
    sonuc = None
    for fk in gorsel_fikirleri(p):
        if sonuc or butce["ozgul"] <= 0: break
        aramalar = [str(a) for a in fk.get("aramalar", [])][:2]
        if aramalar:
            log("görsel fikri deneniyor:", fk.get("fikir"), aramalar)
            sonuc = tur(aramalar, False)
    if not sonuc and butce["ozgul"] > 0:
        sonuc = tur(p.get("gorsel_aramalari") or [p["title"]], True)
    if not sonuc and butce["ozgul"] > 0:
        try:
            metin = kucuk_model(GENEL_ARAMA_SISTEM, f"Haber başlığı: {p['title']}\nÖzet: {' '.join(p.get('ozet', []))}",
                              max_tokens=800, timeout=60)
            genel = [str(x) for x in json_ayikla(metin).get("aramalar", [])][:4]
        except Exception as e:
            log("genel görsel araması üretilemedi:", e); genel = []
        if genel:
            log("görsel: ikinci tur (genel aramalar):", genel)
            sonuc = tur(genel, False)
    if not sonuc:
        konu = konu_aramalari(p)
        if konu:   # konuya göre genel sahne (öğrenci, hastane, belge...) adalet heykelinden önce; kendi 3 denetim hakkıyla
            butce["ozgul"] = max(butce["ozgul"], 3)
            log("görsel: konu turu:", konu[:4])
            sonuc = tur(konu[:4], False)
    if not sonuc:
        son_care = konu_aramalari(p)[:2] + [q for c in p.get("cats", []) for q in KATEGORI_ARAMALARI.get(c, [])] + GENEL_HUKUK_ARAMALARI
        if _adalet_bol: son_care = [q for q in son_care if not _ADALET_SIMGE.search(q)]
        log("görsel: üçüncü tur (konu, kategori ve genel hukuk fotoğrafları)", "· adalet heykeli son yazılarda çok, atlanıyor" if _adalet_bol else "")
        sonuc = tur(list(dict.fromkeys(son_care))[:5], False, genel=True)
    if sonuc: return sonuc
    _y = yedek_gorsel(p)
    if _y:
        log("konuya özgü fotoğraf bulunamadı, genel hukuk fotoğrafı kullanılacak:", _y)
        return {"gorsel": _y, "denetim": {"puan": 4, "goruluyor": "genel hukuk fotoğrafı", "kaynak": "otomatik",
                "neden": "Konuya özgü uygun fotoğraf bulunamadı; daha önce onaylanmış genel hukuk fotoğraflarından seçildi"}}
    neden = "Uygun fotoğraf bulunamadı" + (f"; elenenler: {'; '.join(reddedilen[:3])}" if reddedilen else "")
    log("uygun görsel yok, yazılı kapak kullanılacak")
    return {"denetim": {"puan": 0, "goruluyor": "yazılı kapak", "neden": neden[:300], "kaynak": "otomatik"}}

def gorsel_yenile(tid):
    """bekleyen bir taslağın görselini yeni denetimle baştan seçer"""
    d = taslak_oku(tid)
    if not d or d.get("durum") != "bekliyor" or d.get("tip") not in ("haber", "analiz"): return None
    p = d["post"]
    sec = gorsel_sec(p, gorsel_listesi())
    with _taslak_kilit:
        d = taslak_oku(tid)
        if d.get("durum") != "bekliyor": return None
        d["post"]["foto"] = sec.get("foto"); d["post"]["gorsel"] = sec.get("gorsel"); d["post"]["gorsel_denetim"] = sec.get("denetim")
        taslak_yaz(d)
    return sec.get("denetim")

def yayindaki_gorseli_yenile(slug):
    """yayındaki bir haberin görselini denetimli seçimle yeniler; uygun fotoğraf yoksa yazılı kapağa döner"""
    d = next((taslak_oku(f[:-5]) for f in sorted(os.listdir(TASLAK_DIR), reverse=True)
              if f.endswith(".json") and (taslak_oku(f[:-5]) or {}).get("post", {}).get("slug") == slug), None)
    p = dict(d["post"]) if d else dict(post_bul(slug) or {})
    if not p: print("haber bulunamadı:", slug); return None
    if not p.get("gorsel_aramalari"):
        p["gorsel_aramalari"] = [p["title"]]
    sec = gorsel_sec(p, {k: v for k, v in gorsel_listesi().items() if k != slug})
    dn = sec.get("denetim") or {}
    def hazirla():
        cdir = os.path.join(SITE_DEPO, "commons"); mp = os.path.join(cdir, "meta.json")
        meta = json.load(open(mp, encoding="utf-8"))
        if sec.get("foto"):
            if not commons_indir(sec["foto"], slug): raise RuntimeError("fotoğraf indirilemedi")
        elif sec.get("gorsel"):
            _gorsel_kopyala(slug, sec["gorsel"])
        else:
            meta.pop(slug, None); json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            if os.path.exists(os.path.join(cdir, slug + ".jpg")): os.remove(os.path.join(cdir, slug + ".jpg"))
    _gonder("Görsel yenilendi: " + slug, hazirla)
    if d:
        with _taslak_kilit:
            d = taslak_oku(d["id"]); d["post"]["foto"] = sec.get("foto"); d["post"]["gorsel"] = sec.get("gorsel")
            d["post"]["gorsel_denetim"] = dn; taslak_yaz(d)
    sonuc = (sec.get("foto") or {}).get("title") or (("arşiv " + sec["gorsel"]) if sec.get("gorsel") else "yazılı kapak")
    log("YAYINDAKİ GÖRSEL YENİLENDİ:", slug, "->", sonuc, f"({dn.get('puan')}/5)")
    print(slug, "->", sonuc, "|", dn)
    return dn

def _yayindaki_puan(p, yol):
    """yayındaki görselin puanı: önce konuya özgü ölçüt, geçmezse genel hukuk fotoğrafı ölçütü"""
    jpeg = _kucuk_jpeg(open(yol, "rb").read())
    dn = gorsel_dogrula(p, jpeg)
    if dn["puan"] >= GORSEL_ESIK: return dn, "özgül"
    dg = gorsel_dogrula(p, jpeg, genel=True)
    if dg["puan"] >= GORSEL_ESIK: return dg, "genel"
    return dn, "sorun"

def yayindaki_gorselleri_denetle(son=40):
    """sitedeki son haberlerin fotoğraflarını yeniden puanlar; YALNIZCA rapor verir, hiçbir şeyi değiştirmez"""
    cdir = os.path.join(SITE_DEPO, "commons")
    try: meta = json.load(open(os.path.join(cdir, "meta.json"), encoding="utf-8"))
    except Exception: meta = {}
    sorunlu = []
    for p in _posts()[:son]:
        yol = os.path.join(cdir, p["slug"] + ".jpg")
        if p["slug"] not in meta or not os.path.exists(yol): continue
        try:
            dn, tur_ = _yayindaki_puan(p, yol)
        except Exception as e:
            print("denetlenemedi:", p["slug"], e); continue
        isaret = {"özgül": "TAMAM ", "genel": "GENEL ", "sorun": "SORUN "}[tur_]
        print(f"{isaret}{dn['puan']}/5  {p['slug']}\n        {dn['goruluyor'][:110]}", flush=True)
        if tur_ == "sorun": sorunlu.append(p["slug"])
    print(f"\n{len(sorunlu)} sorunlu görsel. Hepsini tek seferde düzeltmek için: yazar.yayindaki_gorselleri_duzelt()")
    return sorunlu

def yayindaki_gorselleri_duzelt(son=40):
    """sorunlu görselleri bulur, her biri için denetimli yeni görsel seçer ve siteye TEK güncelleme olarak gönderir"""
    cdir = os.path.join(SITE_DEPO, "commons")
    meta = json.load(open(os.path.join(cdir, "meta.json"), encoding="utf-8"))
    taslaklar = {}
    for f in os.listdir(TASLAK_DIR):
        if f.endswith(".json"):
            d = taslak_oku(f[:-5])
            if d: taslaklar[d["post"].get("slug")] = d
    secimler = {}
    for p in _posts()[:son]:
        yol = os.path.join(cdir, p["slug"] + ".jpg")
        if p["slug"] not in meta or not os.path.exists(yol): continue
        try:
            dn, tur_ = _yayindaki_puan(p, yol)
        except Exception as e:
            print("denetlenemedi:", p["slug"], e, flush=True); continue
        if tur_ != "sorun": continue
        print(f"\n>> {p['slug']} ({dn['puan']}/5: {dn['goruluyor'][:70]})", flush=True)
        pp = dict(p)
        d = taslaklar.get(p["slug"])
        pp["gorsel_aramalari"] = (d or {}).get("post", {}).get("gorsel_aramalari") or [p["title"]]
        sec = gorsel_sec(pp, {k: v for k, v in gorsel_listesi().items() if k != p["slug"]})
        yeni_puan = (sec.get("denetim") or {}).get("puan") or 0
        if not (sec.get("foto") or sec.get("gorsel")) or yeni_puan <= dn["puan"]:
            print("   -> daha iyisi bulunamadı, mevcut görsel korunuyor", flush=True); continue
        secimler[p["slug"]] = sec
        # haber haber: bulunan görsel hemen siteye gider
        def hazirla_tek(slug=p["slug"], sec=sec):
            if sec.get("foto"): commons_indir(sec["foto"], slug)
            else: _gorsel_kopyala(slug, sec["gorsel"])
        try:
            _gonder(f"Görsel yenilendi: {p['slug']}", hazirla_tek)
        except Exception as e:
            print("   gönderilemedi:", e, flush=True)
        print("   ->", (sec.get("foto") or {}).get("title") or sec.get("gorsel") or "yazılı kapak", f"({(sec.get('denetim') or {}).get('puan')}/5)", flush=True)
    log(f"YAYINDAKİ {len(secimler)} GÖRSEL YENİLENDİ")
    print(f"\n{len(secimler)} haberin görseli yenilendi ve siteye gönderildi.")

def _gorsel_dene_bolum(slug):
    """bir haber için görsel seçimini SİTEYE YAZMADAN çalıştırır; rapor bölümü HTML'ini döndürür"""
    global _RAPOR
    d = next((taslak_oku(f[:-5]) for f in sorted(os.listdir(TASLAK_DIR), reverse=True)
              if f.endswith(".json") and (taslak_oku(f[:-5]) or {}).get("post", {}).get("slug") == slug), None)
    p = dict(d["post"]) if d else dict(post_bul(slug) or {})
    if not p: return f"<p>haber bulunamadı: {html.escape(slug)}</p>"
    p["gorsel_aramalari"] = p.get("gorsel_aramalari") or [p["title"]]
    print("deneniyor:", p["title"], flush=True)
    _RAPOR = []
    try:
        sec = gorsel_sec(p, {k: v for k, v in gorsel_listesi().items() if k != slug})
    finally:
        aday, _RAPOR = _RAPOR, None
    e = html.escape
    secilen = (sec.get("foto") or {}).get("title") or (("arşiv " + sec["gorsel"]) if sec.get("gorsel") else None)
    print("   ->", secilen or "uygun görsel yok (mevcut korunur)", flush=True)
    kartlar = "".join(
        f'<div class="k{" s" if a["ad"] == secilen else ""}"><img src="{e(a["kucuk"])}" loading="lazy"><div><b>{a["puan"]}/5'
        f'{" · SEÇİLDİ" if a["ad"] == secilen else ""}</b> <small>{e(a["tur"])} · {e(a["ad"][:70])}</small>'
        f'<p>{e(a["goruluyor"])}</p><p class="n">{e(a["neden"])}</p></div></div>'
        for a in sorted(aday, key=lambda a: (a["ad"] != secilen, -a["puan"]))[:6])
    return (f'<section><h2>{e(p["title"])}</h2><p class="n">Aramalar: {e(", ".join(p["gorsel_aramalari"]))} · '
            f'<a href="{SITE}/{e(slug)}/">sitedeki hali</a></p>'
            f'<p><b>{"Seçilen: " + e(secilen) if secilen else "Uygun görsel bulunamadı; mevcut görsel korunur."}</b></p>{kartlar}</section>')

def gorsel_dene(*sluglar, son=0):
    """SİTEYE YAZMADAN görsel seçimini dener ve tüm adayları puanlarıyla gösteren rapor sayfası üretir.
    gorsel_dene('slug') ya da gorsel_dene(son=5) (sitedeki son 5 haber)"""
    sl = list(sluglar) or [x["slug"] for x in _posts()[:son or 5]]
    govde = "".join(_gorsel_dene_bolum(s_) for s_ in sl)
    sayfa = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Görsel denemesi</title>'
             '<style>body{background:#1d2a37;color:#e9eef3;font:15px/1.45 system-ui;margin:0 auto;padding:16px;max-width:920px}'
             'section{border-bottom:2px solid #34475a;padding-bottom:18px;margin-bottom:18px}a{color:#f1d293}'
             '.k{display:flex;gap:14px;background:#26374a;border-radius:10px;padding:10px;margin:10px 0;border-left:5px solid #6b7785}'
             '.k.s{border-color:#1f9d55}.k img{width:260px;height:137px;object-fit:cover;border-radius:6px;flex:none}'
             'b{font-size:16px}.k.s b{color:#5fd38d}small{color:#9fb0c0}p{margin:6px 0}.n{color:#9fb0c0;font-size:13.5px}'
             '@media(max-width:600px){.k{flex-direction:column}.k img{width:100%;height:auto}}</style>'
             '<h1>Görsel denemesi (siteye yazılmadı)</h1>' + govde)
    print("\nRAPOR (tarayıcıda açın):", onizleme_kaydet(sayfa))

def gorsel_yenile_hepsi():
    """tüm bekleyen haber taslaklarının görsellerini yeniden seçer (bir kerelik toplu düzeltme)"""
    for f in sorted(os.listdir(TASLAK_DIR)):
        if f.endswith(".json"):
            d = taslak_oku(f[:-5])
            if d and d.get("durum") == "bekliyor" and d.get("tip") in ("haber", "analiz"):
                dn = gorsel_yenile(d["id"])
                print(d["post"]["title"], "->", dn)

def commons_indir(bilgi, slug):
    try:
        from PIL import Image
        veri = urllib.request.urlopen(urllib.request.Request(bilgi["url"], headers=_UA), timeout=40).read()
        _duz_rgb(Image.open(io.BytesIO(veri))).save(os.path.join(SITE_DEPO, "commons", slug + ".jpg"), "JPEG", quality=90)
        mp = os.path.join(SITE_DEPO, "commons", "meta.json")
        meta = json.load(open(mp, encoding="utf-8"))
        meta[slug] = {k: bilgi[k] for k in ("title", "page", "lic", "artist")}
        if bilgi.get("kaynak"): meta[slug]["kaynak"] = bilgi["kaynak"]
        if bilgi.get("alt"): meta[slug]["alt"] = bilgi["alt"]
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return True
    except Exception as e:
        log("görsel indirilemedi:", e); return False

ALT_SISTEM = """Bir haber sitesinin foto editörüsün. Fotoğrafı görme engelli okur ve Google Görseller için anlatan Türkçe alt metni yaz:
6-14 kelimelik tek cümle; yalnızca fotoğrafta GÖRÜNENİ anlatır; kişi adı, marka, yorum ve haber bilgisi içermez; "fotoğraf"/"görsel"
sözüyle başlamaz. Örnek: "Gün batımında kep fırlatan mezun öğrencilerin silüeti". Yalnızca JSON: {"alt": "..."}"""

def alt_uret(yol):
    jpeg = _kucuk_jpeg(open(yol, "rb").read(), en=640)
    metin = None
    if GEMINI_KEY:
        try: metin = gemini(ALT_SISTEM, "Bu fotoğrafın alt metnini yaz.", jpeg=jpeg)
        except Exception as e: log("gemini alt metni olmadı, Claude kullanılıyor:", str(e)[:120])
    if metin is None:
        import base64
        metin, _ = claude(MODEL_ELEME, ALT_SISTEM, [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                                                    {"type": "text", "text": "Bu fotoğrafın alt metnini yaz."}], max_tokens=1500, timeout=90)
    return alt_temizle(json_ayikla(metin).get("alt", ""))

def alt_metinleri_tamamla(azami=400):
    """alt metni olmayan fotoğraflara (eski fotoğraflar, editörün elle seçtikleri) açıklayıcı alt metni üretir ve siteye gönderir"""
    cdir = os.path.join(SITE_DEPO, "commons"); mp = os.path.join(cdir, "meta.json")
    try: meta = json.load(open(mp, encoding="utf-8"))
    except Exception: return 0
    eksik = [k for k, v in meta.items() if not v.get("alt") and os.path.exists(os.path.join(cdir, k + ".jpg"))][:azami]
    if not eksik: return 0
    log("alt metni üretilecek fotoğraf:", len(eksik))
    yeni = {}
    for k in eksik:
        try:
            a = alt_uret(os.path.join(cdir, k + ".jpg"))
            if len(a.split()) >= 3: yeni[k] = a
        except Exception as e:
            log("alt metni üretilemedi:", k, str(e)[:120])
    if not yeni: return 0
    def hazirla():
        m = json.load(open(mp, encoding="utf-8"))
        for k, a in yeni.items():
            if k in m and not m[k].get("alt"): m[k]["alt"] = a
        json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _gonder(f"Fotoğraflara açıklayıcı alt metni eklendi ({len(yeni)})", hazirla)
    log("alt metni eklendi:", len(yeni))
    return len(yeni)

def alt_metni_dongu():
    time.sleep(120)
    while True:
        try: alt_metinleri_tamamla()
        except Exception as e: log("alt metni döngüsü hatası:", repr(e)[:200])
        time.sleep(3 * 3600)

def _gorsel_kopyala(slug, kaynak):
    if not kaynak: return
    cdir = os.path.join(SITE_DEPO, "commons")
    shutil.copyfile(os.path.join(cdir, kaynak + ".jpg"), os.path.join(cdir, slug + ".jpg"))
    mp = os.path.join(cdir, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    meta[slug] = dict(meta[kaynak])
    json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ denetim
YASAK = ["sonuç olarak", "özetle", "önemle belirtmek", "dikkat çekici", "unutmamak gerekir", "bu bağlamda",
         "merakla bekleniyor", "chatgpt", "claude", "anthropic",
         # haberin konusu yapay zekâ olabilir (ör. bahis şebekesinin yapay zekâ kullanması); yalnızca yazarın kendini ele veren kalıplar yasak
         "yapay zeka olarak", "yapay zekâ olarak", "bir yapay zeka", "bir yapay zekâ", "yapay zeka tarafından", "yapay zekâ tarafından",
         "dil modeli olarak", "bilgi kesim tarihi"]
_YASAK_RE = [(y, re.compile(r"(?<![\wçğıöşü])" + re.escape(y) + r"(?![\wçğıöşü])")) for y in YASAK]

def yasak_bul(metin):
    """yasak ifadeleri TAM KELİME olarak arar ("özetle" yasak, "özetleyen/özetlemek" serbest)"""
    m = str(metin or "").lower()
    return [y for y, rx in _YASAK_RE if rx.search(m)]

_DOLGU_BASI = re.compile(r"(^|(?<=[.!?>]\s)|(?<=>))\s*(Özetle|Sonuç olarak|Bu bağlamda|Kısacası)\s*,\s*(\w)", re.I)

def dolgu_temizle(metin):
    """cümle başındaki yazar dolgularını ("Özetle,", "Sonuç olarak,", "Bu bağlamda,") anlamı değiştirmeden siler"""
    return _DOLGU_BASI.sub(lambda m: m.group(1) + m.group(3).replace("i", "İ").upper(), str(metin or ""))

# Bilinen usul hataları (yürürlükteki CMK'ya göre). 7331 s.K. (1.1.2022): sulh ceza hâkimliğinin tutuklama/adli kontrol kararına itirazı
# yargı çevresindeki asliye ceza mahkemesi hâkimi inceler (268/3-b). Diğer sulh ceza kararlarında (el koyma, kayyım, arama, erişim engeli)
# itirazı hâlâ numara olarak izleyen sulh ceza hâkimliği inceler (268/3-a); kontrol bu yüzden tutuklama/adli kontrol bağlamına bakar.
# 7499 s.K. (1.6.2024): CMK 268/1 itiraz süresi yedi günden iki haftaya çıktı.
_CEZA_BAGLAM = re.compile(r"tutuklama|tutuklan|adli kontrol|sulh ceza|hâkimli|hakimli|cmk|ceza muhakemesi|el koyma|şüpheli|sanık", re.I)
def usul_hatalari(metin):
    """metindeki bilinen ceza usulü hatalarını döndürür (boş liste = sorun yok)"""
    metin = re.sub(r'<p class="duzeltme-notu">.*?</p>', " ", str(metin or ""), flags=re.S)   # okura gösterilen düzeltme notu eski hatayı alıntılar
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", metin)))
    out = []
    cumleler = re.split(r"(?<=[.!?])\s+", t)
    for i, c in enumerate(cumleler):
        cl = c.lower()
        cevre = " ".join(cumleler[max(0, i - 1): i + 1]).lower()
        if (re.search(r"(bir sonraki|sonraki|bir üst|üst|izleyen|sıradaki|numara olarak)\s+(numaralı\s+)?sulh ceza|üst mercii olan sulh ceza", cl)
                and re.search(r"tutuklama|tutuklan|adli kontrol|ev hapsi", cevre)):
            out.append("itiraz mercii eski usul (CMK 268/3-b: asliye ceza hâkimi): " + c[:90])
        elif re.search(r"(yedi|7)\s*gün", cl) and "itiraz" in cl and _CEZA_BAGLAM.search(cl):
            out.append("CMK itiraz süresi iki haftadır (7499 s.K.): " + c[:90])
        elif "itiraz" in cl and "tutuklama" in cl and re.search(r"sulh ceza hâkimliğine itiraz|sulh ceza hakimliğine itiraz", cl) and "gözaltı" not in cl:
            out.append("tutuklamaya itiraz mercii asliye ceza hâkimidir (dilekçe kararı veren hâkimliğe verilir): " + c[:90])
    return out

# ------------------------------------------------------------------ isim kuralı (kırmızı çizgi; kodla uygulanır)
ISIM_NITELIK = {"gazeteci", "siyasetci", "kamu_gorevlisi", "taninmis_kisi"}
RESMI_ALAN = re.compile(r"(\.gov\.tr|tbmm\.gov\.tr|resmigazete\.gov\.tr|yargitay\.gov\.tr|danistay\.gov\.tr|anayasa\.gov\.tr|hsk\.gov\.tr)$")
ISIM_TESPIT_SISTEM = """Bir haber metni veriliyor. Metinde adı geçen TÜM GERÇEK KİŞİLERİ (ad ve/veya soyadıyla anılan her insan) eksiksiz listele.
Kurum, şirket, parti, gazete, mahkeme adları kişi DEĞİLDİR. Atatürk gibi tarihî kişiler ve kanun adlarındaki isimler de listeye girer.
Yalnızca JSON: {"isimler": ["Ad Soyad", ...]}"""
def _katla(t):
    return re.sub(r"\s+", " ", str(t or "").translate(str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosucgiosuaiu")).lower()).strip()
def _alan(u):
    a = re.sub(r"^www\.", "", urllib.parse.urlparse(str(u)).netloc.lower())
    return ".".join(a.split(".")[-3:]) if a.endswith(".com.tr") or a.endswith(".gov.tr") or a.endswith(".org.tr") else ".".join(a.split(".")[-2:])
def isim_tespit(metin):
    """metindeki kişi adlarını bağımsız bir model çağrısıyla bulur; hata olursa None (çağıran güvenli tarafta kalır)"""
    duz = html.unescape(re.sub(r"<[^>]+>", " ", str(metin)))[:9000]
    try:
        js = json_ayikla(kucuk_model(ISIM_TESPIT_SISTEM, duz, 600, timeout=60))
        return [str(x).strip() for x in (js.get("isimler") or []) if str(x).strip()]
    except Exception as e:
        log("isim tespiti yapılamadı:", str(e)[:120]); return None
def isim_beyani_denetle(isimler, kaynak_metin, kaynaklar):
    """bota beyan edilen isimleri kurala göre süzer: (onaylı isimler, hatalar)"""
    onay, hata = [], []
    ks = {str(k[1]) for k in (kaynaklar or []) if isinstance(k, (list, tuple)) and len(k) == 2}
    for x in isimler or []:
        if not isinstance(x, dict): continue
        ad = re.sub(r"\s+", " ", str(x.get("ad") or "")).strip()
        if len(ad.split()) < 2: hata.append(f"isim tam değil: {ad}"); continue
        if x.get("nitelik") not in ISIM_NITELIK: hata.append(f"isim niteliği uygun değil: {ad}"); continue
        # paylaşımlar tanınmış kişileri çoğu zaman yalnız soyadıyla anar ("İmamoğlu", "Sarıgül"): tam ad ya da soyadı geçmesi yeterli;
        # tam adın doğruluğu aşağıdaki iki bağımsız/resmî kaynak şartıyla ayrıca aranır
        _km = _katla(kaynak_metin)
        if _katla(ad) not in _km and not re.search(r"(?<!\w)" + re.escape(_katla(ad.split()[-1])) + r"(?!\w)", _km):
            hata.append(f"isim kaynak paylaşımında geçmiyor: {ad}"); continue
        urls = [str(u) for u in (x.get("kaynaklar") or []) if str(u).startswith("http")]
        alanlar = {_alan(u) for u in urls if _alan(u) not in ("x.com", "twitter.com", "t.co")}
        if not (len(alanlar) >= 2 or any(RESMI_ALAN.search(a) for a in alanlar)):
            hata.append(f"isim iki bağımsız kaynakla doğrulanmadı: {ad}"); continue
        if not all(u in ks for u in urls if _alan(u) in alanlar): hata.append(f"isim kaynakları yazının kaynaklarında yok: {ad}"); continue
        onay.append({"ad": ad, "nitelik": x["nitelik"], "kaynaklar": urls})
    return onay, hata
def isim_metin_denetle(metin, izinli):
    """metinde geçen her kişi adının izinli listede olduğunu doğrular; tespit yapılamazsa güvenli tarafta kalıp reddeder"""
    bulunan = isim_tespit(metin)
    if bulunan is None: return ["isim denetimi yapılamadı"]
    iz = [_katla(a) for a in izinli]
    out = []
    for b in bulunan:
        kb = _katla(b)
        if kb in ("ataturk", "mustafa kemal ataturk"): continue
        if not any(kb == a or kb in a.split() or kb in a or a in kb for a in iz): out.append(f"onaysız isim: {b}")
    return out

ITHAM = ["suçlu olduğu", "suçunu işleyen", "hırsız", "dolandırıcı", "terörist", "katil", "rüşvetçi", "hain"]
# Kişiyi suçlayan kullanımları yakalar; suç adları ve çekimleri (dolandırıcılık/dolandırıcılığı, hırsızlık/hırsızlığa)
# ile masumiyet karinesi anlatımı serbesttir.
ITHAM_DESEN = [
    r"suçlu olduğu(?!\s+(hükmen|kesin|mahkeme|sabit|yargı))",
    r"(?<![a-zçğıöşü])hırsız(?!lı[kğ])", r"(?<![a-zçğıöşü])dolandırıcı(?!lı[kğ])", r"(?<![a-zçğıöşü])terörist(?!\s+örgüt)",
    r"(?<![a-zçğıöşü])katil(?![a-zçğıöşü])", r"(?<![a-zçğıöşü])katiller", r"(?<![a-zçğıöşü])rüşvetçi",
    r"(?<![a-zçğıöşü])hain(?![a-zçğıöşü])", r"(?<![a-zçğıöşü])hainler",
]

def itham_bul(metin):
    """metinde suçlayıcı kullanım içeren cümleleri döndürür (genel hukuki anlatım hariç)"""
    duz = html.unescape(re.sub(r"<[^>]+>", " ", metin))
    out = []
    for c in re.split(r"(?<=[.!?])\s+", duz):
        cl = c.lower()
        # masumiyet karinesini hatırlatan olumsuz cümleler suçlama değildir ("kimsenin suçlu olduğu anlamına gelmez")
        if re.search(r"anlamına gelmez|anlamına gelmiyor|sayılmaz|sayılamaz|kabul edilemez|masumiyet karinesi|kesinleşmiş bir hüküm yok|suçlu olduğu kesinleşmedi", cl): continue
        if any(re.search(d, cl) for d in ITHAM_DESEN): out.append(c.strip())
    return out

ISIM_CIKAR_SISTEM = """Bir hukuk haber sitesinin editörüsün. Aşağıdaki cümlelerde, yayın kuralı gereği yazılamayacak kişi adları geçiyor.
Her cümleyi anlamını ve bilgisini koruyarak, verilen adları (ad ya da soyad hâlinde, "X soruşturması" gibi kalıplar dahil) kullanmadan
yeniden yaz: kişiyi unvanı ya da rolüyle an ("bir milletvekili", "eski belediye başkanı", "korumalar"), soruşturmayı konusuyla an.
Yeni bilgi ekleme. Yalnızca JSON: {"cumleler": [["eski cümle", "yeni cümle"], ...]}"""

def isim_cikar(p, adlar):
    """beyan edilmemiş isimlerin geçtiği cümleleri isimsiz yeniden yazar; başarıyla değiştirdiyse True"""
    kok = [_katla(a_.split()[-1]) for a_ in adlar if a_.strip()]
    if not kok: return False
    alanlar = [("title", p["title"]), ("body", p["body"])] + [(f"ozet{i}", o) for i, o in enumerate(p.get("ozet", []))]
    cumleler = []
    for _, metin in alanlar:
        duz = html.unescape(re.sub(r"<[^>]+>", " ", metin))
        for c in re.split(r"(?<=[.!?])\s+", duz):
            if any(k_ in _katla(c) for k_ in kok): cumleler.append(c.strip())
    for q in p.get("sss") or []:
        for c in q:
            if any(k_ in _katla(str(c)) for k_ in kok): cumleler.append(str(c).strip())
    if not cumleler: return False
    try:
        metin, _ = claude(MODEL_ELEME, ISIM_CIKAR_SISTEM, "Yazılamayacak adlar: " + ", ".join(adlar) + "\n" + "\n".join(f"- {c}" for c in cumleler[:20]),
                          max_tokens=3000, timeout=90)
        degisti = False
        for eski, yeni in json_ayikla(metin).get("cumleler", []):
            eski, yeni = str(eski).strip(), str(yeni).strip()
            if not eski or not yeni or any(k_ in _katla(yeni) for k_ in kok): continue
            for alan in ("title", "body"):
                if eski in p[alan]: p[alan] = p[alan].replace(eski, yeni); degisti = True
            p["ozet"] = [o.replace(eski, yeni) for o in p.get("ozet", [])]
            if p.get("sss"): p["sss"] = [[str(x).replace(eski, yeni) for x in q] for q in p["sss"]]
        if degisti: log("isim çıkarıldı, cümleler yeniden yazıldı:", ", ".join(adlar))
        return degisti
    except Exception as e:
        log("isim çıkarılamadı:", repr(e)[:150]); return False

ITHAM_SISTEM = """Tarafsız bir hukuk haber sitesinin editörüsün. Aşağıdaki cümleler, belirli bir kişiyi ya da grubu suçlu gibi gösterebilecek
ifadeler içeriyor. Her cümleyi anlamını ve bilgisini koruyarak masumiyet karinesine uygun, tarafsız biçimde yeniden yaz
("dolandırıcılar" yerine "dolandırıcılık iddiasıyla soruşturulan kişiler", "katil" yerine "şüpheli/sanık" gibi). Genel hukuki anlatımsa
(kanunun bir suçu tanımlaması gibi) yalnızca suçlayıcı kelimeyi suç adıyla değiştir. Yeni bilgi ekleme.
Yalnızca JSON: {"cumleler": [["eski cümle", "yeni cümle"], ...]}"""

def itham_duzelt(p):
    """başlık ve gövdedeki suçlayıcı cümleleri tarafsızlaştırır; düzeltilemeyen kalırsa liste döner"""
    sorunlu = itham_bul(p["title"] + ". " + p["body"])
    if not sorunlu: return []
    try:
        metin, _ = claude(MODEL_ELEME, ITHAM_SISTEM, "\n".join(f"- {c}" for c in sorunlu[:8]), max_tokens=3000, timeout=90)
        for eski, yeni in json_ayikla(metin).get("cumleler", []):
            eski, yeni = str(eski).strip(), str(yeni).strip()
            if not eski or not yeni: continue
            for alan in ("title", "body"):
                if eski in p[alan]: p[alan] = p[alan].replace(eski, yeni)
                elif eski in html.unescape(p[alan]): p[alan] = html.unescape(p[alan]).replace(eski, yeni)
            p["ozet"] = [x.replace(eski, yeni) for x in p.get("ozet", [])]
    except Exception as e:
        log("itham düzeltmesi yapılamadı:", e)
    kalan = itham_bul(p["title"] + ". " + p["body"])
    if not kalan: log(f"itham düzeltildi ({len(sorunlu)} cümle):", p["title"])
    return kalan

def slugla(s):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")
    s = unicodedata.normalize("NFKD", s.translate(tr)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return "-".join(s.split("-")[:8])

def denetle(p, tw, gorseller, mevcut_sluglar):
    hatalar = []
    for k in ("slug", "title", "cats", "tags", "ozet", "body", "kaynaklar"):
        if not p.get(k): hatalar.append("eksik: " + k)
    if hatalar: return hatalar
    # kaynak etiketi kalıntısı kalmasın (yapay zekâ izi)
    for _k in ("title", "body"):
        p[_k] = re.sub(r"[<(]cite\b[^>]*>", "", str(p.get(_k, ""))).replace("</cite>", "")
    p["ozet"] = [re.sub(r"[<(]cite\b[^>]*>", "", str(x)).replace("</cite>", "") for x in p.get("ozet", [])]
    if p.get("sss"): p["sss"] = [[re.sub(r"[<(]cite\b[^>]*>", "", a_).replace("</cite>", "") for a_ in q] for q in sss_duzelt(p["sss"])]
    p["title"] = p["title"].replace("—", ",").replace("–", "-").strip()
    p["body"] = p["body"].replace("—", ",")
    # büro hizmet sayfalarına bağlantı kalmaz (rehberin konuya uygunluğunu site derlemesi ayrıca denetler); bağlantı metni düz yazı olarak kalır
    p["body"] = re.sub(r'<a\s[^>]*href="https?://(?:www\.)?(?:yagmurtahtasiz\.com|umuttekin\.av\.tr)(?!/blog/|/araclar/)[^"]*"[^>]*>(.*?)</a>', r"\1", p["body"], flags=re.S)
    if len(p["title"]) > 75: hatalar.append(f"başlık {len(p['title'])} karakter")
    p["slug"] = slugla(p["slug"])
    if p["slug"] in mevcut_sluglar: p["slug"] = p["slug"] + "-" + simdi().strftime("%H%M")
    p["cats"] = [c for c in p["cats"] if c in KATEGORILER][:2] or ["Yargı"]
    p["tags"] = [str(t) for t in p["tags"]][:8]
    if not isinstance(p["ozet"], list) or len(p["ozet"]) < 2: hatalar.append("özet")
    if '<p class="lead">' not in p["body"] or p["body"].count("<h2>") < 2: hatalar.append("gövde yapısı")
    kelime = len(re.sub(r"<[^>]+>", " ", p["body"]).split())
    p["tur"] = "Analiz" if p.get("tur") == "Analiz" else "Haber"
    p["kapsamli"] = True  # her taslak haber + hukuki değerlendirme tek yazıda
    kapsamli = True
    alt, ust = (430, 1400) if kapsamli else (180, 800)
    if not alt <= kelime <= ust: hatalar.append(f"kelime {kelime}")
    if kapsamli and p.get("sss"):
        p["sss"] = [[str(q), str(c)] for q, c in p["sss"] if len(str(q)) <= 45][:4]
    k = p["kaynaklar"]
    if not isinstance(k, list) or not all(isinstance(x, list) and len(x) == 2 and str(x[1]).startswith("http") for x in k):
        hatalar.append("kaynak biçimi")
    else:
        if not any(tw["id"] in str(x[1]) for x in k):
            etiket = (f"X paylaşımı: {tw['ad']} (@{tw['kullanici']}), {tw['tarih']} {tw['saat']}" if "x.com/" in tw["url"]
                      else f"{tw['ad']}, {tw['tarih']}: {(re.sub(r'^\s*\[EDİTÖR NOTU:.*?\]\s*', '', tw['metin'], flags=re.S).splitlines() or [''])[0][:150]}")
            k.insert(0, [etiket, tw["url"]])
        # aynı adres iki kez listelenmesin
        gor = set(); p["kaynaklar"] = k = [x for x in k if not (x[1] in gor or gor.add(x[1]))]
        if len([x for x in k if "x.com/" not in str(x[1]) and "twitter.com/" not in str(x[1])]) < 1:
            hatalar.append("paylaşım dışında resmî/mevzuat kaynağı yok")
    p["body"] = dolgu_temizle(p["body"]); p["ozet"] = [dolgu_temizle(o) for o in p.get("ozet", [])]
    for y in yasak_bul(p["title"] + " " + p["body"]): hatalar.append("yasak ifade: " + y)
    for c in itham_duzelt(p):
        hatalar.append("suçlayıcı ifade: " + c[:80])
    # isim kuralı: beyan edilen isimler şartları sağlamalı; metindeki her isim beyan edilmiş olmalı
    _onay, _ih = isim_beyani_denetle(p.pop("isimler", None), tw.get("metin"), p.get("kaynaklar"))
    hatalar += _ih
    if not _ih:
        _tum = " ".join([p["title"], p["body"]] + [str(x) for x in p.get("ozet", [])] + [" ".join(map(str, q)) for q in (p.get("sss") or [])])
        _ih2 = isim_metin_denetle(_tum, [x["ad"] for x in _onay])
        _adlar = [h_.split(": ", 1)[1] for h_ in _ih2 if h_.startswith("onaysız isim: ")]
        if _adlar and len(_adlar) == len(_ih2) and isim_cikar(p, _adlar):   # beyan edilmemiş isim: cümleler isimsiz yeniden yazılır, sonra yeniden denetlenir
            _tum = " ".join([p["title"], p["body"]] + [str(x) for x in p.get("ozet", [])] + [" ".join(map(str, q)) for q in (p.get("sss") or [])])
            _ih2 = isim_metin_denetle(_tum, [x["ad"] for x in _onay])
        hatalar += _ih2
    if _onay: p["isimler"] = _onay
    _usul_metin = " ".join([p["body"]] + [str(x) for x in p.get("ozet", [])] + [" ".join(map(str, q)) for q in (p.get("sss") or [])])
    hatalar += usul_hatalari(_usul_metin)
    # tweetten uzun alıntı (telif): 25 kelimeden uzun ortak dizi olmamalı
    tk = re.sub(r"\s+", " ", tw["metin"].lower()).split()
    gv = " " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p["body"]).lower()) + " "
    for i in range(0, max(0, len(tk) - 25)):
        if " " + " ".join(tk[i:i + 25]) + " " in gv:
            hatalar.append("tweetten uzun alıntı"); break
    if p.get("gorsel") not in gorseller: p["gorsel"] = None
    for x in ("yazar", "anket", "ornek") + (() if kapsamli else ("sss",)):
        p.pop(x, None)
    return hatalar

# ------------------------------------------------------------------ güncelleme
GUNCELLEME_SISTEM = """Tarafsız bir hukuk haber sitesinin editörüsün. Sitede yayımlanmış bir haberin konusunda yeni bir gelişme bildiren paylaşım
geliyor. web_search ile (en fazla 3 arama) gelişmeyi teyit et ve habere eklenecek KISA bir güncelleme notu yaz.
Kurallar: 1-3 cümle, tarafsız, kimseyi suçlamadan; yalnızca doğrulanmış bilgi; yazıda zaten geçmeyen hiçbir kişi adı yazılmaz; uzun tire yok.
Usul bilgisi verirsen: CMK 268 itiraz süresi iki haftadır; tutuklama/adli kontrol kararına itirazı asliye ceza hâkimi inceler (bunlar için "bir
sonraki sulh ceza hâkimliği" eski usuldür); el koyma, kayyım gibi diğer sulh ceza kararlarında numara olarak izleyen sulh ceza hâkimliği inceler. Kanun teklifini yürürlükteki kanun gibi anlatma. Ajans metnini tekrarlayan siteler bağımsız teyit değildir.
YENİ GELİŞME sayılır (kaçırma): dosyanın bir sonraki hukuki adımı ya da yazıda OLMAYAN somut bilgi: iddianame hazırlanması/kabulü, ceza ya da
tutuklama talebi, mütalaa, gözaltı/tutuklama/adli kontrol/tahliye kararı, sayının değişmesi (gözaltı sayısı arttı), duruşma tarihi, ara karar,
hüküm, itiraz/istinaf/temyiz sonucu, kurumun yeni açıklaması, yürürlük tarihi. Yazıda aynı bilgi zaten varsa yeni DEĞİLDİR.
Gelişme yeni ama resmî kaynakla ya da paylaşan hesap dışında iki bağımsız kaynakla teyit edilemiyorsa güncelleme yapma ve "sebep": "teyit_yok"
yaz (sonra yeniden denenir); gerçekten yeni değilse "sebep": "yeni_degil".
TUTARLILIK (zorunlu): Yeni gelişme yazıdaki bir cümleyi eskitiyorsa (ör. yazı "karar henüz açıklanmadı" ya da "tutuklama talebiyle sevk
edildi" diyor ama şüpheli tutuklandı; sayı değişti; "bekleniyor" denen adım gerçekleşti), o cümleleri "duzeltmeler" listesinde ver:
{"alan": "title|ozet|sss|body", "eski": "yazıdaki cümle HARFİ HARFİNE (verilen metinden kopyala)", "yeni": "güncel ve doğrulanmış cümle"}.
Yalnızca gerçekten eskiyen ya da artık yanlış olan cümleler, en fazla 5. Başlık yalnızca artık yanlışsa değişir (en fazla 75 karakter).
Eskiyen cümle yoksa boş liste.
Yalnızca JSON: {"yayinla": true|false, "sebep": "yazildi|yeni_degil|teyit_yok", "neden": "kısa", "not": "güncelleme metni (HTML etiketi yok)",
"kaynak": ["kaynak başlığı", "url"], "duzeltmeler": []}"""

YENILIK_SISTEM = """Bir hukuk haber sitesinin editörüsün. Sitede yayımlanmış bir yazı ve aynı konuda yeni gelen bir paylaşım var.
Paylaşım, yazıda OLMAYAN yeni ve somut bir hukuki gelişme bildiriyor mu? Yeni gelişme: dosyanın bir sonraki adımı (iddianame hazırlanması/
kabulü, ceza ya da tutuklama talebi, mütalaa, gözaltı/tutuklama/tahliye kararı, sayının değişmesi, duruşma tarihi, ara karar, hüküm, itiraz
sonucu, yeni resmî açıklama) ya da yazıda bulunmayan somut bir bilgi. Aynı bilginin başka sözcüklerle tekrarı, yorum, polemik yeni DEĞİLDİR.
Yalnızca JSON: {"yeni": true|false, "ne": "yeni gelişme en fazla 15 kelime ya da null"}"""

def guncelleme_yaz(tw, el, mevcut, bekleyen_not=None):
    govde = html.unescape(re.sub(r"<[^>]+>", " ", mevcut["body"]))[:2500]
    _sss = " | ".join(f"S: {q} C: {c}" for q, c in (mevcut.get("sss") or []) if q)
    mesaj = (f"Yayımlanmış haber: {mevcut['title']} ({mevcut.get('date','')})\nÖzet maddeleri: " + " || ".join(mevcut.get("ozet", []))
             + (f"\nSSS: {_sss}" if _sss else "") + f"\nMetin: {govde}\n\n"
             f"Yeni paylaşım: {tw['ad']} (@{tw['kullanici']}) {tw['tarih']} {tw['saat']}\nBağlantı: {tw['url']}\nMetin:\n{tw['metin']}\n"
             f"Editör notu: {el.get('konu','')}" + (f" | yeni gelişme: {el['yeni_gelisme']}" if el.get("yeni_gelisme") else ""))
    if el.get("capraz_teyit"):
        mesaj += ("\n\nÇAPRAZ TEYİT: Aynı gelişmeyi kısa süre içinde şu bağımsız hesaplar da paylaştı: "
                  + "; ".join(f"@{k} ({u})" for k, u, _ in el["capraz_teyit"]) + ". Bunları paylaşan hesap dışındaki bağımsız kaynaklar olarak say.")
    if bekleyen_not:
        mesaj += ("\n\nONAY BEKLEYEN GÜNCELLEME NOTU (henüz yayımlanmadı; bunu da yazının parçası say):\n" + str(bekleyen_not)
                  + "\n\nGÖREV: Yeni paylaşım, yazıya VE bu bekleyen nota göre yeni bir bilgi ekliyorsa, bekleyen notu ve yeni bilgiyi birleştiren "
                  "TEK bir güncelleme notu yaz (en fazla 4 cümle, olay sırasına göre). Bekleyen nottaki bilgileri koru, tekrar etme. "
                  "Yeni bilgi yoksa \"yayinla\": false, \"sebep\": \"yeni_degil\".")
    if ENV_YAZIM_MODU == "iki":
        notlar = arastir(mesaj, 3)
        metin, _ = claude(MODEL_YAZIM, GUNCELLEME_SISTEM.replace("web_search ile (en fazla 3 arama) gelişmeyi teyit et", "aşağıdaki araştırma notlarıyla gelişmeyi teyit et"),
                          mesaj + NOT_EKI + notlar, max_tokens=6000, timeout=300)
    else:
        metin, _ = claude(MODEL_YAZIM, GUNCELLEME_SISTEM, mesaj, max_tokens=6000,
                          araclar=[{"type": WEB_ARAMA_ARACI, "name": "web_search", "max_uses": 3}], timeout=300)
    return json_ayikla(metin)

ICERIK_DOSYALARI = ["content6.py", "content5.py", "content4.py", "content3.py", "content2.py", "content1.py"]

def _post_konumu(slug):
    """yazının bulunduğu içerik dosyası ve kaynaktaki bayt aralığı: (yol, baytlar, baş, son) ya da None"""
    import ast
    for ad in ICERIK_DOSYALARI:
        yol = os.path.join(SITE_DEPO, ad)
        if not os.path.exists(yol): continue
        kaynak = open(yol, encoding="utf-8").read()
        if repr(slug)[1:-1] not in kaynak: continue
        b = kaynak.encode("utf-8")
        satir_bas = [0]
        for i, ch in enumerate(b):
            if ch == 10: satir_bas.append(i + 1)
        for node in ast.walk(ast.parse(kaynak)):
            if isinstance(node, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == "slug" and isinstance(v, ast.Constant) and v.value == slug
                                                  for k, v in zip(node.keys, node.values)):
                return yol, b, satir_bas[node.lineno - 1] + node.col_offset, satir_bas[node.end_lineno - 1] + node.end_col_offset
    return None

def _post_degistir(slug, degistir):
    """içerik dosyalarında slug'ı verilen yazıyı bulur, degistir(post)->post ile değiştirir (biçimi bozmadan, yalnızca o yazı)"""
    import ast
    k = _post_konumu(slug)
    if not k: raise RuntimeError("yazı bulunamadı: " + slug)
    yol, b, bas, son = k
    eski = ast.literal_eval(b[bas:son].decode("utf-8"))
    yeni = degistir(dict(eski))
    open(yol, "w", encoding="utf-8").write((b[:bas] + repr(yeni).encode("utf-8") + b[son:]).decode("utf-8"))
    return eski

def _post_kaldir(slug):
    """yazıyı içerik dosyasından çıkarır (ardındaki virgül ve satır sonuyla); bulunamazsa False"""
    k = _post_konumu(slug)
    if not k: return False
    yol, b, bas, son = k
    while son < len(b) and b[son:son + 1] in (b" ", b"\t"): son += 1
    if b[son:son + 1] == b",": son += 1
    if b[son:son + 1] == b"\n": son += 1
    while bas > 0 and b[bas - 1:bas] in (b" ", b"\t"): bas -= 1
    open(yol, "w", encoding="utf-8").write((b[:bas] + b[son:]).decode("utf-8"))
    return True

def _ay(n):
    return ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][n - 1]

def _kaynak_ciftleri(x):
    """modelin döndürdüğü kaynak alanını [[başlık, url], ...] biçimine çevirir; tek çift, çift listesi, sözlük ya da düz adres gelebilir"""
    if not x: return []
    if isinstance(x, dict): x = [x]
    if isinstance(x, str): x = [x]
    if isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(y, str) for y in x): x = [x]
    cikti = []
    for k in x if isinstance(x, (list, tuple)) else []:
        if isinstance(k, dict):
            u = k.get("url") or k.get("adres") or k.get("link") or ""
            t = k.get("baslik") or k.get("başlık") or k.get("title") or k.get("ad") or u
        elif isinstance(k, str):
            t = u = k
        elif isinstance(k, (list, tuple)) and len(k) >= 2:
            t, u = k[0], k[1]
        else:
            continue
        if str(u).startswith("http"): cikti.append([str(t), str(u)])
    return cikti

def duzeltmeleri_temizle(liste):
    """modelin verdiği tutarlılık düzeltmelerini doğrular: [{"alan","eski","yeni"}]"""
    out = []
    for d in (liste or [])[:8]:
        if not isinstance(d, dict): continue
        a, e, y = str(d.get("alan") or "body"), str(d.get("eski") or "").strip(), str(d.get("yeni") or "").strip()
        if a not in ("title", "ozet", "sss", "body") or len(e) < 12 or not y or e == y: continue
        if a == "title" and len(y) > 75: continue
        if yasak_bul(y) or itham_bul(y): continue
        if all(e != o["eski"] for o in out): out.append({"alan": a, "eski": e, "yeni": y.replace("—", ",")})
    return out[:6]

def _duzeltme_uygula(p, duzeltmeler):
    """eskiyen cümleleri yazının her yerinde (başlık, özet, SSS, gövde) değiştirir; uygulananların sayısını döndürür"""
    say = 0
    for d in duzeltmeler or []:
        e, y = d["eski"], d["yeni"]
        bulundu = False
        if e in p.get("title", ""):
            p["title"] = p["title"].replace(e, y); bulundu = True
        oz = [str(x) for x in p.get("ozet", [])]
        if any(e in x for x in oz):
            p["ozet"] = [x.replace(e, y) for x in oz]; bulundu = True
        if p.get("sss"):
            yeni_sss = [[str(q).replace(e, y), str(c).replace(e, y)] for q, c in p["sss"]]
            if yeni_sss != [[str(q), str(c)] for q, c in p["sss"]]: p["sss"] = yeni_sss; bulundu = True
        for aday in (e, html.escape(e, quote=False)):
            if aday in p.get("body", ""):
                p["body"] = p["body"].replace(aday, html.escape(y, quote=False)); bulundu = True; break
        if bulundu: say += 1
        else: log("düzeltme cümlesi yazıda bulunamadı:", e[:80])
    return say

def guncelleme_uygula(slug, not_metni, kaynak, duzeltmeler=None):
    n = simdi()
    not_metni = re.sub(r"^\s*Güncelleme(?:\s*\([^)]*\))?\s*:\s*", "", str(not_metni).strip())   # başlık zaten paragrafta var
    paragraf = f'<p><b>Güncelleme ({n.day} {_ay(n.month)} {n.year}, {n.strftime("%H.%M")}):</b> {html.escape(not_metni)}</p>'
    def degistir(p):
        govde = p["body"]
        i = govde.find("</p>")  # spotun hemen arkasına
        p["body"] = govde[:i + 4] + paragraf + govde[i + 4:] if i >= 0 else paragraf + govde
        p["updated"] = n.strftime("%Y-%m-%dT%H:%M")
        # okura gösterilen güncelleme geçmişi: tarih, tür ve ne değiştiği
        _dz = _duzeltme_uygula(p, duzeltmeler)
        _gn = not_metni.strip()
        if _dz: _gn = (_gn[:190] + (" Yazının eskiyen bölümleri bu gelişmeye göre güncellendi."))
        p["gecmis"] = list(p.get("gecmis", [])) + [{"tarih": p["updated"], "tur": "Güncelleme", "not": _gn[:300]}]
        for kc in _kaynak_ciftleri(kaynak):
            if all(kc[1] != k[1] for k in p.get("kaynaklar", [])): p["kaynaklar"] = list(p.get("kaynaklar", [])) + [kc]
        return p
    sakla = {}
    def hazirla():
        sakla["eski"] = _post_degistir(slug, degistir)
    _gonder("Güncelleme: " + slug, hazirla)
    return sakla.get("eski"), paragraf

def guncelleme_geri_al(slug, eski):
    def hazirla():
        _post_degistir(slug, lambda p: eski)
    _gonder("Güncelleme geri alındı: " + slug, hazirla)

# ------------------------------------------------------------------ 3) yayın / yayından kaldırma
_yayin_kilit = threading.RLock()   # yeniden girilebilir: hızlı yayın, kilidi tutarken _gonder'i çağırır

def _git(*a):
    r = subprocess.run(["git", "-C", SITE_DEPO] + list(a), capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError("git " + " ".join(a) + ": " + (r.stderr or r.stdout)[-400:])
    return r.stdout

def _derle_denetle(sure=None):
    t0 = time.time()
    b = subprocess.run(["python3", "build.py"], cwd=SITE_DEPO, capture_output=True, text=True, timeout=300)
    if b.returncode != 0: raise RuntimeError("build: " + b.stderr[-600:])
    t1 = time.time()
    c = subprocess.run(["python3", "check.py"], cwd=SITE_DEPO, capture_output=True, text=True, timeout=300)
    if sure is not None: sure["derle"] = round(t1 - t0, 1); sure["denetle"] = round(time.time() - t1, 1)
    if c.returncode != 0 or "kırık 0" not in c.stdout or "kimlik tamam" not in c.stdout:
        raise RuntimeError("check: " + (c.stdout + c.stderr)[-600:])

_yukleme_tl = threading.local()   # _gonder'in başlattığı Cloudflare yüklemesi (aynı iş parçacığında okunur)

def _canli_izle(tid, url, yukleme=None, bildir_baslik=None):
    """yükleme bitip sayfa sitede açılana kadar taslak "yayınlanıyor" görünür (canli=False); sayfa açıldığı anda canli=True ve
    "Yayında" bildirimi gider. Arama motoru bildirimleri (WebSub, IndexNow) ardından arka planda yapılır; yayını bekletmez."""
    from ortak import canli_bekle, arama_motorlarina_duyur
    t0 = time.time(); gecen = None
    try:
        if yukleme: yukleme.join(timeout=600)
        t1 = time.time()
        gecen = canli_bekle(url)
        log(f"canlıda: yükleme {round(t1 - t0, 1)} sn + görünme {gecen} sn:", url)
    except Exception as e:
        log("canlı denetimi hatası:", e)
    with _taslak_kilit:
        d = taslak_oku(tid)
        if d:
            d["canli"] = True; d["canli_ts"] = time.time()
            if gecen is None: d["canli_uyari"] = "Sayfa birkaç dakika içinde sitede görünmedi; eşitleme döngüsü tamamlayacak."
            taslak_yaz(d)
    if bildir_baslik: bildirim(*bildir_baslik)
    if gecen is not None:
        try: arama_motorlarina_duyur(url, gecen)
        except Exception as e: log("arama motoru bildirimi hatası:", e)

_GIT_AYARLI = False
def _gonder(mesaj, hazirla, cf=True):
    """depoyu uzak dala eşitler, hazirla() ile değiştirir, derler, denetler ve gönderir.
    Hız: Cloudflare yüklemesi derleme ve yerel commit biter bitmez başlar; GitHub'a gönderim yükleme sürerken yapılır."""
    global _GIT_AYARLI
    with _yayin_kilit:
        if not _GIT_AYARLI:   # git yalnızca boyutu/zamanı değişen dosyaları yeniden okusun (görseller sabit bağlantılı, zamanları değişmez)
            try: _git("config", "core.checkStat", "minimal"); _git("config", "core.trustctime", "false"); _GIT_AYARLI = True
            except Exception as e: log("git ayarı yapılamadı:", e)
        for deneme in range(4):
            sure = {}; t = time.time()
            def adim(ad):
                nonlocal t
                n = time.time(); sure[ad] = round(n - t, 1); t = n
            _git("fetch", "-q", "origin", "main"); _git("reset", "-q", "--hard", "origin/main"); adim("git eşitle")
            if hazirla() is False: return False
            adim("hazırla")
            _derle_denetle(sure); t = time.time()
            _git("add", "-A")
            adim("git add")
            if not subprocess.run(["git", "-C", SITE_DEPO, "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
                log("gönderilecek değişiklik yok:", mesaj, "| adımlar (sn):", ", ".join(f"{k} {v}" for k, v in sure.items())); return True
            _git("commit", "-q", "-m", mesaj); adim("commit")
            import cfyukle
            _t = None
            if cf or deneme > 0:   # hızlı yayında site zaten yüklendi; yalnızca taban değiştiyse (yeniden deneme) yeniden yüklenir
                # Cloudflare'e yükleme hemen başlar (15-30 sn); push ile paralel. Kilit içinde sabit kopya: sonraki derleme yüklemeyi bozamaz
                _t = threading.Thread(target=cfyukle.yukle, args=(SITE_DEPO, mesaj, cfyukle.anlik_kopya(SITE_DEPO)), daemon=True)
                _t.start(); adim("kopya")
            r = subprocess.run(["git", "-C", SITE_DEPO, "push", "-q", "origin", "HEAD:main"], capture_output=True, text=True, timeout=120)
            adim("push")
            log("yayın adımları (sn):", ", ".join(f"{k} {v}" for k, v in sure.items()), "|", mesaj[:60])
            if r.returncode == 0:
                _yukleme_tl.t = _t
                return True
            log("push reddedildi, yeniden deneniyor:", r.stderr.strip()[-200:])
            time.sleep(3 + deneme * 2)
        raise RuntimeError("push 4 denemede başarısız")

def _post_olustur(p, n, saat=None):
    """onaylanan taslaktan siteye eklenecek yazı kaydı; saat verilirse (ön derlemedeki yer tutucu) o yazılır"""
    post = {"slug": p["slug"], "saat": saat or n.strftime("%H:%M"), "date": n.strftime("%Y-%m-%d"), "tur": p.get("tur", "Haber"),
            "title": p["title"], "cats": p["cats"], "tags": p["tags"], "ozet": p["ozet"], "body": p["body"],
            "kaynaklar": p["kaynaklar"]}
    # editör uygulamasında seçilen inceleyen avukat: haberi incelemiş sayılır (sitede "Hukuki inceleme" kartı)
    if p.get("denetleyen"): post["denetleyen"] = p["denetleyen"]
    if p.get("denetleyen") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(p.get("incelendi") or "")): post["incelendi"] = p["incelendi"]
    # ek mesainin geçmiş taramasından gelen yazı: sitede olay tarihindeki yerinde durur (yeni gibi görünmez);
    # gerçek eklenme anı ayrıca tutulur, okura not olarak ve arama motorlarına yayın tarihi olarak verilir
    _ot = str(p.get("olay_tarihi") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", _ot) and _ot < n.strftime("%Y-%m-%d"):
        post.update(date=_ot, eklenme=n.strftime("%Y-%m-%dT%H:%M")); post.pop("saat", None)
    if p.get("sss"):
        _s = sss_hazirla(p)
        if _s: post["sss"] = _s
    _k = p.get("karar")
    if isinstance(_k, dict):
        _izin = ("mahkeme", "daire", "esas", "karar_no", "tarih", "konu", "uyusmazlik", "sonuc", "etki", "kaynak")
        _k = {a_: str(v_).strip()[:160] for a_, v_ in _k.items() if a_ in _izin and isinstance(v_, (str, int)) and str(v_).strip() and str(v_).strip().lower() not in ("null", "yok", "bilinmiyor", "-")}
        if _k.get("kaynak") and not (_k["kaynak"].startswith("https://") and _k["kaynak"] in [x[1] for x in p.get("kaynaklar", [])]):
            _k.pop("kaynak")   # künyedeki bağlantı yalnızca haberin kaynaklarında olan bir adres olabilir
        if _k.get("mahkeme") and len(_k) >= 3: post["karar"] = _k
    temiz = lambda x: re.sub(r"[<(]cite\b[^>]*>", "", x).replace("</cite>", "") if isinstance(x, str) else x
    post = {k: (temiz(v) if isinstance(v, str) else [temiz(i) if isinstance(i, str) else [temiz(j) for j in i] if isinstance(i, list) else i for i in v]
                if isinstance(v, list) else v) for k, v in post.items()}
    return post

def _yayin_engeli(post):
    """yazı sitede zaten varsa ya da aynı konu son 12 saatte yayımlandıysa nedenini döndürür"""
    if post["slug"] in site_sluglari() or post["title"] in [x[2] for x in site_yazilari(200)]:
        return "başlık ya da adres sitede zaten var"
    # aynı konuda son 12 saatte yayımlanmış bir haber varsa (iki taslak aynı anda hazırlanmış olabilir) yayımlanmaz
    kok = lambda t: {w[:4] for w in _kelimeler(t) if w not in ("anlama", "geliyor", "nasıl", "işler", "süreç", "değişti", "kimleri", "kapsıyor")}
    k = kok(post["title"])
    for q in _posts()[:40]:
        try:
            yas = time.time() - datetime.datetime.strptime(f"{q['date']} {q.get('saat','00:00')}", "%Y-%m-%d %H:%M").timestamp()
        except Exception:
            continue
        w = kok(q["title"])
        if yas < 12 * 3600 and k and w and len(k & w) / len(k | w) >= 0.5:
            return "benzer haber zaten yayında: " + q["title"]
    return None

def _gorsel_depoya(p, slug, onhazir_ws=None):
    """haberin fotoğrafını depoya koyar; ön derlemede indirilmiş fotoğraf varsa aynısını kopyalar (canlıyla birebir aynı olsun)"""
    if onhazir_ws:
        k = os.path.join(onhazir_ws, "commons", slug + ".jpg")
        if os.path.exists(k):
            shutil.copyfile(k, os.path.join(SITE_DEPO, "commons", slug + ".jpg"))
            mw = json.load(open(os.path.join(onhazir_ws, "commons", "meta.json"), encoding="utf-8"))
            mp = os.path.join(SITE_DEPO, "commons", "meta.json"); meta = json.load(open(mp, encoding="utf-8"))
            meta[slug] = mw[slug]; json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return
    if not (p.get("foto") and commons_indir(p["foto"], slug)):
        _gorsel_kopyala(slug, p.get("gorsel"))

def yayinla(p, hizli_cb=None):
    """yazıyı yayımlar. Taslağın geçerli ön derlemesi varsa site hemen (birkaç sn) yayına alınır ve hizli_cb(url, yükleme) çağrılır;
    depo kaydı (derleme, denetim, git) ardından yapılır ve siteyi yeniden yüklemez."""
    n = simdi()
    with _yayin_kilit:
        hizli = onhazir_dagit(p, n) if hizli_cb else None
        post = _post_olustur(p, n)
        if hizli:
            hizli_cb(f"{SITE}/{post['slug']}/", hizli["yukleme"])
        def hazirla():
            neden = _yayin_engeli(post)
            if neden:
                log("yayımlanmadı:", neden, "|", post["title"]); return False
            _gorsel_depoya(p, post["slug"], hizli["ws"] if hizli else None)
            yol = os.path.join(SITE_DEPO, "content6.py")
            s = open(yol, encoding="utf-8").read()
            i = s.index("POSTS = [") + len("POSTS = [")
            open(yol, "w", encoding="utf-8").write(s[:i] + "\n" + repr(post) + "," + s[i:])
        def geri_al():   # site yayına alındı ama depo kaydı yapılamadı: site depoyla yeniden eşitlenir (haber kalkar)
            import cfyukle
            log("HIZLI YAYIN GERİ ALINIYOR (depo kaydı yapılamadı):", post["title"])
            try: hizli["yukleme"].join(timeout=300)
            except Exception: pass
            cfyukle.yukle(SITE_DEPO, "hızlı yayın geri alındı", cfyukle.anlik_kopya(SITE_DEPO))
        try:
            try:
                sonuc = _gonder("Yeni haber: " + post["title"], hazirla, cf=not hizli)
            except Exception:
                if hizli: geri_al()
                raise
            if sonuc is False:
                if hizli: geri_al()
                return None
        finally:
            if hizli:
                _ONHAZIR_KULLANIMDA.discard(hizli["tid"]); _onhazir_sil(hizli["tid"])
    return f"{SITE}/{post['slug']}/"

def gorsel_sonradan_ekle(slug, sec):
    """görselsiz yayımlanmış habere (editör görsel seçimi bitmeden yayınladıysa) seçilen görseli ekler"""
    if not (sec.get("foto") or sec.get("gorsel")): return False
    def hazirla():
        if slug not in site_sluglari(): return False
        if os.path.exists(os.path.join(SITE_DEPO, "commons", slug + ".jpg")): return False   # zaten görseli var
        if sec.get("foto") and commons_indir(sec["foto"], slug): return
        if sec.get("gorsel"): _gorsel_kopyala(slug, sec["gorsel"]); return
        return False
    return _gonder("Görsel eklendi: " + slug, hazirla)

def gorselleri_tamamla(saat=24):
    """servis açılışında: yeniden başlatma yüzünden yarıda kalan görsel seçimlerini tamamlar.
    Onay bekleyen taslakta görsel yoksa seçip taslağa ekler; görselsiz yayımlanmış habere seçip yayına ekler."""
    time.sleep(45)   # servis tam açılsın, onay/eşitleme işleri önce başlasın
    # yeniden başlatma "görsel bekleniyor" yayınını yarıda bıraktıysa kaldığı yerden sürdür
    for f in sorted(os.listdir(TASLAK_DIR)):
        if not f.endswith(".json"): continue
        try:
            d = taslak_oku(f[:-5])
            if d and d.get("durum") == "yayınlanıyor" and d.get("gorsel_bekleniyor"):
                with _taslak_kilit:
                    d = taslak_oku(f[:-5]); d["durum"] = "bekliyor"; d.pop("gorsel_bekleniyor", None); taslak_yaz(d)
                log("yarıda kalan görsel bekleyen yayın sürdürülüyor:", d["post"]["title"])
                threading.Thread(target=onay_isle, args=("yayinla", d["id"]), daemon=True).start()
        except Exception as e:
            log("görsel bekleyen yayın sürdürülemedi:", f, repr(e)[:120])
    try:
        with _yayin_kilit:
            _git("fetch", "-q", "origin", "main"); _git("reset", "-q", "--hard", "origin/main")
    except Exception as e:
        log("görsel tamamlama: depo güncellenemedi:", e)
    sinir = time.time() - saat * 3600
    for f in sorted(os.listdir(TASLAK_DIR)):
        yol = os.path.join(TASLAK_DIR, f)
        if not f.endswith(".json") or os.path.getmtime(yol) < sinir: continue
        try:
            d = taslak_oku(f[:-5])
            if not d or d.get("tip", "haber") != "haber": continue
            p = d["post"]
            if d.get("durum") == "bekliyor" and not p.get("gorsel_denetim"):
                sec = gorsel_sec(p, {})
                d2 = taslak_oku(d["id"])
                if d2 and d2.get("durum") == "bekliyor" and not d2["post"].get("gorsel_denetim"):
                    d2["post"]["foto"] = sec.get("foto"); d2["post"]["gorsel"] = sec.get("gorsel"); d2["post"]["gorsel_denetim"] = sec.get("denetim")
                    taslak_yaz(d2); log("görsel tamamlama: taslağa görsel eklendi:", p["title"])
            elif (d.get("durum") == "yayınlandı" and not d.get("gorsel_tamam") and not p.get("gorsel_denetim")
                  and p.get("slug") in site_sluglari()
                  and not os.path.exists(os.path.join(SITE_DEPO, "commons", p["slug"] + ".jpg"))):
                sec = gorsel_sec(p, {})
                if gorsel_sonradan_ekle(p["slug"], sec):
                    log("görsel tamamlama: yayındaki habere görsel eklendi:", p["title"])
                d3 = taslak_oku(d["id"])
                if d3: d3["gorsel_tamam"] = True; taslak_yaz(d3)   # bir daha denenmesin (bütçe boşa gitmesin)
        except Exception as e:
            log("görsel tamamlama hatası:", f, repr(e))

def gorsel_bekcisi(aralik=600):
    """Son 72 saatte yayımlanan ve sitede fotoğrafı olmayan her haber için fotoğraf seçip ekler.
    Durum sitenin kendisinden okunur (taslak bayraklarına güvenilmez); her haber için 15 dk, 1 sa, 3 sa aralıklarla en fazla 4 deneme."""
    time.sleep(90)
    while True:
        try:
            _gorsel_bekci_tur()
        except Exception as e:
            log("görsel bekçisi hatası:", repr(e))
        time.sleep(aralik)

def _gorsel_bekci_tur():
    yol = os.path.join(VERI, "gorsel_bekci.json")
    try: kayit = json.load(open(yol, encoding="utf-8"))
    except Exception: kayit = {}
    try:
        with _yayin_kilit:
            _git("fetch", "-q", "origin", "main"); _git("reset", "-q", "--hard", "origin/main")
    except Exception as e:
        log("görsel bekçisi: depo güncellenemedi:", e); return
    an = time.time()
    for p in _posts()[:60]:
        try:
            yts = datetime.datetime.strptime(f"{p['date']} {p.get('saat', '00:00')}", "%Y-%m-%d %H:%M").timestamp()
        except Exception:
            continue
        if an - yts > 72 * 3600: continue
        slug = p["slug"]
        if os.path.exists(os.path.join(SITE_DEPO, "commons", slug + ".jpg")) or slug in _GORSEL_ISLENIYOR: continue
        if an - yts < 300: continue   # yeni yayımlandı: normal akış görseli eklemeye devam ediyor olabilir
        k = kayit.get(slug, {"deneme": 0, "son": 0})
        if k["deneme"] >= 4 or an - k["son"] < (0, 900, 3600, 10800)[k["deneme"]]: continue
        k["deneme"] += 1; k["son"] = an; kayit[slug] = k
        json.dump(kayit, open(yol, "w", encoding="utf-8"), ensure_ascii=False)
        _GORSEL_ISLENIYOR.add(slug)
        try:
            pp = dict(p)
            pp.setdefault("gorsel_aramalari", [p["title"]])
            sec = gorsel_sec(pp, {x: v for x, v in gorsel_listesi().items() if x != slug})
            if gorsel_sonradan_ekle(slug, sec):
                log("görsel bekçisi: fotoğraf eklendi:", slug, (sec.get("denetim") or {}).get("goruluyor", ""))
            else:
                log("görsel bekçisi: fotoğraf eklenemedi, sonra yeniden denenecek:", slug)
        except Exception as e:
            log("görsel bekçisi: deneme hatası:", slug, repr(e))
        finally:
            _GORSEL_ISLENIYOR.discard(slug)

def yayindan_kaldir(slug, neden):
    def hazirla():
        if not _post_kaldir(slug): return False
        # eski (WordPress dönemi) adresi olan yazı: adres 404 yerine arşive yönlendirilir
        ut = os.path.join(SITE_DEPO, "urls.tsv")
        if os.path.exists(ut) and ("/" + slug) in open(ut, encoding="utf-8").read():
            kp = os.path.join(SITE_DEPO, "kaldirilanlar.json")
            L = json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else []
            if all(x["slug"] != slug for x in L): L.append({"slug": slug, "hedef": "/arsiv/", "tarih": simdi().strftime("%Y-%m-%d"), "neden": str(neden)[:120]})
            json.dump(L, open(kp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        g = os.path.join(SITE_DEPO, "commons", slug + ".jpg")
        if os.path.exists(g): os.remove(g)
        mp = os.path.join(SITE_DEPO, "commons", "meta.json")
        meta = json.load(open(mp, encoding="utf-8")); meta.pop(slug, None)
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return _gonder("Haber kaldırıldı: " + slug, hazirla)

# ------------------------------------------------------------------ ana akış
ON_KONTROL_SISTEM = """Bir hukuk haber sitesinin editörüsün. Bir haber hesabının X paylaşımı geldi; PAHALI yazım aşamasına geçmeden önce
Google'da hızlıca kontrol et:
1) teyit: Olay resmî bir kaynakta (kurum sitesi, Resmî Gazete, başsavcılık/bakanlık açıklaması) ya da paylaşan hesap DIŞINDA en az
   iki bağımsız haber sitesinde var mı?
2) zaten_var: Olay, aşağıdaki "Sitemizde yayımlananlar" listesinde zaten işlenmiş mi (aynı olay, yeni gelişme yok)?
Cevabın SONUNDA yalnızca tek satır JSON ver (kod bloğu yok): {"teyit": true|false, "zaten_var": true|false, "neden": "en fazla 20 kelime"}"""

def google_haberler(sorgu, en_cok=15):
    """Google Haberler RSS (ücretsiz, anahtarsız): son 2 günün başlıkları -> ["kaynak | saat | başlık", ...]; hata olursa None"""
    import xml.etree.ElementTree as ET, email.utils
    q = urllib.parse.quote(re.sub(r"\s+", " ", sorgu).strip()[:150] + " when:2d")
    try:
        veri = urllib.request.urlopen(urllib.request.Request(
            f"https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr", headers=_UA), timeout=20).read()
        cikti = []
        for it in ET.fromstring(veri).iter("item"):
            kaynak = (it.findtext("source") or "").strip()
            try: saat = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(TR).strftime("%d.%m %H:%M")
            except Exception: saat = ""
            cikti.append(f"- {kaynak} | {saat} | {(it.findtext('title') or '').strip()[:140]}")
            if len(cikti) >= en_cok: break
        sayac("google_haberler", 1)
        return cikti
    except Exception as e:
        log("google haberler okunamadı:", str(e)[:80]); return None


_yenilik_son = {}   # slug -> [(zaman, kökler)]: "yeni değil" denen paylaşımlar; neredeyse aynı metin 2 saat içinde yeniden sorulmaz

def _yenilik_tekrar_mi(slug, metin):
    k = _ct_kokler(metin)
    if len(k) < 3: return False
    for ts, k2 in _yenilik_son.get(slug, []):
        if time.time() - ts < 7200 and len(k & k2) / max(1, min(len(k), len(k2))) >= 0.7: return True
    return False

AYNI_OLAY_SISTEM = """Bir hukuk haber sitesinin editörüsün. Yeni gelen bir paylaşım ve sitede son günlerde yayımlanmış aday yazılar var.
1) Paylaşım, adaylardan biriyle AYNI somut olayı mı anlatıyor: aynı soruşturma/operasyon, aynı dava, aynı karar, aynı düzenleme?
   Konu benzerliği yetmez: farklı il, farklı kurum, farklı şüpheli grubu, farklı dava ya da farklı düzenleme ise aynı olay DEĞİLDİR.
2) Aynıysa: paylaşım o yazıda OLMAYAN yeni ve somut bir hukuki gelişme bildiriyor mu? Yeni gelişme: dosyanın bir sonraki adımı
   (gözaltı/tutuklama/tahliye kararı, sayının değişmesi, iddianame, duruşma tarihi, ara karar, hüküm, Resmî Gazete'de yayımlanma,
   yeni resmî açıklama) ya da yazıda bulunmayan somut bir bilgi. Aynı bilginin başka sözcüklerle tekrarı yeni DEĞİLDİR.
Yalnızca JSON: {"ayni": true|false, "no": aday numarası ya da null, "yeni": true|false, "ne": "yeni gelişme en fazla 15 kelime ya da null"}"""

def _post_zamani(p):
    try: return datetime.datetime.fromisoformat(f'{p["date"]} {p.get("saat") or "12:00"}').replace(tzinfo=TR)
    except Exception: return None

def ayni_olay_bul(tw, el, gun=3):
    """yeni haber yazılmadan önce: son günlerde yayımlanan yazılardan biri aynı olayı anlatıyor mu?
    Dönen: {"slug","baslik","yeni","ne","saat_once"} ya da None. Aday seçimi ayırt edici kelimelerle, karar küçük modelle verilir."""
    from collections import Counter
    posts = _posts()
    if not posts: return None
    ks = [_kokler(p.get("title", "")) for p in posts]
    df = Counter(k for s_ in ks for k in s_); sinir = max(3, int(len(posts) * 0.02))
    ayirt = lambda s_: {k for k in s_ if df.get(k, 0) <= sinir}
    ak = ayirt(_kokler(str(el.get("konu", ""))))   # editörün konu cümlesindeki kelimeler daha ağır sayılır
    a = ak | ayirt(_kokler((tw.get("metin") or "")[:400]))
    if len(a) < 2: return None
    an = simdi(); adaylar = []
    for p, s_ in zip(posts, ks):
        t = _post_zamani(p)
        if not t or t > an or (an - t).total_seconds() > gun * 86400: continue
        o = a & ayirt(s_)
        # iki ayırt edici kelime ya da çok nadir tek kelime (yer/kişi/kurum adı: Milas, Kozay) aday yapar; sıralama nadirlik ağırlığıyla
        if len(o) >= 2 or any(df.get(k, 0) <= 3 for k in o): adaylar.append((sum((3 if k in ak else 1) / df.get(k, 1) for k in o), t, p))
    if not adaylar: return None
    adaylar = sorted(adaylar, key=lambda x: (-x[0], -x[1].timestamp()))[:6]
    satir = []
    for i, (_, t, p) in enumerate(adaylar, 1):
        govde = html.unescape(re.sub(r"<[^>]+>", " ", p.get("body", "")))
        gecmis = " ".join(str(x.get("not", "")) for x in p.get("gecmis", []) if isinstance(x, dict))
        satir.append(f"ADAY {i}: {p['title']} ({p.get('date','')} {p.get('saat') or ''})\nÖzet: {' '.join(p.get('ozet', []))[:600]}\n"
                     f"Güncellemeler: {gecmis[:500]}\nMetin: {govde[:1500]}")
    mesaj = "\n\n".join(satir) + f"\n\nYENİ PAYLAŞIM (@{tw.get('kullanici')}, {tw.get('tarih')} {tw.get('saat')}):\n{(tw.get('metin') or '')[:1500]}"
    js = json_ayikla(kucuk_model(AYNI_OLAY_SISTEM, mesaj, 300, timeout=60))
    if not js.get("ayni"): return None
    try: _, t, p = adaylar[int(js.get("no")) - 1]
    except Exception: return None
    return {"slug": p["slug"], "baslik": p["title"], "yeni": bool(js.get("yeni")), "ne": js.get("ne") or None,
            "saat_once": (an - t).total_seconds() / 3600}

def yeni_gelisme_mi(tw, post):
    """paylaşım, yayındaki yazıda olmayan yeni bir hukuki gelişme bildiriyor mu? (ucuz model; içerik karşılaştırması)"""
    govde = html.unescape(re.sub(r"<[^>]+>", " ", post.get("body", "")))
    gecmis = " ".join(str(x.get("not", "")) for x in post.get("gecmis", []) if isinstance(x, dict))
    mesaj = (f"YAZI: {post['title']} ({post.get('date','')} {post.get('saat','')})\nÖzet: {' '.join(post.get('ozet', []))}\n"
             f"Güncellemeler: {gecmis[:800]}\nMetin: {govde[:3500]}\n\nYENİ PAYLAŞIM (@{tw.get('kullanici')}, {tw.get('tarih')} {tw.get('saat')}):\n{tw.get('metin','')[:1200]}")
    js = json_ayikla(kucuk_model(YENILIK_SISTEM, mesaj, 300, timeout=60))
    return bool(js.get("yeni")), (js.get("ne") or None)

# --- çapraz teyit: aynı gelişmeyi kısa süre içinde başka bağımsız hesaplar da paylaştıysa ---
_CT_DOLGU = _DOLGU | set("sondakika son dakika haber haberi flaş flas canlı video açıklama açıklaması açıkladı hakkında kişi kişiler yeni ilk "
                         "oldu olduğu edildi etti tarafından üzerine sonra önce bugün dün ise ancak".split())
CT_SISTEM = """Bir hukuk haber sitesinin editörüsün. ANA paylaşım ile ADAY paylaşımları karşılaştır: hangi adaylar ANA paylaşımla AYNI somut
gelişmeyi (aynı kişi ya da kurum, aynı olay, aynı hukuki adım: ör. aynı kişiye aynı gün açılan dava, aynı operasyon, aynı karar) bildiriyor?
Yalnızca aynı genel konudan söz etmek (ör. iki ayrı uyuşturucu operasyonu, aynı soruşturmanın farklı bir adımı, aynı kişiyle ilgili başka bir
gelişme) AYNI DEĞİLDİR. Emin değilsen aynı sayma. Yalnızca JSON: {"ayni": [aday numaraları], "neden": "en fazla 15 kelime"}"""

def _ct_kokler(t):
    t = re.sub(r"https?://\S+", " ", t or "")
    return {w[:5] for w in re.findall(r"[a-zçğıöşü0-9]{3,}", t.replace("İ", "i").replace("I", "ı").lower()) if w not in _CT_DOLGU}

def _kurum(k):
    """aynı kuruluşun farklı hesapları tek kaynak sayılır (Haberturk / HaberturkTV)"""
    k = re.sub(r"(tv|haber|gazetesi|com|tr|_)+$", "", (k or "").lower())
    return k[:6]

def _son_akis(saat=24, azami=4_000_000):
    yol = os.path.join(VERI, "akis.jsonl"); out = []
    try:
        with open(yol, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - azami)); f.readline() if n > azami else None
            bas = time.time() - saat * 3600
            for s_ in f:
                try: d = json.loads(s_)
                except Exception: continue
                if d.get("ts", 0) >= bas: out.append(d)
    except OSError: pass
    return out

def capraz_teyit(tw, el, dk=90):
    """aynı gelişmeyi ±dk dakika içinde paylaşan bağımsız hesaplar: [(kullanıcı, adres, grup)].
    Teyit için en az iki bağımsız haber kaynağı ya da bir resmî hesap gerekir; olmazsa boş liste."""
    import math
    akis = _son_akis()
    if not akis: return []
    df = {}
    for d in akis:
        for t in _ct_kokler(d.get("metin")): df[t] = df.get(t, 0) + 1
    N = len(akis); idf = lambda t: math.log((N + 1) / (df.get(t, 0) + 1))
    A = _ct_kokler(tw.get("metin")) | _ct_kokler(el.get("konu"))
    if len(A) < 3: return []
    wA = sum(idf(t) for t in A); t0 = tw.get("ts") or time.time()
    adaylar = {}
    for d in akis:
        if d.get("url") == tw.get("url") or abs((d.get("ts") or 0) - t0) > dk * 60: continue
        if _kurum(d.get("kullanici")) == _kurum(tw.get("kullanici")) or d.get("grup") == "siyasi": continue
        B = _ct_kokler(d.get("metin")); o = A & B
        if len(o) < 3 or not B: continue
        puan = sum(idf(t) for t in o) / min(wA, sum(idf(t) for t in B))
        if puan < 0.4: continue
        k = _kurum(d.get("kullanici"))
        if k not in adaylar or puan > adaylar[k][0]: adaylar[k] = (puan, d)
    L = sorted(adaylar.values(), key=lambda x: -x[0])[:8]
    if not L or (len(L) < 2 and not any(d.get("grup") == "resmi" for _, d in L)): return []
    temiz = lambda t, n: re.sub(r"https?://\S+", "", t or "")[:n]
    mesaj = ("ANA (@" + str(tw.get("kullanici")) + "): " + temiz(tw.get("metin"), 600) + "\n\nADAYLAR:\n"
             + "\n".join(f"{i + 1}. (@{d.get('kullanici')}) " + temiz(d.get("metin"), 400) for i, (_, d) in enumerate(L)))
    try:
        js = json_ayikla(kucuk_model(CT_SISTEM, mesaj, 400, timeout=60))
        ayni = {int(x) for x in (js.get("ayni") or []) if str(x).isdigit()}
    except Exception as e:
        log("çapraz teyit sorulamadı:", str(e)[:120]); return []
    onay = [d for i, (_, d) in enumerate(L) if i + 1 in ayni]
    if any(d.get("grup") == "resmi" for d in onay):
        return [(d.get("kullanici"), d.get("url"), d.get("grup")) for d in onay]
    # ajans metnini aynen kullanan hesaplar tek kaynak sayılır; ANA paylaşımın kopyası da bağımsız teyit değildir
    gruplar = _ct_kopya_gruplari([tw] + onay)
    bagimsiz = {gruplar[i + 1] for i in range(len(onay))} - {gruplar[0]}
    if len(bagimsiz) >= 2 and len({_kurum(d.get("kullanici")) for d in onay}) >= 2:
        return [(d.get("kullanici"), d.get("url"), d.get("grup")) for d in onay]
    if onay: log(f"çapraz teyit: {len(onay)} hesap aynı gelişmeyi verdi ama {len(bagimsiz)} bağımsız metin var (ajans kopyası)")
    return []

_AJANS = re.compile(r"\((aa|dha|iha|anka|ilke|mezopotamya|ma)\)|\b(anadolu ajansı|demirören haber ajansı|ihlas haber ajansı|anka haber ajansı)\b", re.I)

def _ct_kopya_gruplari(L):
    """aynı ajans metnini (ya da birbirinin kopyasını) paylaşan öğeleri aynı gruba koyar: öğe sırasıyla grup numaraları"""
    def parca(t):
        w = re.findall(r"[a-zçğıöşü0-9]+", re.sub(r"https?://\S+", " ", t or "").replace("İ", "i").replace("I", "ı").lower())
        return {" ".join(w[i:i + 4]) for i in range(max(0, len(w) - 3))}
    P = [parca(d.get("metin")) for d in L]
    A = [(_AJANS.search(d.get("metin") or "") or [None])[0] for d in L]
    grup = list(range(len(L)))
    def bul(i):
        while grup[i] != i: i = grup[i]
        return i
    for i in range(len(L)):
        for j in range(i):
            kopya = P[i] and P[j] and len(P[i] & P[j]) / max(1, min(len(P[i]), len(P[j]))) >= 0.5
            ayni_ajans = A[i] and A[j] and A[i].lower() == A[j].lower()
            if kopya or ayni_ajans: grup[bul(i)] = bul(j)
    return [bul(i) for i in range(len(L))]

def on_kontrol(tw, el):
    """haber hesabı kaynaklı paylaşımlarda yazımdan önce ücretsiz Gemini + Google araması ile teyit ve tekrar kontrolü.
    Gemini yoksa ya da hata verirse None döner (yazım her zamanki gibi devam eder)."""
    mesaj = (f"Paylaşan: {tw['ad']} (@{tw['kullanici']}), {tw['tarih']} {tw['saat']}\nMetin:\n{tw['metin']}\n"
             f"Konu: {el.get('konu','')}\n\nSitemizde yayımlananlar:\n{site_listesi(40)}")
    metin = None
    if GEMINI_KEY:
        # ücretsiz yol: Google Haberler RSS'inden son haber başlıkları + Gemini değerlendirmesi
        try:
            basliklar = google_haberler(el.get("konu") or tw["metin"][:120])
            if basliklar is not None:
                metin = gemini(ON_KONTROL_SISTEM.replace("Google'da hızlıca kontrol et", "aşağıdaki Google Haberler sonuçlarına bakarak kontrol et"),
                               mesaj + "\n\nGoogle Haberler sonuçları (son 2 gün; kaynak | saat | başlık):\n"
                               + ("\n".join(basliklar) or "- sonuç yok"), timeout=60)
        except Exception as e:
            log("ücretsiz ön kontrol olmadı, Haiku + 2 arama kullanılıyor:", str(e)[:80]); metin = None
    if metin is None:
        try:
            metin, _ = claude(MODEL_ELEME, ON_KONTROL_SISTEM, mesaj, max_tokens=3000, timeout=120,
                              araclar=[{"type": WEB_ARAMA_ARACI, "name": "web_search", "max_uses": 2}])
        except Exception as e:
            log("ön kontrol yapılamadı, yazıma geçiliyor:", str(e)[:120]); return None
    try:
        js = json_ayikla(metin)
    except Exception:
        # JSON yarım kaldıysa alanları metinden doğrudan oku
        t = re.search(r'"teyit"\s*:\s*(true|false)', metin); z = re.search(r'"zaten_var"\s*:\s*(true|false)', metin)
        if not (t and z):
            log("ön kontrol cevabı okunamadı, yazıma geçiliyor:", metin[:120].replace("\n", " ")); return None
        js = {"teyit": t.group(1) == "true", "zaten_var": z.group(1) == "true", "neden": "(kısmi cevap)"}
    return {"teyit": bool(js.get("teyit")), "zaten_var": bool(js.get("zaten_var")), "neden": str(js.get("neden", ""))[:200]}

def isle(tw, zorla=False):
    """zorla=True: editör panelden "Yine de yaz" dedi; ön süzgeç, eleme kararı, "yakında yazıldı" ve ön kontrol atlanır"""
    _akis_tl.tw, _akis_tl.el, _akis_tl.zorla, _akis_tl.tid = tw, None, zorla, None
    try: return _isle(tw, zorla)
    finally: _akis_tl.tw = _akis_tl.el = None; _akis_tl.zorla = False; _akis_tl.tid = None

def _isle(tw, zorla=False):
    if not zorla and tw["grup"] in ("kisi", "siyasi") and not on_suzgec(tw["metin"]):
        akibet_kaydet("ön süzgeç", "Metinde hukuki bir kelime yok (kişi ve siyasetçi hesaplarında yapay zekâya gönderilmeden elenir)")
        return
    try:
        el = ele(tw)
    except Exception as e:
        log("eleme hatası:", e); akibet_kaydet("hata", "Eleme yapılamadı: " + str(e)[:200]); return
    _akis_tl.el = el
    ekle_jsonl("eleme.jsonl", {"ts": time.time(), "tw": tw["url"], "kullanici": tw["kullanici"], **el})
    import ortak as _om
    _om.maliyet_bilgi(konu=el.get("konu") or (tw.get("metin") or "")[:160])
    if zorla and not el.get("haber"):
        el["eleme_neden"] = el.get("neden"); el["haber"] = True; el["islem"] = el.get("islem") or "yeni"
        el["konu"] = el.get("konu") or (tw.get("metin") or "")[:90]; el["oncelik"] = el.get("oncelik") or 2
        if el.get("tur") not in ("resmi", "siyasi", "gazeteci", "iddia"): el["tur"] = "gazeteci"
        log("editör isteğiyle eleme kararı aşıldı:", el["konu"])
    if not el.get("haber") and el.get("ilgili") and tw.get("grup") != "siyasi":
        # "sitede zaten var" kararı başlık listesine bakılarak verilir; yazının içeriğiyle karşılaştırıp yeni adım varsa güncellemeye çevir
        _slug = str(el["ilgili"]).strip("/").split("/")[-1]
        _post = post_bul(_slug)
        if _post and _yenilik_tekrar_mi(_slug, tw.get("metin")):
            el["neden"] = (el.get("neden") or "") + " (aynı bilgi az önce yazının içeriğiyle karşılaştırıldı: yeni bilgi yok)"
        elif _post:
            try:
                _yeni, _ne = yeni_gelisme_mi(tw, _post)
            except Exception as e:
                _yeni, _ne = False, None; log("yenilik denetimi yapılamadı:", str(e)[:120])
            if _yeni:
                log("elenen paylaşımda yeni gelişme bulundu, güncellemeye alındı:", _ne, "->", _slug)
                el.update(haber=True, islem="guncelleme", guncellenecek=_slug, yeni_gelisme=_ne, eleme_neden=el.get("neden"))
                el["tur"] = el.get("tur") or "iddia"; el["oncelik"] = el.get("oncelik") or 2
            else:
                _yenilik_son.setdefault(_slug, []).append((time.time(), _ct_kokler(tw.get("metin"))))
                _yenilik_son[_slug] = _yenilik_son[_slug][-30:]
                el["neden"] = (el.get("neden") or "") + " (yazının içeriğiyle karşılaştırıldı: yeni bilgi yok)"
    if not el.get("haber"):
        _om.maliyet_bilgi(sonuc="elendi", neden=el.get("neden"))
        akibet_kaydet("elendi", el.get("neden"))
        if os.environ.get("HH_AYRINTI"): log("elendi:", el.get("neden"), "|", el.get("konu"))
        return
    konu = el.get("konu", "")
    log(f"SİNYAL [{el.get('tur')}/{el.get('oncelik')}] @{tw['kullanici']}: {konu} -> {tw['url']}")
    if not el.get("guncellenecek") and not zorla:
        _onceki = yakinda_yazildi(konu)
        if _onceki:
            log("aynı konu yakın zamanda yazıldı, tekrar yazılmadı:", konu, "~", _onceki); konu_ekle(konu, "zaten yazıldı", f"Son saatlerde benzer konu yazıldı: {_onceki}"); return
        # aynı olaya ikinci yazı açılmaz: yeni bilgi yoksa yazılmaz; son 24 saatte yazılmışsa yeni bilgi o yazıya güncelleme olarak eklenir
        try: _ayni = ayni_olay_bul(tw, el)
        except Exception as e: _ayni = None; log("aynı olay denetimi yapılamadı:", str(e)[:150])
        if _ayni and not _ayni["yeni"]:
            log("aynı olay sitede zaten yazıldı, yeni bilgi yok:", konu, "~", _ayni["baslik"])
            konu_ekle(konu, "zaten var", f"Aynı olay sitede yazıldı, yeni bilgi yok: {_ayni['baslik']}"); return
        if _ayni and _ayni["saat_once"] < 24:
            log("aynı olay son 24 saatte yazıldı, yeni bilgi güncelleme olarak eklenecek:", _ayni["ne"], "->", _ayni["slug"])
            el.update(islem="guncelleme", guncellenecek=_ayni["slug"], yeni_gelisme=_ayni["ne"])
    konu_ekle(konu, "yazılıyor")
    if sinir_doldu(sayac("yazi"), GUNLUK_YAZI_SINIRI) or sinir_doldu(saatlik_yazi(), SAATLIK_YAZI_SINIRI):
        log("yazı sınırı dolu, atlandı"); konu_ekle(konu, "sınır", "Günlük ya da saatlik yazı sınırı dolu"); return
    t0 = time.time()
    if el.get("islem") == "guncelleme" and el.get("guncellenecek"):
        mevcut = post_bul(str(el["guncellenecek"]).strip("/"))
        if mevcut:
            with _guncelleme_kilit:
                if mevcut["slug"] in _guncellenen:
                    konu_ekle(konu, "zaten yazıldı", "Bu yazının güncellemesi şu an başka bir paylaşımdan hazırlanıyor"); return
                _guncellenen.add(mevcut["slug"])
            try:
                _bg = bekleyen_guncelleme(mevcut["slug"])
                if _bg and (taslak_oku(_bg) or {}).get("durum") == "yayınlanıyor":
                    # bekleyen güncelleme şu an yayınlanıyor: yayından sonra yeni bir güncelleme olarak yeniden denenir
                    ekle_jsonl("bekleyen.jsonl", {"ts": time.time(), "tw": tw, "eleme": el})
                    konu_ekle(konu, "teyit bekliyor", "Bu yazının bekleyen güncellemesi şu an yayınlanıyor; paylaşım birazdan yeniden denenecek"); return
                return _guncelleme_isle(tw, el, mevcut, konu, t0, zorla, _bg)
            finally:
                with _guncelleme_kilit: _guncellenen.discard(mevcut["slug"])
        log("güncellenecek yazı bulunamadı, yeni haber olarak devam:", el.get("guncellenecek"))
    return _yeni_haber_isle(tw, el, konu, t0, zorla)

_guncellenen = set(); _guncelleme_kilit = threading.Lock()

def bekleyen_guncelleme(slug):
    """bu yazı için onay bekleyen (ya da yayınlanmakta olan) güncelleme taslağı varsa kimliği"""
    for f in sorted(os.listdir(TASLAK_DIR), reverse=True)[:400]:
        if "-g-" not in f: continue
        try: d = json.load(open(os.path.join(TASLAK_DIR, f), encoding="utf-8"))
        except Exception: continue
        if d.get("tip") == "guncelleme" and d.get("durum") in ("bekliyor", "yayınlanıyor") and (d.get("post") or {}).get("slug") == slug:
            return d["id"]
    return None

BIRLESTIR_SISTEM = """Bir hukuk haber sitesinin editörüsün. Aynı yazı için farklı paylaşımlardan hazırlanmış, onay bekleyen birkaç güncelleme
notu var. Bunları TEK bir güncelleme notunda birleştir: tekrarları at, notlarda geçen bütün farklı ve doğrulanmış bilgileri koru, olay sırasına göre yaz.
Notlarda olmayan bilgi ekleme. En fazla 4 cümle, tarafsız, kimseyi suçlamadan; notlarda geçmeyen kişi adı yok; uzun tire yok; HTML yok.
Yalnızca JSON: {"not": "birleşik güncelleme notu"}"""

def guncelleme_taslaklarini_birlestir():
    """aynı yazı için onay bekleyen birden fazla güncelleme taslağını en eskisinde birleştirir; diğerleri "birleştirildi" olur"""
    gruplar = {}
    for f in sorted(os.listdir(TASLAK_DIR)):
        if "-g-" not in f: continue
        try: d = json.load(open(os.path.join(TASLAK_DIR, f), encoding="utf-8"))
        except Exception: continue
        if d.get("tip") == "guncelleme" and d.get("durum") == "bekliyor":
            gruplar.setdefault((d.get("post") or {}).get("slug"), []).append(d)
    n = 0
    for slug, L in gruplar.items():
        if not slug or len(L) < 2: continue
        L.sort(key=lambda d: d["ts"])
        notlar = [d["post"].get("not") or "" for d in L]
        try:
            birlesik = json_ayikla(kucuk_model(BIRLESTIR_SISTEM, "\n\n".join(f"{i + 1}. {x}" for i, x in enumerate(notlar)), 800, timeout=60)).get("not")
        except Exception as e:
            log("güncelleme taslakları birleştirilemedi:", slug, str(e)[:120]); continue
        birlesik = re.sub(r"\s+", " ", str(birlesik or "")).replace("—", ",").strip()
        if len(birlesik) < 20 or yasak_bul(birlesik) or itham_bul(birlesik):
            log("birleşik güncelleme notu denetimden geçmedi, en eski not korunuyor:", slug); birlesik = notlar[0]
        with _taslak_kilit:
            ana = taslak_oku(L[0]["id"])
            digerleri = [taslak_oku(d["id"]) for d in L[1:]]
            if not ana or ana.get("durum") != "bekliyor": continue
            digerleri = [d for d in digerleri if d and d.get("durum") == "bekliyor"]
            if not digerleri: continue
            kaynak = _kaynak_ciftleri(ana["post"].get("kaynak"))
            for d in digerleri:
                for k in _kaynak_ciftleri(d["post"].get("kaynak")):
                    if all(k[1] != x[1] for x in kaynak): kaynak.append(k)
                ana.setdefault("birlesen", []).append({"ts": time.time(), "url": (d.get("tw") or {}).get("url"), "kullanici": (d.get("tw") or {}).get("kullanici"),
                                                       "tid": d["id"], "eski_not": d["post"].get("not")})
                d["durum"] = "birleştirildi"; d["birlesti"] = ana["id"]; taslak_yaz(d)
            ana.setdefault("ilk_not", ana["post"].get("not"))
            ana["post"]["not"] = birlesik; ana["post"]["kaynak"] = kaynak; ana["guncellendi_ts"] = time.time()
            _dzl = duzeltmeleri_temizle([x for t_ in [ana] + digerleri for x in (t_["post"].get("duzeltmeler") or [])])
            if _dzl: ana["post"]["duzeltmeler"] = _dzl
            taslak_yaz(ana)
        n += len(digerleri)
        log(f"güncelleme taslakları birleştirildi: {len(digerleri) + 1} taslak -> {ana['id']} ({slug})")
    return n

def _guncelleme_isle(tw, el, mevcut, konu, t0, zorla, bekleyen_tid=None):
    bekleyen = taslak_oku(bekleyen_tid) if bekleyen_tid else None
    if bekleyen and bekleyen.get("durum") != "bekliyor": bekleyen = None
    if True:
        if True:
            if el.get("tur") in ("iddia", "gazeteci") and not zorla:
                try:
                    ct = capraz_teyit(tw, el)
                    if ct: el["capraz_teyit"] = ct; log("güncelleme için çapraz teyit:", ", ".join("@" + str(k) for k, _, _ in ct))
                except Exception as e: log("çapraz teyit hatası:", repr(e)[:150])
            try:
                g = guncelleme_yaz(tw, el, mevcut, bekleyen_not=(bekleyen or {}).get("post", {}).get("not"))
            except Exception as e:
                log("güncelleme yazım hatası:", e); konu_ekle(konu, "hata", str(e)[:200]); return
            if not g.get("yayinla") or not g.get("not"):
                if g.get("sebep") == "teyit_yok" and not zorla:
                    # yeni gelişme ama henüz teyit yok: yeni haberlerdeki gibi 20 dk ve 1 saat sonra yeniden denenir
                    log("güncelleme teyit bekliyor:", g.get("neden"))
                    ekle_jsonl("bekleyen.jsonl", {"ts": time.time(), "tw": tw, "eleme": el})
                    konu_ekle(konu, "teyit bekliyor", "Güncelleme: " + str(g.get("neden") or "")); return
                log("güncelleme yazılmadı:", g.get("neden")); konu_ekle(konu, "güncelleme yok", g.get("neden")); return
            if yasak_bul(g["not"]) or itham_bul(g["not"]):
                log("güncelleme denetimden geçmedi"); konu_ekle(konu, "denetim", "Güncelleme notunda yasak ya da suçlayıcı ifade var"); return
            _izinli = [x["ad"] for x in (mevcut.get("isimler") or []) if isinstance(x, dict)]
            _yeni_metin = g["not"] + " " + " ".join(d_.get("yeni", "") for d_ in (g.get("duzeltmeler") or []) if isinstance(d_, dict))
            _bul = isim_tespit(_yeni_metin)
            _mk = _katla(html.unescape(re.sub(r"<[^>]+>", " ", mevcut.get("title", "") + " " + mevcut.get("body", ""))))
            if _bul is None or any(_katla(b) not in _mk and not any(_katla(b) in _katla(a) for a in _izinli) for b in _bul):
                log("güncelleme isim denetiminden geçmedi:", _bul); konu_ekle(konu, "denetim", "Güncelleme notunda yazıda olmayan kişi adı"); return
            _uh = usul_hatalari(g["not"] + " " + " ".join(d_.get("yeni", "") for d_ in (g.get("duzeltmeler") or []) if isinstance(d_, dict)))
            if _uh:
                log("güncelleme usul denetiminden geçmedi:", _uh[0]); konu_ekle(konu, "denetim", "Usul hatası: " + _uh[0][:150]); return
            if bekleyen:
                with _taslak_kilit:
                    d = taslak_oku(bekleyen["id"])
                    if d and d.get("durum") == "bekliyor":
                        eski_not = d["post"].get("not")
                        d["post"]["not"] = g["not"]
                        _dzl = duzeltmeleri_temizle(list(d["post"].get("duzeltmeler") or []) + list(g.get("duzeltmeler") or []))
                        if _dzl: d["post"]["duzeltmeler"] = _dzl
                        d["post"]["kaynak"] = _kaynak_ciftleri(d["post"].get("kaynak")) + [k for k in _kaynak_ciftleri(g.get("kaynak"))
                                                                                         if all(k[1] != x[1] for x in _kaynak_ciftleri(d["post"].get("kaynak")))]
                        d.setdefault("birlesen", []).append({"ts": time.time(), "url": tw.get("url"), "kullanici": tw.get("kullanici"), "eski_not": eski_not})
                        d["guncellendi_ts"] = time.time(); taslak_yaz(d)
                        _akis_tl.tid = d["id"]
                        log("bekleyen güncelleme taslağı genişletildi:", d["id"], "<-", tw.get("url"))
                        konu_ekle(konu, "güncelleme onay bekliyor", "Yeni bilgi, onay bekleyen güncelleme taslağına eklendi")
                        bildirim("Güncelleme taslağı genişletildi", f"{mevcut['title']}\n{g['not'][:200]}")
                        return
            tid = taslak_kaydet(tw, el, {"ilk": False}, {"slug": mevcut["slug"], "title": mevcut["title"], "not": g["not"],
                                "kaynak": g.get("kaynak"), "duzeltmeler": duzeltmeleri_temizle(g.get("duzeltmeler")), "cats": mevcut.get("cats", []), "body": mevcut["body"],
                                "ozet": mevcut.get("ozet", []), "kaynaklar": mevcut.get("kaynaklar", [])},
                                int(time.time() - t0), tip="guncelleme")
            if guncelleme_otomatik():
                # güncellemeler bütün denetimlerden geçtiyse editör onayı beklemeden yayına alınır (panelden kapatılabilir: GUNCELLEME_OTOMATIK)
                with _taslak_kilit:
                    _d = taslak_oku(tid); _d["otomatik"] = True; taslak_yaz(_d)
                log("güncelleme otomatik yayına alınıyor:", mevcut["title"])
                konu_ekle(konu, "güncelleme yayında", "Denetimlerden geçti, otomatik yayınlandı")
                onay_isle("yayinla", tid); return
            konu_ekle(konu, "güncelleme onay bekliyor"); taslak_bildir(tid); return

def guncelleme_otomatik():
    return os.environ.get("GUNCELLEME_OTOMATIK", _ENV.get("GUNCELLEME_OTOMATIK", "1")) != "0"

def _yeni_haber_isle(tw, el, konu, t0, zorla):
    import ortak as _o, ortak as _om
    if _o.butce_doldu():
        log(f"günlük bütçe doldu ({_o.bugunku_maliyet():.2f} $), yazılmadı:", konu); konu_ekle(konu, "bütçe", f"Günlük pay doldu ({_o.bugunku_maliyet():.2f} $)")
        if sayac("butce_bildirim") == 0:
            sayac("butce_bildirim", 1)
            bildirim("Günlük bütçe doldu", f"Bugünkü harcama {_o.bugunku_maliyet():.2f} $. Yeni haber yazımı yarın 00:00'a kadar duruyor.")
        return
    if basarisiz_tekrar(konu) and not zorla:
        log("bu konu son 12 saatte iki kez yazılamadı, tekrar denenmiyor:", konu); konu_ekle(konu, "tekrar denenmedi", "Bu konu son 12 saatte iki kez yazılamadı"); return
    try:
        if el.get("tur") == "iddia" and not el.get("guncellenecek") and not zorla:
            ok = on_kontrol(tw, el)
            if ok and ok["zaten_var"]:
                log("ön kontrol: sitede zaten var, yazılmadı:", ok["neden"]); konu_ekle(konu, "zaten var", ok["neden"]); return
            if ok and not ok["teyit"]:
                try: ct = capraz_teyit(tw, el)
                except Exception as e: log("çapraz teyit hatası:", repr(e)[:150]); ct = []
                if ct:
                    el["capraz_teyit"] = ct; ok["teyit"] = True
                    log("çapraz teyit: aynı gelişmeyi bağımsız hesaplar da paylaştı:", ", ".join("@" + str(k) for k, _, _ in ct))
                    _om.maliyet_bilgi(capraz_teyit=", ".join("@" + str(k) for k, _, _ in ct))
            if ok and not ok["teyit"]:
                log("ön kontrol: henüz teyit yok, bekletiliyor:", ok["neden"])
                ekle_jsonl("bekleyen.jsonl", {"ts": time.time(), "tw": tw, "eleme": el})
                konu_ekle(konu, "teyit bekliyor", ok.get("neden")); return
        _m0 = _o.bugunku_maliyet()
        sonuc, gorseller = yaz(tw, el)
        log(f"yazım maliyeti: {_o.bugunku_maliyet() - _m0:.3f} $ ({ENV_YAZIM_MODU}):", konu)
    except Exception as e:
        log("yazım hatası:", e); konu_ekle(konu, "hata", str(e)[:200]); return
    if not sonuc.get("yayinla"):
        log("yazılmadı:", sonuc.get("neden"))
        if el.get("tur") == "iddia" and sonuc.get("teyit") is False:
            ekle_jsonl("bekleyen.jsonl", {"ts": time.time(), "tw": tw, "eleme": el})
            bildirim("Teyit bekleyen gelişme", f"@{tw['kullanici']}: {konu}\n{sonuc.get('neden','')}", tw["url"])
        konu_ekle(konu, "yazılmadı", sonuc.get("neden")); return
    p = sonuc["post"]
    hatalar = denetle(p, tw, gorseller, site_sluglari())
    if hatalar:
        log("denetim başarısız:", hatalar, p.get("title"))
        ekle_jsonl("reddedilen.jsonl", {"ts": time.time(), "tw": tw["url"], "hatalar": hatalar, "post": p})
        konu_ekle(konu, "denetim", "; ".join(hatalar)[:300]); return
    # Haber ve hukuki değerlendirme tek yazıda; geniş kesimi etkileyen hukuki konular (eleme "analiz": true) Analiz bölümünde yer alır
    p["tur"] = "Analiz" if el.get("analiz") else "Haber"
    # Editör onayı: taslak, haber UÇTAN UCA hazır olduktan sonra (başlık + gerçek fotoğraf) kaydedilir ve telefona bildirilir.
    # Kural: taslak fotoğrafsız listeye düşmez; editör "Yayınla" dediğinde haber fotoğrafıyla birlikte doğrudan siteye gider.
    seo_bilgi = None
    try:
        import seo
        if seo.ACIK: seo_bilgi = seo.incele(p, uygula=True, mevcut_sluglar=site_sluglari())
    except Exception as e:
        log("başlık seçimi atlandı:", repr(e)[:150])
    _GORSEL_ISLENIYOR.add(p["slug"])
    sec = {}
    try:
        for _deneme in range(2):   # fotoğraf bulunamazsa bir kez daha (farklı aramalarla) denenir
            try:
                sec = gorsel_sec(p, gorseller) or {}
            except Exception as e:
                log("görsel seçimi hatası:", repr(e)); sec = {}
            if sec.get("foto") or sec.get("gorsel"): break
            log("taslak için uygun fotoğraf bulunamadı, yeniden deneniyor:", p.get("slug"))
    finally:
        _GORSEL_ISLENIYOR.discard(p["slug"])
    p["foto"] = sec.get("foto"); p["gorsel"] = sec.get("gorsel"); p["gorsel_denetim"] = sec.get("denetim")
    tid = taslak_kaydet(tw, el, sonuc, p, int(time.time() - t0))
    with _taslak_kilit:
        _d = taslak_oku(tid)
        if seo_bilgi: _d["seo"] = seo_bilgi
        _d["gorsel_tamam"] = True
        if not (p.get("foto") or p.get("gorsel")):
            _d["hata"] = "Uygun gerçek fotoğraf bulunamadı. Görsel bölümünden fotoğraf seçin; fotoğrafsız haber yayına çıkmaz."
        taslak_yaz(_d)
    log("görsel taslakla birlikte hazır:" if (p.get("foto") or p.get("gorsel")) else "taslak fotoğrafsız (editör seçmeli):", tid)
    konu_ekle(konu, "onay bekliyor", ("Çapraz teyit: aynı gelişmeyi " + ", ".join("@" + str(k) for k, _, _ in el["capraz_teyit"]) + " de paylaştı")
              if el.get("capraz_teyit") else None)
    taslak_bildir(tid)
    # analiz önerisi: kısa haber YAYINLANDIKTAN sonra hazırlanır (bkz. onay_isle)

GENISLETME_SISTEM = """Tarafsız bir hukuk haber sitesinin kıdemli hukuk muhabirisin. Sitede az önce yayımlanan KISA bir haber var.
Bu haberi aynı sayfada genişletecek EK BÖLÜMLER yazacaksın; ayrı bir yazı değil. Önce web_search ile (en fazla 5 arama) mevzuat ve
resmî kaynakları bul.
Ek bölümler haberde OLMAYAN konuları işler: vatandaşın/yatırımcının/kurumun yapması gerekenler, başvuru yolları ve süreler, emsal kararlar
ve uygulama, mevzuatın arka planı, sık karşılaşılacak sorunlar. Haberdeki olguları tekrar etme; ara başlıklar haberdekilerden farklı olsun.
Kurallar: tarafsız, itham yok, masumiyet karinesi; haberde zaten geçmeyen hiçbir kişi adı yazılmaz; doğrulanmamış sayı/madde/ceza yok; başka sitelerin metni yok;
uzun tire yok; "sonuç olarak", "özetle", "bu bağlamda", "dikkat çekici", "kritik", "merakla bekleniyor" yok. Sitedeki ilgili başka bir yazıya
uygunsa 1 doğal iç bağlantı (<a href="/slug/">...</a>) verebilirsin.
Haberin ötesinde gerçekten yeni ve doğrulanmış bilgi katamıyorsan genişletme yapma.
Yalnızca JSON:
{"yayinla": true|false, "neden": "kısa",
 "ekler": "3-4 adet <h2>...</h2><p>...</p> bölümü, toplam 300-650 kelime",
 "sss": [["en fazla 45 karakterlik kısa soru", "1-2 cümle cevap"], ... en fazla 4],
 "kaynaklar": [["kaynak başlığı", "url"], ...]}"""

def genisletme_hazirla(tw, el, haber):
    t0 = time.time()
    hm = html.unescape(re.sub(r"<[^>]+>", " ", haber["body"]))
    mesaj = (f"YAYINDAKİ HABER (/{haber['slug']}/): {haber['title']}\nÖzet: {' '.join(haber.get('ozet', []))}\nMetin: {hm}\n"
             f"Kaynaklar: {haber.get('kaynaklar')}\n\nKonu notu: {el.get('konu','')}\nBugün: {simdi().strftime('%d.%m.%Y')}\n\n"
             f"Sitede son yayımlananlar:\n{site_listesi(40)}")
    try:
        if ENV_YAZIM_MODU == "iki":
            metin, _ = claude(MODEL_YAZIM, GENISLETME_SISTEM, mesaj + NOT_EKI + arastir(mesaj, 5), max_tokens=12000, timeout=400)
        else:
            metin, _ = claude(MODEL_YAZIM, GENISLETME_SISTEM, mesaj, max_tokens=12000,
                              araclar=[{"type": WEB_ARAMA_ARACI, "name": "web_search", "max_uses": 5}], timeout=400)
        g = json_ayikla(metin)
    except Exception as e:
        log("genişletme yazım hatası:", e); return
    if not g.get("yayinla") or not g.get("ekler"):
        log("genişletme yapılmadı:", g.get("neden")); return
    ekler = g["ekler"].replace("—", ",")
    hatalar = []
    kelime = len(re.sub(r"<[^>]+>", " ", ekler).split())
    if ekler.count("<h2>") < 2 or not 200 <= kelime <= 900: hatalar.append(f"yapı/kelime {kelime}")
    ekler = dolgu_temizle(ekler)
    for y_ in yasak_bul(ekler): hatalar.append("yasak ifade: " + y_)
    if itham_bul(ekler): hatalar.append("suçlayıcı ifade")
    _bul = isim_tespit(ekler); _mk = _katla(html.unescape(re.sub(r"<[^>]+>", " ", haber.get("title", "") + " " + haber["body"])))
    if _bul is None or any(_katla(b) not in _mk for b in _bul): hatalar.append("haberde olmayan kişi adı")
    from difflib import SequenceMatcher
    def cumleler(b): return [s.strip() for s in re.split(r"[.!?]", html.unescape(re.sub(r"<[^>]+>", " ", b))) if len(s.split()) > 6]
    hc, ec = cumleler(haber["body"]), cumleler(ekler)
    benzer = sum(1 for x in ec if hc and max(SequenceMatcher(None, x, y2).ratio() for y2 in hc) > 0.6)
    if ec and benzer / len(ec) > 0.2: hatalar.append(f"haberle çok benzer ({benzer}/{len(ec)} cümle)")
    if hatalar:
        log("genişletme denetimi başarısız:", hatalar); ekle_jsonl("reddedilen.jsonl", {"ts": time.time(), "hatalar": hatalar, "ekler": ekler}); return
    sss = [[q, c] for q, c in sss_duzelt(g.get("sss")) if len(q) <= 45][:4]
    kay = [k for k in (g.get("kaynaklar") or []) if isinstance(k, list) and len(k) == 2 and str(k[1]).startswith("http")]
    tid = taslak_kaydet(tw, el, {"ilk": False}, {"slug": haber["slug"], "title": haber["title"], "body": haber["body"],
                        "ozet": haber.get("ozet", []), "cats": haber.get("cats", []), "kaynaklar": haber.get("kaynaklar", []),
                        "foto": haber.get("foto"), "gorsel": haber.get("gorsel"), "ekler": ekler, "sss": sss, "ek_kaynaklar": kay},
                        int(time.time() - t0), tip="genisletme")
    taslak_bildir(tid)

def genisletme_uygula(slug, ekler, sss, ek_kaynaklar):
    n = simdi()
    def degistir(p):
        p["body"] = p["body"] + ekler
        if sss: p["sss"] = sss
        mevcut = {k[1] for k in p.get("kaynaklar", [])}
        p["kaynaklar"] = list(p.get("kaynaklar", [])) + [k for k in ek_kaynaklar if k[1] not in mevcut]
        p["updated"] = n.strftime("%Y-%m-%dT%H:%M")
        _y = len([k for k in ek_kaynaklar if k[1] not in mevcut])
        p["gecmis"] = list(p.get("gecmis", [])) + [{"tarih": p["updated"], "tur": "Genişletme",
                       "not": "Habere yeni bölümler eklendi" + (" ve sık sorulan sorular güncellendi" if sss else "") + (f"; {_y} yeni kaynak eklendi" if _y else "") + "."}]
        return p
    sakla = {}
    def hazirla():
        sakla["eski"] = _post_degistir(slug, degistir)
    _gonder("Haber genişletildi: " + slug, hazirla)
    return sakla.get("eski")

# ------------------------------------------------------------------ editör onayı
TASLAK_DIR = os.path.join(VERI, "taslak")
os.makedirs(TASLAK_DIR, exist_ok=True)
_taslak_kilit = threading.Lock()

def taslak_kaydet(tw, el, sonuc, p, yazim_sn, tip="haber"):
    tid = simdi().strftime("%m%d%H%M%S") + "-" + {"haber": "", "analiz": "a-", "guncelleme": "g-", "genisletme": "e-"}[tip] + p["slug"][:20]
    d = {"id": tid, "tip": tip, "ts": time.time(), "durum": "bekliyor", "tw": tw, "eleme": el, "ilk": sonuc.get("ilk"),
         "diger_siteler": sonuc.get("diger_siteler"), "tek_kaynak": bool(sonuc.get("tek_kaynak")), "post": p, "yazim_sn": yazim_sn}
    if tw.get("olay_tarihi") and tip == "haber":   # eski tarihli (ek mesai geçmiş taraması): olay tarihiyle yayımlanır, X'te paylaşılmaz
        p["olay_tarihi"] = tw["olay_tarihi"]; d["x_paylas"] = False
    try:
        import ortak as _om
        if not _om.maliyet_is_id(): _om.maliyet_is_baslat(kaynak=tw.get("url"))
        d["maliyet_is"] = _om.maliyet_is_id()
        _om.maliyet_bilgi(tid=tid, slug=p.get("slug"), baslik=p.get("title"), tip=tip, sonuc="taslak")
    except Exception as e:
        log("maliyet bağlantısı yazılamadı:", e)
    json.dump(d, open(os.path.join(TASLAK_DIR, tid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _akis_tl.tid = tid
    log(f"TASLAK HAZIR ({yazim_sn} sn): {p['title']} [{tid}]")
    return tid

def taslak_oku(tid):
    p = os.path.join(TASLAK_DIR, os.path.basename(tid) + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def taslak_yaz(d):
    json.dump(d, open(os.path.join(TASLAK_DIR, d["id"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def taslak_gorseli(p):
    """(görsel adresi, düz metin kredi)"""
    foto = p.get("foto")
    if foto:
        if foto.get("kaynak"): return foto["url"], f"Fotoğraf: {foto['artist']} / {foto['kaynak']}" + (f", {foto['lic']}" if foto.get("lic", "").startswith("CC") else "")
        return foto["url"], f"Fotoğraf: {foto['artist']} / Wikimedia Commons, {foto['lic']}"
    if p.get("gorsel"):
        return f"{SITE}/gorsel/{p['gorsel']}.jpg", "Arşiv fotoğrafı"
    return None, "Yazılı kapak (uygun fotoğraf bulunamadı)"

_KAPAK_ONBELLEK = {}
def yazili_kapak_uri(p):
    """sitede görselsiz haberler için üretilen yazılı kapağın önizleme kopyası (data URI)"""
    import base64
    anah = (p["title"], tuple(p.get("cats", [])))
    if anah not in _KAPAK_ONBELLEK:
        try:
            im = runpy.run_path(os.path.join(SITE_DEPO, "images.py"))["typographic"](p["title"], "manset", (p.get("cats") or ["Hukuki Haberler"])[0])
            b = io.BytesIO(); im.resize((800, 420)).save(b, "JPEG", quality=80)
            _KAPAK_ONBELLEK.clear(); _KAPAK_ONBELLEK[anah] = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        except Exception as e:
            log("yazılı kapak üretilemedi:", e); return f"{SITE}/gorsel/kapak.jpg"
    return _KAPAK_ONBELLEK[anah]

_CSS_ONBELLEK = {}
def _site_css():
    yol = os.path.join(SITE_DEPO, "tema.py")
    try:
        m = os.path.getmtime(yol)
        if _CSS_ONBELLEK.get("m") != m:
            _CSS_ONBELLEK.update(m=m, css=runpy.run_path(yol)["CSS"])
        return _CSS_ONBELLEK["css"]
    except Exception:
        return ""

def onizleme_html(d, butonsuz=False):
    """taslağı sitedeki haber sayfası görünümünde tek dosyalık HTML'e çevirir (Yayınla/Reddet düğmeleriyle;
    butonsuz=True ise düğmeler uygulamada yerli olarak çizildiği için sayfaya konmaz)"""
    from ortak import NTFY_ONAY as onay_konu
    p, tw, tid = d["post"], d["tw"], d.get("id", "")
    css = _site_css()
    e = html.escape
    img, kredi = taslak_gorseli(p)
    img = img or yazili_kapak_uri(p)
    kredi = e(kredi)
    ozet = "".join(f"<li>{e(x)}</li>" for x in p.get("ozet", []))
    tip = d.get("tip", "haber")
    kaynaklar = list(p.get("kaynaklar", []))
    govde = p["body"]
    if tip == "guncelleme":
        n = simdi()
        ek = (f'<p style="background:#fff3cd;color:#5c4400;padding:8px 10px;border-radius:6px"><b>Güncelleme ({n.day} {_ay(n.month)} '
              f'{n.year}, {n.strftime("%H.%M")}):</b> {e(p.get("not", ""))}</p>')
        i = govde.find("</p>"); govde = govde[:i + 4] + ek + govde[i + 4:] if i >= 0 else ek + govde
        kaynaklar += _kaynak_ciftleri(p.get("kaynak"))
    if tip == "genisletme":
        govde = govde + ('<div style="border-left:5px solid #f1d293;padding-left:14px;margin-top:18px">'
                         '<p style="color:#f1d293;font:700 13px system-ui;letter-spacing:.06em">EKLENECEK BÖLÜMLER</p>' + p.get("ekler", "") + '</div>')
        kaynaklar += p.get("ek_kaynaklar", [])
    sss = "".join(f'<div class="sq"><h3>{e(q)}</h3><p>{e(c)}</p></div>' for q, c in sss_duzelt(p.get("sss")))
    if sss: sss = f'<section class="sss"><h2>Merak edilenler</h2>{sss}</section>'
    kay = " · ".join(f'<a href="{e(u)}">{e(t)}</a>' for t, u in _kaynak_ciftleri(kaynaklar))
    ilk = {"guncelleme": "MEVCUT HABERE GÜNCELLEME ÖNERİSİ", "analiz": "ANALİZ ÖNERİSİ",
           "genisletme": "YAYINDAKİ HABERİ GENİŞLETME ÖNERİSİ (sarı çizgili bölümler eklenecek)"}.get(tip) or (
        "İLK: başka sitede yok" if d.get("ilk") else f"{len(d.get('diger_siteler') or [])} sitede var")
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Önizleme: {e(p['title'])}</title><style>{css}
.onz{{background:#fff3cd;color:#5c4400;padding:10px 14px;font:600 14px/1.4 system-ui;border-radius:6px;margin:12px 0}}</style></head>
<body><main class="wrap" style="max-width:820px;margin:0 auto;padding:0 16px">
<div class="onz">ÖNİZLEME (henüz yayında değil) · {e(', '.join(p.get('cats', [])))} · kaynak: @{e(tw['kullanici'])} {e(tw['saat'])} · {ilk}</div>
{('<div style="background:#5c1f1f;color:#ffd7d7;padding:10px 14px;border-radius:6px;margin:12px 0;font:600 14px/1.4 system-ui">'
      'TEK KAYNAK: Bu bilgi yalnızca @' + e(tw['kullanici']) + ' paylaşımına dayanıyor, henüz resmî ya da ikinci bir kaynakla teyit edilmedi.</div>') if d.get('tek_kaynak') else ''}
<article class="post"><h1>{e(p['title'])}</h1>
<div class="meta pmeta"><span class="tur">Haber</span><span>Hukuki Haberler Editörlüğü</span></div>
<figure class="hero-img"><div class="pic"><img src="{e(img)}" alt="" style="width:100%;height:auto"></div><figcaption class="credit">{kredi}</figcaption></figure>
<aside class="ozet"><b>Öne çıkanlar</b><ul>{ozet}</ul></aside>
<div class="body">{govde}</div>{sss}<p class="kaynak"><b>Kaynak:</b> {kay}</p></article>
{"</main></body></html>" if butonsuz else ""}<style>
.kd{{display:flex;gap:10px;position:sticky;bottom:0;padding:12px 0;background:var(--bg,#1d2a37)}}
.kd button{{flex:1;height:54px;border:0;border-radius:8px;color:#fff;font:700 18px system-ui;display:flex;align-items:center;justify-content:center;gap:10px;transition:opacity .2s}}
#by{{background:#1f9d55}} #br{{background:#c53030}} .kd button:disabled{{opacity:.45}} .kd button.aktif{{opacity:1}}
.don{{width:18px;height:18px;border:3px solid rgba(255,255,255,.35);border-top-color:#fff;border-radius:50%;animation:d 0.8s linear infinite}}
@keyframes d{{to{{transform:rotate(360deg)}}}}
#sonuc{{font:600 15px system-ui;text-align:center;margin:6px 0 18px}} #sonuc a{{color:#f1d293}}
</style>
<div class="kd"><button id="by" onclick="karar('yayinla')">Yayınla</button><button id="br" onclick="karar('reddet')">Reddet</button></div>
<p id="sonuc"></p></main>
<script>
var by=document.getElementById('by'), br=document.getElementById('br'), s=document.getElementById('sonuc'), zam=null;
var durumAdresi=location.pathname.slice(0,-5)+'.json';
function kilit(b,metin,donen){{by.disabled=br.disabled=true;b.classList.add('aktif');b.innerHTML=(donen?'<span class="don"></span>':'')+metin;}}
function ac(){{by.disabled=br.disabled=false;by.classList.remove('aktif');br.classList.remove('aktif');by.textContent='Yayınla';br.textContent='Reddet';}}
function goster(d){{
  var t=d.durum||'';
  if(t=='yayınlandı'){{kilit(by,'✓ Yayınlandı');by.style.background='#1f9d55';
     s.innerHTML=d.url?'Haber yayında: <a href="'+d.url+'">'+d.url.replace('https://','')+'</a><br>Sitede görünmesi 1-3 dakika sürebilir.':'';return true;}}
  if(t=='yayınlanıyor'){{kilit(by,'Yayınlanıyor…',true);s.textContent='Site güncelleniyor, lütfen bekleyin.';return false;}}
  if(t=='reddedildi'||t=='geri alındı'){{kilit(br,'✗ Reddedildi');s.textContent='';return true;}}
  if(t=='yayından kaldırıldı'){{kilit(br,'✗ Yayından kaldırıldı');s.textContent='';return true;}}
  if(t=='kaldırılıyor'){{kilit(br,'Kaldırılıyor…',true);return false;}}
  return null;
}}
function izle(beklenen){{
  clearInterval(zam); var sayac=0;
  zam=setInterval(function(){{
    sayac++;
    fetch(durumAdresi+'?t='+Date.now()).then(function(r){{return r.json()}}).then(function(d){{
      var bitti=goster(d);
      if(bitti===true) clearInterval(zam);
      else if(bitti===null && sayac>4 && d.hata){{clearInterval(zam);ac();s.innerHTML='<span style="color:#ff8a8a">Hata: '+d.hata+'</span>';}}
      else if(sayac>90){{clearInterval(zam);s.textContent='Uzun sürdü; sonucu "Yayın Durumu" kanalından kontrol edin.';}}
    }}).catch(function(){{}});
  }},2000);
}}
function karar(k){{
  if(k=='yayinla') kilit(by,'Yayınlanıyor…',true); else kilit(br,'Reddediliyor…',true);
  s.textContent='Gönderiliyor…';
  fetch('https://ntfy.sh/{onay_konu}',{{method:'POST',body:k+' {tid}'}})
   .then(function(r){{ if(!r.ok) throw new Error(r.status); s.textContent=k=='yayinla'?'Site güncelleniyor, lütfen bekleyin.':''; izle(k); }})
   .catch(function(e){{ac();s.innerHTML='<span style="color:#ff8a8a">Gönderilemedi: '+e.message+'</span>';}});
}}
fetch(durumAdresi+'?t='+Date.now()).then(function(r){{return r.json()}}).then(function(d){{var b=goster(d); if(b===false) izle();}}).catch(function(){{}});
</script></body></html>"""
    if butonsuz:
        sayfa = sayfa[:sayfa.index("</main></body></html>") + len("</main></body></html>")]
        sayfa = sayfa.replace("</style></head>", ".onz{display:none}main.wrap{padding-bottom:150px!important}</style></head>", 1)
    return sayfa

ONIZLEME_DIR = os.path.join(VERI, "onizleme")
os.makedirs(ONIZLEME_DIR, exist_ok=True)

def onizleme_kaydet(icerik, tid=""):
    """önizlemeyi tahmin edilemeyen adla kaydeder, adresini döndürür"""
    from ortak import ONIZLEME_ADRES
    if not ONIZLEME_ADRES: return None
    ad = os.urandom(16).hex() + ".html"
    open(os.path.join(ONIZLEME_DIR, ad), "w", encoding="utf-8").write(icerik)
    open(os.path.join(ONIZLEME_DIR, ad[:-5] + ".tid"), "w").write(tid)
    return ONIZLEME_ADRES.rstrip("/") + "/" + ad

def panel_anahtar():
    from ortak import ENV
    if ENV.get("PANEL_ANAHTAR"): return ENV["PANEL_ANAHTAR"]
    p = os.path.join(VERI, "panel_anahtar.txt")
    if not os.path.exists(p): open(p, "w").write(os.urandom(12).hex())
    return open(p).read().strip()

def panel_adresi():
    from ortak import ONIZLEME_ADRES
    return ONIZLEME_ADRES.rstrip("/") + "/panel-" + panel_anahtar() if ONIZLEME_ADRES else None

def panel_verisi(gun=7):
    sinir = time.time() - gun * 86400
    out = []
    for f in os.listdir(TASLAK_DIR):
        if not f.endswith(".json"): continue
        try:
            d = json.load(open(os.path.join(TASLAK_DIR, f), encoding="utf-8"))
        except Exception:
            continue
        if d.get("ts", 0) < sinir: continue
        out.append({"id": d["id"], "tip": d.get("tip", "haber"), "durum": d.get("durum"), "baslik": d["post"]["title"],
                    "kat": ", ".join(d["post"].get("cats", [])), "kaynak": d["tw"].get("kullanici", ""),
                    "saat": time.strftime("%d.%m %H:%M", time.localtime(d["ts"] + 0)), "ts": d["ts"], "url": d.get("url"),
                    "ilk": d.get("ilk"), "hata": d.get("hata")})
    return sorted(out, key=lambda x: -x["ts"])


# ------------------------------------------------------------------ iOS editör uygulaması için JSON API
BEKLEYEN_DURUMLAR = ("bekliyor", "yayınlanıyor", "kaldırılıyor")

_YZ_ONB = {}
def _yazarlar_verisi():
    p = os.path.join(SITE_DEPO, "yazarlar.json")
    try: mt = os.path.getmtime(p)
    except OSError: return {}
    if _YZ_ONB.get("mt") != mt: _YZ_ONB.update(mt=mt, d=json.load(open(p, encoding="utf-8")))
    return _YZ_ONB["d"]

def editorler():
    """inceleme yapan avukatlar (yazarlar.json "inceleme" eşlemesindekiler): [{kod, ad, alan}]"""
    d = _yazarlar_verisi(); kodlar = set((d.get("inceleme") or {}).values())
    def foto(y):   # sitedeki küçük (128 px) fotoğraf
        f = y.get("foto") or "/yazar/" + str(y.get("adres") or y["kod"]) + ".jpg"
        f = re.sub(r"^(/yazar/[^/]+)\.jpg$", r"\1-k.jpg", f)
        return f if f.startswith("http") else SITE + f
    return [{"kod": y["kod"], "ad": (str(y.get("unvan") or "") + " " + y["kisi"]).strip(), "alan": y.get("alan") or "", "foto": foto(y)}
            for y in d.get("yazarlar", []) if y.get("kod") in kodlar]

_IK_ONB = {}
def otomatik_editor(p):
    """sitenin inceleme kuralına göre (inceleme_kurali.py, build.py ile aynı) taslağın inceleyecek avukatı; yoksa None"""
    yol = os.path.join(SITE_DEPO, "inceleme_kurali.py")
    try:
        mt = os.path.getmtime(yol)
        if _IK_ONB.get("mt") != mt: _IK_ONB.update(mt=mt, m=runpy.run_path(yol))
        g = _IK_ONB["m"]["grup"](p.get("title", ""), p.get("tags", []), [])
    except Exception as e:
        log("inceleme kuralı okunamadı:", repr(e)[:120]); return None
    return (_yazarlar_verisi().get("inceleme") or {}).get(g) if g else None

def _editor_bilgisi(p):
    oto = otomatik_editor(p); kod = p.get("denetleyen") or oto
    ad = next((e["ad"] for e in editorler() if e["kod"] == kod), None) if kod else None
    return {"editor": kod if ad else None, "editor_ad": ad, "editor_otomatik": oto, "editor_secildi": bool(p.get("denetleyen")),
            "incelendi": bool(p.get("incelendi"))}

def onhazir_gecerli(tid, p, taban=None):
    k = _ONHAZIR.get(tid)
    return bool(k and k["taban"] == (taban or _depo_tabani()) and k["imza"] == _onhazir_imza(p) and k["gun"] == simdi().strftime("%Y-%m-%d"))

def _uygulama_ogesi(d, taban=None):
    p, tw = d["post"], d["tw"]
    img, _ = taslak_gorseli(p)
    durum = d.get("durum")
    if durum == "yayınlandı" and d.get("canli") is False and time.time() - (d.get("yayin_ts") or 0) < 900: durum = "yayınlanıyor"   # sitede açılana kadar
    return {"id": d["id"], "tip": d.get("tip", "haber"), "durum": durum, "baslik": p["title"],
            "kat": ", ".join(p.get("cats", [])), "kaynak": tw.get("kullanici", ""), "kaynak_ad": tw.get("ad", ""),
            "ts": d["ts"], "url": d.get("url"), "ilk": bool(d.get("ilk")), "hata": d.get("hata"), "gorsel_bekleniyor": bool(d.get("gorsel_bekleniyor")),
            "gorsel": ((p.get("foto") or {}).get("kucuk") or commons_kucuk_url(img, 330)) if img else
                      (f"{SITE}/gorsel/m/{p.get('slug')}.jpg" if d.get("tip") in ("guncelleme", "genisletme") and p.get("slug") else None), "not": p.get("not") if d.get("tip") == "guncelleme" else None, "duzeltmeler": p.get("duzeltmeler") if d.get("tip") == "guncelleme" else None, "olay_tarihi": p.get("olay_tarihi"),
            "birlesen": len(d.get("birlesen") or []), "karar_ts": d.get("karar_ts"), "gorsel_puan": (p.get("gorsel_denetim") or {}).get("puan"),
            "gorsel_kaynak": (p.get("gorsel_denetim") or {}).get("kaynak"),
            **(_editor_bilgisi(p) if d.get("tip", "haber") == "haber" else {}),
            "hazir": onhazir_gecerli(d["id"], p, taban) if d.get("durum") == "bekliyor" and d.get("tip", "haber") == "haber" else False}

def uygulama_listesi(gun=10):
    sinir = time.time() - gun * 86400
    out = []; taban = _depo_tabani()
    for f in os.listdir(TASLAK_DIR):
        if not f.endswith(".json"): continue
        try:
            d = json.load(open(os.path.join(TASLAK_DIR, f), encoding="utf-8"))
        except Exception:
            continue
        if d.get("ts", 0) < sinir and d.get("durum") not in BEKLEYEN_DURUMLAR: continue
        out.append(_uygulama_ogesi(d, taban))
    return sorted(out, key=lambda x: -x["ts"])

def son_yayin_suresi():
    """son yayımlanan haberin onaydan canlıya süresi (sn)"""
    en = None
    for f in sorted(os.listdir(TASLAK_DIR), reverse=True)[:80]:
        if not f.endswith(".json"): continue
        try: d = json.load(open(os.path.join(TASLAK_DIR, f), encoding="utf-8"))
        except Exception: continue
        if d.get("canli_ts") and d.get("karar_ts") and d.get("tip", "haber") == "haber" and (not en or d["canli_ts"] > en[0]):
            en = (d["canli_ts"], d["canli_ts"] - d["karar_ts"])
    return round(en[1]) if en else None

def editor_sec(tid, kod):
    """editör uygulamasından inceleyen avukat seçimi: seçilen avukat haberi incelemiş sayılır (sitede "Hukuki inceleme" kartı)"""
    if kod not in {e["kod"] for e in editorler()}: return 422, {"hata": "Geçersiz editör"}
    with _taslak_kilit:
        d = taslak_oku(tid)
        if not d: return 404, {"hata": "Taslak bulunamadı"}
        if d.get("durum") != "bekliyor" or d.get("tip", "haber") != "haber":
            return 409, {"hata": "Editör yalnızca onay bekleyen haberde seçilebilir", "oge": _uygulama_ogesi(d)}
        d["post"]["denetleyen"] = kod; d["post"]["incelendi"] = simdi().strftime("%Y-%m-%d")
        taslak_yaz(d)
    log("editör seçildi:", kod, tid)
    _ONHAZIR_UYAN.set()
    return 200, {"oge": _uygulama_ogesi(taslak_oku(tid))}

def uygulama_detay(d):
    p, tw = d["post"], d["tw"]
    o = _uygulama_ogesi(d)
    _, kredi = taslak_gorseli(p)
    govde = re.sub(r"<[^>]+>", " ", p.get("body", ""))
    o.update({"ozet": p.get("ozet", []), "kredi": kredi, "kelime": len(govde.split()),
              "kaynaklar": [{"ad": t, "url": u} for t, u in p.get("kaynaklar", [])],
              "tweet_metin": (tw.get("metin") or "")[:1500], "tweet_url": tw.get("url"), "saat": tw.get("saat"),
              "diger_siteler": len(d.get("diger_siteler") or []), "sss": len(p.get("sss") or []),
              "slug": p.get("slug"), "gorsel_denetim": p.get("gorsel_denetim"), "seo": d.get("seo"),
              "gorsel_buyuk": commons_kucuk_url(taslak_gorseli(p)[0], 960) if taslak_gorseli(p)[0] else None})
    return o

def gorsel_adaylari(tid, sorgu=None):
    """editörün seçebileceği Commons fotoğrafları (taslağa önbelleğe alınır; seçim sıra numarasıyla yapılır)"""
    d = taslak_oku(tid)
    p = d["post"]
    aramalar = [sorgu] if sorgu else (p.get("gorsel_aramalari") or [p["title"]])
    adaylar = (openverse_adaylar(aramalar, azami=10) + pixabay_adaylar(aramalar, azami=6) + pexels_adaylar(aramalar, azami=6)
               + commons_adaylar(aramalar, azami=10))
    with _taslak_kilit:
        d = taslak_oku(tid); d["gorsel_adaylari"] = adaylar; taslak_yaz(d)
    return [{"no": i, "kucuk": a.get("kucuk") or commons_kucuk_url(a["url"], 500),
             "baslik": a["title"].split(": ", 1)[-1][:80] if a.get("kaynak") else a["title"].replace("File:", "").rsplit(".", 1)[0],
             "lisans": a["lic"] + " · " + (a.get("kaynak") or "Commons"), "yazar": a["artist"][:60]}
            for i, a in enumerate(adaylar)]

def gorsel_degistir(tid, secim):
    """secim: aday sıra numarası | 'yok' (yazılı kapak) | 'otomatik' (denetimli yeniden seçim); (tamam, mesaj)"""
    d = taslak_oku(tid)
    if not d: return False, "Taslak bulunamadı"
    if d.get("durum") != "bekliyor": return False, "Yalnızca bekleyen taslağın görseli değiştirilebilir"
    if secim == "otomatik":
        dn = gorsel_yenile(tid)
        return True, ("Yeni görsel seçildi" if dn and dn.get("puan") else "Uygun fotoğraf yok, yazılı kapak kullanılacak")
    with _taslak_kilit:
        d = taslak_oku(tid); p = d["post"]
        if secim == "yok":
            p["foto"] = None; p["gorsel"] = None
            p["gorsel_denetim"] = {"puan": 0, "goruluyor": "yazılı kapak", "neden": "Editör yazılı kapağı seçti", "kaynak": "editör"}
        else:
            try: a = (d.get("gorsel_adaylari") or [])[int(secim)]
            except Exception: return False, "Aday bulunamadı, listeyi yenileyin"
            p["foto"] = a; p["gorsel"] = None
            p["gorsel_denetim"] = {"puan": None, "goruluyor": a["title"].replace("File:", ""), "neden": "Editör seçti", "kaynak": "editör"}
        if str(d.get("hata") or "").startswith("Uygun gerçek fotoğraf bulunamadı"): d.pop("hata", None)
        taslak_yaz(d)
    log("GÖRSEL DEĞİŞTİ (uygulama):", d["post"]["title"], "->", secim)
    return True, "Görsel değiştirildi"

def taslak_duzenle(tid, veri):
    """bekleyen taslağın başlığını, öne çıkanlarını ya da güncelleme notunu değiştirir; (tamam, mesaj)"""
    with _taslak_kilit:
        d = taslak_oku(tid)
        if not d: return False, "Taslak bulunamadı"
        if d.get("durum") != "bekliyor": return False, f"Bu taslak artık düzenlenemez ({d.get('durum')})"
        p = d["post"]
        if "baslik" in veri and d.get("tip") == "haber":
            b = re.sub(r"\s+", " ", str(veri["baslik"])).strip()
            if not 15 <= len(b) <= 75: return False, f"Başlık 15-75 karakter olmalı (şu an {len(b)})"
            p["title"] = b
        if "ozet" in veri:
            oz = [re.sub(r"\s+", " ", str(x)).strip() for x in (veri["ozet"] or [])]
            oz = [x for x in oz if x][:6]
            if not oz: return False, "En az bir öne çıkan madde olmalı"
            if any(len(x) > 300 for x in oz): return False, "Öne çıkan maddeler en fazla 300 karakter olabilir"
            p["ozet"] = oz
        if "etiketler" in veri and d.get("tip") == "haber":
            et = []
            for t in (veri["etiketler"] or []):
                t = re.sub(r"\s+", " ", str(t)).strip()[:60]
                if t and t.lower() not in [x.lower() for x in et]: et.append(t)
            if not 2 <= len(et) <= 8: return False, "2-8 etiket olmalı"
            p["tags"] = et
        if "not" in veri and d.get("tip") == "guncelleme":
            n = re.sub(r"\s+", " ", str(veri["not"])).strip()
            if not 20 <= len(n) <= 700: return False, "Güncelleme notu 20-700 karakter olmalı"
            p["not"] = n
        d["duzenlendi"] = time.time(); taslak_yaz(d)
        log("TASLAK DÜZENLENDİ (uygulama):", p["title"])
        return True, "Kaydedildi"

def uygulama_karar(tid, komut):
    """kararı arka planda işletir; durum değişene kadar en fazla ~1,5 sn bekleyip güncel kaydı döndürür"""
    d = taslak_oku(tid)
    if not d: return 404, {"hata": "Taslak bulunamadı"}
    dr = d.get("durum")
    if d.get("deneme") and komut == "yayinla":
        return 409, {"hata": "Bu bir deneme taslağı, yayınlanamaz. Reddet ile kaldırabilirsiniz.", "oge": _uygulama_ogesi(d)}
    gecerli = {"yayinla": dr == "bekliyor",
               "reddet": dr == "bekliyor" or dr == "yayınlandı",
               "geriyukle": dr == "reddedildi"}.get(komut)
    if gecerli is None: return 400, {"hata": "Bilinmeyen komut"}
    if not gecerli: return 409, {"hata": f"Bu taslak şu an '{dr}' durumunda; işlem yapılamaz", "oge": _uygulama_ogesi(d)}
    log("uygulama kararı:", komut, tid)
    threading.Thread(target=_karar_isci, args=(komut, tid), daemon=True).start()
    for _ in range(15):
        time.sleep(0.1)
        y = taslak_oku(tid)
        if y and y.get("durum") != dr: return 202, {"oge": _uygulama_ogesi(y)}
    return 202, {"oge": _uygulama_ogesi(taslak_oku(tid))}

def _karar_isci(komut, tid):
    try:
        onay_isle(komut, tid)
        d = taslak_oku(tid)
        if d and komut != "geriyukle":
            d["karar_ts"] = time.time(); taslak_yaz(d)
    except Exception as e:
        log("uygulama kararı hatası:", repr(e))

def uygulama_kur_bildir():
    """telefona tek dokunuşla uygulamayı ayarlayan bağlantıyı ntfy ile gönderir"""
    from ortak import ONIZLEME_ADRES, NTFY_KONU, ntfy_json
    if not ONIZLEME_ADRES: print("ONIZLEME_ADRES tanımlı değil"); return
    kur = ONIZLEME_ADRES.rstrip("/") + "/kur?" + urllib.parse.urlencode({"adres": ONIZLEME_ADRES.rstrip("/"), "anahtar": panel_anahtar()})
    ntfy_json(NTFY_KONU, "HH Editör kurulumu", "iPhone'da HH Editör yüklüyse bu bildirime dokunun; sunucu adresi ve anahtar kendiliğinden girilir.",
              [{"action": "view", "label": "Uygulamayı ayarla", "url": kur}], tikla=kur)
    print("kurulum bildirimi gönderildi")

def panel_html():
    from ortak import NTFY_ONAY
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><meta name="apple-mobile-web-app-capable" content="yes"><title>Taslaklar · Hukuki Haberler</title>
<style>
body{margin:0;background:#1d2a37;color:#e9eef3;font:15px/1.45 system-ui,-apple-system,sans-serif}
header{position:sticky;top:0;background:#22303f;padding:14px 16px;border-bottom:1px solid #34475a;display:flex;justify-content:space-between;align-items:center;z-index:2}
header b{font-size:18px} header small{color:#9fb0c0}
.flt{display:flex;gap:6px;padding:10px 16px;overflow-x:auto} .flt button{background:#2c3e50;color:#cfd8e1;border:0;border-radius:16px;padding:6px 12px;font:600 13px system-ui;white-space:nowrap}
.flt button.on{background:#f1d293;color:#22303f}
.k{margin:10px 16px;background:#26374a;border-radius:10px;padding:12px 14px;border-left:5px solid #f1d293}
.k.yayınlandı{border-color:#1f9d55} .k.reddedildi,.k.geri{border-color:#6b7785;opacity:.75} .k.yayınlanıyor{border-color:#3b82f6}
.u{display:flex;gap:8px;align-items:center;font-size:12.5px;color:#9fb0c0;flex-wrap:wrap}
.r{font:700 11.5px system-ui;padding:3px 8px;border-radius:10px;letter-spacing:.03em}
.r.bekliyor{background:#f1d293;color:#3b2f00} .r.yayınlandı{background:#1f9d55;color:#fff} .r.reddedildi,.r.diger{background:#6b7785;color:#fff}
.r.yayınlanıyor{background:#3b82f6;color:#fff}
.t{display:block;color:#fff;font:700 16px/1.35 Georgia,serif;margin:6px 0 8px;text-decoration:none}
.d{display:flex;gap:8px} .d button{flex:1;height:40px;border:0;border-radius:7px;color:#fff;font:700 15px system-ui}
.y{background:#1f9d55} .x{background:#c53030} .d a{color:#f1d293;font-weight:600}
.bos{padding:40px 16px;text-align:center;color:#9fb0c0}
</style></head><body>
<header><b>Taslaklar</b><small id="zaman"></small></header>
<div class="flt"><button data-f="hepsi" class="on">Hepsi</button><button data-f="bekliyor">Bekleyen</button><button data-f="yayınlandı">Yayınlanan</button><button data-f="reddedildi">Reddedilen</button></div>
<div id="liste"><p class="bos">Yükleniyor…</p></div>
<script>
var filtre='hepsi', ONAY='__ONAY__', islemde={};
var TIP={haber:'Haber',guncelleme:'Güncelleme',genisletme:'Genişletme',analiz:'Analiz'};
var ETIKET={'bekliyor':'BEKLİYOR','yayınlandı':'YAYINLANDI','yayınlanıyor':'YAYINLANIYOR…','reddedildi':'REDDEDİLDİ','geri alındı':'GERİ ALINDI','yayından kaldırıldı':'KALDIRILDI','kaldırılıyor':'KALDIRILIYOR…','zaten var':'ZATEN VAR'};
function esc(s){return String(s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ciz(v){
  var L=v.filter(function(x){return filtre=='hepsi'||x.durum==filtre||(filtre=='reddedildi'&&/red|geri|kald/.test(x.durum))});
  if(!L.length){document.getElementById('liste').innerHTML='<p class="bos">Bu listede taslak yok.</p>';return;}
  document.getElementById('liste').innerHTML=L.map(function(x){
    var dr=islemde[x.id]&&x.durum=='bekliyor'?'yayınlanıyor':x.durum;
    var sinif=['bekliyor','yayınlandı','yayınlanıyor','reddedildi'].indexOf(dr)>=0?dr:'diger';
    var alt='';
    if(dr=='bekliyor') alt='<div class="d"><button class="y" data-k="yayinla" data-id="'+x.id+'">Yayınla</button><button class="x" data-k="reddet" data-id="'+x.id+'">Reddet</button></div>';
    else if(dr=='yayınlandı'&&x.url) alt='<div class="d"><a href="'+x.url+'">Sitede aç</a></div>';
    if(x.hata&&dr=='bekliyor') alt+='<div style="color:#ff8a8a;font-size:13px;margin-top:6px">Son deneme hata verdi: '+esc(x.hata)+'</div>';
    return '<div class="k '+sinif+'"><div class="u"><span class="r '+sinif+'">'+(ETIKET[dr]||esc(dr).toUpperCase())+'</span>'+
      '<span>'+(TIP[x.tip]||x.tip)+'</span><span>'+esc(x.saat)+'</span><span>'+esc(x.kat)+'</span><span>@'+esc(x.kaynak)+'</span>'+
      (x.tip=='haber'?'<span>'+(x.ilk?'İLK':'')+'</span>':'')+'</div>'+
      '<a class="t" href="'+location.pathname+'/t/'+x.id+'.html">'+esc(x.baslik)+'</a>'+alt+'</div>';
  }).join('');
}
var son=[];
function yukle(){fetch(location.pathname+'.json?t='+Date.now()).then(function(r){return r.json()}).then(function(v){son=v;ciz(v);
  document.getElementById('zaman').textContent='güncellendi '+new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});});}
function karar(k,id){
  if(k=='reddet'&&!confirm('Bu taslak reddedilsin mi?'))return;
  islemde[id]=1; ciz(son);
  fetch('https://ntfy.sh/'+ONAY,{method:'POST',body:k+' '+id}).then(function(){setTimeout(yukle,1500)}).catch(function(e){delete islemde[id];alert('Gönderilemedi: '+e)});
}
document.querySelectorAll('.flt button').forEach(function(b){b.onclick=function(){
  document.querySelectorAll('.flt button').forEach(function(z){z.classList.remove('on')});b.classList.add('on');filtre=b.dataset.f;ciz(son);}});
document.getElementById('liste').addEventListener('click',function(e){var b=e.target.closest('button[data-k]'); if(b) karar(b.dataset.k,b.dataset.id);});
yukle(); setInterval(yukle,5000);
</script></body></html>""".replace("__ONAY__", NTFY_ONAY)

def onizleme_sunucu():
    """yalnızca önizleme klasöründeki rastgele adlı dosyaları sunar; liste vermez, 7 günden eski dosyaları siler"""
    import http.server, socketserver
    from ortak import ONIZLEME_PORT
    import hmac
    class H(http.server.BaseHTTPRequestHandler):
        def _gonder(self, kod, tur, veri):
            self.send_response(kod); self.send_header("Content-Type", tur + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store"); self.send_header("X-Robots-Tag", "noindex")
            self.send_header("Content-Length", str(len(veri)))
            self.end_headers(); self.wfile.write(veri)
        def _js(self, kod, obj):
            self._gonder(kod, "application/json", json.dumps(obj, ensure_ascii=False).encode())
        def _api(self, yontem):
            """/api/... — Authorization: Bearer <panel anahtarı> ister"""
            ad = self.path.split("?")[0].rstrip("/")
            gelen = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
            if not hmac.compare_digest(gelen.encode(), panel_anahtar().encode()):
                time.sleep(1); return self._js(401, {"hata": "Anahtar geçersiz"})
            if yontem == "GET" and ad == "/api/durum":
                return self._js(200, {"tamam": True, "surum": 1, "yayin_acik": YAYIN_ACIK})
            if yontem == "GET" and ad == "/api/taslaklar":
                return self._js(200, {"taslaklar": uygulama_listesi(), "zaman": time.time(), "editorler": editorler(), "son_yayin_sn": son_yayin_suresi()})
            m = re.fullmatch(r"/api/taslak/([0-9a-z-]+)(/onizleme|/karar|/duzenle|/gorseller|/gorsel|/editor)?", ad)
            if not m: return self._js(404, {"hata": "Yol bulunamadı"})
            tid, alt = m.group(1), m.group(2) or ""
            d = taslak_oku(tid)
            if not d: return self._js(404, {"hata": "Taslak bulunamadı"})
            if yontem == "GET" and alt == "":
                return self._js(200, uygulama_detay(d))
            if yontem == "GET" and alt == "/onizleme":
                return self._gonder(200, "text/html", onizleme_html(d, butonsuz=True).encode())
            if yontem == "GET" and alt == "/gorseller":
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("q", [""])[0].strip()[:80]
                return self._js(200, {"adaylar": gorsel_adaylari(tid, q or None)})
            if yontem != "POST": return self._js(405, {"hata": "Yöntem desteklenmiyor"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                veri = json.loads(self.rfile.read(n).decode("utf-8")) if 0 < n <= 65536 else {}
            except Exception:
                return self._js(400, {"hata": "Gövde okunamadı"})
            if alt == "/karar":
                kod, js = uygulama_karar(tid, str(veri.get("komut", "")))
                return self._js(kod, js)
            if alt == "/editor":
                kod, js = editor_sec(tid, str(veri.get("kod", "")))
                return self._js(kod, js)
            if alt == "/gorsel":
                tamam, mesaj = gorsel_degistir(tid, str(veri.get("secim", "")))
                return self._js(200 if tamam else 422, {"mesaj": mesaj, "oge": uygulama_detay(taslak_oku(tid))} if tamam else {"hata": mesaj})
            if alt == "/duzenle":
                tamam, mesaj = taslak_duzenle(tid, veri)
                return self._js(200 if tamam else 422, {"mesaj": mesaj, "oge": uygulama_detay(taslak_oku(tid))} if tamam else {"hata": mesaj})
            return self._js(404, {"hata": "Yol bulunamadı"})
        def do_OPTIONS(self):
            self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST"); self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", "0"); self.end_headers()
        def do_POST(self):
            if self.path.split("?")[0] == "/sayac":
                import panel; return panel.sayac_isle(self)
            if self.path.startswith("/yonetim"):
                import panel; return panel.isle(self, "POST")
            if self.path.startswith("/api/"):
                try: return self._api("POST")
                except Exception as e:
                    log("api hatası:", repr(e)); return self._js(500, {"hata": "Sunucu hatası"})
            self.send_response(404); self.end_headers()
        def do_GET(self):
            if self.path.startswith("/yonetim"):
                import panel; return panel.isle(self, "GET")
            if self.path.startswith("/api/"):
                try: return self._api("GET")
                except Exception as e:
                    log("api hatası:", repr(e)); return self._js(500, {"hata": "Sunucu hatası"})
            if self.path.startswith("/uygulama/"):   # HH Editör'ün bilgisayarsız kurulum sayfası (imza.py)
                import imza; return imza.sayfa_isle(self, self.path.split("?")[0].rstrip("/"))
            ad = self.path.split("?")[0].lstrip("/")
            m = re.fullmatch(r"fonts/([a-z0-9-]+\.woff2)", ad)
            if m and os.path.exists(os.path.join(SITE_DEPO, "site", "fonts", m.group(1))):   # önizlemedeki site yazı tipleri
                veri = open(os.path.join(SITE_DEPO, "site", "fonts", m.group(1)), "rb").read()
                self.send_response(200); self.send_header("Content-Type", "font/woff2"); self.send_header("Cache-Control", "public, max-age=604800")
                self.send_header("Content-Length", str(len(veri))); self.end_headers(); self.wfile.write(veri); return
            if ad == "kur":
                hedef = "hhpanel://kur?" + urllib.parse.urlsplit(self.path).query
                self.send_response(302); self.send_header("Location", hedef); self.send_header("Content-Length", "0"); self.end_headers(); return
            m = re.fullmatch(r"ac/([0-9a-z-]{6,60})", ad)
            if m:  # ntfy bildirimine dokununca HH Editör'de ilgili taslağı açar
                hedef = "hhpanel://taslak/" + m.group(1)
                govde = (f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                         f'<body style="background:#1d2a37;color:#fff;font:17px system-ui;text-align:center;padding-top:30vh">'
                         f'<a href="{hedef}" style="color:#f1d293">HH Editör\'de aç</a>'
                         f'<script>location.href="{hedef}"</script>').encode()
                self.send_response(302); self.send_header("Location", hedef)
                self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(govde)))
                self.end_headers(); self.wfile.write(govde); return
            pk = "panel-" + panel_anahtar()
            gonder = self._gonder
            if ad == pk:
                return gonder(200, "text/html", panel_html().encode())
            if ad == pk + ".json":
                return gonder(200, "application/json", json.dumps(panel_verisi(), ensure_ascii=False).encode())
            m = re.fullmatch(pk + r"/t/([0-9a-z-]+)\.(html|json)", ad)
            if m:
                d = taslak_oku(m.group(1))
                if not d: return gonder(404, "text/plain", b"yok")
                if m.group(2) == "json":
                    return gonder(200, "application/json", json.dumps({"durum": d.get("durum"), "url": d.get("url"), "hata": d.get("hata")}, ensure_ascii=False).encode())
                return gonder(200, "text/html", onizleme_html(d).encode())
            if re.fullmatch(r"[0-9a-f]{32}\.json", ad):
                tp = os.path.join(ONIZLEME_DIR, ad[:-5] + ".tid")
                d = taslak_oku(open(tp).read().strip()) if os.path.exists(tp) else None
                govde = json.dumps({"durum": d.get("durum"), "url": d.get("url"), "hata": d.get("hata")} if d else {}, ensure_ascii=False).encode()
                self.send_response(200 if d else 404)
                self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Cache-Control", "no-store")
                self.end_headers(); self.wfile.write(govde); return
            yol = os.path.join(ONIZLEME_DIR, ad)
            if not re.fullmatch(r"[0-9a-f]{32}\.html", ad) or not os.path.exists(yol):
                self.send_response(404); self.end_headers(); return
            veri = open(yol, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Robots-Tag", "noindex")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(veri)
        def log_message(self, *a): pass
    for f in os.listdir(ONIZLEME_DIR):
        if time.time() - os.path.getmtime(os.path.join(ONIZLEME_DIR, f)) > 7 * 86400: os.remove(os.path.join(ONIZLEME_DIR, f))
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", ONIZLEME_PORT), H) as s:
        log("önizleme sunucusu açık, port", ONIZLEME_PORT); s.serve_forever()

def _ntfy_dosya(ad, icerik, konu):
    """ntfy'ye dosya yükler, dosyanın adresini döndürür"""
    req = urllib.request.Request(f"https://ntfy.sh/{konu}", data=icerik.encode("utf-8"), method="PUT",
                                 headers={"Filename": ad, "Title": "onizleme", "Priority": "1"})
    js = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return (js.get("attachment") or {}).get("url")

def taslak_bildir(tid):
    from ortak import NTFY_KONU, NTFY_ONAY, ntfy_json
    d = taslak_oku(tid); p = d["post"]; tw = d["tw"]
    ilk = "İLK" if d.get("ilk") else f"{len(d.get('diger_siteler') or [])} sitede var"
    mesaj = f"{', '.join(p.get('cats', []))} · @{tw['kullanici']} {tw['saat']} · {ilk}\nOkuyup Yayınla/Reddet için dokunun"
    eylemler = [
        {"action": "http", "label": "Yayınla", "url": f"https://ntfy.sh/{NTFY_ONAY}", "method": "POST", "body": f"yayinla {tid}", "clear": True},
        {"action": "http", "label": "Reddet", "url": f"https://ntfy.sh/{NTFY_ONAY}", "method": "POST", "body": f"reddet {tid}", "clear": True},
        {"action": "view", "label": "Tweet", "url": tw["url"]},
    ]
    foto = p.get("foto")
    onizleme = None
    try:
        onizleme = onizleme_kaydet(onizleme_html(d), tid)
    except Exception as e:
        log("önizleme yüklenemedi:", e)
    if onizleme:
        # karar önizleme sayfasındaki düğmelerle verilir (orada canlı durum görünür); bildirim düğmeleri durum gösteremez
        eylemler = [{"action": "view", "label": "Önizle ve karar ver", "url": onizleme},
                    {"action": "view", "label": "Tüm taslaklar", "url": panel_adresi() or tw["url"]}]
    on_ek = {"analiz": "Analiz önerisi: ", "guncelleme": "Güncelleme: ", "genisletme": "Genişletme önerisi: "}.get(d.get("tip"), "")
    if d.get("tip") == "guncelleme": mesaj = p.get("not", "")[:300] + "\n" + mesaj
    from ortak import ENV
    if ENV.get("UYGULAMA_ACIK", "0") == "1":  # iPhone'da HH Editör kurulu: dokununca taslak uygulamada açılır
        from ortak import ONIZLEME_ADRES
        uyg = (ONIZLEME_ADRES.rstrip("/") + "/ac/" + tid) if ONIZLEME_ADRES else "hhpanel://taslak/" + tid
        eylemler = [{"action": "view", "label": "Uygulamada aç", "url": uyg}] + ([{"action": "view", "label": "Web önizleme", "url": onizleme}] if onizleme else [])
        mesaj = mesaj.replace("Okuyup Yayınla/Reddet için dokunun", "HH Editör'de açmak için dokunun")
        onizleme = uyg
    ntfy_json(NTFY_KONU, on_ek + p["title"], mesaj, eylemler, oncelik=4 if d["eleme"].get("oncelik") == 1 else 3,
              tikla=onizleme)

def _gercek_gorsel_var(p):
    """haberin yayına gerçek bir fotoğrafla çıkacağı ya da editörün bilerek yazılı kapak seçtiği durum"""
    if p.get("foto") or p.get("gorsel"): return True
    dn = p.get("gorsel_denetim") or {}
    return dn.get("kaynak") == "editör" and dn.get("goruluyor") == "yazılı kapak"

def _gorsel_bekle(tid, azami_sn=600):
    """KURAL: haber gerçek fotoğrafı olmadan yayına çıkmaz. Editör görsel seçimi bitmeden 'Yayınla'ya bastıysa taslak
    "görsel bekleniyor" olarak bekler; fotoğraf gelince yayın kendiliğinden sürer. Gelmezse bir kez daha aranır;
    yine yoksa taslak bekleyenlere döner ve editöre haber verilir (yazılı kapakla yayın yapılmaz)."""
    bas = time.time(); d = taslak_oku(tid)
    log("yayın görsel bekliyor:", (d or {}).get("post", {}).get("title", tid))
    while time.time() - bas < azami_sn:
        d = taslak_oku(tid)
        if not d: return None
        if _gercek_gorsel_var(d["post"]): break
        if d["post"]["slug"] not in _GORSEL_ISLENIYOR and d.get("gorsel_tamam"): break   # seçim bitti ama fotoğraf çıkmadı
        time.sleep(5)
    d = taslak_oku(tid)
    if d and not _gercek_gorsel_var(d["post"]) and d["post"]["slug"] not in _GORSEL_ISLENIYOR:
        try:
            _GORSEL_ISLENIYOR.add(d["post"]["slug"])
            pp = dict(d["post"]); pp.setdefault("gorsel_aramalari", [pp["title"]])
            sec = gorsel_sec(pp, gorsel_listesi())
            if sec.get("foto") or sec.get("gorsel"):
                with _taslak_kilit:
                    d = taslak_oku(tid)
                    d["post"]["foto"] = sec.get("foto"); d["post"]["gorsel"] = sec.get("gorsel"); d["post"]["gorsel_denetim"] = sec.get("denetim")
                    taslak_yaz(d)
        except Exception as e:
            log("yayın öncesi görsel arama hatası:", repr(e)[:150])
        finally:
            _GORSEL_ISLENIYOR.discard(d["post"]["slug"])
    d = taslak_oku(tid)
    with _taslak_kilit:
        d = taslak_oku(tid)
        d.pop("gorsel_bekleniyor", None)
        if not _gercek_gorsel_var(d["post"]):
            d["durum"] = "bekliyor"; d["hata"] = "Uygun gerçek fotoğraf bulunamadı; haber yazılı kapakla yayımlanmadı. Görsel bölümünden yeniden seçin."
            taslak_yaz(d)
            log("YAYIMLANMADI (fotoğraf yok):", d["post"]["title"])
            bildirim("Fotoğraf bulunamadı", d["post"]["title"] + "\nHaber yayımlanmadı; panelden görsel seçin.")
            return None
        taslak_yaz(d)
    log("görsel hazır, yayına devam:", d["post"]["title"])
    return d

def onay_isle(komut, tid):
    with _taslak_kilit:
        d = taslak_oku(tid)
        if not d: log("onay: taslak bulunamadı", tid); return
        if d.get("deneme") and komut == "yayinla":
            bildirim("İşlem yapılmadı", "Deneme taslağı yayınlanamaz"); return
        if komut == "geriyukle":  # yanlışlıkla reddedilen taslak bekleyenlere döner (yayınlanmış bir şey değişmez)
            if d["durum"] == "reddedildi":
                d["durum"] = "bekliyor"; d.pop("hata", None); taslak_yaz(d); log("GERİ YÜKLENDİ:", d["post"]["title"])
            return
        if d.get("tip") == "genisletme":
            if komut == "reddet" and d["durum"] == "yayınlandı":
                try:
                    guncelleme_geri_al(d["post"]["slug"], d["eski"]); d["durum"] = "geri alındı"; taslak_yaz(d)
                    bildirim("Genişletme geri alındı", d["post"]["title"])
                except Exception as e:
                    log("geri alma hatası:", e); bildirim("Geri alma hatası", str(e)[:200])
                return
            if d["durum"] != "bekliyor":
                bildirim("İşlem yapılmadı", f"Bu genişletme zaten {d['durum']}: {d['post']['title']}"); return
            if komut == "reddet":
                d["durum"] = "reddedildi"; taslak_yaz(d); bildirim("Genişletme reddedildi", d["post"]["title"]); return
            d["durum"] = "yayınlanıyor"; taslak_yaz(d)
            try:
                pp = d["post"]
                d["eski"] = genisletme_uygula(pp["slug"], pp["ekler"], pp.get("sss"), pp.get("ek_kaynaklar", []))
                _yk = getattr(_yukleme_tl, "t", None); _yukleme_tl.t = None
                d["durum"] = "yayınlandı"; d["url"] = f"{SITE}/{pp['slug']}/"; d["canli"] = False; d["yayin_ts"] = time.time(); taslak_yaz(d)
                log("GENİŞLETME YAYINDA:", pp["title"])
                threading.Thread(target=_canli_izle, args=(tid, d["url"], _yk, ("Haber genişletildi", pp["title"], d["url"])), daemon=True).start()
            except Exception as e:
                d["durum"] = "bekliyor"; taslak_yaz(d); log("genişletme hatası:", e); bildirim("Genişletme hatası", str(e)[:200])
            return
        if d.get("tip") == "guncelleme":
            if komut == "reddet" and d["durum"] == "yayınlandı":
                try:
                    guncelleme_geri_al(d["post"]["slug"], d["eski"]); d["durum"] = "geri alındı"; taslak_yaz(d)
                    bildirim("Güncelleme geri alındı", d["post"]["title"])
                except Exception as e:
                    log("geri alma hatası:", e); bildirim("Geri alma hatası", str(e)[:200])
                return
            if d["durum"] != "bekliyor":
                bildirim("İşlem yapılmadı", f"Bu güncelleme zaten {d['durum']}: {d['post']['title']}"); return
            if komut == "reddet":
                d["durum"] = "reddedildi"; taslak_yaz(d); bildirim("Güncelleme reddedildi", d["post"]["title"]); return
            d["durum"] = "yayınlanıyor"; d.pop("hata", None); taslak_yaz(d)
            try:
                eski, _ = guncelleme_uygula(d["post"]["slug"], d["post"]["not"], d["post"].get("kaynak"), d["post"].get("duzeltmeler"))
                _yk = getattr(_yukleme_tl, "t", None); _yukleme_tl.t = None
                d["durum"] = "yayınlandı"; d["eski"] = eski; d["url"] = f"{SITE}/{d['post']['slug']}/"; d["canli"] = False; d["yayin_ts"] = time.time(); taslak_yaz(d)
                log("GÜNCELLEME YAYINDA:", d["post"]["title"])
                threading.Thread(target=_canli_izle, args=(tid, d["url"], _yk, ("Güncelleme yayında", d["post"]["title"], d["url"])), daemon=True).start()
            except Exception as e:
                d["durum"] = "bekliyor"; d["hata"] = str(e)[:160]; taslak_yaz(d); log("güncelleme hatası:", e); bildirim("Güncelleme hatası", str(e)[:200])
            return
        if d["durum"] == "yayınlandı" and komut == "reddet":
            # yayınlanmış haberde Reddet = yayından kaldır
            d["durum"] = "kaldırılıyor"; taslak_yaz(d)
            try:
                yayindan_kaldir(d["post"]["slug"], "editör kararı")
                d["durum"] = "yayından kaldırıldı"; taslak_yaz(d)
                log("YAYINDAN KALDIRILDI (editör):", d["post"]["title"])
                bildirim("Yayından kaldırıldı", d["post"]["title"])
            except Exception as e:
                d["durum"] = "yayınlandı"; taslak_yaz(d)
                log("kaldırma hatası:", e); bildirim("Kaldırma hatası", f"{d['post']['title']}\n{str(e)[:200]}")
            return
        if d["durum"] != "bekliyor":
            log("onay: taslak zaten", d["durum"], tid)
            bildirim("İşlem yapılmadı", f"Bu taslak zaten {d['durum']}: {d['post']['title']}", d.get("url")); return
        if komut == "reddet":
            d["durum"] = "reddedildi"; taslak_yaz(d); log("REDDEDİLDİ:", d["post"]["title"])
            bildirim("Reddedildi", d["post"]["title"]); return
        d["durum"] = "yayınlanıyor"; d.pop("hata", None)
        if d.get("tip", "haber") == "haber" and not _gercek_gorsel_var(d["post"]): d["gorsel_bekleniyor"] = True
        taslak_yaz(d)
    if d.get("gorsel_bekleniyor"):
        d = _gorsel_bekle(tid)
        if not d: return
    p, tw = d["post"], d["tw"]
    hizli_bilgi = {}
    def hizli_cb(url_, yukleme):
        """ön derleme kullanıldı: site yükleniyor; editöre yayın durumu hemen bildirilir (depo kaydı arkadan sürer)"""
        hizli_bilgi["url"] = url_
        with _taslak_kilit:
            d_ = taslak_oku(tid); d_["durum"] = "yayınlandı"; d_["url"] = url_; d_["canli"] = False; d_["yayin_ts"] = time.time(); d_["hizli"] = True
            taslak_yaz(d_)
        threading.Thread(target=_canli_izle, args=(tid, url_, yukleme, ("Yayında", p["title"], url_)), daemon=True).start()
    try:
        url = yayinla(p, hizli_cb=hizli_cb)
    except Exception as e:
        log("yayın hatası:", e); d["durum"] = "bekliyor"; d["hata"] = str(e)[:160]; taslak_yaz(d)
        bildirim("Yayın hatası", f"{p['title']}\n{str(e)[:200]}"); return
    if not url:
        d["durum"] = "zaten var"; taslak_yaz(d); bildirim("Yayınlanmadı", "Bu başlık sitede zaten var: " + p["title"]); return
    _yk = getattr(_yukleme_tl, "t", None); _yukleme_tl.t = None
    if hizli_bilgi:
        d = taslak_oku(tid)
    else:
        d["durum"] = "yayınlandı"; d["url"] = url; d["canli"] = False; d["yayin_ts"] = time.time(); taslak_yaz(d)
    sayac("yazi", 1)
    gecikme = int(time.time() - tw["ts"])
    log(f"YAYINDA (onaylı; kaynaktan {gecikme // 60} dk sonra): {p['title']} -> {url}")
    ekle_jsonl("yayinlar.jsonl", {"ts": time.time(), "tweet_id": tw["id"] if str(tw["id"]).isdigit() else None, "tw": tw["url"],
                                  "slug": p["slug"], "url": url, "baslik": p["title"], "tur": d["eleme"].get("tur"),
                                  "ilk": d.get("ilk"), "gecikme_sn": gecikme})
    if not hizli_bilgi:
        threading.Thread(target=_canli_izle, args=(tid, url, _yk, ("Yayında", p["title"], url)), daemon=True).start()
    if d.get("tip", "haber") == "haber" and d.get("x_paylas", True):
        import xpaylas
        # resmî kurum kaynaklı haberde kaynak tweet alıntılanır; siyasetçi/gazeteci kaynaklılarda alıntı yok (tarafsızlık)
        alinti = tw.get("id") if d["eleme"].get("tur") == "resmi" and str(tw.get("id", "")).isdigit() else None
        threading.Thread(target=xpaylas.paylas, daemon=True,
                         args=(p["title"], url.rstrip("/"), alinti, os.path.join(SITE_DEPO, "site", "gorsel", p["slug"] + ".jpg"))).start()   # kanonik adres (yönlendirmesiz) kartı X için kolaylaştırır
    from ortak import ENV
    if (d.get("tip", "haber") == "haber" and not p.get("kapsamli") and d["eleme"].get("analiz")
            and ENV.get("GENISLETME_TASLAK", "0") == "1"):  # varsayılan kapalı: haber ve analiz tek yazıda
        threading.Thread(target=genisletme_hazirla, args=(tw, d["eleme"], p), daemon=True).start()


# ------------------------------------------------------------------ maliyet bağlamları (yazı başına maliyet için)
import ortak as _om

def _is_baglami(fn, bilgi_fn):
    """fonksiyonu yeni bir iş bağlamında çalıştırır; bilgi_fn(args) işe eklenecek bilgileri döndürür"""
    def ic(*a, **k):
        try: bilgi = bilgi_fn(*a, **k) or {}
        except Exception: bilgi = {}
        onceki = _om.maliyet_is_baslat(is_id=bilgi.pop("is_id", None), **bilgi)
        try: return fn(*a, **k)
        finally: _om.maliyet_geri_yukle(onceki)
    ic.__name__ = fn.__name__; ic.__doc__ = fn.__doc__
    return ic

def _yayin_bilgisi(komut, tid):
    d = taslak_oku(tid) or {}
    return {"is_id": d.get("maliyet_is")} if d.get("maliyet_is") else {"tid": tid, "slug": (d.get("post") or {}).get("slug"), "baslik": (d.get("post") or {}).get("title")}

def _yazi_bilgisi_slug(slug, *a, **k):
    p = post_bul(slug) or {}
    return {"slug": slug, "baslik": p.get("title"), "kaynak": "bakım", "sonuc": "görsel yenileme"}

def _yazi_bilgisi_tid(tid, *a, **k):
    d = taslak_oku(tid) or {}
    return {"is_id": d.get("maliyet_is")} if d.get("maliyet_is") else {"tid": tid, "slug": (d.get("post") or {}).get("slug"), "baslik": (d.get("post") or {}).get("title")}

isle = _is_baglami(isle, lambda tw, *a, **k: {"kaynak": tw.get("url"), "hesap": tw.get("kullanici"), "grup": tw.get("grup")})
onay_isle = _is_baglami(_om.maliyet_asamasi("yayın")(onay_isle), _yayin_bilgisi)
yayindaki_gorseli_yenile = _is_baglami(yayindaki_gorseli_yenile, _yazi_bilgisi_slug)
gorsel_yenile = _is_baglami(gorsel_yenile, _yazi_bilgisi_tid)
for _ad, _asama in (("ele", "eleme"), ("on_kontrol", "ön kontrol"), ("arastir", "araştırma"), ("yaz", "yazım"), ("gorsel_sec", "görsel"),
                    ("gorsel_dogrula", "görsel denetimi"), ("itham_duzelt", "dil denetimi"), ("sss_hazirla", "SSS"),
                    ("guncelleme_yaz", "güncelleme yazımı"), ("genisletme_hazirla", "genişletme")):
    if _ad in globals(): globals()[_ad] = _om.maliyet_asamasi(_asama)(globals()[_ad])

# ------------------------------------------------------------------ ön derleme (hızlı yayın)
# Taslak hazır olduğunda site, haber dahil ayrı bir çalışma kopyasında derlenir, tam denetimden geçirilir ve dosyaları Cloudflare'e
# önceden gönderilir. Yayın saati ancak onayda belli olduğu için ön derlemede saat yerine YER_SAAT yazılır; onayda yalnızca bu yer
# tutucu gerçek saatle değiştirilip site yayına alınır (birkaç sn). Ön derlemeden sonra başka yayın olduysa (taban değiştiyse),
# taslak değiştiyse ya da gün döndüyse normal yola dönülür. Asıl depo ön derlemede hiç değişmez.
ONHAZIR_DIR = os.path.join(VERI, "onhazir")
YER_SAAT = "QQ:QQ"
ONHAZIR_AZAMI = 2                  # aynı anda hazır tutulan en yeni taslak sayısı (disk/işlemci)
_ONHAZIR = {}                      # tid -> {"ws", "taban", "imza", "gun", "ts"}
_onhazir_is = threading.Lock()     # aynı anda tek ön derleme
_ONHAZIR_KULLANIMDA = set()        # hızlı yayında kullanılan çalışma kopyaları (depo kaydı bitene kadar silinmez)

def _onhazir_imza(p):
    alan = {k: p.get(k) for k in ("slug", "title", "cats", "tags", "ozet", "body", "kaynaklar", "sss", "karar", "tur", "olay_tarihi", "denetleyen", "incelendi")}
    alan["foto"] = (p.get("foto") or {}).get("url"); alan["gorsel"] = p.get("gorsel")
    return hashlib.md5(json.dumps(alan, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

def _depo_tabani():
    return subprocess.run(["git", "-C", SITE_DEPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

def _onhazir_sil(tid):
    k = _ONHAZIR.pop(tid, None)
    shutil.rmtree(os.path.join(ONHAZIR_DIR, tid), ignore_errors=True)
    return k

def _gercek_kopya(ws, rel):
    """sabit bağlantılı çalışma kopyasında yerinde yazılacak dosyayı asıl depodan koparır"""
    y = os.path.join(ws, rel)
    if os.path.exists(y):
        tmp = y + ".kopya"; shutil.copy2(y, tmp); os.replace(tmp, y)

def onhazirla(tid):
    """taslağı yayına hazır derler: çalışma kopyası, haber + fotoğraf, derleme, denetim, Cloudflare'e ön gönderim"""
    import cfyukle
    with _onhazir_is:
        d = taslak_oku(tid)
        if not d or d.get("tip", "haber") != "haber" or d.get("durum") != "bekliyor" or not _gercek_gorsel_var(d["post"]): return False
        p = d["post"]; imza = _onhazir_imza(p); bugun = simdi().strftime("%Y-%m-%d")
        t0 = time.time(); ws = os.path.join(ONHAZIR_DIR, tid)
        with _yayin_kilit:   # depo sabitken kopyalanır (birkaç sn)
            taban = _depo_tabani()
            if subprocess.run(["git", "-C", SITE_DEPO, "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
                return False   # depo yarım bir işlemin ortasında
            shutil.rmtree(ws, ignore_errors=True); os.makedirs(ws)
            for ad in os.listdir(SITE_DEPO):
                if ad in (".git", "__pycache__"): continue
                r = subprocess.run(["cp", "-al", os.path.join(SITE_DEPO, ad), os.path.join(ws, ad)], capture_output=True, text=True)
                if r.returncode != 0: raise RuntimeError("ön derleme kopyası: " + r.stderr[-200:])
        for rel in ("content6.py", os.path.join("commons", "meta.json"), os.path.join(".gorsel_onbellek", ".onbellek.json"),
                    os.path.join(".gorsel_onbellek", "md5.json")):
            _gercek_kopya(ws, rel)
        post = _post_olustur(p, simdi(), saat=YER_SAAT)
        # fotoğraf (asıl depodaki commons_indir ile aynı işlem, çalışma kopyasına)
        cdir = os.path.join(ws, "commons"); mp = os.path.join(cdir, "meta.json"); meta = json.load(open(mp, encoding="utf-8"))
        slug = post["slug"]
        if p.get("foto"):
            from PIL import Image
            bilgi = p["foto"]
            veri = urllib.request.urlopen(urllib.request.Request(bilgi["url"], headers=_UA), timeout=40).read()
            _duz_rgb(Image.open(io.BytesIO(veri))).save(os.path.join(cdir, slug + ".jpg"), "JPEG", quality=90)
            meta[slug] = {k: bilgi[k] for k in ("title", "page", "lic", "artist")}
            if bilgi.get("kaynak"): meta[slug]["kaynak"] = bilgi["kaynak"]
            if bilgi.get("alt"): meta[slug]["alt"] = bilgi["alt"]
        elif p.get("gorsel"):
            shutil.copyfile(os.path.join(cdir, p["gorsel"] + ".jpg"), os.path.join(cdir, slug + ".jpg"))
            meta[slug] = dict(meta[p["gorsel"]])
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        yol = os.path.join(ws, "content6.py"); s = open(yol, encoding="utf-8").read()
        i = s.index("POSTS = [") + len("POSTS = [")
        open(yol, "w", encoding="utf-8").write(s[:i] + "\n" + repr(post) + "," + s[i:])
        for betik in ("build.py", "check.py"):
            # denetim çalışma kopyasındaki siteye bakar; yayın kimliği denetimi asıl deponun git kaydına karşı yapılır (GIT_DIR)
            r = subprocess.run(["nice", "-n", "15", "python3", betik], cwd=ws, capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, GIT_DIR=os.path.join(SITE_DEPO, ".git")))
            if r.returncode != 0 or (betik == "check.py" and ("kırık 0" not in r.stdout or "kimlik tamam" not in r.stdout)):
                log("ön derleme başarısız:", betik, (r.stdout + r.stderr)[-300:]); shutil.rmtree(ws, ignore_errors=True); return False
        yer_dosyalari = []
        for kok_, _, fs_ in os.walk(os.path.join(ws, "site")):
            for f_ in fs_:
                if f_.endswith((".html", ".xml", ".json", ".txt", ".js")) and YER_SAAT.encode() in open(os.path.join(kok_, f_), "rb").read():
                    yer_dosyalari.append(os.path.join(kok_, f_))
        try:
            cfyukle.on_gonder(ws)   # dosyalar Cloudflare'e önceden (yayına almadan)
        except Exception as e:
            log("ön gönderim olmadı (onayda gönderilir):", str(e)[:200])
        _ONHAZIR[tid] = {"ws": ws, "taban": taban, "imza": imza, "gun": bugun, "ts": time.time(), "yer": yer_dosyalari}
        log(f"ön derleme hazır ({round(time.time() - t0, 1)} sn):", p["title"][:70])
        return True

def onhazir_dagit(p, n):
    """onay anında: geçerli ön derleme varsa saati yazar ve siteyi yayına alır; {"ws", "yukleme"} ya da None. _yayin_kilit tutulurken çağrılır."""
    import cfyukle
    tid = next((t for t, k in _ONHAZIR.items() if os.path.basename(k["ws"]) == t and (taslak_oku(t) or {}).get("post", {}).get("slug") == p["slug"]), None)
    k = _ONHAZIR.get(tid) if tid else None
    if not k: return None
    neden = None
    if k["taban"] != _depo_tabani(): neden = "ön derlemeden sonra başka yayın oldu"
    elif k["imza"] != _onhazir_imza(p): neden = "taslak değişti"
    elif k["gun"] != n.strftime("%Y-%m-%d"): neden = "gün değişti"
    elif not os.path.isdir(os.path.join(k["ws"], "site")): neden = "ön derleme klasörü yok"
    else:
        te = time.time(); neden = _yayin_engeli(_post_olustur(p, n)); te = round(time.time() - te, 2)
        if te > 0.5: log("hızlı yayın: tekrar denetimi", te, "sn")
    if neden:
        log("hızlı yayın kullanılmadı:", neden); return None
    t0 = time.time()
    saat = n.strftime("%H:%M").encode(); yer = YER_SAAT.encode(); say = 0
    for y in k.get("yer") or []:   # yer tutucu içeren dosyalar ön derlemede belirlendi; bütün site taranmaz
        b = open(y, "rb").read()
        if yer in b:
            tmp = y + ".tmp"; open(tmp, "wb").write(b.replace(yer, saat)); os.replace(tmp, y); say += 1
    t = threading.Thread(target=cfyukle.yukle, args=(k["ws"], "Yeni haber: " + p["title"], cfyukle.anlik_kopya(k["ws"])), daemon=True)
    t.start()
    _ONHAZIR_KULLANIMDA.add(tid)
    log(f"hızlı yayın: ön derleme kullanıldı ({say} dosyaya saat yazıldı, {round(time.time() - t0, 2)} sn):", p["title"][:70])
    return {"ws": k["ws"], "yukleme": t, "tid": tid}

_ONHAZIR_UYAN = threading.Event()   # taslak değişince (ör. editör seçimi) ön derleme 10 sn beklemeden yenilensin

def onhazir_dongu():
    """onay bekleyen en yeni haber taslaklarını yayına hazır tutar; yayımlanan, reddedilen ya da eskiyen ön derlemeleri temizler"""
    time.sleep(15)
    os.makedirs(ONHAZIR_DIR, exist_ok=True)
    for ad in os.listdir(ONHAZIR_DIR): shutil.rmtree(os.path.join(ONHAZIR_DIR, ad), ignore_errors=True)   # açılışta temiz
    while True:
        try:
            if os.environ.get("ONHAZIR", _ENV.get("ONHAZIR", "1")) != "0":
                bekleyen = []
                for f in sorted(os.listdir(TASLAK_DIR), reverse=True):
                    if not f.endswith(".json"): continue
                    d = taslak_oku(f[:-5]) or {}
                    if d.get("tip", "haber") == "haber" and d.get("durum") == "bekliyor" and _gercek_gorsel_var(d.get("post") or {}):
                        bekleyen.append(d)
                    if len(bekleyen) >= ONHAZIR_AZAMI: break
                istenen = {d["id"] for d in bekleyen}
                for t in list(_ONHAZIR):
                    if t not in istenen and t not in _ONHAZIR_KULLANIMDA: _onhazir_sil(t)
                taban, bugun = _depo_tabani(), simdi().strftime("%Y-%m-%d")
                for d in bekleyen:
                    k = _ONHAZIR.get(d["id"])
                    if k and k["taban"] == taban and k["imza"] == _onhazir_imza(d["post"]) and k["gun"] == bugun: continue
                    try: onhazirla(d["id"])
                    except Exception as e: log("ön derleme hatası:", repr(e)[:200]); _onhazir_sil(d["id"])
        except Exception as e:
            log("ön derleme döngüsü hatası:", repr(e)[:200])
        _ONHAZIR_UYAN.wait(10); _ONHAZIR_UYAN.clear()
