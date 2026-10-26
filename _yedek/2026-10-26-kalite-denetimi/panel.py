# -*- coding: utf-8 -*-
"""Hukuki Haberler yönetim paneli (/yonetim).

Önizleme sunucusuna (ONIZLEME_PORT) bağlanır; ayrı bir süreç ya da paket gerektirmez.
- Giriş: PANEL_SIFRE (.env) ya da tanımlı değilse editör uygulamasının panel anahtarı.
- Oturum: HttpOnly + SameSite=Strict çerez; 30 gün. Yazma isteklerinde X-HH-Panel başlığı zorunlu.
- Uzun işler (derleme, yayın, görsel) arka planda "iş" olarak çalışır; arayüz durumunu sorgular.
- Okur mesajları sitedeki /api/iletisim ucundan çekilir, burada saklanır, sitedeki kopyası silinir.
"""
import os, re, json, time, html, hmac, hashlib, secrets, threading, subprocess, urllib.parse, urllib.request, datetime, runpy, glob, shutil

import ortak
from ortak import log, VERI, SITE_DEPO, SITE, KOK, ENV_DOSYA, simdi, http_json, bildirim
import yazar

ARAYUZ = os.path.join(KOK, "panel")
_OTURUM_DOSYA = os.path.join(VERI, "panel_oturum.json")
_MESAJ_DOSYA = os.path.join(VERI, "mesajlar.json")
_MESAJ_ANAHTAR_DOSYA = os.path.join(VERI, "mesaj_anahtar.txt")
_MESAJ_CF_DOSYA = os.path.join(VERI, "mesaj_anahtar_cf.json")
_ISLEM_GUNLUGU = "panel_islemleri.jsonl"
_BASLANGIC = time.time()
_kilit = threading.Lock()
_mesaj_kilit = threading.Lock()
OTURUM_SN = 30 * 86400

KONU_ADLARI = {"ihbar": "Haber ihbarı", "duzeltme": "Düzeltme talebi", "cevap": "Cevap ve düzeltme hakkı",
               "icerik": "Kişilik hakkı / içerik kaldırma talebi", "kvkk": "KVKK başvurusu", "teknik": "Teknik sorun", "diger": "Diğer"}

# ------------------------------------------------------------------ yardımcılar
def _env_oku():
    return ortak._env()

def _sifre():
    e = _env_oku()
    return e.get("PANEL_SIFRE") or yazar.panel_anahtar()

def _jsonl_oku(ad, son=None):
    p = os.path.join(VERI, ad)
    if not os.path.exists(p): return []
    satirlar = open(p, encoding="utf-8", errors="replace").read().splitlines()
    if son: satirlar = satirlar[-son:]
    out = []
    for ln in satirlar:
        try: out.append(json.loads(ln))
        except Exception: pass
    return out

def _islem_kaydet(islem, ayrinti=""):
    ortak.ekle_jsonl(_ISLEM_GUNLUGU, {"ts": time.time(), "islem": islem, "ayrinti": str(ayrinti)[:300]})

def _git_site(*a, zaman=60):
    r = subprocess.run(["git", "-C", SITE_DEPO] + list(a), capture_output=True, text=True, timeout=zaman)
    return r.stdout.strip()

# ------------------------------------------------------------------ oturum
_hatali = {}   # ip -> [zamanlar]

def _oturumlar():
    try: return json.load(open(_OTURUM_DOSYA, encoding="utf-8"))
    except Exception: return {}

def _oturum_yaz(d):
    tmp = _OTURUM_DOSYA + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8")); os.replace(tmp, _OTURUM_DOSYA)
    try: os.chmod(_OTURUM_DOSYA, 0o600)
    except Exception: pass

def _ozet(t): return hashlib.sha256(t.encode()).hexdigest()

def _cerez(h):
    for parca in (h.headers.get("Cookie") or "").split(";"):
        k, _, v = parca.strip().partition("=")
        if k == "hh_oturum": return v
    return ""

def _oturum_gecerli(h):
    t = _cerez(h)
    if not t or len(t) < 30: return False
    with _kilit:
        d = _oturumlar(); o = d.get(_ozet(t))
        if not o or time.time() - o.get("ts", 0) > OTURUM_SN: return False
        if time.time() - o.get("son", 0) > 300:
            o["son"] = time.time(); _oturum_yaz(d)
    return True

def _ip(h):
    return h.headers.get("CF-Connecting-IP") or h.headers.get("X-Forwarded-For", "").split(",")[0].strip() or h.client_address[0]

def giris(h, veri):
    ip = _ip(h); simdi_ = time.time()
    _hatali[ip] = [t for t in _hatali.get(ip, []) if simdi_ - t < 900]
    if len(_hatali[ip]) >= 6:
        return 429, {"hata": "Çok fazla hatalı deneme. 15 dakika sonra yeniden deneyin."}, None
    if not hmac.compare_digest(str(veri.get("sifre", "")).strip().encode(), _sifre().encode()):
        _hatali[ip].append(simdi_); time.sleep(1.2)
        log("panel: hatalı giriş denemesi", ip)
        return 401, {"hata": "Şifre hatalı."}, None
    t = secrets.token_urlsafe(32)
    with _kilit:
        d = _oturumlar()
        d = {k: v for k, v in d.items() if simdi_ - v.get("ts", 0) < OTURUM_SN}
        d[_ozet(t)] = {"ts": simdi_, "son": simdi_, "ip": ip, "tarayici": (h.headers.get("User-Agent") or "")[:120]}
        _oturum_yaz(d)
    _islem_kaydet("giriş", ip)
    cerez = f"hh_oturum={t}; Path=/yonetim; HttpOnly; SameSite=Strict; Max-Age={OTURUM_SN}"
    if (h.headers.get("X-Forwarded-Proto") or "") == "https": cerez += "; Secure"
    return 200, {"tamam": True}, cerez

def cikis(h):
    t = _cerez(h)
    with _kilit:
        d = _oturumlar(); d.pop(_ozet(t), None); _oturum_yaz(d)
    return "hh_oturum=; Path=/yonetim; HttpOnly; SameSite=Strict; Max-Age=0"

def tum_oturumlari_kapat():
    with _kilit: _oturum_yaz({})

# ------------------------------------------------------------------ arka plan işleri
_isler = {}

def is_baslat(ad, fn, *a, **k):
    iid = secrets.token_hex(6)
    _isler[iid] = {"id": iid, "ad": ad, "durum": "çalışıyor", "bas": time.time(), "mesaj": ""}
    def calis():
        try:
            sonuc = fn(*a, **k)
            if sonuc is False:
                _isler[iid].update(durum="hata", mesaj="İşlem uygulanmadı (değişiklik yok ya da kayıt bulunamadı).")
            else:
                _isler[iid].update(durum="tamam", mesaj=sonuc if isinstance(sonuc, str) else "Tamamlandı.")
        except Exception as e:
            log("panel işi hatası:", ad, repr(e))
            _isler[iid].update(durum="hata", mesaj=str(e)[:400])
            _depoyu_temizle()
        _isler[iid]["bit"] = time.time()
        _islem_kaydet(ad, _isler[iid]["durum"] + ": " + str(_isler[iid]["mesaj"])[:200])
    threading.Thread(target=calis, daemon=True).start()
    if len(_isler) > 60:
        for eski in sorted(_isler, key=lambda x: _isler[x]["bas"])[:20]: _isler.pop(eski, None)
    return iid

def _depoyu_temizle():
    """başarısız bir yayın denemesinden kalan yarım değişiklikleri atar (site deposu GitHub'daki son hâline döner)"""
    try:
        with yazar._yayin_kilit:
            subprocess.run(["git", "-C", SITE_DEPO, "reset", "-q", "--hard", "origin/main"], capture_output=True, timeout=120)
            subprocess.run(["git", "-C", SITE_DEPO, "clean", "-fdq", "--", "site", "commons"], capture_output=True, timeout=120)
        _ONBELLEK["anahtar"] = None
    except Exception as e:
        log("depo temizlenemedi:", e)

# ------------------------------------------------------------------ site içeriği
_ONBELLEK = {"anahtar": None, "veri": None}

def _icerik_imzasi():
    return tuple(os.path.getmtime(os.path.join(SITE_DEPO, a)) if os.path.exists(os.path.join(SITE_DEPO, a)) else 0
                 for a in yazar.ICERIK_DOSYALARI)

def _denetleyen_haritasi():
    """yayındaki her yazının hukuki inceleme kartında görünen avukat (derlenmiş sayfadan okunur; derlemedeki kural tek kaynak olur)"""
    out = {}
    for yol in glob.glob(os.path.join(SITE_DEPO, "site", "*.html")):
        try: s = open(yol, encoding="utf-8").read()
        except Exception: continue
        m = re.search(r'class="inceleme"[^>]*data-denetleyen="([a-z0-9-]+)"', s)
        if m: out[os.path.basename(yol)[:-5]] = m.group(1)
        elif "Yağmur Tahtasız tarafından hukuki" in s: out[os.path.basename(yol)[:-5]] = "yagmur-tahtasiz"
        elif "Umut Tekin tarafından hukuki" in s: out[os.path.basename(yol)[:-5]] = "umut-tekin"
    return out

def tum_yazilar():
    imza = _icerik_imzasi()
    if _ONBELLEK["anahtar"] == imza and _ONBELLEK["veri"] is not None: return _ONBELLEK["veri"]
    yazilar = []
    for ad in yazar.ICERIK_DOSYALARI:
        yol = os.path.join(SITE_DEPO, ad)
        if not os.path.exists(yol): continue
        try: posts = runpy.run_path(yol)["POSTS"]
        except Exception as e:
            log("panel: içerik okunamadı", ad, e); continue
        for p in posts:
            yazilar.append(dict(p, _dosya=ad))
    den = _denetleyen_haritasi()
    meta = {}
    try: meta = json.load(open(os.path.join(SITE_DEPO, "commons", "meta.json"), encoding="utf-8"))
    except Exception: pass
    for p in yazilar:
        p["_denetleyen"] = den.get(p["slug"])
        p["_gorsel"] = os.path.exists(os.path.join(SITE_DEPO, "site", "gorsel", p["slug"] + ".jpg"))
        p["_gorsel_kaynak"] = (meta.get(p["slug"]) or {}).get("title", "")
    yazilar.sort(key=lambda p: (p.get("date", ""), p.get("saat", "")), reverse=True)
    _ONBELLEK.update(anahtar=imza, veri=yazilar)
    return yazilar

def _kelime(govde):
    return len(re.sub(r"<[^>]+>", " ", govde or "").split())

def _yazi_ozeti(p):
    return {"slug": p["slug"], "baslik": p["title"], "tarih": p.get("date", ""), "saat": p.get("saat", ""), "tur": p.get("tur", "Haber"),
            "kategoriler": p.get("cats", []), "etiket_sayisi": len(p.get("tags", [])), "kelime": _kelime(p.get("body")),
            "denetleyen": p.get("_denetleyen"), "denetleyen_elle": p.get("denetleyen"), "incelendi": p.get("incelendi"), "yazar": p.get("yazar"), "gorsel": p.get("_gorsel"),
            "guncellendi": p.get("updated"), "dosya": p.get("_dosya"), "url": f"{SITE}/{p['slug']}/",
            "kucuk": f"/yonetim/gorsel/{p['slug']}.jpg" if p.get("_gorsel") else None}

def yazi_listesi(q):
    L = tum_yazilar()
    ara = (q.get("q") or "").strip().lower()
    kat, tur, den, yil = q.get("kategori"), q.get("tur"), q.get("denetleyen"), q.get("yil")
    if ara: L = [p for p in L if ara in p["title"].lower() or ara in p["slug"] or any(ara in t.lower() for t in p.get("tags", []))]
    if kat: L = [p for p in L if kat in p.get("cats", [])]
    if tur: L = [p for p in L if p.get("tur", "Haber") == tur]
    if den == "yok": L = [p for p in L if not p.get("_denetleyen")]
    elif den: L = [p for p in L if p.get("_denetleyen") == den]
    if yil: L = [p for p in L if p.get("date", "").startswith(yil)]
    if q.get("gorsel") == "yok": L = [p for p in L if not p.get("_gorsel")]
    sayfa = max(1, int(q.get("sayfa") or 1)); adet = min(100, max(10, int(q.get("adet") or 25)))
    return {"toplam": len(L), "sayfa": sayfa, "adet": adet, "yazilar": [_yazi_ozeti(p) for p in L[(sayfa - 1) * adet: sayfa * adet]]}

def yazi_detay(slug):
    p = next((x for x in tum_yazilar() if x["slug"] == slug), None)
    if not p: return None
    o = _yazi_ozeti(p)
    o.update({"ozet": p.get("ozet", []), "govde": p.get("body", ""), "etiketler": p.get("tags", []), "kaynaklar": p.get("kaynaklar", []),
              "sss": p.get("sss", []), "gecmis": p.get("gecmis", []), "gorsel_kaynak": p.get("_gorsel_kaynak"), "karar": p.get("karar")})
    return o

_DUZENLENEBILIR = ("title", "ozet", "body", "tags", "cats", "tur", "denetleyen", "incelendi", "yazar", "kaynaklar", "sss")

def yazi_dogrula(veri):
    """düzenleme isteğini doğrular; (değişecek alanlar, geçmiş notu) döndürür, hata varsa ValueError"""
    hatalar = []
    yeni = {}
    if "baslik" in veri:
        b = re.sub(r"\s+", " ", str(veri["baslik"])).strip()
        if not 10 <= len(b) <= 110: hatalar.append(f"Başlık 10-110 karakter olmalı (şu an {len(b)}).")
        yeni["title"] = b
    if "ozet" in veri:
        oz = [re.sub(r"\s+", " ", str(x)).strip() for x in (veri.get("ozet") or []) if str(x).strip()][:6]
        if any(len(x) > 400 for x in oz): hatalar.append("Öne çıkan maddeler en fazla 400 karakter olabilir.")
        yeni["ozet"] = oz
    if "govde" in veri:
        g = str(veri["govde"]).strip()
        if _kelime(g) < 40: hatalar.append("Metin çok kısa (en az 40 kelime).")
        if re.search(r"<\s*(script|iframe|object|embed|form|style)\b", g, re.I) or re.search(r"\son\w+\s*=", g, re.I) or "javascript:" in g.lower():
            hatalar.append("Metinde betik, iframe, form ya da olay özniteliği kullanılamaz.")
        yeni["body"] = g
    if "etiketler" in veri:
        yeni["tags"] = [re.sub(r"\s+", " ", str(t)).strip()[:60] for t in (veri.get("etiketler") or []) if str(t).strip()][:12]
    if "kategoriler" in veri:
        k = [c for c in (veri.get("kategoriler") or []) if c in yazar.KATEGORILER][:3]
        if not k: hatalar.append("En az bir geçerli kategori seçin.")
        yeni["cats"] = k
    if "tur" in veri:
        if veri["tur"] not in ("Haber", "Analiz"): hatalar.append("Tür Haber ya da Analiz olmalı.")
        yeni["tur"] = veri["tur"]
    if "denetleyen" in veri:
        import yazar_yonetimi
        kodlar = {y["kod"] for y in yazar_yonetimi.ozet()}
        if veri["denetleyen"] not in ("otomatik", "yok", *kodlar): hatalar.append("Geçersiz inceleyen seçimi.")
        yeni["denetleyen"] = veri["denetleyen"]
    if "incelendi" in veri:
        v = str(veri.get("incelendi") or "").strip()[:10]
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v): hatalar.append("İnceleme tarihi geçersiz.")
        yeni["incelendi"] = v
    if "yazar" in veri:
        import yazar_yonetimi
        if veri["yazar"] and veri["yazar"] not in {y["kod"] for y in yazar_yonetimi.ozet()}: hatalar.append("Geçersiz yazar seçimi.")
        yeni["yazar"] = veri["yazar"] or ""
    if "kaynaklar" in veri:
        ks = []
        for k in veri.get("kaynaklar") or []:
            if isinstance(k, (list, tuple)) and len(k) == 2 and str(k[1]).startswith(("http://", "https://")):
                ks.append([str(k[0]).strip()[:200] or str(k[1]), str(k[1]).strip()])
        yeni["kaynaklar"] = ks
    if "sss" in veri:
        yeni["sss"] = [[str(a).strip(), str(c).strip()] for a, c in (veri.get("sss") or []) if str(a).strip() and str(c).strip()][:8]
    if hatalar: raise ValueError(" ".join(hatalar))
    if not yeni: raise ValueError("Değişiklik yok.")
    return yeni, re.sub(r"\s+", " ", str(veri.get("not") or "")).strip()[:300]

def yazi_kaydet(slug, yeni, not_):
    """doğrulanmış değişiklikleri yayındaki yazıya uygular; derlenip denetlendikten sonra yayına gönderilir"""
    def degistir(p):
        for k, v in yeni.items():
            if k == "denetleyen":
                if v == "otomatik": p.pop("denetleyen", None)
                else: p["denetleyen"] = v
            elif k == "incelendi":
                if not v: p.pop("incelendi", None)
                else: p["incelendi"] = v
            elif k == "yazar":
                if not v: p.pop("yazar", None)
                else: p["yazar"] = v
            elif k in ("tags", "sss", "kaynaklar", "ozet") and not v: p.pop(k, None)
            else: p[k] = v
        if not_:
            n = simdi()
            p["updated"] = n.strftime("%Y-%m-%dT%H:%M")
            p["gecmis"] = list(p.get("gecmis", [])) + [{"tarih": p["updated"], "tur": "Düzeltme", "not": not_}]
        return p
    def hazirla():
        yazar._post_degistir(slug, degistir)
    yazar._gonder("Düzenleme: " + slug, hazirla)
    return "Yazı güncellendi ve yayına gönderildi."

def guncelleme_notu(slug, veri):
    n = re.sub(r"\s+", " ", str(veri.get("not") or "")).strip()
    if not 20 <= len(n) <= 700: raise ValueError("Güncelleme notu 20-700 karakter olmalı.")
    kaynak = []
    if str(veri.get("kaynak_url") or "").startswith(("http://", "https://")):
        kaynak = [[str(veri.get("kaynak_ad") or veri["kaynak_url"]).strip()[:200], str(veri["kaynak_url"]).strip()]]
    yazar.guncelleme_uygula(slug, n, kaynak)
    return "Güncelleme notu eklendi ve yayına gönderildi."

# ------------------------------------------------------------------ yeni yazı (elle)
def _yeni_yazi_isle(veri):
    p = {"slug": yazar.slugla(veri.get("slug") or veri["baslik"]), "title": veri["baslik"], "tur": veri["tur"], "cats": veri["kategoriler"],
         "tags": veri["etiketler"], "ozet": veri["ozet"], "body": veri["govde"], "kaynaklar": veri["kaynaklar"],
         "gorsel_aramalari": veri.get("gorsel_aramalari") or [veri["baslik"]]}
    if p["slug"] in yazar.site_sluglari() or any(x["slug"] == p["slug"] for x in tum_yazilar()):
        p["slug"] = p["slug"] + "-" + simdi().strftime("%H%M")
    n = simdi()
    tw = {"id": "elle-" + p["slug"], "kullanici": "editor", "ad": "Hukuki Haberler Editörlüğü", "grup": "resmi",
          "tarih": n.strftime("%d.%m.%Y"), "saat": n.strftime("%H.%M"), "ts": time.time(), "url": p["kaynaklar"][0][1], "metin": p["title"]}
    el = {"haber": True, "islem": "yeni", "tur": "elle", "konu": p["title"], "oncelik": 2, "analiz": p["tur"] == "Analiz"}
    t0 = time.time()
    ortak.maliyet_is_baslat(kaynak="elle (panel)", konu=p["title"])
    if veri.get("gorsel") != "yok":
        sec = yazar.gorsel_sec(p, yazar.gorsel_listesi())
        p["foto"] = sec.get("foto"); p["gorsel"] = sec.get("gorsel"); p["gorsel_denetim"] = sec.get("denetim")
    seo_bilgi = None
    try:
        import seo
        if seo.ACIK: seo_bilgi = seo.incele(p, uygula=False)   # elle yazılan başlık değiştirilmez; yalnızca öneri gösterilir
    except Exception as e:
        log("başlık önerisi atlandı:", repr(e)[:150])
    tid = yazar.taslak_kaydet(tw, el, {"ilk": True}, p, int(time.time() - t0))
    d = yazar.taslak_oku(tid); d["x_paylas"] = bool(veri.get("x_paylas")); d["elle"] = True
    if seo_bilgi: d["seo"] = seo_bilgi
    yazar.taslak_yaz(d)
    return "Taslak hazır: onay bekleyenler listesinde. (" + tid + ")"

def yeni_yazi(veri):
    hatalar = []
    b = re.sub(r"\s+", " ", str(veri.get("baslik") or "")).strip()
    if not 15 <= len(b) <= 75: hatalar.append(f"Başlık 15-75 karakter olmalı (şu an {len(b)}).")
    tur = veri.get("tur") if veri.get("tur") in ("Haber", "Analiz") else "Haber"
    kat = [c for c in (veri.get("kategoriler") or []) if c in yazar.KATEGORILER][:2]
    if not kat: hatalar.append("En az bir kategori seçin.")
    oz = [re.sub(r"\s+", " ", str(x)).strip() for x in (veri.get("ozet") or []) if str(x).strip()][:6]
    if len(oz) < 2: hatalar.append("En az iki öne çıkan madde yazın.")
    g = str(veri.get("govde") or "").strip()
    if not g.startswith("<"):
        paragraflar = [x.strip() for x in re.split(r"\n\s*\n", g) if x.strip()]
        g = "".join((f'<p class="lead">{html.escape(x)}</p>' if i == 0 else
                     (f"<h2>{html.escape(x[3:].strip())}</h2>" if x.startswith("## ") else f"<p>{html.escape(x)}</p>"))
                    for i, x in enumerate(paragraflar))
    if '<p class="lead">' not in g: hatalar.append('Metnin ilk paragrafı giriş (spot) olmalı.')
    if _kelime(g) < 150: hatalar.append(f"Metin en az 150 kelime olmalı (şu an {_kelime(g)}).")
    if re.search(r"<\s*(script|iframe|object|embed|form|style)\b", g, re.I) or re.search(r"\son\w+\s*=", g, re.I): hatalar.append("Metinde betik ya da iframe kullanılamaz.")
    et = [str(t).strip()[:60] for t in (veri.get("etiketler") or []) if str(t).strip()][:8]
    if len(et) < 2: hatalar.append("En az iki etiket yazın.")
    ks = [[str(k[0]).strip()[:200] or str(k[1]), str(k[1]).strip()] for k in (veri.get("kaynaklar") or [])
          if isinstance(k, (list, tuple)) and len(k) == 2 and str(k[1]).startswith(("http://", "https://"))]
    if not ks: hatalar.append("En az bir kaynak bağlantısı ekleyin (resmî kaynak, karar ya da mevzuat).")
    for y in yazar.YASAK:
        if y in (b + " " + g).lower(): hatalar.append("Kullanılmaması gereken ifade: " + y)
    if hatalar: raise ValueError(" ".join(hatalar))
    temiz = {"baslik": b, "tur": tur, "kategoriler": kat, "ozet": oz, "govde": g, "etiketler": et, "kaynaklar": ks,
             "slug": veri.get("slug"), "gorsel": veri.get("gorsel"), "x_paylas": veri.get("x_paylas"),
             "gorsel_aramalari": [x for x in (veri.get("gorsel_aramalari") or []) if str(x).strip()][:4]}
    return is_baslat("Yeni yazı: " + b, _yeni_yazi_isle, temiz)

# ------------------------------------------------------------------ gösterge
def _servis_ozeti():
    son_yukleme = ""
    try:
        import cfyukle; son_yukleme = cfyukle.son_yuklenen()
    except Exception: pass
    head = _git_site("rev-parse", "HEAD")
    return {"calisma_sn": int(time.time() - _BASLANGIC), "site_commit": head[:8], "cf_commit": son_yukleme[:8],
            "cf_esit": bool(head) and head == son_yukleme, "yayin_acik": _env_oku().get("YAYIN_ACIK", "1") == "1"}

def gosterge():
    L = tum_yazilar()
    bugun = simdi().date()
    gunler = [(bugun - datetime.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    sayim = {g: 0 for g in gunler}
    for p in L:
        if p.get("date") in sayim: sayim[p["date"]] += 1
    taslaklar = yazar.uygulama_listesi(gun=2)
    mesajlar = mesaj_listesi()
    kat = {}
    for p in L:
        if p.get("date", "") >= gunler[0]:
            for c in p.get("cats", []): kat[c] = kat.get(c, 0) + 1
    log_satir = _log_satirlari(1500)
    gun_bas = simdi().strftime("%Y-%m-%d")
    hatalar = [s for s in log_satir if s.startswith(gun_bas) and re.search(r"hata|hatası|başarısız|error", s, re.I)]
    e = _env_oku()
    try: maliyet = ortak.bugunku_maliyet()
    except Exception: maliyet = 0
    return {
        "toplam_yazi": len(L), "toplam_analiz": sum(1 for p in L if p.get("tur") == "Analiz"),
        "ay_yazi": sum(1 for p in L if p.get("date", "") >= (simdi() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")), "bugun": sayim.get(gun_bas, 0), "hafta": sum(sayim[g] for g in gunler[-7:]),
        "seri": [{"gun": g, "adet": sayim[g]} for g in gunler],
        "bekleyen": sum(1 for t in taslaklar if t["durum"] == "bekliyor"),
        "bekleyen_liste": [t for t in taslaklar if t["durum"] == "bekliyor"][:6],
        "okunmamis": sum(1 for m in mesajlar if m.get("durum") == "yeni"),
        "son_mesajlar": [m for m in mesajlar if m.get("durum") != "arşiv"][:5],
        "son_yazilar": [_yazi_ozeti(p) for p in L[:8]],
        "kategoriler": sorted(kat.items(), key=lambda x: -x[1])[:8],
        "denetleyen": {**{k: sum(1 for p in L if p.get("_denetleyen") == k) for k in {p.get("_denetleyen") for p in L} if k},
                       "yok": sum(1 for p in L if not p.get("_denetleyen"))},
        "gorselsiz": sum(1 for p in L if not p.get("_gorsel") and p.get("date", "") >= "2026"),
        "maliyet": round(maliyet, 3), "butce": round(ortak.gunluk_sinir(), 2),
        "bugun_hata": len(hatalar), "son_hatalar": hatalar[-5:],
        "servis": _servis_ozeti(), "mesaj_baglanti": mesaj_baglanti_durumu(),
    }

# ------------------------------------------------------------------ kayıtlar, maliyet, yayın geçmişi
def _log_satirlari(n=600):
    p = os.path.join(VERI, "gunluk.log")
    if not os.path.exists(p): return []
    with open(p, "rb") as f:
        f.seek(0, 2); boy = f.tell(); f.seek(max(0, boy - n * 400))
        return f.read().decode("utf-8", "replace").splitlines()[-n:]

_GIZLI = re.compile(r"(sk-ant-[\w-]+|AIza[\w-]{20,}|Bearer\s+[\w.-]+|[A-Za-z0-9_-]{40,})")

def kayitlar(q):
    n = min(3000, max(50, int(q.get("n") or 500)))
    ara = (q.get("q") or "").strip().lower()
    tur = q.get("tur") or ""
    s = _log_satirlari(n * (4 if (ara or tur) else 1))
    if ara: s = [x for x in s if ara in x.lower()]
    if tur == "hata": s = [x for x in s if re.search(r"hata|hatası|başarısız|error|traceback", x, re.I)]
    elif tur == "yayin": s = [x for x in s if re.search(r"YAYINDA|kaldırıldı|Cloudflare|Güncelleme|Düzenleme|GÖRSEL", x)]
    return {"satirlar": [_GIZLI.sub("***", x) for x in s[-n:]]}

def maliyet():
    bugun = ortak._sayac_oku()
    tekil = {}
    for d in _jsonl_oku("sayac_gecmis.jsonl", son=120):   # aynı gün birden çok kez arşivlenmiş olabilir: en büyük maliyetli kayıt geçerli
        g_ = d.get("gun")
        if g_ and g_ != bugun.get("gun") and d.get("maliyet_mikro", 0) >= tekil.get(g_, {}).get("maliyet_mikro", -1): tekil[g_] = d
    gecmis = [tekil[g_] for g_ in sorted(tekil)]
    def satir(d):
        return {"gun": d.get("gun"), "maliyet": round(d.get("maliyet_mikro", 0) / 1e6, 3), "yazi": d.get("yazi", 0),
                "tweet": d.get("tweet", 0), "eleme": d.get("eleme", 0)}
    seri = [satir(d) for d in gecmis][-30:] + [satir(bugun)]
    return {"seri": seri, "butce": round(ortak.gunluk_sinir(), 2),
            "toplam_30": round(sum(x["maliyet"] for x in seri[-30:]), 2), "ham_bugun": {k: v for k, v in bugun.items() if k != "gun"}}

def maliyet_detay(gun=None):
    """seçilen günün maliyetini işlere (gelen paylaşım → taslak → yazı) ve aşamalara böler"""
    gun = gun or simdi().strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", gun): raise ValueError("Geçersiz gün.")
    yol = os.path.join(VERI, "maliyet", gun + ".jsonl")
    kayitlar = []
    if os.path.exists(yol):
        for ln in open(yol, encoding="utf-8", errors="replace"):
            try: kayitlar.append(json.loads(ln))
            except Exception: pass
    isler, asamalar, modeller = {}, {}, {}
    def is_(i):
        return isler.setdefault(i, {"is": i, "usd": 0.0, "cagri": 0, "asamalar": {}, "bilgi": {}, "ilk": None, "son": None})
    for k in kayitlar:
        if k.get("tur") == "bilgi":
            b = is_(k["is"])["bilgi"]
            b.update({a: v for a, v in k.items() if a not in ("ts", "is", "tur") and v})
            continue
        usd = float(k.get("usd") or 0)
        a = k.get("asama") or "diğer"; m = k.get("model") or "?"
        asamalar[a] = asamalar.get(a, 0) + usd
        modeller[m] = modeller.get(m, 0) + usd
        i = k.get("is") or ("bakim:" + (k.get("slug") or a))
        x = is_(i); x["usd"] += usd; x["cagri"] += 1; x["asamalar"][a] = x["asamalar"].get(a, 0) + usd
        x["ilk"] = min(x["ilk"] or k["ts"], k["ts"]); x["son"] = max(x["son"] or k["ts"], k["ts"])
        if not x["bilgi"].get("slug") and k.get("slug"): x["bilgi"].update(slug=k["slug"], baslik=k.get("baslik"), kaynak="bakım")
    # taslak durumları (yayınlandı mı?) ve yazı başına birleştirme
    yazilar, elenen, digerleri = {}, {"adet": 0, "usd": 0.0, "ornekler": []}, []
    for x in isler.values():
        if x["cagri"] == 0: continue
        b = x["bilgi"]
        x["usd"] = round(x["usd"], 6); x["asamalar"] = {a: round(v, 6) for a, v in sorted(x["asamalar"].items(), key=lambda z: -z[1])}
        if b.get("tid"):
            d = yazar.taslak_oku(b["tid"]) or {}
            b["durum"] = d.get("durum"); b["url"] = d.get("url")
        if b.get("slug") or b.get("tid"):
            anahtar = b.get("slug") or b.get("tid")
            y = yazilar.setdefault(anahtar, {"slug": b.get("slug"), "tid": b.get("tid"), "baslik": b.get("baslik"), "durum": b.get("durum"),
                                             "url": b.get("url"), "kaynak": b.get("kaynak"), "hesap": b.get("hesap"), "usd": 0.0, "asamalar": {}, "isler": 0, "ts": x["ilk"]})
            y["usd"] = round(y["usd"] + x["usd"], 6); y["isler"] += 1
            for a, v in x["asamalar"].items(): y["asamalar"][a] = round(y["asamalar"].get(a, 0) + v, 6)
            for a in ("baslik", "durum", "url", "tid", "hesap"):
                if not y.get(a) and b.get(a): y[a] = b[a]
            if b.get("kaynak") and b.get("kaynak") != "bakım": y["kaynak"] = b["kaynak"]
        elif b.get("sonuc") == "elendi" or (not b.get("sonuc") and set(x["asamalar"]) <= {"eleme"}):
            elenen["adet"] += 1; elenen["usd"] += x["usd"]
            elenen["ornekler"].append({"konu": b.get("konu"), "hesap": b.get("hesap"), "kaynak": b.get("kaynak"), "usd": x["usd"], "neden": b.get("neden")})
        else:
            digerleri.append({"konu": b.get("konu") or b.get("baslik") or "(bağlamsız çağrı)", "sonuc": b.get("sonuc") or "—", "hesap": b.get("hesap"),
                              "kaynak": b.get("kaynak"), "usd": x["usd"], "asamalar": x["asamalar"], "ts": x["ilk"]})
    elenen["usd"] = round(elenen["usd"], 6)
    elenen["ornekler"] = sorted(elenen["ornekler"], key=lambda z: -z["usd"])[:30]
    toplam_kayit = round(sum(asamalar.values()), 6)
    gunluk = (ortak._sayac_oku() if gun == simdi().strftime("%Y-%m-%d") else
              next((d for d in reversed(_jsonl_oku("sayac_gecmis.jsonl", son=120)) if d.get("gun") == gun), {}))
    return {"gun": gun, "toplam_kayit": toplam_kayit, "toplam_gun": round(gunluk.get("maliyet_mikro", 0) / 1e6, 6),
            "ilk_kayit": min((k["ts"] for k in kayitlar), default=None),
            "asamalar": sorted(([a, round(v, 6)] for a, v in asamalar.items()), key=lambda z: -z[1]),
            "modeller": sorted(([a, round(v, 6)] for a, v in modeller.items()), key=lambda z: -z[1]),
            "yazilar": sorted(yazilar.values(), key=lambda z: -z["usd"]), "elenen": elenen,
            "digerleri": sorted(digerleri, key=lambda z: -z["usd"])[:60],
            "gunler": sorted((f[:-6] for f in os.listdir(os.path.join(VERI, "maliyet")) if f.endswith(".jsonl")), reverse=True) if os.path.isdir(os.path.join(VERI, "maliyet")) else []}

def yayin_gecmisi():
    satirlar = _git_site("log", "-30", "--format=%h|%ad|%s", "--date=format:%d.%m %H:%M").splitlines()
    return {"commitler": [dict(zip(("kisa", "zaman", "mesaj"), s.split("|", 2))) for s in satirlar if "|" in s],
            "servis": _servis_ozeti(), "islemler": list(reversed(_jsonl_oku(_ISLEM_GUNLUGU, son=40)))}

def yeniden_derle():
    def hazirla(): return None
    yazar._gonder("Panelden yeniden derleme", hazirla)
    import cfyukle
    if cfyukle.acik():
        ok = cfyukle.yukle(SITE_DEPO, "panelden yeniden yükleme", cfyukle.anlik_kopya(SITE_DEPO))
        return "Site derlendi ve Cloudflare'e yüklendi." if ok else "Site derlendi; Cloudflare yüklemesi başarısız (kayıtlara bakın)."
    return "Site derlendi ve GitHub'a gönderildi."

def indexnow_bildir(url):
    if not url.startswith(SITE + "/"): raise ValueError("Yalnızca hukukihaberler.com adresleri bildirilebilir.")
    kod, _ = http_json("https://api.indexnow.org/indexnow", "POST", {}, {
        "host": "hukukihaberler.com", "key": ortak.INDEXNOW_ANAHTAR, "keyLocation": f"{SITE}/{ortak.INDEXNOW_ANAHTAR}.txt", "urlList": [url]})
    return f"IndexNow yanıtı: {kod}"

# ------------------------------------------------------------------ kaynak listeleri (X hesapları, resmî sayfalar)
def kaynak_listeleri():
    return {ad: {"metin": open(ortak.ayar_dosyasi(ad), encoding="utf-8").read(),
                 "ozellestirilmis": os.path.exists(os.path.join(VERI, ad))}
            for ad in ("hesaplar.txt", "kaynaklar.txt")}

def kaynak_kaydet(veri):
    for ad in ("hesaplar.txt", "kaynaklar.txt"):
        if ad not in veri: continue
        metin = str(veri[ad]).replace("\r\n", "\n")
        if len(metin) > 60000: raise ValueError(ad + " çok uzun.")
        for i, ln in enumerate(metin.splitlines(), 1):
            ln = ln.strip()
            if not ln or ln.startswith("#"): continue
            if ad == "hesaplar.txt":
                if not (re.fullmatch(r"\[[a-z_-]+\]", ln) or re.fullmatch(r"@?[A-Za-z0-9_]{1,30}", ln)):
                    raise ValueError(f"hesaplar.txt satır {i}: geçersiz kullanıcı adı ya da grup ({ln[:40]})")
            else:
                parca = [x.strip() for x in ln.split("|", 2)]
                if len(parca) != 3 or not parca[1].startswith(("http://", "https://")):
                    raise ValueError(f"kaynaklar.txt satır {i}: 'Ad | adres | desen' biçiminde olmalı")
                if parca[2] != "*":
                    try: re.compile(parca[2])
                    except re.error as e: raise ValueError(f"kaynaklar.txt satır {i}: düzenli ifade hatalı ({e})")
        yol = os.path.join(VERI, ad)
        open(yol + ".tmp", "w", encoding="utf-8").write(metin.rstrip() + "\n"); os.replace(yol + ".tmp", yol)
        _islem_kaydet("kaynak listesi kaydedildi", ad)
    return "Kaydedildi. X hesap kuralları servis yeniden başlatılınca uygulanır; resmî sayfa taraması bir sonraki turda yeni listeyi okur."

def kaynak_varsayilana_don(ad):
    if ad not in ("hesaplar.txt", "kaynaklar.txt"): raise ValueError("Geçersiz dosya.")
    p = os.path.join(VERI, ad)
    if os.path.exists(p): os.rename(p, p + f".{int(time.time())}.yedek")
    return "Varsayılan listeye dönüldü."

# ------------------------------------------------------------------ ayarlar (.env)
AYARLAR = [
    # (anahtar, etiket, tür, varsayılan, açıklama, grup)
    ("GENISLETME_TASLAK", "Genişletme taslakları", "bool", "0", "Kısa haberler için ayrı genişletme taslağı hazırlansın.", "Yayın"),
    ("SEO_BASLIK", "Başlığı aranan ifadeye göre seç", "bool", "1", "Taslak hazırlanırken Google önerileri ve Search Console sorgularına bakılır; uygun ifade başlığa ve etiketlere işlenir (elle yazılan yazılarda yalnızca öneri gösterilir).", "Yayın"),
    ("FIRSAT_GOSTERIM", "Fırsat sorgusu için en az gösterim", "int", "5", "Search Console'da 28 günde en az bu kadar gösterim alıp az tıklanan sorgular başlık seçiminde öne çıkar; trafik arttıkça yükseltin.", "Yayın"),
    ("ONHAZIR", "Taslakları yayına hazır tut (hızlı yayın)", "bool", "1", "Onay bekleyen en yeni 2 haber taslağı sitede derlenip denetlenmiş ve dosyaları Cloudflare'e gönderilmiş halde bekletilir; Yayınla deyince birkaç saniyede yayına girer. Arada başka yayın olduysa normal yoldan (yaklaşık 20 sn) yayımlanır.", "Yayın"),
    ("CF_YUKLEYICI", "Cloudflare yükleme yöntemi", "secim:api|wrangler", "api", "api: siteyi doğrudan Cloudflare API'siyle yükler (yaklaşık 5 sn; sorun olursa kendiliğinden wrangler'a geçer). wrangler: Cloudflare'in kendi aracı (20-30 sn).", "Yayın"),
    ("GUNCELLEME_OTOMATIK", "Güncellemeler onaysız yayınlansın", "bool", "1", "Yayındaki bir habere gelen yeni gelişme (güncelleme notu, düzeltme) isim, itham ve usul denetimlerinden geçerse editör onayı beklemeden habere eklenir. Kapatılırsa güncellemeler onay bekleyenlere düşer. Yeni haberler her durumda editör onayıyla yayınlanır.", "Yayın"),
    ("MESAI_OTOMATIK", "Otomatik ek mesai", "bool", "1", "Aylık API kredisinin kullanılmadan yanacak kısmı varsa bot art arda web'de güncel ve geçmiş (1 hafta - 4 ay) hukuki gelişmeleri arar; sitede olmayanlar normal onay hattına girer. Kredi yanmayacak duruma gelince ya da günlük pay dolunca kendiliğinden durur.", "Yayın"),
    ("CF_YUKLE", "Cloudflare'e doğrudan yükleme", "bool", "0", "Her yayından sonra site Cloudflare Pages'e yüklenir.", "Yayın"),
    ("GUNLUK_BUTCE_USD", "Günlük bütçe (USD)", "float", "3", "Aylık kredi takibi kuruluysa kullanılmaz (günlük pay krediden hesaplanır); kredi girilmemişse aşılınca yeni yazım durur.", "Bütçe ve sınırlar"),
    ("GUNLUK_YAZI_SINIRI", "Günlük yazı sınırı", "int", "0", "0 = sınırsız.", "Bütçe ve sınırlar"),
    ("SAATLIK_YAZI_SINIRI", "Saatlik yazı sınırı", "int", "0", "0 = sınırsız.", "Bütçe ve sınırlar"),
    ("GUNLUK_TWEET_SINIRI", "Günlük işlenecek paylaşım sınırı", "int", "0", "0 = sınırsız.", "Bütçe ve sınırlar"),
    ("GUNLUK_ELEME_SINIRI", "Günlük eleme sınırı", "int", "0", "0 = sınırsız.", "Bütçe ve sınırlar"),
    ("MODEL_ELEME", "Eleme modeli", "text", "claude-haiku-5-5", "Gelen paylaşımları ön eleyen model.", "Yazım"),
    ("MODEL_YAZIM", "Yazım modeli", "text", "claude-sonnet-5-5", "Haber metnini yazan model.", "Yazım"),
    ("YAZIM_MODU", "Yazım modu", "secim:iki|tek", "iki", "iki: önce araştırma sonra yazım; tek: tek adımda.", "Yazım"),
    ("NTFY_KONU", "Bildirim kanalı (taslaklar)", "text", "", "ntfy.sh konu adı.", "Bildirimler"),
    ("NTFY_DURUM", "Bildirim kanalı (yayın/hata)", "text", "", "Boşsa taslak kanalı kullanılır.", "Bildirimler"),
]
GIZLI_AYARLAR = [("ANTHROPIC_API_KEY", "Anthropic API anahtarı"), ("X_BEARER", "X API bearer"), ("GEMINI_API_KEY", "Gemini API anahtarı"),
                 ("CLOUDFLARE_API_TOKEN", "Cloudflare API anahtarı"), ("CLOUDFLARE_ACCOUNT_ID", "Cloudflare hesap kimliği"),
                 ("PEXELS_KEY", "Pexels anahtarı"), ("PIXABAY_KEY", "Pixabay anahtarı"), ("PANEL_SIFRE", "Panel giriş şifresi")]

def ayarlar():
    e = _env_oku()
    return {"ayarlar": [{"anahtar": k, "etiket": et, "tur": t, "deger": e.get(k, v), "aciklama": a, "grup": g} for k, et, t, v, a, g in AYARLAR],
            "gizli": [{"anahtar": k, "etiket": et, "tanimli": bool(e.get(k))} for k, et in GIZLI_AYARLAR]}

def _env_yaz(degisen):
    satirlar = open(ENV_DOSYA, encoding="utf-8").read().splitlines() if os.path.exists(ENV_DOSYA) else []
    kalan = dict(degisen)
    for i, ln in enumerate(satirlar):
        k = ln.split("=", 1)[0].strip()
        if not ln.strip().startswith("#") and "=" in ln and k in kalan:
            satirlar[i] = f"{k}={kalan.pop(k)}"
    satirlar += [f"{k}={v}" for k, v in kalan.items()]
    if os.path.exists(ENV_DOSYA): shutil.copy2(ENV_DOSYA, os.path.join(VERI, "env.yedek"))
    open(ENV_DOSYA + ".tmp", "w", encoding="utf-8").write("\n".join(satirlar) + "\n")
    try: os.chmod(ENV_DOSYA + ".tmp", 0o600)
    except Exception: pass
    os.replace(ENV_DOSYA + ".tmp", ENV_DOSYA)

def ayar_kaydet(veri):
    tanim = {k: (t, v) for k, _, t, v, _, _ in AYARLAR}
    degisen = {}
    for k, v in (veri.get("ayarlar") or {}).items():
        if k not in tanim: raise ValueError("Bilinmeyen ayar: " + k)
        t = tanim[k][0]; v = str(v).strip()
        if t == "bool": v = "1" if v in ("1", "true", "True", "on") else "0"
        elif t == "int":
            if not re.fullmatch(r"\d{1,6}", v): raise ValueError(k + " bir tam sayı olmalı.")
        elif t == "float":
            if not re.fullmatch(r"\d{1,5}(\.\d{1,3})?", v): raise ValueError(k + " bir sayı olmalı (ör. 10 ya da 7.5).")
        elif t.startswith("secim:"):
            if v not in t[6:].split("|"): raise ValueError(k + " için geçersiz seçim.")
        elif not re.fullmatch(r"[\w.:/-]{0,120}", v): raise ValueError(k + " geçersiz karakter içeriyor.")
        degisen[k] = v
    izinli_gizli = {k for k, _ in GIZLI_AYARLAR}
    for k, v in (veri.get("gizli") or {}).items():
        v = str(v).strip()
        if k not in izinli_gizli: raise ValueError("Bilinmeyen anahtar: " + k)
        if not v: continue
        if not re.fullmatch(r"[\x21-\x7e]{8,400}", v): raise ValueError(k + " geçersiz görünüyor (boşluk içermemeli, en az 8 karakter).")
        degisen[k] = v
    if not degisen: raise ValueError("Değişiklik yok.")
    _env_yaz(degisen)
    _islem_kaydet("ayarlar kaydedildi", ", ".join(sorted(degisen)))
    if "PANEL_SIFRE" in degisen: tum_oturumlari_kapat()
    return "Kaydedildi. Değişikliklerin geçerli olması için servisi yeniden başlatın."

def yeniden_baslat():
    _islem_kaydet("servis yeniden başlatıldı")
    log("panel: servis yeniden başlatılıyor (systemd yeniden açar, açılışta kod güncellenir)")
    threading.Timer(1.5, lambda: os._exit(0)).start()
    return "Servis yeniden başlatılıyor; yaklaşık 30 saniye sonra panel yeniden açılır."

# ------------------------------------------------------------------ okur mesajları
def _mesajlar_oku():
    try: return json.load(open(_MESAJ_DOSYA, encoding="utf-8"))
    except Exception: return []

def _mesajlar_yaz(L):
    open(_MESAJ_DOSYA + ".tmp", "w", encoding="utf-8").write(json.dumps(L, ensure_ascii=False, indent=1))
    try: os.chmod(_MESAJ_DOSYA + ".tmp", 0o600)
    except Exception: pass
    os.replace(_MESAJ_DOSYA + ".tmp", _MESAJ_DOSYA)

def mesaj_listesi():
    return sorted(_mesajlar_oku(), key=lambda m: -m.get("ts", 0))

def mesaj_guncelle(no, veri):
    with _mesaj_kilit:
        L = _mesajlar_oku()
        m = next((x for x in L if x.get("no") == no), None)
        if not m: raise ValueError("Mesaj bulunamadı.")
        if "durum" in veri:
            if veri["durum"] not in ("yeni", "okundu", "yanıtlandı", "arşiv"): raise ValueError("Geçersiz durum.")
            m["durum"] = veri["durum"]; m["durum_ts"] = time.time()
        if "not" in veri: m["not"] = str(veri["not"])[:2000]
        if veri.get("sil"):
            L = [x for x in L if x.get("no") != no]
        _mesajlar_yaz(L)
    return "Kaydedildi."

def _mesaj_anahtari():
    if not os.path.exists(_MESAJ_ANAHTAR_DOSYA):
        open(_MESAJ_ANAHTAR_DOSYA, "w").write(secrets.token_hex(24))
        try: os.chmod(_MESAJ_ANAHTAR_DOSYA, 0o600)
        except Exception: pass
    return open(_MESAJ_ANAHTAR_DOSYA).read().strip()

def mesaj_baglanti_durumu():
    try: d = json.load(open(_MESAJ_CF_DOSYA, encoding="utf-8"))
    except Exception: d = {}
    return {"hazir": bool(d.get("tamam")), "hata": d.get("hata"), "son_esitleme": d.get("son_esitleme"), "son_hata": d.get("son_hata")}

def _cf_anahtar_kur():
    """mesaj okuma anahtarını Cloudflare Pages projesine gizli ortam değişkeni olarak yazar (bir kez) ve siteyi yeniden yükler"""
    e = _env_oku()
    tok, hesap, proje = e.get("CLOUDFLARE_API_TOKEN"), e.get("CLOUDFLARE_ACCOUNT_ID"), e.get("CF_PROJE", "hukukihaberler-yayin")
    if not (tok and hesap): return False, "Cloudflare anahtarı ya da hesap kimliği tanımlı değil."
    govde = {"deployment_configs": {"production": {"env_vars": {"MESAJ_ANAHTAR": {"type": "secret_text", "value": _mesaj_anahtari()}}}}}
    kod, js = http_json(f"https://api.cloudflare.com/client/v4/accounts/{hesap}/pages/projects/{proje}", "PATCH",
                        {"Authorization": "Bearer " + tok}, govde, 30)
    if kod != 200 or not (isinstance(js, dict) and js.get("success")):
        hata = "; ".join(x.get("message", "") for x in (js.get("errors") or [])) if isinstance(js, dict) else str(js)[:200]
        return False, f"Cloudflare ortam değişkeni yazılamadı ({kod}): {hata[:200]}"
    import cfyukle
    if cfyukle.acik(): cfyukle.yukle(SITE_DEPO, "mesaj anahtarı etkinleştirme", cfyukle.anlik_kopya(SITE_DEPO))
    return True, ""

def _cf_durum_yaz(**k):
    try: d = json.load(open(_MESAJ_CF_DOSYA, encoding="utf-8"))
    except Exception: d = {}
    d.update(k); json.dump(d, open(_MESAJ_CF_DOSYA, "w", encoding="utf-8"), ensure_ascii=False)

def mesaj_esitle():
    """sitedeki yeni mesajları alır, buraya kaydeder, sitedeki kopyalarını siler; yeni mesaj sayısını döndürür"""
    anahtar = _mesaj_anahtari()
    istek = urllib.request.Request(SITE + "/api/iletisim", headers={"Authorization": "Bearer " + anahtar, "User-Agent": "hh-panel/1.0"})
    try:
        with urllib.request.urlopen(istek, timeout=30) as r: js = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _cf_durum_yaz(son_hata="Site mesaj anahtarını henüz tanımıyor (Cloudflare ayarı bekleniyor).")
            return None
        raise
    gelen = js.get("mesajlar") or []
    yeni = []
    with _mesaj_kilit:
        L = _mesajlar_oku(); var = {m.get("no") for m in L}
        for m in gelen:
            if m.get("no") in var: continue
            m = {k: v for k, v in m.items() if k != "anahtar"}
            m["ts"] = m.get("ts", 0) / 1000 if m.get("ts", 0) > 1e11 else m.get("ts", 0)
            m["durum"] = "yeni"; m["alindi"] = time.time()
            L.append(m); yeni.append(m)
        if yeni: _mesajlar_yaz(L)
    if gelen:
        anahtarlar = ",".join(m["anahtar"] for m in gelen if m.get("anahtar"))
        try:
            urllib.request.urlopen(urllib.request.Request(SITE + "/api/iletisim?k=" + urllib.parse.quote(anahtarlar, safe=",:-"), method="DELETE",
                                   headers={"Authorization": "Bearer " + anahtar, "User-Agent": "hh-panel/1.0"}), timeout=30).read()
        except Exception as e:
            log("mesajlar sitede silinemedi:", e)
    for m in yeni:
        log("YENİ OKUR MESAJI:", m.get("no"), m.get("konu_ad"), "|", m.get("baslik", "")[:80])
        try:
            from ortak import NTFY_KONU, ntfy_json, ONIZLEME_ADRES
            ntfy_json(NTFY_KONU, "Yeni okur mesajı · " + (m.get("konu_ad") or ""), (m.get("baslik") or "")[:120],
                      tikla=(ONIZLEME_ADRES.rstrip("/") + "/yonetim/#/mesajlar/" + m["no"]) if ONIZLEME_ADRES else None)
        except Exception as e:
            log("mesaj bildirimi gönderilemedi:", e)
    _cf_durum_yaz(son_esitleme=time.time(), son_hata=None)
    return len(yeni)

_hemen = {"son": 0.0, "kilit": threading.Lock()}

def mesaj_hemen_esitle():
    """formdan gelen bildirimle eşitleme (aynı anda tek iş; 3 sn içindeki tekrarlar birleşir)"""
    if time.time() - _hemen["son"] < 3 or not _hemen["kilit"].acquire(blocking=False): return
    _hemen["son"] = time.time()
    def is_():
        try:
            time.sleep(1)
            n = mesaj_esitle()
            if n: log(f"okur mesajı anında alındı ({n})")
        except Exception as e: log("anlık mesaj eşitleme hatası:", repr(e)[:200])
        finally: _hemen["kilit"].release()
    threading.Thread(target=is_, daemon=True).start()

def mesaj_dongu(aralik=300):   # yedek: anlık bildirim kaçarsa 5 dakikada bir denetlenir (Cloudflare KV ücretsiz liste sınırı günde 1000)
    time.sleep(20)
    try: _zeski_temizle()
    except Exception as e: log("ziyaret temizliği:", e)
    while True:
        try:
            d = mesaj_baglanti_durumu()
            if not d["hazir"]:
                tamam, hata = _cf_anahtar_kur()
                _cf_durum_yaz(tamam=tamam, hata=hata or None, kurulum_ts=time.time())
                if tamam: log("panel: okur mesajı anahtarı Cloudflare'e tanımlandı")
                else: log("panel:", hata)
            if mesaj_baglanti_durumu()["hazir"]:
                mesaj_esitle()
        except Exception as e:
            _cf_durum_yaz(son_hata=str(e)[:200])
            log("mesaj eşitleme hatası:", repr(e)[:200])
        time.sleep(aralik if mesaj_baglanti_durumu()["hazir"] else 1800)

# ------------------------------------------------------------------ HTTP
_TURLER = {".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg"}
_CSP = ("default-src 'self'; img-src 'self' data: blob: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "frame-src 'self'; frame-ancestors 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'")

def _gonder(h, kod, tur, veri, cerez=None, ek=None):
    h.send_response(kod)
    h.send_header("Content-Type", tur + ("; charset=utf-8" if tur.startswith(("text/", "application/j")) else ""))
    h.send_header("Cache-Control", "no-store"); h.send_header("X-Robots-Tag", "noindex, nofollow")
    h.send_header("X-Content-Type-Options", "nosniff"); h.send_header("Referrer-Policy", "same-origin")
    h.send_header("X-Frame-Options", "SAMEORIGIN"); h.send_header("Content-Security-Policy", _CSP)
    if cerez: h.send_header("Set-Cookie", cerez)
    for k, v in (ek or {}).items(): h.send_header(k, v)
    h.send_header("Content-Length", str(len(veri)))
    h.end_headers(); h.wfile.write(veri)

def _js(h, kod, obj, cerez=None):
    _gonder(h, kod, "application/json", json.dumps(obj, ensure_ascii=False, default=str).encode(), cerez)

def _govde(h):
    n = int(h.headers.get("Content-Length") or 0)
    if n > 2_000_000: raise ValueError("İstek çok büyük.")
    return json.loads(h.rfile.read(n).decode("utf-8")) if n else {}

def isle(h, yontem):
    try:
        return _isle(h, yontem)
    except ValueError as e:
        return _js(h, 422, {"hata": str(e)})
    except Exception as e:
        log("panel hatası:", repr(e)[:300])
        return _js(h, 500, {"hata": "Sunucu hatası: " + str(e)[:200]})

def _isle(h, yontem):
    u = urllib.parse.urlsplit(h.path)
    yol = u.path.rstrip("/") or "/yonetim"
    q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

    # arayüz dosyaları (oturumsuz da açılır; veri yalnızca API'den gelir)
    if yontem == "GET" and yol == "/yonetim":
        s = open(os.path.join(ARAYUZ, "index.html"), encoding="utf-8").read()
        for ad in ("app.js", "app.css"):
            s = s.replace("/yonetim/statik/" + ad, f"/yonetim/statik/{ad}?v={int(os.path.getmtime(os.path.join(ARAYUZ, ad)))}")
        return _gonder(h, 200, "text/html", s.encode())
    m = re.fullmatch(r"/yonetim/statik/([a-z0-9_-]+\.(js|css|svg|png))", yol)
    if yontem == "GET" and m:
        p = os.path.join(ARAYUZ, m.group(1))
        if not os.path.exists(p): return _gonder(h, 404, "text/plain", b"yok")
        return _gonder(h, 200, _TURLER["." + m.group(2)], open(p, "rb").read())

    if yol == "/yonetim/api/giris" and yontem == "POST":
        kod, js, cerez = giris(h, _govde(h))
        return _js(h, kod, js, cerez)
    if yol == "/yonetim/api/mesaj-bildir" and yontem == "POST":
        # sitedeki iletişim formu yeni mesajı kaydettiği anda haber verir; mesajlar hemen buraya alınır
        gelen = (h.headers.get("Authorization") or "")[7:]
        try: beklenen = _mesaj_anahtari()
        except Exception: beklenen = ""
        if not beklenen or not hmac.compare_digest(gelen.encode(), beklenen.encode()):
            return _js(h, 401, {"hata": "yetkisiz"})
        mesaj_hemen_esitle()
        return _js(h, 202, {"tamam": True})
    if not _oturum_gecerli(h):
        return _js(h, 401, {"hata": "Oturum açın.", "giris": True})
    if yontem == "POST" and h.headers.get("X-HH-Panel") != "1":
        return _js(h, 403, {"hata": "Geçersiz istek."})

    m = re.fullmatch(r"/yonetim/gorsel/([a-z0-9-]{3,160})\.jpg", yol)
    if m and yontem == "GET":
        for alt in ("m", ""):
            p = os.path.join(SITE_DEPO, "site", "gorsel", alt, m.group(1) + ".jpg")
            if os.path.exists(p): return _gonder(h, 200, "image/jpeg", open(p, "rb").read())
        return _gonder(h, 404, "text/plain", b"yok")

    a = yol[len("/yonetim/api"):] if yol.startswith("/yonetim/api") else None
    if a is None: return _js(h, 404, {"hata": "Yol bulunamadı."})
    G = yontem == "GET"
    veri = {} if G else _govde(h)

    if a == "/cikis" and not G: return _js(h, 200, {"tamam": True}, cikis(h))
    if a == "/oturum" and G:
        import yazar_yonetimi
        return _js(h, 200, {"tamam": True, "kategoriler": yazar.KATEGORILER, "site": SITE, "konular": KONU_ADLARI, "yazarlar": yazar_yonetimi.ozet()})
    if a == "/gosterge" and G: return _js(h, 200, gosterge())
    if a == "/ziyaret" and G: return _js(h, 200, ziyaret_ozeti(q.get("gun") or 14))
    if a == "/google/durum" and G: return _js(h, 200, gsc_durum())
    if a == "/google/sertifika" and not G: return _js(h, 200, {"sertifika": gsc_sertifika()})
    if a == "/google/eposta" and not G: return _js(h, 200, {"eposta": gsc_eposta_kaydet(veri.get("eposta")), "durum": gsc_durum()})
    if a == "/google/anahtar" and not G: return _js(h, 200, {"eposta": gsc_anahtar_kaydet(str(veri.get("json") or "")), "durum": gsc_durum()})
    if a == "/google" and G:
        try: return _js(h, 200, gsc_ozet(q))
        except RuntimeError as e: return _js(h, 409, {"hata": str(e)})
    m = re.fullmatch(r"/is/([0-9a-f]{12})", a)
    if m and G:
        i = _isler.get(m.group(1))
        return _js(h, 200 if i else 404, i or {"hata": "İş bulunamadı."})

    # taslaklar (onay)
    if a == "/taslaklar" and G:
        gun = min(60, max(1, int(q.get("gun") or 14)))
        return _js(h, 200, {"taslaklar": yazar.uygulama_listesi(gun=gun)})
    m = re.fullmatch(r"/taslak/([0-9a-z-]+)(/onizleme|/karar|/duzenle|/gorseller|/gorsel)?", a)
    if m:
        tid, alt = m.group(1), m.group(2) or ""
        d = yazar.taslak_oku(tid)
        if not d: return _js(h, 404, {"hata": "Taslak bulunamadı."})
        if G and alt == "":
            o = yazar.uygulama_detay(d); o["govde"] = d["post"].get("body", ""); o["x_paylas"] = d.get("x_paylas", True)
            o["eleme"] = d.get("eleme"); o["etiketler"] = d["post"].get("tags", []); o["tur_yazi"] = d["post"].get("tur", "Haber")
            return _js(h, 200, o)
        if G and alt == "/onizleme":
            return _gonder(h, 200, "text/html", yazar.onizleme_html(d, butonsuz=True).encode())
        if G and alt == "/gorseller":
            return _js(h, 200, {"adaylar": yazar.gorsel_adaylari(tid, (q.get("q") or "").strip()[:80] or None)})
        if not G and alt == "/karar":
            komut = str(veri.get("komut", ""))
            kod, js = yazar.uygulama_karar(tid, komut)
            _islem_kaydet("taslak " + komut, d["post"]["title"])
            return _js(h, kod, js)
        if not G and alt == "/duzenle":
            tamam, mesaj = yazar.taslak_duzenle(tid, veri)
            if tamam and "x_paylas" in veri:
                with yazar._taslak_kilit:
                    d2 = yazar.taslak_oku(tid); d2["x_paylas"] = bool(veri["x_paylas"]); yazar.taslak_yaz(d2)
            return _js(h, 200 if tamam else 422, {"mesaj": mesaj} if tamam else {"hata": mesaj})
        if not G and alt == "/gorsel":
            tamam, mesaj = yazar.gorsel_degistir(tid, str(veri.get("secim", "")))
            return _js(h, 200 if tamam else 422, {"mesaj": mesaj} if tamam else {"hata": mesaj})
        return _js(h, 405, {"hata": "Yöntem desteklenmiyor."})

    # yayındaki yazılar
    if a == "/yazilar" and G: return _js(h, 200, yazi_listesi(q))
    m = re.fullmatch(r"/yazi/([a-z0-9-]{3,160})(/kaydet|/kaldir|/guncelleme|/gorsel-yenile)?", a)
    if m:
        slug, alt = m.group(1), m.group(2) or ""
        if G and alt == "":
            o = yazi_detay(slug)
            return _js(h, 200 if o else 404, o or {"hata": "Yazı bulunamadı."})
        if not next((x for x in tum_yazilar() if x["slug"] == slug), None): return _js(h, 404, {"hata": "Yazı bulunamadı."})
        if not G and alt == "/kaydet":
            yeni, not_ = yazi_dogrula(veri)   # doğrulama hemen (hata anında döner), derleme ve yayın arka planda
            return _js(h, 202, {"is": is_baslat("Yazı düzenlendi: " + slug, yazi_kaydet, slug, yeni, not_)})
        if not G and alt == "/kaldir":
            if str(veri.get("onay")) != slug: raise ValueError("Onay için yazının kısa adresini (slug) yazın.")
            return _js(h, 202, {"is": is_baslat("Yayından kaldırıldı: " + slug, yazar.yayindan_kaldir, slug, str(veri.get("neden") or "panel"))})
        if not G and alt == "/guncelleme":
            n = re.sub(r"\s+", " ", str(veri.get("not") or "")).strip()
            if not 20 <= len(n) <= 700: raise ValueError("Güncelleme notu 20-700 karakter olmalı.")
            return _js(h, 202, {"is": is_baslat("Güncelleme notu: " + slug, guncelleme_notu, slug, veri)})
        if not G and alt == "/gorsel-yenile":
            return _js(h, 202, {"is": is_baslat("Görsel yenilendi: " + slug, lambda: (yazar.yayindaki_gorseli_yenile(slug) is not None) and "Görsel yenilendi ve yayına gönderildi.")})
        return _js(h, 405, {"hata": "Yöntem desteklenmiyor."})
    if a == "/yeni-yazi" and not G:
        return _js(h, 202, {"is": yeni_yazi(veri)})

    # mesajlar
    if a == "/mesajlar" and G:
        return _js(h, 200, {"mesajlar": mesaj_listesi(), "baglanti": mesaj_baglanti_durumu()})
    if a == "/mesajlar/esitle" and not G:
        if not mesaj_baglanti_durumu()["hazir"]:
            tamam, hata = _cf_anahtar_kur(); _cf_durum_yaz(tamam=tamam, hata=hata or None)
            if not tamam: raise ValueError(hata)
        n = mesaj_esitle()
        return _js(h, 200, {"mesaj": "Site henüz mesaj anahtarını tanımıyor; Cloudflare yüklemesi bitince yeniden deneyin." if n is None else f"{n} yeni mesaj alındı."})
    m = re.fullmatch(r"/mesaj/(HH-\d{6}-[A-Z0-9]{3,8})", a)
    if m and not G: return _js(h, 200, {"mesaj": mesaj_guncelle(m.group(1), veri)})

    # kaynaklar, ayarlar, sistem
    if a == "/kaynaklar" and G: return _js(h, 200, kaynak_listeleri())
    if a == "/kaynaklar" and not G: return _js(h, 200, {"mesaj": kaynak_kaydet(veri)})
    if a == "/kaynaklar/varsayilan" and not G: return _js(h, 200, {"mesaj": kaynak_varsayilana_don(str(veri.get("ad")))})
    if a == "/ayarlar" and G: return _js(h, 200, ayarlar())
    if a == "/ayarlar" and not G: return _js(h, 200, {"mesaj": ayar_kaydet(veri)})
    if a == "/maliyet" and G: return _js(h, 200, maliyet())
    if a == "/akis" and G:
        import akis_panel
        return _js(h, 200, akis_panel.liste(q))
    if a == "/akis/capraz" and G:   # bir paylaşım için çapraz teyit denemesi (değişiklik yapmaz)
        import akis_panel
        tw = akis_panel._tw_bul(str(q.get("url") or ""))
        if not tw: return _js(h, 404, {"hata": "Paylaşım bulunamadı."})
        t0 = time.time(); ct = yazar.capraz_teyit(tw, {})
        return _js(h, 200, {"teyit": bool(ct), "hesaplar": ct, "sn": round(time.time() - t0, 1)})
    if a == "/akis/yaz" and not G:
        import akis_panel
        tw = akis_panel.yine_de_yaz_hazirla(str(veri.get("url") or ""))
        return _js(h, 202, {"is": is_baslat("Yine de yaz: " + (tw.get("metin") or "")[:60], akis_panel.yine_de_yaz, tw)})
    if a == "/rozet" and G:
        with _mesaj_kilit: L = _mesajlar_oku()
        bek = sum(1 for t in yazar.uygulama_listesi(gun=2) if t["durum"] == "bekliyor")
        son = max((m.get("alindi") or 0 for m in L), default=0)
        return _js(h, 200, {"okunmamis": sum(1 for m in L if m.get("durum") == "yeni"), "bekleyen": bek, "son_mesaj": son})
    if a == "/yazarlar" and G:
        import yazar_yonetimi
        return _js(h, 200, yazar_yonetimi.liste())
    if a == "/yazarlar/inceleme" and not G:
        import yazar_yonetimi
        yazar_yonetimi.inceleme_dogrula(veri)   # hatalar hemen dönsün
        return _js(h, 202, {"is": is_baslat("İnceleme atamaları", yazar_yonetimi.inceleme_kaydet, veri)})
    m = re.fullmatch(r"/yazar-kayit(?:/([a-z0-9-]+))?(/sil)?", a)
    if m and not G:
        import yazar_yonetimi
        kod, sil_ = m.group(1), m.group(2)
        if sil_: return _js(h, 202, {"is": is_baslat("Yazar kaldırıldı: " + kod, yazar_yonetimi.sil, kod)})
        d0 = yazar_yonetimi.oku(); mevcut = next((y for y in d0["yazarlar"] if y["kod"] == kod), None) if kod else None
        if kod and not mevcut: return _js(h, 404, {"hata": "Yazar bulunamadı."})
        yazar_yonetimi.dogrula(veri, mevcut, [y for y in d0["yazarlar"] if not mevcut or y["kod"] != kod])   # hatalar hemen dönsün
        return _js(h, 202, {"is": is_baslat(("Yazar güncellendi: " if kod else "Yazar eklendi: ") + str(veri.get("kisi") or ""), yazar_yonetimi.kaydet, kod, veri)})
    if a == "/seo/firsatlar" and G:
        import seo
        return _js(h, 200, {"firsatlar": seo.firsatlar(100), "toplam_sorgu": len(seo.gsc_sorgulari()), "esik": seo.FIRSAT_GOSTERIM})
    if a == "/seo/incele" and G:   # yayındaki bir yazı için öneri (değiştirmez)
        import seo, copy
        pp = yazar.post_bul((q.get("slug") or "").strip())
        if not pp: return _js(h, 404, {"hata": "Yazı bulunamadı."})
        return _js(h, 200, seo.incele(copy.deepcopy(pp), uygula=False))
    if a == "/seo/oneri" and G:
        import seo
        sorgu = (q.get("q") or "").strip()[:80]
        return _js(h, 200, {"sorgu": sorgu, "oneriler": seo.oneriler(sorgu) if sorgu else []})
    if a == "/bakiyeler" and G: return _js(h, 200, bakiyeler())
    if a == "/bakiye" and not G: return _js(h, 200, {"mesaj": bakiye_kaydet(veri)})
    if a == "/maliyet/detay" and G: return _js(h, 200, maliyet_detay(q.get("gun")))
    if a == "/kayitlar" and G: return _js(h, 200, kayitlar(q))
    if a == "/yayin" and G: return _js(h, 200, yayin_gecmisi())
    if a == "/yayin/derle" and not G: return _js(h, 202, {"is": is_baslat("Site yeniden derlendi", yeniden_derle)})
    if a == "/x-bakiye/oku" and not G:
        r = x_kredi_oku()
        _islem_kaydet("X bakiyesi okundu", f"{r['tutar']:.2f} $")
        return _js(h, 200, {"mesaj": f"X bakiyesi X API'den okundu: {r['tutar']:.2f} $", "ham": r["ham"]})
    if a == "/x-bakiye" and not G:
        import x_bakiye
        g = x_bakiye.bakiye_gir(veri.get("tutar"), veri.get("not") or "")
        _islem_kaydet("X bakiyesi girildi", f"{g['tutar']} $"); _x_onbellek["ts"] = 0
        return _js(h, 200, {"mesaj": f"X bakiyesi {g['tutar']} $ olarak kaydedildi; bundan sonraki harcama botun sayaçlarından düşülerek gösterilecek."})
    if a == "/mesai" and G:
        import mesai
        return _js(h, 200, {"calisiyor": mesai.DURUM["calisiyor"], "son": mesai.DURUM["son"], "otomatik": mesai.otomatik_gerekli(),
                            "kredi": mesai.DURUM.get("kredi"), "gecmis": mesai.DURUM.get("gecmis", [])[-10:]})
    if a == "/mesai" and not G:
        import mesai
        mod = "gecmis" if veri.get("mod") == "gecmis" else "guncel"
        try: gun = max(2, min(60, int(veri.get("gun") or 21))); adet = max(1, min(15, int(veri.get("adet") or 8)))
        except ValueError: raise ValueError("Gün ve adet sayı olmalı.")
        if mesai.DURUM["calisiyor"]: raise ValueError("Ek mesai turu zaten çalışıyor.")
        _islem_kaydet("ek mesai başlatıldı", f"{mod} {gun} gün, {adet} öğe")
        return _js(h, 202, {"is": is_baslat(("Ek mesai: güncel" if mod == "guncel" else f"Ek mesai: son {gun} gün"), mesai.calistir, mod, gun, adet)})
    if a == "/yayin/indexnow" and not G: return _js(h, 200, {"mesaj": indexnow_bildir(str(veri.get("url") or ""))})
    if a == "/uygulama-imza" and G:
        import imza; return _js(h, 200, imza.ozet())
    if a == "/uygulama-imza/istek" and not G:
        import imza; return _js(h, 200, {"csr": imza.istek_olustur()})
    if a == "/uygulama-imza/sertifika" and not G:
        import imza, base64
        return _js(h, 200, {"sertifika": imza.sertifika_yukle(base64.b64decode(str(veri.get("dosya") or "")))})
    if a == "/uygulama-imza/profil" and not G:
        import imza, base64
        return _js(h, 200, {"profil": imza.profil_yukle(base64.b64decode(str(veri.get("dosya") or "")))})
    if a == "/uygulama-imza/yenile" and not G:
        import imza; return _js(h, 200, imza.ipa_guncelle(zorla=True) or {"mesaj": "imzalanacak sürüm yok"})
    if a == "/yayin/cf-deneme" and not G:
        import cfyukle
        return _js(h, 200, cfyukle.deneme_yukle(SITE_DEPO))
    if a == "/servis/yeniden-baslat" and not G: return _js(h, 200, {"mesaj": yeniden_baslat()})
    if a == "/oturumlar/kapat" and not G:
        tum_oturumlari_kapat(); return _js(h, 200, {"mesaj": "Tüm oturumlar kapatıldı."}, "hh_oturum=; Path=/yonetim; Max-Age=0")
    return _js(h, 404, {"hata": "Yol bulunamadı."})


# ------------------------------------------------------------------ ziyaretçi istatistikleri (çerezsiz)
# Site her sayfa açılışında /sayac adresine küçük bir sinyal gönderir. IP adresi saklanmaz: aynı gün içindeki tekrarları
# ayırt etmek için IP + tarayıcı + o güne özel rastgele tuzdan geri döndürülemez bir özet üretilir; tuz gün bitince silinir.
import sqlite3
_ZDB = os.path.join(VERI, "ziyaret.db")
_zkilit = threading.Lock()
_ztuz = {"gun": None, "tuz": None}
_zsinir = {}
_BOT = re.compile(r"bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|quora|pinterest|whatsapp|telegram|discord|"
                  r"headless|lighthouse|pagespeed|gtmetrix|python|curl|wget|httpclient|okhttp|go-http|java/|axios|node-fetch|monitor|uptime|preview", re.I)

def _zbag():
    b = sqlite3.connect(_ZDB, timeout=10)
    b.execute("CREATE TABLE IF NOT EXISTS olay(ts INTEGER, gun TEXT, saat INTEGER, yol TEXT, kaynak TEXT, ulke TEXT, cihaz TEXT, z TEXT)")
    b.execute("CREATE INDEX IF NOT EXISTS olay_gun ON olay(gun)")
    b.execute("CREATE INDEX IF NOT EXISTS olay_ts ON olay(ts)")
    return b

def _gun_tuzu(gun):
    """o güne özel rastgele tuz; servis yeniden başlasa da gün içinde aynı kalır, ertesi gün yenisiyle değiştirilir (eskisi silinir)"""
    if _ztuz["gun"] != gun:
        yol = os.path.join(VERI, "sayac_tuz.json")
        try: d = json.load(open(yol))
        except Exception: d = {}
        if d.get("gun") != gun:
            d = {"gun": gun, "tuz": secrets.token_hex(16)}
            open(yol, "w").write(json.dumps(d))
            try: os.chmod(yol, 0o600)
            except Exception: pass
        _ztuz.update(d)
    return _ztuz["tuz"]

def _kaynak_adi(ref):
    if not ref: return "Doğrudan"
    try: h = urllib.parse.urlsplit(ref).hostname or ""
    except Exception: return "Diğer"
    h = h.lower().removeprefix("www.").removeprefix("m.")
    if h.endswith("hukukihaberler.com"): return "(site içi)"
    for ad, desen in (("Google", r"(^|\.)google\.|googleusercontent|news\.google|discover"), ("Bing", r"bing\.com"), ("Yandex", r"yandex\."),
                      ("X (Twitter)", r"(^|\.)(t\.co|x\.com|twitter\.com)$"), ("Facebook", r"facebook\.com|fb\.com"), ("Instagram", r"instagram\.com"),
                      ("LinkedIn", r"linkedin\.com|lnkd\.in"), ("WhatsApp", r"whatsapp"), ("Telegram", r"telegram|t\.me"), ("DuckDuckGo", r"duckduckgo"),
                      ("Ekşi Sözlük", r"eksisozluk"), ("yagmurtahtasiz.com", r"yagmurtahtasiz\.com"), ("umuttekin.av.tr", r"umuttekin\.av\.tr")):
        if re.search(desen, h): return ad
    return h[:60] or "Diğer"

def _cihaz(ua, gen):
    if re.search(r"ipad|tablet", ua, re.I): return "Tablet"
    if re.search(r"mobi|iphone|android", ua, re.I) or (gen and gen < 768): return "Mobil"
    return "Masaüstü"

def sayac_isle(h):
    """sitedeki sayfa görüntülemesini kaydeder; her durumda 204 döner (sinyal başarısızlığı okuru etkilemez)"""
    try:
        n = int(h.headers.get("Content-Length") or 0)
        veri = json.loads(h.rfile.read(n).decode("utf-8", "replace")) if 0 < n <= 4000 else {}
        ua = h.headers.get("User-Agent") or ""
        yol = str(veri.get("p") or "")[:300]
        if yol.startswith("/") and not _BOT.search(ua) and not yol.startswith(("/yonetim", "/api/")):
            yol = re.sub(r"\.html$", "", yol.split("?")[0].split("#")[0]) or "/"
            if yol != "/" and not yol.endswith("/") and "." not in yol.rsplit("/", 1)[-1]: yol += "/"
            ip = _ip(h); simd = time.time(); gun = simdi().strftime("%Y-%m-%d")
            z = hashlib.sha256((_gun_tuzu(gun) + "|" + ip + "|" + ua).encode()).hexdigest()[:16]
            dk = int(simd // 60)
            if _zsinir.get(z, (0, 0))[0] != dk: _zsinir[z] = (dk, 0)
            _zsinir[z] = (dk, _zsinir[z][1] + 1)
            if _zsinir[z][1] <= 30:
                kayit = (int(simd), gun, simdi().hour, yol, _kaynak_adi(str(veri.get("r") or "")[:400]),
                         (h.headers.get("CF-IPCountry") or "")[:2].upper(), _cihaz(ua, int(veri.get("w") or 0) if str(veri.get("w") or "").isdigit() else 0), z)
                with _zkilit:
                    b = _zbag(); b.execute("INSERT INTO olay VALUES (?,?,?,?,?,?,?,?)", kayit); b.commit(); b.close()
            if len(_zsinir) > 20000: _zsinir.clear()
    except Exception as e:
        log("sayaç hatası:", repr(e)[:160])
    h.send_response(204)
    h.send_header("Access-Control-Allow-Origin", "*"); h.send_header("Cache-Control", "no-store")
    h.send_header("Content-Length", "0"); h.end_headers()

def _zeski_temizle():
    with _zkilit:
        b = _zbag(); b.execute("DELETE FROM olay WHERE ts < ?", (int(time.time()) - 400 * 86400,)); b.commit(); b.close()

_ULKE = {"TR": "Türkiye", "DE": "Almanya", "NL": "Hollanda", "US": "ABD", "GB": "Birleşik Krallık", "FR": "Fransa", "AZ": "Azerbaycan",
         "CY": "Kıbrıs", "BE": "Belçika", "AT": "Avusturya", "CH": "İsviçre", "SE": "İsveç", "BG": "Bulgaristan", "GR": "Yunanistan", "RU": "Rusya"}

def ziyaret_ozeti(gun=14):
    gun = max(1, min(400, int(gun)))
    bugun = simdi().date()
    gunler = [(bugun - datetime.timedelta(days=i)).isoformat() for i in range(gun - 1, -1, -1)]
    bas = gunler[0]
    with _zkilit:
        b = _zbag()
        seri = {g: (z, v) for g, z, v in b.execute("SELECT gun, COUNT(DISTINCT z), COUNT(*) FROM olay WHERE gun >= ? GROUP BY gun", (bas,))}
        def grup(alan, sinir=12):
            return b.execute(f"SELECT {alan}, COUNT(DISTINCT z||gun) AS n, COUNT(*) FROM olay WHERE gun >= ? GROUP BY {alan} ORDER BY n DESC LIMIT ?", (bas, sinir)).fetchall()
        sayfalar = b.execute("SELECT yol, COUNT(*) AS v, COUNT(DISTINCT z||gun) FROM olay WHERE gun >= ? GROUP BY yol ORDER BY v DESC LIMIT 15", (bas,)).fetchall()
        kaynak, cihaz, ulke = grup("kaynak", 12), grup("cihaz", 5), grup("ulke", 10)
        saatler = dict(b.execute("SELECT saat, COUNT(*) FROM olay WHERE gun = ? GROUP BY saat", (bugun.isoformat(),)).fetchall())
        simdi_ = b.execute("SELECT COUNT(DISTINCT z) FROM olay WHERE ts >= ?", (int(time.time()) - 300,)).fetchone()[0]
        son = b.execute("SELECT ts, yol, kaynak, cihaz, ulke FROM olay ORDER BY ts DESC LIMIT 25").fetchall()
        donem = b.execute("SELECT COUNT(DISTINCT z||gun), COUNT(*) FROM olay WHERE gun >= ?", (bas,)).fetchone()
        ilk = b.execute("SELECT MIN(gun) FROM olay").fetchone()[0]
        b.close()
    basliklar = {}
    try: basliklar = {"/" + p["slug"] + "/": p["title"] for p in tum_yazilar()}
    except Exception: pass
    basliklar.update({"/": "Ana sayfa", "/arsiv/": "Arşiv", "/iletisim/": "İletişim", "/yazarlar/": "Yazarlar", "/analiz/": "Analiz",
                      "/mevzuat/": "Mevzuat", "/kesfet/": "Keşfet", "/hakkinda/": "Hakkında", "/kunye/": "Künye", "/konular/": "Konular",
                      "/av-yagmur-tahtasiz/": "Av. Yağmur Tahtasız", "/av-umut-tekin/": "Av. Umut Tekin", "/yayin-ilkeleri/": "Yayın İlkeleri",
                      "/gizlilik-politikasi/": "Gizlilik Politikası", "/kaydedilenler/": "Kaydedilenler", "/arama/": "Arama"})
    ad = lambda y: basliklar.get(y) or y
    return {
        "gun": gun, "ilk_kayit": ilk,
        "seri": [{"gun": g, "ziyaretci": seri.get(g, (0, 0))[0], "goruntulenme": seri.get(g, (0, 0))[1]} for g in gunler],
        "bugun": {"ziyaretci": seri.get(bugun.isoformat(), (0, 0))[0], "goruntulenme": seri.get(bugun.isoformat(), (0, 0))[1]},
        "donem": {"ziyaretci": donem[0], "goruntulenme": donem[1]}, "su_an": simdi_,
        "saatler": [{"saat": s, "adet": saatler.get(s, 0)} for s in range(24)],
        "sayfalar": [{"yol": y, "baslik": ad(y), "goruntulenme": v, "ziyaretci": z} for y, v, z in sayfalar],
        "kaynaklar": [{"ad": k, "ziyaretci": n, "goruntulenme": v} for k, n, v in kaynak],
        "cihazlar": [{"ad": k, "ziyaretci": n} for k, n, _ in cihaz],
        "ulkeler": [{"ad": _ULKE.get(k, k or "Bilinmiyor"), "ziyaretci": n} for k, n, _ in ulke],
        "son": [{"ts": t, "yol": y, "baslik": ad(y), "kaynak": k, "cihaz": c, "ulke": _ULKE.get(u, u)} for t, y, k, c, u in son],
    }


# ------------------------------------------------------------------ Google Search Console (arama kelimeleri)
# Google, aramada yazılan kelimeyi siteye göndermez; kelime, gösterim, tıklama ve sıra verisi yalnızca Search Console'da bulunur.
# Bağlantı bir hizmet hesabıyla kurulur: anahtar JSON'u panelden bir kez yapıştırılır (bir daha gösterilmez), hizmet hesabının
# e-postası Search Console'da mülke kullanıcı olarak eklenir. İmzalama sunucudaki openssl ile yapılır; ek paket gerekmez.
import base64, tempfile
_GSC_ANAHTAR = os.path.join(VERI, "gsc_hizmet_hesabi.json")
_GSC_MULK = os.environ.get("GSC_MULK", "sc-domain:hukukihaberler.com")
_GSC_TOKEN_URL = os.environ.get("GSC_TOKEN_URL", "https://oauth2.googleapis.com/token")
_GSC_API = os.environ.get("GSC_API", "https://www.googleapis.com/webmasters/v3")
_gsc_jeton = {"deger": None, "bitis": 0}
_gsc_onbellek = {}

def _b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

_GSC_OZEL = os.path.join(VERI, "gsc_ozel.pem")
_GSC_SERTIFIKA = os.path.join(VERI, "gsc_sertifika.pem")
_GSC_EPOSTA = os.path.join(VERI, "gsc_eposta.txt")

def _gsc_hesap():
    """bağlantı bilgisi: ya panelin kendi ürettiği anahtar + hizmet hesabı e-postası ya da yapıştırılmış JSON anahtar"""
    if os.path.exists(_GSC_OZEL) and os.path.exists(_GSC_EPOSTA):
        return {"client_email": open(_GSC_EPOSTA).read().strip(), "private_key": open(_GSC_OZEL).read()}
    try: return json.load(open(_GSC_ANAHTAR, encoding="utf-8"))
    except Exception: return None

def gsc_sertifika():
    """sunucuda RSA anahtarı ve kendinden imzalı sertifika üretir (yoksa); Google Cloud'a yüklenecek AÇIK sertifikayı döndürür.
    Özel anahtar sunucudan hiç çıkmaz."""
    if not (os.path.exists(_GSC_OZEL) and os.path.exists(_GSC_SERTIFIKA)):
        r = subprocess.run(["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "3650", "-subj", "/CN=hukukihaberler-panel",
                            "-keyout", _GSC_OZEL, "-out", _GSC_SERTIFIKA], capture_output=True, timeout=60)
        if r.returncode != 0: raise RuntimeError("Anahtar üretilemedi: " + r.stderr.decode()[-200:])
        os.chmod(_GSC_OZEL, 0o600)
        _islem_kaydet("Search Console için sunucuda anahtar üretildi")
    return open(_GSC_SERTIFIKA).read()

def gsc_eposta_kaydet(eposta):
    eposta = str(eposta).strip()
    if not re.fullmatch(r"[a-z0-9-]{3,40}@[a-z0-9-]{4,40}\.iam\.gserviceaccount\.com", eposta): raise ValueError("Geçerli bir hizmet hesabı e-postası değil.")
    if not os.path.exists(_GSC_OZEL): raise ValueError("Önce sunucuda anahtar üretilmeli.")
    open(_GSC_EPOSTA, "w").write(eposta)
    _gsc_jeton.update(deger=None, bitis=0); _gsc_onbellek.clear()
    _islem_kaydet("Search Console hizmet hesabı kaydedildi", eposta)
    return eposta

def gsc_anahtar_kaydet(metin):
    try: d = json.loads(metin)
    except Exception: raise ValueError("Yapıştırılan metin geçerli bir JSON değil. İndirilen .json dosyasının tamamını yapıştırın.")
    if d.get("type") != "service_account" or not d.get("client_email") or "PRIVATE KEY" not in str(d.get("private_key", "")):
        raise ValueError("Bu bir hizmet hesabı anahtarı değil (type: service_account, client_email ve private_key alanları olmalı).")
    d = {k: d[k] for k in ("type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri") if k in d}
    open(_GSC_ANAHTAR + ".tmp", "w", encoding="utf-8").write(json.dumps(d))
    os.chmod(_GSC_ANAHTAR + ".tmp", 0o600); os.replace(_GSC_ANAHTAR + ".tmp", _GSC_ANAHTAR)
    _gsc_jeton.update(deger=None, bitis=0); _gsc_onbellek.clear()
    _islem_kaydet("Google Search Console anahtarı kaydedildi", d["client_email"])
    return d["client_email"]

def _gsc_jeton_al():
    if _gsc_jeton["deger"] and time.time() < _gsc_jeton["bitis"] - 60: return _gsc_jeton["deger"]
    h = _gsc_hesap()
    if not h: raise RuntimeError("Search Console bağlantısı kurulmadı.")
    simd = int(time.time())
    govde = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()) + "." + _b64(json.dumps({
        "iss": h["client_email"], "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": _GSC_TOKEN_URL, "iat": simd, "exp": simd + 3600}).encode())
    with tempfile.NamedTemporaryFile("w", suffix=".pem", dir=VERI, delete=False) as f:
        f.write(h["private_key"]); yol = f.name
    try:
        os.chmod(yol, 0o600)
        r = subprocess.run(["openssl", "dgst", "-sha256", "-sign", yol], input=govde.encode(), capture_output=True, timeout=20)
    finally:
        os.remove(yol)
    if r.returncode != 0: raise RuntimeError("Anahtar imzalanamadı; anahtar bozuk olabilir.")
    jwt = govde + "." + _b64(r.stdout)
    istek = urllib.request.Request(_GSC_TOKEN_URL, data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode(),
                                   headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(istek, timeout=30) as x: js = json.loads(x.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError("Google anahtarı kabul etmedi: " + e.read().decode("utf-8", "replace")[:200])
    _gsc_jeton.update(deger=js["access_token"], bitis=time.time() + int(js.get("expires_in", 3600)))
    return js["access_token"]

def _gsc_istek(yol, govde=None):
    istek = urllib.request.Request(_GSC_API + yol, data=json.dumps(govde).encode() if govde is not None else None,
                                   headers={"Authorization": "Bearer " + _gsc_jeton_al(), "Content-Type": "application/json"}, method="POST" if govde is not None else "GET")
    try:
        with urllib.request.urlopen(istek, timeout=40) as x: return json.loads(x.read())
    except urllib.error.HTTPError as e:
        metin = e.read().decode("utf-8", "replace")
        if e.code == 403: raise RuntimeError("Hizmet hesabının bu mülke erişimi yok. Search Console > Ayarlar > Kullanıcılar ve izinler bölümünden hizmet hesabı e-postasını ekleyin.")
        raise RuntimeError(f"Search Console hatası ({e.code}): {metin[:200]}")

def gsc_durum():
    h = _gsc_hesap()
    if not h: return {"bagli": False, "mulk": _GSC_MULK}
    try:
        siteler = [s.get("siteUrl") for s in (_gsc_istek("/sites").get("siteEntry") or [])]
        return {"bagli": _GSC_MULK in siteler, "eposta": h["client_email"], "mulk": _GSC_MULK, "siteler": siteler,
                "hata": None if _GSC_MULK in siteler else "Hizmet hesabı henüz mülke eklenmemiş. Search Console'da bu e-postayı kullanıcı olarak ekleyin."}
    except Exception as e:
        return {"bagli": False, "eposta": h["client_email"], "mulk": _GSC_MULK, "hata": str(e)[:300]}

def _gsc_sorgu(bas, son, boyutlar, filtre=None, adet=250):
    anahtar = (bas, son, tuple(boyutlar), json.dumps(filtre, sort_keys=True), adet)
    o = _gsc_onbellek.get(anahtar)
    if o and time.time() - o[0] < 1800: return o[1]
    govde = {"startDate": bas, "endDate": son, "dimensions": boyutlar, "rowLimit": adet, "dataState": "all"}
    if filtre: govde["dimensionFilterGroups"] = [{"filters": filtre}]
    satirlar = _gsc_istek("/sites/" + urllib.parse.quote(_GSC_MULK, safe="") + "/searchAnalytics/query", govde).get("rows") or []
    _gsc_onbellek[anahtar] = (time.time(), satirlar)
    return satirlar

def gsc_ozet(q):
    gun = max(1, min(480, int(q.get("gun") or 28)))
    son = simdi().date(); bas = son - datetime.timedelta(days=gun - 1)
    b, s = bas.isoformat(), son.isoformat()
    sayfa = (q.get("sayfa") or "").strip()
    filtre = [{"dimension": "page", "operator": "includingRegex", "expression": "^" + re.escape(ortak.SITE + sayfa.rstrip("/")) + "/?$"}] if sayfa else None   # sondaki / olsa da olmasa da
    def satir(r, adlar):
        return {**dict(zip(adlar, r.get("keys", []))), "tiklama": r.get("clicks", 0), "gosterim": r.get("impressions", 0),
                "oran": round(r.get("ctr", 0) * 100, 1), "sira": round(r.get("position", 0), 1)}
    seri = [satir(r, ["tarih"]) for r in _gsc_sorgu(b, s, ["date"], filtre, 500)]
    kelimeler = [satir(r, ["kelime"]) for r in _gsc_sorgu(b, s, ["query"], filtre, 250)]
    t_tik = sum(x["tiklama"] for x in seri); t_gos = sum(x["gosterim"] for x in seri)
    ort_sira = round(sum(x["sira"] * x["gosterim"] for x in seri) / t_gos, 1) if t_gos else 0
    out = {"gun": gun, "bas": b, "son": s, "sayfa": sayfa, "seri": seri, "kelimeler": kelimeler, "firsat_esik": int(_env_oku().get("FIRSAT_GOSTERIM", "5") or 5),
           "toplam": {"tiklama": t_tik, "gosterim": t_gos, "oran": round(t_tik / t_gos * 100, 1) if t_gos else 0, "sira": ort_sira},
           "son_veri": seri[-1]["tarih"] if seri else None}
    if not sayfa:
        basliklar = {}
        try:
            for p in tum_yazilar(): basliklar[ortak.SITE + "/" + p["slug"] + "/"] = basliklar[ortak.SITE + "/" + p["slug"]] = p["title"]
        except Exception: pass
        basliklar[ortak.SITE + "/"] = "Ana sayfa"
        sayfalar = [satir(r, ["adres"]) for r in _gsc_sorgu(b, s, ["page"], None, 100)]
        for x in sayfalar:
            x["yol"] = x["adres"].replace(ortak.SITE, "") or "/"; x["baslik"] = basliklar.get(x["adres"]) or basliklar.get(x["adres"].rstrip("/") + "/") or x["yol"]
        out["sayfalar"] = sayfalar
        out["cihazlar"] = [satir(r, ["cihaz"]) for r in _gsc_sorgu(b, s, ["device"], None, 10)]
    return out


# ------------------------------------------------------------------ servis bakiyeleri
# Anthropic kalan krediyi API ile vermez: son bilinen bakiye elle (konsoldan bakılarak) girilir, o andan sonra kaydedilen
# harcama düşülerek tahmini kalan hesaplanır. X API kullanımı resmî /2/usage/tweets ucundan okunur.
_BAKIYE = os.path.join(VERI, "bakiye.json")
_x_onbellek = {"ts": 0, "veri": None}

def _bakiye_oku():
    try: return json.load(open(_BAKIYE, encoding="utf-8"))
    except Exception: return {}

def _harcama_sonra(ts):
    """ts anından sonra kaydedilen ücretli çağrıların toplamı (ayrıntılı kayıtlardan)"""
    d = os.path.join(VERI, "maliyet"); top = 0.0
    if not os.path.isdir(d): return 0.0
    bas_gun = datetime.datetime.fromtimestamp(ts, ortak.TR).strftime("%Y-%m-%d")
    for f in os.listdir(d):
        if not f.endswith(".jsonl") or f[:-6] < bas_gun: continue
        for ln in open(os.path.join(d, f), encoding="utf-8", errors="replace"):
            try: k = json.loads(ln)
            except Exception: continue
            if k.get("tur") == "cagri" and k.get("ts", 0) >= ts: top += float(k.get("usd") or 0)
    return top

def bakiye_kaydet(veri):
    """konsolda görülen aylık API kredisinin gerçek kalanını kaydeder (verilme ya da bitiş tarihi eşleşen kredi güncellenir)"""
    import kredi
    if veri.get("servis") != "anthropic": raise ValueError("Yalnızca Anthropic kredisi elle girilir.")
    try: tutar = float(str(veri.get("bakiye")).replace(",", "."))
    except Exception: raise ValueError("Kalan kredi bir sayı olmalı (ör. 174.71).")
    if not 0 <= tutar < 100000: raise ValueError("Kalan kredi geçersiz.")
    tar = {}
    for ad in ("bitis", "verilme"):
        v = str(veri.get(ad) or "").strip()
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v): raise ValueError("Tarihler YYYY-AA-GG biçiminde olmalı.")
        tar[ad] = v or None
    if not (tar["bitis"] or tar["verilme"]): raise ValueError("Kredinin son kullanma ya da veriliş tarihini girin.")
    k = kredi.kredi_gir(tutar, **tar)
    _islem_kaydet("aylık API kredisi doğrulandı", f"{tutar:.2f} $ ({k['verilme']} – {k['bitis']})")
    return "Kredi kaydedildi; günlük pay yeniden hesaplandı."

def _x_kullanim():
    if time.time() - _x_onbellek["ts"] < 600 and _x_onbellek["veri"]: return _x_onbellek["veri"]
    bearer = _env_oku().get("X_BEARER")
    if not bearer: return {"hata": "X anahtarı tanımlı değil."}
    kod, js = http_json("https://api.x.com/2/usage/tweets?days=30", headers={"Authorization": "Bearer " + bearer}, timeout=20)
    if kod != 200 or not isinstance(js, dict) or "data" not in js:
        out = {"hata": f"X kullanım bilgisi alınamadı ({kod})", "ayrinti": (str(js)[:200] if js else "")}
    else:
        v = js["data"]
        gunluk = [{"gun": (x.get("date") or "")[:10], "adet": int(sum(int(u.get("usage", 0)) for u in (x.get("usage") or [])) if isinstance(x.get("usage"), list) else int(x.get("usage") or 0))}
                  for x in (v.get("daily_project_usage", {}) or {}).get("usage", [])] if isinstance(v.get("daily_project_usage"), dict) else []
        out = {"kullanim": int(v.get("project_usage") or 0), "sinir": int(v.get("project_cap") or 0), "yenilenme_gunu": v.get("cap_reset_day"),
               "gunluk": gunluk[-30:]}
    _x_onbellek.update(ts=time.time(), veri=out)
    return out

def _sayi_bul(js, anahtarlar=("total_balance", "balance", "credit_balance", "remaining_balance", "prepaid_balance")):
    """X kredi cevabında dolar bakiyesini bulur (alan adları belgede yazmadığı için esnek arar)"""
    if isinstance(js, dict):
        for k in anahtarlar:
            v = js.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool): return float(v)
            if isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip()): return float(v)
            if isinstance(v, dict):
                r = _sayi_bul(v, anahtarlar)
                if r is not None: return r
        for v in js.values():
            if isinstance(v, (dict, list)):
                r = _sayi_bul(v, anahtarlar)
                if r is not None: return r
    elif isinstance(js, list):
        for v in js:
            r = _sayi_bul(v, anahtarlar)
            if r is not None: return r
    return None

_x_canli = {"ts": 0, "tutar": None, "hata": None}

def x_kredi_oku(kaydet=True):
    """X API kullandıkça öde bakiyesini resmî /2/usage/credits ucundan okur; kaydet=True ise panel bakiyesine işler"""
    bearer = _env_oku().get("X_BEARER")
    if not bearer: raise ValueError("X anahtarı tanımlı değil.")
    kod, js = http_json("https://api.x.com/2/usage/credits", headers={"Authorization": "Bearer " + bearer}, timeout=20)
    if kod != 200: raise ValueError(f"X bakiye okunamadı ({kod}): {str(js)[:200]}")
    tutar = _sayi_bul(js)
    if tutar is None: raise ValueError("X bakiye cevabında tutar bulunamadı: " + json.dumps(js, ensure_ascii=False)[:300])
    # birim sent olarak gelirse (ör. 2496) dolara çevir: bakiye mantıklı aralıkta değilse
    if tutar > 10000: tutar = tutar / 100
    if kaydet:
        import x_bakiye
        x_bakiye.bakiye_gir(tutar, "X API /2/usage/credits (otomatik)")
        _x_onbellek["ts"] = 0
    return {"tutar": tutar, "ham": js}

def bakiye_gece_dongu():
    """her gece 00.00'da X bakiyesini X API'den okuyup kaydeder (tarayıcı ya da Claude gerekmez)"""
    son = None
    while True:
        try:
            n = simdi()
            if n.hour == 0 and son != n.date():
                son = n.date()
                r = x_kredi_oku()
                log(f"gece bakiye okuması: X {r['tutar']:.2f} $")
                _islem_kaydet("X bakiyesi otomatik okundu", f"{r['tutar']:.2f} $")
        except Exception as e:
            log("gece bakiye okuması hatası:", repr(e)[:200])
        time.sleep(60)

def bakiyeler():
    gecmis = maliyet()["seri"]
    son7 = [x["maliyet"] for x in gecmis[-8:-1]] or [x["maliyet"] for x in gecmis]
    ort = sum(son7) / len(son7) if son7 else 0
    anth = {"servis": "anthropic", "ad": "Anthropic (Claude) · Max aylık API kredisi", "tur": "kredi", "gunluk_ortalama": round(ort, 2),
            "satin_alinan": "Kullanılmıyor: otomatik yükleme kapalı; aylık kredi bitince bot ücretli çağrıyı kendisi durdurur."}
    o = ortak.kredi_ozeti()
    if o:
        kalan, bitis, sebep = ortak.kredi_durumu()
        bugun = simdi().date()
        aktif = [k for k in o["krediler"] if k["aktif"]]
        anth.update(kalan=round(kalan, 2), bitis=bitis, durdu=sebep, esik=ortak.KREDI_ESIK, donem=sum(k["tutar"] for k in aktif) or 200,
                    krediler=o["krediler"][-4:], gunluk_pay=o["gunluk_pay"], bugunku=round(max(o["bugunku"], ortak.bugunku_maliyet()), 3), sonraki_kredi=o["sonraki_kredi"],
                    sonraki_gun=(datetime.date.fromisoformat(o["sonraki_kredi"]) - bugun).days,
                    abonelik_gunu=o["abonelik_gunu"], kredi_gunu=o["kredi_gunu"], pay_doldu=max(o["bugunku"], ortak.bugunku_maliyet()) >= o["gunluk_pay"] > 0)
        # bu hızla süresi dolarken kullanılmadan kalacak tutar (yalnızca bilgi)
        yanacak = 0.0
        for k in aktif:
            gun_sayisi = max(0, (datetime.date.fromisoformat(k["bitis"]) - bugun).days)
            yanacak += max(0.0, k["kalan"] - ort * gun_sayisi) if k["bitis"] == bitis else 0
        anth["yanacak"] = round(yanacak, 2)
        anth["durum"] = "kritik" if sebep or kalan < 5 else "dusuk" if ort and kalan < ort * 3 else "iyi"
    else:
        anth.update(durum="bilinmiyor")
    try: x = _x_kullanim()
    except Exception as e: x = {"hata": str(e)[:200]}
    x.update(servis="x", ad="X API", tur="kota")
    if x.get("sinir"):
        oran = x["kullanim"] / x["sinir"]
        x["durum"] = "kritik" if oran > 0.95 else "dusuk" if oran > 0.8 else "iyi"
    # X kullandıkça öde kredisi: akış "CreditsDepleted" (402) dönüyorsa kota sayacından bağımsız olarak bitti göster
    _son = [l for l in _log_satirlari(600) if "CreditsDepleted" in l]
    _bitti = _son and _son[-1][:16] >= (simdi() - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
    try:
        import x_bakiye
        x["tahmin"] = x_bakiye.durum(_son[-1][:16] if _bitti else None)
        k = x["tahmin"].get("kalan")
        if k is not None and not _bitti:
            gun = x["tahmin"].get("kac_gun")
            x["durum"] = "kritik" if k < 2 else "dusuk" if (gun is not None and gun < 3) else "iyi"
    except Exception as e:
        log("X bakiye tahmini hatası:", repr(e)[:150])
    # canlı bakiye: X'in resmî kredi ucu (5 dakika önbellekli); okunabildiyse tahmin ve eski "bitti" uyarısı yerine bu gösterilir
    try:
        if time.time() - _x_canli["ts"] > 300:
            _x_canli.update(ts=time.time(), tutar=x_kredi_oku(kaydet=False)["tutar"], hata=None)
    except Exception as e:
        _x_canli.update(ts=time.time(), hata=str(e)[:150])
    if _x_canli.get("tutar") is not None and not _x_canli.get("hata"):
        x["net"] = round(_x_canli["tutar"], 2); x["net_ts"] = _x_canli["ts"]
        _bitti = x["net"] <= 0
        x["durum"] = "kritik" if x["net"] < 2 else "dusuk" if (x.get("tahmin", {}).get("gunluk_ortalama") or 0) * 3 > x["net"] else "iyi"
    if _bitti:
        x.update(durum="kritik", aciklama="X API kredisi bitti; akış durdu. console.x.com/accounts/2111191497882145042 adresinden kredi yüklenmeli.")
    return {"servisler": [anth, x,
        {"servis": "gemini", "ad": "Google Gemini", "tur": "ucretsiz", "durum": "iyi", "aciklama": "Ücretsiz katman; kota dolarsa ya da yoğunlukta Claude'a geçilir."},
        {"servis": "cloudflare", "ad": "Cloudflare", "tur": "ucretsiz", "durum": "iyi", "aciklama": "Ücretsiz plan (Pages, KV, DNS)."},
        {"servis": "gsc", "ad": "Google Search Console API", "tur": "ucretsiz", "durum": "iyi", "aciklama": "Ücretsiz."}]}
