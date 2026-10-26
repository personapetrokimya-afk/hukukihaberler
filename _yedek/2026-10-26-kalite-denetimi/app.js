/* Hukuki Haberler · Yönetim paneli */
(function () {
"use strict";

// ------------------------------------------------------------ yardımcılar
const $ = (s, k) => (k || document).querySelector(s);
const $$ = (s, k) => Array.from((k || document).querySelectorAll(s));
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sayi = (n) => new Intl.NumberFormat("tr-TR").format(n || 0);
const AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
const tarihYaz = (t) => { if (!t) return ""; const [y, a, g] = String(t).slice(0, 10).split("-"); return `${+g} ${AYLAR[+a - 1]} ${y}`; };
const zamanYaz = (ts) => { if (!ts) return ""; const d = new Date(ts * 1000); return d.toLocaleString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); };
const once = (ts) => {
  if (!ts) return ""; const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return "az önce"; if (s < 3600) return Math.floor(s / 60) + " dk önce"; if (s < 86400) return Math.floor(s / 3600) + " sa önce";
  return Math.floor(s / 86400) + " gün önce";
};
const sure = (sn) => { const g = Math.floor(sn / 86400), s = Math.floor(sn % 86400 / 3600), d = Math.floor(sn % 3600 / 60); return (g ? g + " gün " : "") + (s ? s + " sa " : "") + d + " dk"; };

const IKON = {
  gosterge: '<path d="M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z"/>',
  onay: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
  yazilar: '<path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  yeni: '<path d="M12 5v14M5 12h14"/>',
  elek: '<path d="M3 5h18l-7 8.5V19l-4 2v-7.5z"/>',
  mesaj: '<path d="M4 4h16v12H5.2L4 17.2z"/><path d="M8 9h8M8 12h5"/>',
  x: '<path d="M4 4l16 16M20 4L4 20"/>',
  sayfa: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  yayin: '<path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/>',
  maliyet: '<path d="M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  kayit: '<path d="M4 6h16M4 10h16M4 14h10M4 18h7"/>',
  ayar: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  yazar: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  ara: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  ziyaret: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
};
const ikon = (ad) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IKON[ad] || ""}</svg>`;

const MENU = [
  { grup: "Genel", ogeler: [{ yol: "gosterge", ad: "Gösterge", ikon: "gosterge" }, { yol: "ziyaretciler", ad: "Ziyaretçiler", ikon: "ziyaret" }, { yol: "google", ad: "Google arama kelimeleri", ikon: "ara" }] },
  { grup: "İçerik", ogeler: [
    { yol: "taslaklar", ad: "Onay bekleyenler", ikon: "onay", rozet: "bekleyen" },
    { yol: "elenenler", ad: "Elenen haberler", ikon: "elek" },
    { yol: "yazilar", ad: "Yayındaki yazılar", ikon: "yazilar" },
    { yol: "yeni", ad: "Yeni yazı", ikon: "yeni" },
    { yol: "yazarlar", ad: "Yazarlar ve inceleme", ikon: "yazar" },
  ] },
  { grup: "Okurlar", ogeler: [{ yol: "mesajlar", ad: "Mesajlar", ikon: "mesaj", rozet: "okunmamis" }] },
  { grup: "Haber kaynakları", ogeler: [
    { yol: "kaynaklar/x", ad: "X hesapları", ikon: "x" },
    { yol: "kaynaklar/sayfalar", ad: "Resmî sayfalar", ikon: "sayfa" },
  ] },
  { grup: "Sistem", ogeler: [
    { yol: "yayin", ad: "Yayın ve servis", ikon: "yayin", rozet: "hata" },
    { yol: "maliyet", ad: "Maliyet", ikon: "maliyet" },
    { yol: "kayitlar", ad: "Kayıtlar", ikon: "kayit" },
    { yol: "ayarlar", ad: "Ayarlar", ikon: "ayar" },
  ] },
];

let OTURUM = { kategoriler: [], konular: {} };
const ROZET = { bekleyen: 0, okunmamis: 0, hata: 0 };
let zamanlayici = null;

// ------------------------------------------------------------ API
async function api(yol, secenek = {}) {
  const ayar = { method: secenek.yontem || (secenek.veri ? "POST" : "GET"), headers: { "X-HH-Panel": "1" }, credentials: "same-origin" };
  if (secenek.veri) { ayar.headers["Content-Type"] = "application/json"; ayar.body = JSON.stringify(secenek.veri); }
  let r;
  try { r = await fetch("/yonetim/api" + yol, ayar); }
  catch (e) { throw new Error("Sunucuya ulaşılamadı. Bağlantıyı kontrol edin."); }
  let js = {};
  try { js = await r.json(); } catch (e) {}
  if (r.status === 401 && js.giris) { girisGoster(); throw new Error("Oturum kapandı."); }
  if (!r.ok) throw new Error(js.hata || ("Hata " + r.status));
  return js;
}

// ------------------------------------------------------------ bildirim, pencere, iş takibi
function bildir(metin, tur = "", sure_ = 4500) {
  const d = document.createElement("div");
  d.className = "bildirim " + tur;
  d.innerHTML = (tur === "is" ? '<span class="don"></span>' : "") + `<div>${esc(metin)}</div>`;
  $("#bildirimler").appendChild(d);
  if (sure_) setTimeout(() => d.remove(), sure_);
  return d;
}
function hata(e) { bildir(e && e.message ? e.message : String(e), "hata", 7000); }

function pencere({ baslik, metin = "", onay = "Onayla", vazgec = "Vazgeç", tehlike = false, girdi = null }) {
  return new Promise((coz) => {
    const p = $("#pencere"), f = $("#pencere-form");
    f.innerHTML = `<div class="p-ust"><h3>${esc(baslik)}</h3></div><div class="p-ic">${metin}${girdi ? `<div class="alan mt"><label for="p-girdi">${esc(girdi.etiket)}</label>${girdi.cok ? `<textarea id="p-girdi" rows="4" placeholder="${esc(girdi.yer || "")}"></textarea>` : `<input id="p-girdi" type="text" autocomplete="off" placeholder="${esc(girdi.yer || "")}">`}</div>` : ""}</div>
      <div class="p-alt"><button class="btn" value="hayir" type="submit">${esc(vazgec)}</button><button class="btn ${tehlike ? "btn-kirmizi" : "btn-ana"}" value="evet" type="submit" id="p-evet">${esc(onay)}</button></div>`;
    const gi = $("#p-girdi", f);
    if (gi && girdi.beklenen) { const ev = $("#p-evet", f); ev.disabled = true; gi.addEventListener("input", () => { ev.disabled = gi.value.trim() !== girdi.beklenen; }); }
    p.onclose = () => coz(p.returnValue === "evet" ? (gi ? gi.value.trim() : true) : false);
    p.returnValue = ""; p.showModal(); (gi || $("#p-evet", f)).focus();
  });
}

function isTakip(id, baslangic, bitince) {
  const t = bildir(baslangic + " — sürüyor…", "is", 0);
  const dene = async () => {
    try {
      const i = await api("/is/" + id);
      if (i.durum === "çalışıyor") { t.querySelector("div").textContent = `${baslangic} — sürüyor (${Math.round(Date.now() / 1000 - i.bas)} sn)…`; return setTimeout(dene, 2000); }
      t.remove();
      bildir(i.mesaj || (i.durum === "tamam" ? "Tamamlandı." : "Hata."), i.durum === "tamam" ? "tamam" : "hata", 8000);
      if (bitince) bitince(i);
    } catch (e) { t.remove(); hata(e); }
  };
  setTimeout(dene, 1500);
}

// ------------------------------------------------------------ giriş
function girisGoster() {
  $("#uygulama").hidden = true; $("#giris").hidden = false; $("#sifre").value = ""; $("#sifre").focus();
  if (zamanlayici) clearInterval(zamanlayici);
}
$("#giris-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const b = e.target.querySelector("button"); b.disabled = true; $("#giris-hata").textContent = "";
  try { await api("/giris", { veri: { sifre: $("#sifre").value } }); await baslat(); }
  catch (er) { $("#giris-hata").textContent = er.message; }
  b.disabled = false;
});
$("#cikis").addEventListener("click", async () => { try { await api("/cikis", { veri: {} }); } catch (e) {} girisGoster(); });

// ------------------------------------------------------------ menü ve yönlendirme
function menuCiz() {
  const aktif = (location.hash.slice(2) || "gosterge");
  $("#menu-liste").innerHTML = MENU.map((g) => `<div class="menu-grup"><span>${esc(g.grup)}</span>${g.ogeler.map((o) => {
    const on = aktif === o.yol || aktif.startsWith(o.yol + "/") || (o.yol === "taslaklar" && aktif.startsWith("taslak/")) || (o.yol === "yazilar" && aktif.startsWith("yazi/")) || (o.yol === "yazarlar" && aktif.startsWith("yazar/"));
    const r = o.rozet && ROZET[o.rozet] ? `<span class="rozet ${o.rozet === "hata" ? "kirmizi" : ""}">${ROZET[o.rozet]}</span>` : "";
    return `<a href="#/${o.yol}" class="${on ? "on" : ""}">${ikon(o.ikon)}<span>${esc(o.ad)}</span>${r}</a>`;
  }).join("")}</div>`).join("");
}
let BASLIK_TABAN = "";
function baslikYaz(b, alt = "", sag = "") { $("#sayfa-baslik").textContent = b; $("#sayfa-alt").textContent = alt; $("#ust-sag").innerHTML = sag; BASLIK_TABAN = b + " · Yönetim"; document.title = ((ROZET.okunmamis || 0) ? `(${ROZET.okunmamis}) ` : "") + BASLIK_TABAN; }
const icerik = () => $("#icerik");
function yukleniyor() { icerik().innerHTML = '<div class="yukleniyor"></div>'; }

let sayfaTemizle = null;
let SAYFA_NO = 0;   // her sayfa geçişinde artar; eski sayfanın gecikmeli yenilemeleri yeni sayfaya çizim yapmaz
async function yonlendir() {
  SAYFA_NO++;
  if (sayfaTemizle) { sayfaTemizle(); sayfaTemizle = null; }
  const eski = $("#icerik"), taze = eski.cloneNode(false); eski.replaceWith(taze);   // önceki sayfanın olay dinleyicileri kalmasın
  document.body.classList.remove("menu-acik");
  const h = location.hash.slice(2) || "gosterge";
  const [ad, ...kalan] = h.split("/");
  const arg = decodeURIComponent(kalan.join("/"));
  menuCiz(); yukleniyor(); window.scrollTo(0, 0);
  const SAYFA = { gosterge: sGosterge, taslaklar: sTaslaklar, taslak: sTaslak, yazilar: sYazilar, yazi: sYazi, yeni: sYeni, yazarlar: sYazarlar, yazar: sYazar, elenenler: sElenenler,
    mesajlar: sMesajlar, ziyaretciler: sZiyaret, google: sGoogle, kaynaklar: sKaynaklar, yayin: sYayin, maliyet: sMaliyet, kayitlar: sKayitlar, ayarlar: sAyarlar };
  try { await (SAYFA[ad] || sGosterge)(arg); }
  catch (e) { if (e.message !== "Oturum kapandı.") { icerik().innerHTML = `<div class="kart"><div class="bos"><b>Sayfa yüklenemedi</b>${esc(e.message)}</div></div>`; } }
  $("#icerik").focus({ preventScroll: true });
}
window.addEventListener("hashchange", yonlendir);
$("#menu-ac").addEventListener("click", () => document.body.classList.add("menu-acik"));
$("#menu-ortu").addEventListener("click", () => document.body.classList.remove("menu-acik"));

let SON_MESAJ = null;
const baslikRozet = () => { const n = ROZET.okunmamis || 0; document.title = (n ? `(${n}) ` : "") + (BASLIK_TABAN || "Yönetim"); };
async function rozetGuncelle() {
  try {
    const g = await api("/rozet");
    const yeniGeldi = SON_MESAJ !== null && g.son_mesaj > SON_MESAJ && g.okunmamis > 0;
    SON_MESAJ = g.son_mesaj;
    ROZET.bekleyen = g.bekleyen; ROZET.okunmamis = g.okunmamis;
    menuCiz(); baslikRozet();
    if (yeniGeldi) {
      const t = bildir("Yeni okur mesajı geldi. Görmek için tıklayın.", "tamam", 10000);
      if (t) { t.style.cursor = "pointer"; t.addEventListener("click", () => { location.hash = "#/mesajlar"; t.remove(); }); }
    }
    return g;
  } catch (e) { return null; }
}
document.addEventListener("visibilitychange", () => { if (!document.hidden && $("#uygulama") && !$("#uygulama").hidden) rozetGuncelle(); });

// ------------------------------------------------------------ ortak parçalar
const DURUM_ET = { "bekliyor": "sari", "yayınlandı": "yesil", "yayınlanıyor": "mavi", "kaldırılıyor": "mavi", "reddedildi": "", "geri alındı": "", "yayından kaldırıldı": "kirmizi", "zaten var": "", "birleştirildi": "mavi" };
const durumEt = (d) => `<span class="et ${DURUM_ET[d] ?? ""}">${esc(d)}</span>`;
const TIP_AD = { haber: "Haber", guncelleme: "Güncelleme", genisletme: "Genişletme", analiz: "Analiz" };
let DENETLEYEN = { "yagmur-tahtasiz": "Av. Yağmur Tahtasız", "umut-tekin": "Av. Umut Tekin" };
const YZ_RENK = ["mor", "mavi", "yesil", "sari", "lac"];
const yazarRenk = (k) => YZ_RENK[Math.max(0, Object.keys(DENETLEYEN).indexOf(k)) % YZ_RENK.length];
const denetleyenEt = (d) => d ? `<span class="et ${yazarRenk(d)}">${esc(DENETLEYEN[d] || d)}</span>` : '<span class="soluk kucuk">—</span>';
const yazarSecenek = () => Object.entries(DENETLEYEN);
const kucukGorsel = (u) => u ? `<img class="kucuk-gorsel" src="${esc(u)}" alt="" loading="lazy">` : '<span class="kucuk-gorsel yok">görsel yok</span>';

function grafik(seri, anahtar, etiket) {
  const enb = Math.max(1, ...seri.map((x) => x[anahtar]));
  return `<div class="grafik">${seri.map((x, i) => `<div title="${esc(etiket(x))}: ${x[anahtar]}"><b>${x[anahtar] || ""}</b><i class="${i === seri.length - 1 ? "bugun" : ""}" style="height:${Math.max(2, x[anahtar] / enb * 100)}%"></i><em>${esc(etiket(x))}</em></div>`).join("")}</div>`;
}

function cipAlani(kap, degerler, yer) {
  let L = [...degerler];
  const ciz = () => {
    kap.innerHTML = L.map((v, i) => `<span class="cip">${esc(v)}<button type="button" data-i="${i}" aria-label="Kaldır">×</button></span>`).join("") + `<input type="text" placeholder="${esc(yer)}">`;
    const inp = $("input", kap);
    inp.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === ",") && inp.value.trim()) { e.preventDefault(); L.push(inp.value.trim().replace(/,$/, "")); ciz(); $("input", kap).focus(); }
      else if (e.key === "Backspace" && !inp.value && L.length) { L.pop(); ciz(); $("input", kap).focus(); }
    });
    inp.addEventListener("blur", () => { if (inp.value.trim()) { L.push(inp.value.trim()); ciz(); } });
  };
  kap.classList.add("cip-alani");
  kap.addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) { L.splice(+b.dataset.i, 1); ciz(); } else if (e.target === kap) $("input", kap).focus(); });
  ciz();
  return () => { const v = $("input", kap).value.trim(); return v ? [...L, v] : L; };
}

function satirListesi(kap, satirlar, alanlar, ekle) {
  // alanlar: [{yer, tur}] — her satır bir dizi değer
  const ciz = () => {
    kap.innerHTML = satirlar.map((s, i) => `<div class="satir-ozet">${alanlar.map((a, j) => a.cok
      ? `<textarea rows="2" data-i="${i}" data-j="${j}" placeholder="${esc(a.yer)}">${esc(s[j] || "")}</textarea>`
      : `<input type="${a.tur || "text"}" data-i="${i}" data-j="${j}" placeholder="${esc(a.yer)}" value="${esc(s[j] || "")}" style="${a.gen ? "flex:" + a.gen : ""}">`).join("")}
      <button type="button" class="btn btn-kucuk btn-hayalet" data-sil="${i}" aria-label="Satırı sil">✕</button></div>`).join("") +
      `<button type="button" class="btn btn-kucuk" data-ekle>+ ${esc(ekle)}</button>`;
  };
  kap.addEventListener("input", (e) => { const t = e.target; if (t.dataset.i != null) satirlar[+t.dataset.i][+t.dataset.j] = t.value; });
  kap.addEventListener("click", (e) => {
    if (e.target.closest("[data-sil]")) { satirlar.splice(+e.target.closest("[data-sil]").dataset.sil, 1); ciz(); }
    if (e.target.closest("[data-ekle]")) { satirlar.push(alanlar.map(() => "")); ciz(); const g = $$("[data-i]", kap); if (g.length) g[g.length - alanlar.length].focus(); }
  });
  ciz();
  return () => satirlar.map((s) => s.map((x) => String(x || "").trim())).filter((s) => s.some(Boolean));
}

// ------------------------------------------------------------ GÖSTERGE
function bakiyeKarti(bk, ml) {
  if (!bk) return "";
  const a = bk.servisler.find((x) => x.servis === "anthropic") || {}, x = bk.servisler.find((y) => y.servis === "x") || {}, t = x.tahmin || {};
  const usd = (v) => v == null ? "—" : "$" + Number(v).toFixed(2);
  const ren = (d) => d === "kritik" ? "kirmizi" : d === "dusuk" ? "sari" : "yesil";
  const durumYaz = (d) => d === "kritik" ? "Kritik" : d === "dusuk" ? "Azalıyor" : d === "iyi" ? "Yeterli" : "Bilinmiyor";
  const saat = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : "";
  const aktif = (a.krediler || []).filter((k) => k.aktif !== false && k.bitis >= new Date().toISOString().slice(0, 10));
  const xNet = x.net != null ? x.net : t.kalan;
  const cs = ((ml && ml.seri) || []).slice(-7), xg = Object.fromEntries((t.seri || []).map((v) => [v.gun, v.usd]));
  const kutu = (baslik, tutar, durum, alt) => `<div class="kart sayi-kart" style="padding:22px"><div class="satir"><span>${baslik}</span><span class="et ${ren(durum)}" style="margin-left:auto">${durumYaz(durum)}</span></div>
    <b style="font-size:40px;line-height:1.1;margin:8px 0 6px">${usd(tutar)}</b><small>${alt}</small></div>`;
  return `<div class="izgara iz-2">
    ${kutu("Claude API · kalan kredi", a.kalan, a.durdu ? "kritik" : a.durum,
      aktif.map((k) => `${usd(k.kalan)} → ${tarihYaz(k.bitis)} bitiyor`).join(" · ") + (a.yanacak > 1 ? `<br><span style="font-weight:650">${usd(a.yanacak)} kullanılmadan yanacak (ek mesai açık)</span>` : "") + `<br>Bugün harcanan ${usd(a.bugunku)}`)}
    ${kutu("X API · kalan bakiye", xNet, x.durum,
      (x.net != null ? `X'ten canlı okundu (${saat(x.net_ts)})` : "X'e ulaşılamadı; son okumadan tahmin") + ` · bugün harcanan ${usd(t.bugun)} · günlük ort. ${usd(t.gunluk_ortalama)}` + (t.gunluk_ortalama ? ` · yaklaşık ${Math.floor((xNet || 0) / t.gunluk_ortalama)} gün yeter` : "") + (x.aciklama ? `<br><span style="color:var(--kirmizi)">${esc(x.aciklama)}</span>` : ""))}
  </div>
  <details class="kart mt" style="padding:12px 18px"><summary class="soluk kucuk" style="cursor:pointer">Son 7 günün API harcaması</summary>
    <table class="mt"><thead><tr><th>Gün</th><th>Claude</th><th>X</th></tr></thead><tbody>${cs.slice().reverse().map((c) => `<tr><td>${tarihYaz(c.gun)}</td><td>${usd(c.maliyet)}</td><td>${usd(xg[c.gun])}</td></tr>`).join("")}</tbody></table></details>`;
}

async function sGosterge() {
  baslikYaz("Gösterge", "Sitenin ve yayın hattının genel durumu", `<a class="btn" href="#/yeni">${ikon("yeni")}<span class="metin">Yeni yazı</span></a>`);
  const [g, z, bk, ml] = await Promise.all([api("/gosterge"), api("/ziyaret?gun=14").catch(() => null), api("/bakiyeler").catch(() => null), api("/maliyet").catch(() => null)]);
  ROZET.bekleyen = g.bekleyen; ROZET.okunmamis = g.okunmamis; menuCiz();
  const oran = g.butce ? Math.min(100, g.maliyet / g.butce * 100) : 0;
  const s = g.servis;
  icerik().innerHTML = `
  ${bakiyeKarti(bk, ml)}
  <div class="izgara iz-5 mt">
    <a class="kart sayi-kart vurgu" href="#/taslaklar"><span>Onay bekleyen</span><b>${sayi(g.bekleyen)}</b><small>${g.bekleyen ? "Editör kararı bekliyor" : "Bekleyen taslak yok"}</small></a>
    <a class="kart sayi-kart" href="#/yazilar"><span>Bugün yayımlanan</span><b>${sayi(g.bugun)}</b><small>Son 7 gün: ${sayi(g.hafta)}</small></a>
    <a class="kart sayi-kart" href="#/yazilar"><span>Toplam haber</span><b>${sayi(g.toplam_yazi)}</b><small>${sayi(g.toplam_yazi - (g.toplam_analiz || 0))} haber · ${sayi(g.toplam_analiz || 0)} analiz</small></a>
    <a class="kart sayi-kart" href="#/mesajlar"><span>Okunmamış mesaj</span><b>${sayi(g.okunmamis)}</b><small>${g.mesaj_baglanti.hazir ? "İletişim formu bağlı" : "Form bağlantısı kuruluyor"}</small></a>
    <a class="kart sayi-kart" href="#/maliyet"><span>Bugünkü maliyet</span><b>$${g.maliyet.toFixed(2)}</b><small>Bugünkü pay: $${g.butce}</small><div class="ilerleme"><i class="${oran > 90 ? "tehlike" : oran > 70 ? "uyari" : ""}" style="width:${oran}%"></i></div></a>
  </div>
  ${z ? `<div class="izgara iz-4 mt">
    <a class="kart sayi-kart vurgu" href="#/ziyaretciler"><span>Şu an sitede</span><b>${sayi(z.su_an)}</b><small>Son 5 dakikada etkin ziyaretçi</small></a>
    <a class="kart sayi-kart" href="#/ziyaretciler"><span>Bugün ziyaretçi</span><b>${sayi(z.bugun.ziyaretci)}</b><small>${sayi(z.bugun.goruntulenme)} sayfa görüntüleme</small></a>
    <a class="kart sayi-kart" href="#/ziyaretciler"><span>Son 14 gün</span><b>${sayi(z.donem.ziyaretci)}</b><small>${sayi(z.donem.goruntulenme)} sayfa görüntüleme</small></a>
    <a class="kart sayi-kart" href="#/ziyaretciler"><span>En çok gelen kaynak</span><b style="font-size:20px">${esc((z.kaynaklar.find((k) => k.ad !== "(site içi)") || {}).ad || "—")}</b><small>${z.ilk_kayit ? "Sayım başlangıcı: " + tarihYaz(z.ilk_kayit) : "Henüz ziyaret kaydı yok"}</small></a>
  </div>
  <div class="kart mt"><div class="kart-ust"><h2>Son 14 günde ziyaretçi</h2><a href="#/ziyaretciler">Ayrıntı</a></div>
    <div class="kart-ic">${grafik(z.seri, "ziyaretci", (x) => { const [, a, gn] = x.gun.split("-"); return `${+gn} ${AYLAR[+a - 1]}`; })}</div></div>` : ""}
  <div class="izgara iz-21 mt">
    <div class="kart"><div class="kart-ust"><h2>Son 14 günde yayımlanan</h2><span class="soluk">${sayi(g.seri.reduce((a, x) => a + x.adet, 0))} yazı</span></div>
      <div class="kart-ic">${grafik(g.seri, "adet", (x) => { const [, a, gn] = x.gun.split("-"); return `${+gn} ${AYLAR[+a - 1]}`; })}</div></div>
    <div class="kart"><div class="kart-ust"><h2>Servis durumu</h2><a href="#/yayin">Ayrıntı</a></div>
      <div class="kart-ic"><dl class="anahtar-deger">
        <dt>Yayın</dt><dd><span class="et yesil">Editör onayıyla</span></dd>
        <dt>Çalışma süresi</dt><dd>${esc(sure(s.calisma_sn))}</dd>
        <dt>Son derleme</dt><dd><code>${esc(s.site_commit)}</code></dd>
        <dt>Cloudflare</dt><dd>${s.cf_esit ? '<span class="et yesil">Güncel</span>' : `<span class="et sari">Eşitleniyor</span> <code>${esc(s.cf_commit || "—")}</code>`}</dd>
        <dt>Bugünkü hata</dt><dd>${g.bugun_hata ? `<a href="#/kayitlar">${g.bugun_hata} kayıt</a>` : '<span class="et yesil">Yok</span>'}</dd>
        <dt>Görselsiz yazı</dt><dd>${g.gorselsiz ? `<a href="#/yazilar">${g.gorselsiz}</a>` : '<span class="et yesil">Yok</span>'}</dd>
      </dl></div></div>
  </div>
  <div class="izgara iz-2 mt">
    <div class="kart"><div class="kart-ust"><h2>Onay bekleyenler</h2><a href="#/taslaklar">Tümü</a></div>
      ${g.bekleyen_liste.length ? `<ul class="liste">${g.bekleyen_liste.map((t) => `<li><div class="ana-satir"><a href="#/taslak/${esc(t.id)}">${esc(t.baslik)}</a><small>${esc(TIP_AD[t.tip] || t.tip)} · ${esc(t.kat)} · ${once(t.ts)}</small></div><a class="btn btn-kucuk" href="#/taslak/${esc(t.id)}">İncele</a></li>`).join("")}</ul>` : '<div class="bos"><b>Bekleyen taslak yok</b>Yeni taslaklar burada görünür.</div>'}</div>
    <div class="kart"><div class="kart-ust"><h2>Son okur mesajları</h2><a href="#/mesajlar">Tümü</a></div>
      ${g.son_mesajlar.length ? `<ul class="liste">${g.son_mesajlar.map((m) => `<li><div class="ana-satir"><a href="#/mesajlar/${esc(m.no)}">${m.durum === "yeni" ? '<span class="nokta" style="background:var(--mavi);margin-right:6px"></span>' : ""}${esc(m.baslik)}</a><small>${esc(m.konu_ad)} · ${esc(m.ad)} · ${once(m.ts)}</small></div></li>`).join("")}</ul>` : '<div class="bos"><b>Mesaj yok</b>İletişim formundan gelen mesajlar burada listelenir.</div>'}</div>
  </div>
  <div class="kart mt"><div class="kart-ust"><h2>Son yayımlanan yazılar</h2><a href="#/yazilar">Tüm yazılar</a></div>
    <div class="tablo-kap"><table><thead><tr><th></th><th>Başlık</th><th>Tür</th><th>Hukuki inceleme</th><th>Tarih</th></tr></thead><tbody>
    ${g.son_yazilar.map((p) => `<tr><td style="width:76px">${kucukGorsel(p.kucuk)}</td><td class="baslik-hucre"><a href="#/yazi/${esc(p.slug)}">${esc(p.baslik)}</a><small>${esc(p.kategoriler.join(", "))}</small></td><td><span class="et ${p.tur === "Analiz" ? "mor" : "lac"}">${esc(p.tur)}</span></td><td>${denetleyenEt(p.denetleyen)}</td><td class="soluk kucuk">${tarihYaz(p.tarih)} ${esc(p.saat)}</td></tr>`).join("")}
    </tbody></table></div></div>
  <div class="izgara iz-2 mt">
    <div class="kart"><div class="kart-ust"><h2>Hukuki inceleme dağılımı</h2><a href="#/yazarlar">Ayrıntı</a></div><div class="kart-ic"><dl class="anahtar-deger">
      ${yazarSecenek().map(([k, ad]) => `<dt>${esc(ad)}</dt><dd>${sayi(g.denetleyen[k] || 0)} yazı</dd>`).join("")}<dt>İnceleme kartı yok</dt><dd>${sayi(g.denetleyen.yok)} yazı</dd></dl></div></div>
    <div class="kart"><div class="kart-ust"><h2>Son 14 gün · kategoriler</h2></div><div class="kart-ic"><dl class="anahtar-deger">
      ${g.kategoriler.map(([k, n]) => `<dt>${esc(k)}</dt><dd>${n}</dd>`).join("") || '<dt class="soluk">Kayıt yok</dt><dd></dd>'}</dl></div></div>
  </div>
  ${g.son_hatalar.length ? `<div class="kart mt"><div class="kart-ust"><h2>Bugünkü son hatalar</h2><a href="#/kayitlar">Kayıtlar</a></div><div class="kart-ic"><div class="kayit">${g.son_hatalar.map((x) => `<span class="h">${esc(x)}</span>`).join("\n")}</div></div></div>` : ""}`;
}

// ------------------------------------------------------------ TASLAKLAR
async function sTaslaklar() {
  let filtre = sessionStorage.getItem("hh-taslak-filtre") || "bekliyor";
  baslikYaz("Onay bekleyenler", "Botun ve editörlerin hazırladığı taslaklar; yayın için editör onayı gerekir", `<a class="btn" href="#/yeni">${ikon("yeni")}<span class="metin">Yeni yazı</span></a>`);
  let veri = [], z = null;
  const no = SAYFA_NO, aktif = () => no === SAYFA_NO;
  const ISLEMDE = ["yayınlanıyor", "kaldırılıyor"];
  const yerel = {};   // tıklanan taslağın sunucu yanıtı gelene kadar gösterilecek durumu
  const durumu = (x) => yerel[x.id] && x.durum === "bekliyor" ? yerel[x.id] : x.durum;
  const uyar = (f, x) => f === "hepsi" || (f === "bekliyor" ? durumu(x) === "bekliyor" || ISLEMDE.includes(durumu(x)) : f === "reddedildi" ? /red|geri|kald|zaten/.test(durumu(x)) && !ISLEMDE.includes(durumu(x)) : durumu(x) === f);
  const ciz = () => {
    const say = (f) => veri.filter((x) => uyar(f, x)).length;
    const L = veri.filter((x) => uyar(filtre, x));
    icerik().innerHTML = `<div class="sekmeler">${[["bekliyor", "Bekleyen"], ["yayınlandı", "Yayınlanan"], ["reddedildi", "Reddedilen / kaldırılan"], ["hepsi", "Tümü"]].map(([f, a]) => `<button data-f="${f}" class="${filtre === f ? "on" : ""}">${a}<span class="et">${say(f)}</span></button>`).join("")}</div>
      <div class="kart">${L.length ? L.map((t) => { const d = durumu(t), islemde = ISLEMDE.includes(d); return `<div class="taslak ${islemde ? "islemde" : ""}" data-tid="${esc(t.id)}">
        ${t.gorsel ? `<img src="${esc(t.gorsel)}" alt="" loading="lazy">` : '<span class="gorsel-yok">yazılı kapak</span>'}
        <div class="govde"><div class="meta">${islemde ? `<span class="et mavi"><span class="don"></span> ${esc(t.gorsel_bekleniyor ? "fotoğraf bekleniyor, hazır olunca yayınlanacak" : d)}</span>` : durumEt(d)}<span class="et ${t.tip === "haber" ? "lac" : "mor"}">${esc(TIP_AD[t.tip] || t.tip)}</span>${t.ilk ? '<span class="et yesil">İlk veren</span>' : ""}${t.olay_tarihi ? `<span class="et sari" title="Ek mesai: olay tarihiyle yayımlanır, ana sayfada yeni gibi görünmez, X'te paylaşılmaz">Eski tarihli · ${esc(tarihYaz(t.olay_tarihi))}</span>` : ""}${t.birlesen ? `<span class="et mavi" title="Sonradan gelen paylaşımlardaki yeni bilgiler bu taslağa eklendi">+${t.birlesen} paylaşım eklendi</span>` : ""}<span>${esc(t.kat)}</span><span>@${esc(t.kaynak)}</span><span>${once(t.ts)}</span></div>
          <a class="t" href="#/taslak/${esc(t.id)}">${esc(t.baslik)}</a>
          ${t.hata && !islemde ? `<div class="uyari-kutu kirmizi kucuk">Son deneme hata verdi: ${esc(t.hata)}</div>` : ""}
          ${islemde ? `<div class="soluk kucuk">${d === "yayınlanıyor" ? "Site derleniyor ve yükleniyor; bitince bu listeden kalkar." : "Yayından kaldırılıyor…"}</div>` : ""}</div>
        <div class="eylem">${d === "bekliyor" ? `<button class="btn btn-yesil btn-kucuk" data-k="yayinla" data-id="${esc(t.id)}">Yayınla</button><button class="btn btn-kucuk btn-cizgi-kirmizi" data-k="reddet" data-id="${esc(t.id)}">Reddet</button>` : ""}
          ${islemde ? `<button class="btn btn-kucuk" disabled>${d === "yayınlanıyor" ? "Yayınlanıyor…" : "Kaldırılıyor…"}</button>` : ""}
          ${d === "reddedildi" ? `<button class="btn btn-kucuk" data-k="geriyukle" data-id="${esc(t.id)}">Geri yükle</button>` : ""}
          ${t.url && !islemde ? `<a class="btn btn-kucuk" href="${esc(t.url)}" target="_blank" rel="noopener">Sitede ↗</a>` : ""}
          <a class="btn btn-kucuk" href="#/taslak/${esc(t.id)}">Aç</a></div></div>`; }).join("") : '<div class="bos"><b>Bu listede taslak yok</b>Bot yeni bir haber hazırladığında burada görünür.</div>'}</div>`;
  };
  const zamanla = () => {
    clearInterval(z);
    if (!aktif()) return;
    const hizli = veri.some((x) => ISLEMDE.includes(durumu(x)));
    z = setInterval(() => { if (!document.hidden) yukle().catch(() => {}); }, hizli ? 3000 : 15000);
  };
  const yukle = async () => {
    if (!aktif()) return;
    const onceki = Object.fromEntries(veri.map((x) => [x.id, durumu(x)]));
    const yeni = (await api("/taslaklar?gun=21")).taslaklar;
    if (!aktif()) return;   // bu arada başka sayfaya geçildi
    veri = yeni;
    for (const x of veri) {
      if (yerel[x.id] && x.durum !== "bekliyor") delete yerel[x.id];
      const o = onceki[x.id];
      if (o === "yayınlanıyor" && x.durum === "yayınlandı") bildir("Yayınlandı: " + x.baslik, "tamam", 6000);
      else if (o === "kaldırılıyor" && /kald|red/.test(x.durum)) bildir("Kaldırıldı: " + x.baslik, "tamam", 6000);
      else if (ISLEMDE.includes(o || "") && x.durum === "bekliyor") bildir("Yayın tamamlanamadı: " + x.baslik + (x.hata ? " (" + x.hata + ")" : ""), "hata", 10000);
    }
    ROZET.bekleyen = veri.filter((x) => x.durum === "bekliyor").length; menuCiz(); ciz(); zamanla();
  };
  await yukle();
  const tik = async (e) => {
    const s = e.target.closest(".sekmeler button");
    if (s) { filtre = s.dataset.f; sessionStorage.setItem("hh-taslak-filtre", filtre); return ciz(); }
    const b = e.target.closest("button[data-k]"); if (!b) return;
    const t = veri.find((x) => x.id === b.dataset.id), k = b.dataset.k;
    if (k === "yayinla" || k === "reddet") {
      if (k === "reddet" && !(await pencere({ baslik: "Taslak reddedilsin mi?", metin: `<p>${esc(t ? t.baslik : "")}</p>`, onay: "Reddet", tehlike: true }))) return;
      if (k === "yayinla") { yerel[b.dataset.id] = "yayınlanıyor"; ciz(); }
      const r = await kararVer(k, b.dataset.id, t, true);
      if (!aktif()) return;
      if (!r) { delete yerel[b.dataset.id]; ciz(); return; }
      if (r.oge && r.oge.durum) { const i = veri.findIndex((x) => x.id === b.dataset.id); if (i >= 0) veri[i] = Object.assign(veri[i], r.oge); }
      ciz(); zamanla(); setTimeout(() => yukle().catch(() => {}), 2500);
      return;
    }
    await kararVer(k, b.dataset.id, t); if (aktif()) await yukle();
  };
  icerik().addEventListener("click", tik);
  sayfaTemizle = () => { clearInterval(z); icerik().removeEventListener("click", tik); };
}

async function kararVer(komut, id, t, onaylandi = false) {
  if (komut === "reddet" && !onaylandi) {
    const ok = await pencere({ baslik: t && t.durum === "yayınlandı" ? "Yayından kaldırılsın mı?" : "Taslak reddedilsin mi?", metin: `<p>${esc(t ? t.baslik : "")}</p>`, onay: t && t.durum === "yayınlandı" ? "Yayından kaldır" : "Reddet", tehlike: true });
    if (!ok) return;
  }
  try {
    const r = await api(`/taslak/${encodeURIComponent(id)}/karar`, { veri: { komut } });
    bildir({ yayinla: "Yayınlanıyor; derleme ve yükleme 1-2 dakika sürer.", reddet: "Karar işlendi.", geriyukle: "Taslak bekleyenlere döndü." }[komut], "tamam");
    return r;
  } catch (e) { hata(e); }
}

function seoKarti(o, bekliyor, simdiki) {
  const degisti = o.eski && o.eski.baslik !== simdiki;
  const et = o.uygulandi ? '<span class="et yesil">Uygulandı</span>' : o.adaylar && o.adaylar.length ? '<span class="et mavi">Öneri</span>' : '<span class="et">Değişmedi</span>';
  const oneri = Object.entries(o.oneriler || {});
  return `<div class="kart mt"><div class="kart-ust"><h2>Arama uyumu</h2>${et}</div><div class="kart-ic">
    ${o.anahtar_ifade ? `<p class="mb">Anahtar ifade: <b>${esc(o.anahtar_ifade)}</b></p>` : ""}
    ${o.neden ? `<p class="soluk kucuk mb">${esc(o.neden)}</p>` : ""}
    ${degisti ? `<div class="uyari-kutu mavi mb satir"><span style="flex:1">Yazarın özgün başlığı: <b>${esc(o.eski.baslik)}</b></span>${bekliyor ? `<button class="btn btn-kucuk" data-seo-baslik="${esc(o.eski.baslik)}">Özgüne dön</button>` : ""}</div>` : ""}
    ${(o.adaylar || []).length ? `<div class="kalin kucuk mb">Başlık adayları</div><ul class="liste mb">${o.adaylar.map((a) => `<li><div class="ana-satir"><b style="white-space:normal;font-weight:550">${esc(a.baslik)}</b><small style="white-space:normal">${a.baslik.length} karakter${a.not ? " · " + esc(a.not) : ""}${a.uygun ? "" : ` · <span style="color:var(--kirmizi)">uygulanmaz: ${esc(a.sorun)}</span>`}</small></div>${bekliyor && a.uygun && a.baslik !== simdiki ? `<button class="btn btn-kucuk" data-seo-baslik="${esc(a.baslik)}">Kullan</button>` : a.baslik === simdiki ? '<span class="et yesil">Kullanılıyor</span>' : ""}</li>`).join("")}</ul>` : ""}
    ${o.yeni && o.yeni.etiketler && o.yeni.etiketler.length ? `<div class="satir mb"><span class="kucuk" style="flex:1"><b>Önerilen etiketler:</b> ${esc(o.yeni.etiketler.join(", "))}</span>${bekliyor ? `<button class="btn btn-kucuk" data-seo-etiket="${esc(o.yeni.etiketler.join(", "))}">Kullan</button>` : ""}</div>` : ""}
    ${(o.ifadeler || []).length ? `<details class="mb" open><summary class="kalin kucuk">Aday ifadeler: hacim ve rekabet (tahmini)</summary><div class="tablo-kap mt"><table><thead><tr><th>İfade</th><th>Hacim</th><th>Rekabet</th><th>Puan</th></tr></thead><tbody>${o.ifadeler.slice(0, 10).map((v) => `<tr${o.anahtar_ifade && v.ifade.toLowerCase() === String(o.anahtar_ifade).toLowerCase() ? ' style="background:var(--yesil-acik, rgba(22,163,74,.08))"' : ""}><td style="white-space:normal">${esc(v.ifade)}${v.gsc ? `<br><small class="soluk">Google'da ${v.gsc.sira}. sıradayız · ${v.gsc.gosterim} gösterim</small>` : ""}</td><td><span class="et ${v.hacim >= 67 ? "yesil" : v.hacim >= 34 ? "mavi" : ""}">${v.hacim >= 67 ? "Yüksek" : v.hacim >= 34 ? "Orta" : "Düşük"}</span></td><td><span class="et ${v.rekabet >= 67 ? "kirmizi" : v.rekabet >= 34 ? "sari" : "yesil"}">${v.rekabet >= 67 ? "Yüksek" : v.rekabet >= 34 ? "Orta" : "Düşük"}</span></td><td class="kalin">${v.puan}</td></tr>`).join("")}</tbody></table></div><div class="soluk kucuk mt">Hacim: Google önerilerindeki sırası ve Search Console gösterimi. Rekabet: ifade uzunluğu ve sitenin o aramadaki sırası. Ücretsiz veriden tahmindir.</div></details>` : ""}
    <details class="mb"><summary class="kalin kucuk">Google önerileri (${oneri.reduce((t, [, l]) => t + l.length, 0)})</summary>${oneri.map(([t, l]) => `<div class="kucuk mt"><b>${esc(t)}</b>: ${l.length ? l.map((x, i) => `<span class="et" title="${i + 1}. sırada öneriliyor">${esc(x)}</span>`).join(" ") : '<span class="soluk">öneri yok</span>'}</div>`).join("")}</details>
    <details><summary class="kalin kucuk">Search Console'da örtüşen sorgular (${(o.gsc || []).length})</summary>${(o.gsc || []).length ? `<ul class="liste">${o.gsc.map((x) => `<li><div class="ana-satir"><b style="font-weight:550">${esc(x.kelime)}</b><small>${sayi(x.gosterim)} gösterim · ${sayi(x.tiklama)} tıklama · sıra ${x.sira}</small></div>${x.firsat ? '<span class="et sari">Fırsat</span>' : ""}</li>`).join("")}</ul>` : '<div class="soluk kucuk mt">Son 28 günde bu haberle örtüşen sorgu yok.</div>'}</details>
    ${o.sure != null ? `<div class="soluk kucuk mt">İnceleme ${o.sure} sn sürdü.</div>` : ""}
  </div></div>`;
}

async function sTaslak(id) {
  const d = await api("/taslak/" + encodeURIComponent(id));
  baslikYaz(TIP_AD[d.tip] || "Taslak", d.baslik, `<a class="btn" href="#/taslaklar">← Liste</a>`);
  const bekliyor = d.durum === "bekliyor";
  icerik().innerHTML = `
  <div class="izgara iz-21">
    <div class="kart"><div class="kart-ust"><h2>Önizleme</h2><span class="soluk kucuk">Sitedeki görünümüyle</span></div>
      <div class="kart-ic"><iframe class="onizleme" src="/yonetim/api/taslak/${encodeURIComponent(id)}/onizleme" title="Önizleme"></iframe></div></div>
    <div>
      <div class="kart"><div class="kart-ust"><h2>Durum</h2>${durumEt(d.durum)}</div><div class="kart-ic"><dl class="anahtar-deger">
        <dt>Tür</dt><dd>${esc(TIP_AD[d.tip] || d.tip)} · ${esc(d.tur_yazi || "")}</dd>${d.olay_tarihi ? `<dt>Yayın tarihi</dt><dd><span class="et sari">Eski tarihli: ${esc(tarihYaz(d.olay_tarihi))}</span> Olay tarihiyle listelenir; yazıda "siteye eklenme" notu çıkar, X'te paylaşılmaz.</dd>` : ""}
        <dt>Kaynak</dt><dd>${d.tweet_url ? `<a href="${esc(d.tweet_url)}" target="_blank" rel="noopener">@${esc(d.kaynak)} ↗</a>` : "@" + esc(d.kaynak)}</dd>
        <dt>Kategori</dt><dd>${esc(d.kat)}</dd><dt>Kelime</dt><dd>${sayi(d.kelime)}</dd>
        <dt>İlk veren</dt><dd>${d.ilk ? "Evet" : "Hayır"}${d.diger_siteler ? ` · ${d.diger_siteler} sitede var` : ""}</dd>
        <dt>Görsel</dt><dd>${d.gorsel_puan != null ? `Denetim puanı ${d.gorsel_puan}/5` : esc(d.gorsel_kaynak || "—")}</dd>
        <dt>Hazırlandı</dt><dd>${zamanYaz(d.ts)}</dd>${d.url ? `<dt>Adres</dt><dd><a href="${esc(d.url)}" target="_blank" rel="noopener">Sitede aç ↗</a></dd>` : ""}
      </dl>${d.hata ? `<div class="uyari-kutu kirmizi mt">Son deneme hata verdi: ${esc(d.hata)}</div>` : ""}</div>
      <div class="yapiskan-alt">
        ${bekliyor ? `<button class="btn btn-yesil" data-k="yayinla">Yayınla</button><button class="btn btn-cizgi-kirmizi" data-k="reddet">Reddet</button>` : ""}
        ${d.durum === "yayınlandı" ? `<button class="btn btn-cizgi-kirmizi" data-k="reddet">Yayından kaldır</button>` : ""}
        ${d.durum === "reddedildi" ? `<button class="btn" data-k="geriyukle">Geri yükle</button>` : ""}
      </div></div>
      ${bekliyor && d.tip === "haber" ? `<div class="kart mt"><div class="kart-ust"><h2>Düzenle</h2></div><div class="kart-ic">
        <div class="alan"><label for="t-baslik">Başlık <span class="soluk kucuk" id="t-sayac"></span></label><input id="t-baslik" type="text" maxlength="75" value="${esc(d.baslik)}"></div>
        <div class="alan"><label for="t-etiket">Etiketler <span class="soluk kucuk">(virgülle ayırın, 2-8 adet)</span></label><input id="t-etiket" type="text" value="${esc((d.etiketler || []).join(", "))}"></div>
        <div class="alan"><span>Öne çıkanlar</span><div id="t-ozet"></div></div>
        <label class="anahtar mb"><input type="checkbox" id="t-x" ${d.x_paylas !== false ? "checked" : ""}> Yayımlanınca X'te paylaş</label>
        <button class="btn btn-ana" id="t-kaydet">Kaydet</button></div></div>` : ""}
      ${d.seo ? seoKarti(d.seo, bekliyor, d.baslik) : ""}
      ${bekliyor && d.tip === "guncelleme" ? `<div class="kart mt"><div class="kart-ust"><h2>Güncelleme notu</h2></div><div class="kart-ic"><textarea id="t-not" rows="5">${esc(d.not || "")}</textarea><button class="btn btn-ana mt" id="t-not-kaydet">Kaydet</button></div></div>` : ""}
      ${d.tip === "guncelleme" && (d.duzeltmeler || []).length ? `<div class="kart mt"><div class="kart-ust"><h2>Yazıda değişecek cümleler</h2></div><div class="kart-ic">
        <p class="soluk kucuk mb">Güncelleme yayımlanınca bu cümleler yazının ${"başlık, özet, sık sorulan sorular ve metninde"} yenileriyle değiştirilir; böylece yazıda eskiyen bilgi kalmaz.</p>
        ${d.duzeltmeler.map(x => `<div class="mb"><div class="kucuk soluk"><s>${esc(x.eski)}</s></div><div>${esc(x.yeni)}</div></div>`).join("")}</div></div>` : ""}
    </div>
  </div>
  ${bekliyor ? `<div class="kart mt"><div class="kart-ust"><h2>Görsel</h2><div class="satir"><button class="btn btn-kucuk" id="g-oto">Otomatik yeniden seç</button><button class="btn btn-kucuk" id="g-yok">Yazılı kapak kullan</button></div></div>
    <div class="kart-ic"><div class="satir mb">${d.gorsel_buyuk ? `<img src="${esc(d.gorsel_buyuk)}" alt="" style="width:240px;border-radius:10px">` : '<span class="soluk">Şu an yazılı kapak kullanılıyor.</span>'}
      <div class="soluk kucuk" style="flex:1">${esc((d.gorsel_denetim && d.gorsel_denetim.goruluyor) || "")}<br>${esc(d.kredi || "")}</div></div>
      <form class="satir" id="g-ara"><input type="search" class="ara" placeholder="Fotoğraf ara (ör. Yargıtay binası, mahkeme salonu)"><button class="btn">Ara</button></form>
      <div id="g-adaylar" class="gorsel-aday mt"></div></div></div>` : ""}`;

  const getOzet = $("#t-ozet") ? satirListesi($("#t-ozet"), (d.ozet || []).map((x) => [x]), [{ yer: "Madde", cok: true }], "Madde ekle") : null;
  const sayac = () => { const i = $("#t-baslik"); if (i) $("#t-sayac").textContent = `(${i.value.length}/75)`; };
  if ($("#t-baslik")) { $("#t-baslik").addEventListener("input", sayac); sayac(); }
  icerik().addEventListener("click", async (e) => {
    const k = e.target.closest("button[data-k]");
    if (k) { const r = await kararVer(k.dataset.k, id, d); if (r) setTimeout(yonlendir, 600); return; }
    const sb = e.target.closest("[data-seo-baslik]");
    if (sb && $("#t-baslik")) { $("#t-baslik").value = sb.dataset.seoBaslik; sayac(); $("#t-baslik").focus(); bildir("Başlık alana yazıldı; kaydetmek için Kaydet'e basın.", "tamam"); return; }
    const se = e.target.closest("[data-seo-etiket]");
    if (se && $("#t-etiket")) { $("#t-etiket").value = se.dataset.seoEtiket; bildir("Etiketler alana yazıldı; kaydetmek için Kaydet'e basın.", "tamam"); return; }
    if (e.target.id === "t-kaydet") {
      try { await api(`/taslak/${encodeURIComponent(id)}/duzenle`, { veri: { baslik: $("#t-baslik").value, etiketler: $("#t-etiket").value.split(",").map((x) => x.trim()).filter(Boolean), ozet: getOzet().map((x) => x[0]), x_paylas: $("#t-x").checked } }); bildir("Kaydedildi.", "tamam"); $(".onizleme").src += ""; } catch (er) { hata(er); }
    }
    if (e.target.id === "t-not-kaydet") {
      try { await api(`/taslak/${encodeURIComponent(id)}/duzenle`, { veri: { not: $("#t-not").value } }); bildir("Kaydedildi.", "tamam"); $(".onizleme").src += ""; } catch (er) { hata(er); }
    }
    if (e.target.id === "g-oto" || e.target.id === "g-yok") {
      const t = bildir(e.target.id === "g-oto" ? "Yeni görsel seçiliyor (bir dakika sürebilir)…" : "Kaydediliyor…", "is", 0);
      try { const r = await api(`/taslak/${encodeURIComponent(id)}/gorsel`, { veri: { secim: e.target.id === "g-oto" ? "otomatik" : "yok" } }); t.remove(); bildir(r.mesaj, "tamam"); yonlendir(); } catch (er) { t.remove(); hata(er); }
    }
    const ad = e.target.closest("button[data-no]");
    if (ad) {
      try { const r = await api(`/taslak/${encodeURIComponent(id)}/gorsel`, { veri: { secim: ad.dataset.no } }); bildir(r.mesaj, "tamam"); yonlendir(); } catch (er) { hata(er); }
    }
  });
  const ga = $("#g-ara");
  if (ga) ga.addEventListener("submit", async (e) => {
    e.preventDefault(); const q = $("input", ga).value.trim(); $("#g-adaylar").innerHTML = '<div class="yukleniyor"></div>';
    try {
      const r = await api(`/taslak/${encodeURIComponent(id)}/gorseller?q=${encodeURIComponent(q)}`);
      $("#g-adaylar").innerHTML = r.adaylar.map((a) => `<button type="button" data-no="${a.no}" title="${esc(a.baslik)} · ${esc(a.lisans)}"><img src="${esc(a.kucuk)}" alt="" loading="lazy"><span>${esc(a.baslik)}</span><span>${esc(a.lisans)}</span></button>`).join("") || '<p class="soluk">Sonuç yok.</p>';
    } catch (er) { $("#g-adaylar").innerHTML = ""; hata(er); }
  });
}

// ------------------------------------------------------------ YAZILAR
async function sYazilar() {
  const f = Object.assign({ q: "", kategori: "", tur: "", denetleyen: "", gorsel: "", sayfa: 1 }, JSON.parse(sessionStorage.getItem("hh-yazi-filtre") || "{}"));
  baslikYaz("Yayındaki yazılar", "Sitedeki tüm yazıları arayın, düzenleyin ya da yayından kaldırın", `<a class="btn btn-ana" href="#/yeni">${ikon("yeni")}<span class="metin">Yeni yazı</span></a>`);
  icerik().innerHTML = `<div class="kart"><div class="kart-ic"><form class="satir" id="y-filtre">
    <input type="search" class="ara" name="q" placeholder="Başlık, etiket ya da adres ara" value="${esc(f.q)}" style="min-width:220px">
    <select name="kategori" style="width:auto"><option value="">Tüm kategoriler</option>${OTURUM.kategoriler.map((k) => `<option ${f.kategori === k ? "selected" : ""}>${esc(k)}</option>`).join("")}</select>
    <select name="tur" style="width:auto"><option value="">Tüm türler</option><option ${f.tur === "Haber" ? "selected" : ""}>Haber</option><option ${f.tur === "Analiz" ? "selected" : ""}>Analiz</option></select>
    <select name="denetleyen" style="width:auto"><option value="">Tüm incelemeler</option>${yazarSecenek().map(([k, ad]) => `<option value="${esc(k)}" ${f.denetleyen === k ? "selected" : ""}>${esc(ad)}</option>`).join("")}<option value="yok" ${f.denetleyen === "yok" ? "selected" : ""}>İnceleme kartı yok</option></select>
    <select name="gorsel" style="width:auto"><option value="">Görsel: hepsi</option><option value="yok" ${f.gorsel === "yok" ? "selected" : ""}>Görseli olmayan</option></select>
  </form></div><div id="y-tablo"><div class="yukleniyor"></div></div></div>`;
  const yukle = async () => {
    sessionStorage.setItem("hh-yazi-filtre", JSON.stringify(f));
    const r = await api("/yazilar?" + new URLSearchParams(Object.fromEntries(Object.entries(f).filter(([, v]) => v))));
    const son = Math.max(1, Math.ceil(r.toplam / r.adet));
    const acik = ["q", "kategori", "tur", "denetleyen", "gorsel"].filter((k) => f[k]);
    const uyari = acik.length ? `<div class="satir" style="padding:10px 16px;background:rgba(232,196,128,.14);border-bottom:1px solid var(--cizgi,#e5e7eb)"><span><b>Süzgeç açık:</b> yalnızca seçtiğiniz ölçütlere uyan ${sayi(r.toplam)} yazı gösteriliyor.</span><button type="button" class="btn btn-kucuk" id="y-temizle" style="margin-left:auto">Süzgeçleri temizle</button></div>` : "";
    $("#y-tablo").innerHTML = uyari + (r.yazilar.length ? `<div class="tablo-kap"><table><thead><tr><th></th><th>Başlık</th><th>Tür</th><th>Hukuki inceleme</th><th>Kelime</th><th>Tarih</th><th></th></tr></thead><tbody>
      ${r.yazilar.map((p) => `<tr><td style="width:76px">${kucukGorsel(p.kucuk)}</td>
        <td class="baslik-hucre"><a href="#/yazi/${esc(p.slug)}">${esc(p.baslik)}</a><small>${esc(p.kategoriler.join(", "))}${p.guncellendi ? " · güncellendi" : ""}</small></td>
        <td><span class="et ${p.tur === "Analiz" ? "mor" : "lac"}">${esc(p.tur)}</span></td><td>${denetleyenEt(p.denetleyen)}${p.denetleyen_elle ? ' <span class="soluk kucuk" title="Elle seçildi">✎</span>' : ""}</td>
        <td class="soluk">${sayi(p.kelime)}</td><td class="soluk kucuk" style="white-space:nowrap">${tarihYaz(p.tarih)}</td>
        <td style="white-space:nowrap"><a class="btn btn-kucuk" href="#/yazi/${esc(p.slug)}">Düzenle</a> <a class="btn btn-kucuk btn-hayalet" href="${esc(p.url)}" target="_blank" rel="noopener" aria-label="Sitede aç">↗</a></td></tr>`).join("")}
      </tbody></table></div><div class="sayfalama"><span>${sayi(r.toplam)} yazı · sayfa ${r.sayfa}/${son}</span><div class="satir">
        <button class="btn btn-kucuk" data-s="${r.sayfa - 1}" ${r.sayfa <= 1 ? "disabled" : ""}>← Önceki</button><button class="btn btn-kucuk" data-s="${r.sayfa + 1}" ${r.sayfa >= son ? "disabled" : ""}>Sonraki →</button></div></div>`
      : '<div class="bos"><b>Sonuç yok</b>Filtreleri değiştirip yeniden deneyin.</div>');
  };
  let gecikme;
  $("#y-filtre").addEventListener("input", (e) => { const fm = new FormData($("#y-filtre")); for (const [k, v] of fm) f[k] = v; f.sayfa = 1; clearTimeout(gecikme); gecikme = setTimeout(yukle, e.target.name === "q" ? 300 : 0); });
  $("#y-filtre").addEventListener("submit", (e) => e.preventDefault());
  $("#y-tablo").addEventListener("click", (e) => { if (e.target.closest("#y-temizle")) { Object.assign(f, { q: "", kategori: "", tur: "", denetleyen: "", gorsel: "", sayfa: 1 }); $("#y-filtre").reset(); $$("#y-filtre select").forEach((x) => { x.selectedIndex = 0; }); $("#y-filtre input[name=q]").value = ""; yukle(); return; } const b = e.target.closest("button[data-s]"); if (b) { f.sayfa = +b.dataset.s; yukle(); window.scrollTo(0, 0); } });
  await yukle();
}

async function sYazi(slug) {
  const p = await api("/yazi/" + encodeURIComponent(slug));
  baslikYaz("Yazıyı düzenle", p.baslik, `<a class="btn" href="#/yazilar">← Liste</a><a class="btn" href="#/google/${encodeURIComponent("/" + p.slug)}">${ikon("ara")}<span class="metin">Google'da bu yazı</span></a><a class="btn" href="${esc(p.url)}" target="_blank" rel="noopener">Sitede aç ↗</a>`);
  let sekme = "icerik";
  const denSecim = p.denetleyen_elle || "otomatik";
  icerik().innerHTML = `
  <div class="sekmeler" id="y-sekme">${[["icerik", "İçerik"], ["sinif", "Sınıflandırma ve inceleme"], ["kaynak", "Kaynaklar ve SSS"], ["islem", "Görsel ve işlemler"]].map(([k, a]) => `<button data-s="${k}" class="${k === sekme ? "on" : ""}">${a}</button>`).join("")}</div>
  <form id="y-form" class="kart">
    <div class="kart-ic" data-p="icerik">
      <div class="alan"><label for="y-baslik">Başlık <span class="soluk kucuk" id="y-sayac"></span></label><input id="y-baslik" type="text" maxlength="110" value="${esc(p.baslik)}"></div>
      <div class="alan"><span>Öne çıkanlar</span><small>Haberin başında maddeler hâlinde gösterilir.</small><div id="y-ozet"></div></div>
      <div class="alan"><div class="satir"><label for="y-govde" style="flex:1">Metin (HTML)</label><button type="button" class="btn btn-kucuk" id="y-onizle">Önizlemeyi göster</button></div>
        <small>İlk paragraf <code>&lt;p class="lead"&gt;</code> ile başlar; ara başlıklar <code>&lt;h2&gt;</code>. Betik ve iframe kabul edilmez.</small>
        <textarea id="y-govde" class="kod" spellcheck="false">${esc(p.govde)}</textarea>
        <iframe id="y-onizleme" class="onizleme" sandbox="" hidden title="Metin önizlemesi"></iframe></div>
    </div>
    <div class="kart-ic" data-p="sinif" hidden>
      <div class="alan"><span>Kategoriler</span><div class="secim-grubu">${OTURUM.kategoriler.map((k) => `<label><input type="checkbox" name="kat" value="${esc(k)}" ${p.kategoriler.includes(k) ? "checked" : ""}>${esc(k)}</label>`).join("")}</div></div>
      <div class="alan"><span>Tür</span><div class="secim-grubu">${["Haber", "Analiz"].map((t) => `<label><input type="radio" name="tur" value="${t}" ${p.tur === t ? "checked" : ""}>${t}</label>`).join("")}</div></div>
      <div class="alan"><span>Hukuki inceleme kartı</span><small>Otomatik seçim <a href="#/yazarlar">Yazarlar</a> sayfasındaki inceleme atamalarına göre yapılır. Şu an: ${p.denetleyen ? esc(DENETLEYEN[p.denetleyen] || p.denetleyen) : "kart yok"}.</small>
        <div class="secim-grubu">${[["otomatik", "Otomatik"], ...yazarSecenek(), ["yok", "Kart gösterme"]].map(([v, a]) => `<label><input type="radio" name="den" value="${esc(v)}" ${denSecim === v ? "checked" : ""}>${esc(a)}</label>`).join("")}</div>
        <label class="anahtar mt"><input type="checkbox" id="y-incelendi" ${p.incelendi ? "checked" : ""}> Bu yazıyı seçilen avukat gerçekten inceledi${p.incelendi ? ` <span class="soluk kucuk">(${esc(p.incelendi)})</span>` : ""}</label>
        <small>İşaretlenmezse kart yalnızca avukatın sitedeki görevini gösterir; "incelenmiştir" ifadesi ve avukat sayfasındaki "İncelediği haberler" listesi yalnızca işaretli yazılarda çıkar.</small></div>
      <div class="alan"><span>Yazar (imza)</span><small>Yalnızca yazıyı o kişi kendisi yazdıysa seçin; aksi hâlde "Hukuki Haberler Editörlüğü" imzası kalır.</small>
        <div class="secim-grubu">${[["", "Editörlük"], ...yazarSecenek()].map(([v, a]) => `<label><input type="radio" name="yzr" value="${esc(v)}" ${(p.yazar || "") === v ? "checked" : ""}>${esc(a)}</label>`).join("")}</div></div>
      <div class="alan"><span>Etiketler</span><small>Enter ile ekleyin; en fazla 12.</small><div id="y-etiket"></div></div>
    </div>
    <div class="kart-ic" data-p="kaynak" hidden>
      <div class="alan"><span>Kaynaklar</span><small>Haberin altında listelenir. Resmî kaynak, karar ya da mevzuat bağlantısı.</small><div id="y-kaynak"></div></div>
      <div class="alan"><span>Merak edilenler (SSS)</span><div id="y-sss"></div></div>
    </div>
    <div class="kart-ic" data-p="islem" hidden>
      <div class="izgara iz-2">
        <div><h3 class="mb" style="font-size:15px">Kapak görseli</h3>${p.kucuk ? `<img src="${esc(p.kucuk)}" alt="" style="width:100%;max-width:420px;border-radius:10px">` : '<p class="soluk">Görsel yok (yazılı kapak).</p>'}
          <p class="soluk kucuk">${esc(p.gorsel_kaynak || "")}</p><button type="button" class="btn" id="y-gorsel">Görseli otomatik yenile</button></div>
        <div><h3 class="mb" style="font-size:15px">Güncelleme notu ekle</h3><p class="soluk kucuk">Habere tarihli "Güncelleme" paragrafı olarak eklenir ve geçmişe işlenir.</p>
          <textarea id="y-gnot" rows="4" placeholder="Yeni gelişmeyi 20-700 karakterle yazın"></textarea>
          <div class="satir mt"><input type="text" id="y-gkad" placeholder="Kaynak adı (isteğe bağlı)"><input type="url" id="y-gkurl" placeholder="https://kaynak adresi"></div>
          <button type="button" class="btn btn-ana mt" id="y-gekle">Notu ekle ve yayınla</button></div>
      </div>
      <hr style="border:0;border-top:1px solid var(--cizgi2);margin:22px 0">
      <div class="izgara iz-2">
        <div><h3 class="mb" style="font-size:15px">Arama motorlarına bildir</h3><p class="soluk kucuk">Bing ve Yandex'e IndexNow ile anında bildirilir.</p><button type="button" class="btn" id="y-index">IndexNow'a bildir</button></div>
        <div><h3 class="mb" style="font-size:15px">Geçmiş</h3>${(p.gecmis || []).length ? `<ul class="liste">${p.gecmis.map((g) => `<li style="padding:6px 0"><div class="ana-satir"><b style="white-space:normal">${esc(g.tur)} · ${esc(g.tarih.replace("T", " "))}</b><small>${esc(g.not)}</small></div></li>`).join("")}</ul>` : '<p class="soluk">Kayıt yok.</p>'}</div>
      </div>
      <hr style="border:0;border-top:1px solid var(--cizgi2);margin:22px 0">
      <div class="uyari-kutu kirmizi"><b>Yayından kaldır</b><p class="kucuk" style="margin:4px 0 10px">Yazı siteden ve arşivden çıkarılır; adres 404 döner. Bu işlem panelden geri alınamaz.</p><button type="button" class="btn btn-kirmizi" id="y-kaldir">Yayından kaldır…</button></div>
      <p class="soluk kucuk mt">Kayıt yeri: <code>${esc(p.dosya)}</code> · adres: <code>/${esc(p.slug)}/</code></p>
    </div>
    <div class="yapiskan-alt"><input type="text" id="y-not" placeholder="Okura gösterilecek düzeltme notu (isteğe bağlı)" style="max-width:420px"><button class="btn btn-ana" type="submit">Kaydet ve yayınla</button></div>
  </form>`;
  const getOzet = satirListesi($("#y-ozet"), (p.ozet || []).map((x) => [x]), [{ yer: "Madde", cok: true }], "Madde ekle");
  const getEtiket = cipAlani($("#y-etiket"), p.etiketler || [], "Etiket yazıp Enter");
  const getKaynak = satirListesi($("#y-kaynak"), (p.kaynaklar || []).map((x) => [x[0], x[1]]), [{ yer: "Kaynak adı" }, { yer: "https://", tur: "url", gen: 1.3 }], "Kaynak ekle");
  const getSss = satirListesi($("#y-sss"), (p.sss || []).map((x) => [x[0], x[1]]), [{ yer: "Soru" }, { yer: "Cevap", cok: true }], "Soru ekle");
  const sayac = () => { $("#y-sayac").textContent = `(${$("#y-baslik").value.length} karakter)`; };
  $("#y-baslik").addEventListener("input", sayac); sayac();
  $("#y-sekme").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; sekme = b.dataset.s; $$("#y-sekme button").forEach((x) => x.classList.toggle("on", x === b)); $$("[data-p]").forEach((x) => (x.hidden = x.dataset.p !== sekme)); });
  $("#y-onizle").addEventListener("click", () => {
    const f = $("#y-onizleme"); f.hidden = !f.hidden; $("#y-onizle").textContent = f.hidden ? "Önizlemeyi göster" : "Önizlemeyi gizle";
    f.srcdoc = `<!doctype html><meta charset="utf-8"><style>body{font:17px/1.7 Georgia,serif;max-width:720px;margin:24px auto;padding:0 16px;color:#1b2733}.lead{font-size:19px;font-weight:600}h2{font:700 21px system-ui;margin-top:28px}a{color:#1d5fb8}</style><h1 style="font:700 28px/1.25 Georgia">${esc($("#y-baslik").value)}</h1>${$("#y-govde").value}`;
  });
  $("#y-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const veri = { baslik: $("#y-baslik").value, ozet: getOzet().map((x) => x[0]), govde: $("#y-govde").value, etiketler: getEtiket(),
      kategoriler: $$("input[name=kat]:checked").map((x) => x.value), tur: ($("input[name=tur]:checked") || {}).value,
      denetleyen: ($("input[name=den]:checked") || {}).value, incelendi: $("#y-incelendi") && $("#y-incelendi").checked ? (p.incelendi || new Date(Date.now() + 3 * 3600e3).toISOString().slice(0, 10)) : "", yazar: ($("input[name=yzr]:checked") || { value: "" }).value, kaynaklar: getKaynak(), sss: getSss(), not: $("#y-not").value };
    try { const r = await api("/yazi/" + encodeURIComponent(slug) + "/kaydet", { veri }); isTakip(r.is, "Yazı derleniyor ve yayına gönderiliyor", () => {}); }
    catch (er) { hata(er); }
  });
  $("#y-gorsel").addEventListener("click", async () => {
    if (!(await pencere({ baslik: "Görsel yenilensin mi?", metin: "<p>Konuya uygun yeni bir fotoğraf denetimli olarak seçilir ve yayına gönderilir. Uygun fotoğraf bulunamazsa yazılı kapak kullanılır.</p>", onay: "Yenile" }))) return;
    try { const r = await api("/yazi/" + encodeURIComponent(slug) + "/gorsel-yenile", { veri: {} }); isTakip(r.is, "Görsel seçiliyor", () => yonlendir()); } catch (er) { hata(er); }
  });
  $("#y-gekle").addEventListener("click", async () => {
    try { const r = await api("/yazi/" + encodeURIComponent(slug) + "/guncelleme", { veri: { not: $("#y-gnot").value, kaynak_ad: $("#y-gkad").value, kaynak_url: $("#y-gkurl").value } }); $("#y-gnot").value = ""; isTakip(r.is, "Güncelleme notu ekleniyor", () => yonlendir()); } catch (er) { hata(er); }
  });
  $("#y-index").addEventListener("click", async () => { try { const r = await api("/yayin/indexnow", { veri: { url: p.url } }); bildir(r.mesaj, "tamam"); } catch (er) { hata(er); } });
  $("#y-kaldir").addEventListener("click", async () => {
    const onay = await pencere({ baslik: "Yazı yayından kaldırılsın mı?", metin: `<p><b>${esc(p.baslik)}</b></p><p>Onaylamak için yazının kısa adresini yazın: <code>${esc(p.slug)}</code></p>`, onay: "Kalıcı olarak kaldır", tehlike: true, girdi: { etiket: "Kısa adres", beklenen: p.slug } });
    if (!onay) return;
    try { const r = await api("/yazi/" + encodeURIComponent(slug) + "/kaldir", { veri: { onay, neden: "panel" } }); isTakip(r.is, "Yazı yayından kaldırılıyor", (i) => { if (i.durum === "tamam") location.hash = "#/yazilar"; }); } catch (er) { hata(er); }
  });
}

// ------------------------------------------------------------ YENİ YAZI
async function sYeni() {
  baslikYaz("Yeni yazı", "Elle hazırlanan yazı önce taslak olur; onaylayınca yayımlanır");
  const taslak = JSON.parse(localStorage.getItem("hh-yeni-taslak") || "{}");
  icerik().innerHTML = `<form id="n-form" class="kart"><div class="kart-ic">
    <div class="izgara iz-21"><div>
      <div class="alan"><label for="n-baslik">Başlık <span class="soluk kucuk" id="n-sayac"></span></label><input id="n-baslik" type="text" maxlength="75" required value="${esc(taslak.baslik || "")}" placeholder="15-75 karakter; haberin özünü taşıyan, tarafsız başlık"></div>
      <div class="alan"><span>Öne çıkanlar</span><small>En az iki madde. Sayı, tarih ve süre gibi somut bilgileri öne çıkarın.</small><div id="n-ozet"></div></div>
      <div class="alan"><label for="n-govde">Metin</label><small>Düz metin yazabilirsiniz: paragrafları boş satırla ayırın, ara başlık için satıra <code>## </code> ile başlayın. İlk paragraf giriş (spot) olur. HTML de kabul edilir. En az 150 kelime.</small>
        <textarea id="n-govde" class="kod" style="font-family:var(--yazi-tipi);font-size:15px" required>${esc(taslak.govde || "")}</textarea><small id="n-kelime" class="soluk"></small></div>
    </div><div>
      <div class="alan"><span>Tür</span><div class="secim-grubu">${["Haber", "Analiz"].map((t) => `<label><input type="radio" name="tur" value="${t}" ${(taslak.tur || "Haber") === t ? "checked" : ""}>${t}</label>`).join("")}</div></div>
      <div class="alan"><span>Kategoriler (en fazla 2)</span><div class="secim-grubu">${OTURUM.kategoriler.map((k) => `<label><input type="checkbox" name="kat" value="${esc(k)}" ${(taslak.kategoriler || []).includes(k) ? "checked" : ""}>${esc(k)}</label>`).join("")}</div></div>
      <div class="alan"><span>Etiketler</span><div id="n-etiket"></div></div>
      <div class="alan"><span>Kaynaklar</span><small>En az bir resmî kaynak, karar ya da mevzuat bağlantısı.</small><div id="n-kaynak"></div></div>
      <div class="alan"><span>Kapak görseli</span><div class="secim-grubu"><label><input type="radio" name="gorsel" value="otomatik" checked>Otomatik seç (denetimli)</label><label><input type="radio" name="gorsel" value="yok">Yazılı kapak</label></div>
        <input type="text" id="n-garama" placeholder="Görsel arama terimleri, virgülle (isteğe bağlı, İngilizce önerilir)" value="${esc((taslak.gorsel_aramalari || []).join(", "))}"></div>
      <label class="anahtar"><input type="checkbox" id="n-x"> Yayımlanınca X'te paylaş</label>
    </div></div></div>
    <div class="yapiskan-alt"><span class="soluk kucuk" id="n-durum">Yazdıklarınız bu tarayıcıda otomatik saklanır.</span><button type="button" class="btn" id="n-temizle">Formu temizle</button><button class="btn btn-ana" type="submit">Taslak oluştur</button></div></form>`;
  const getOzet = satirListesi($("#n-ozet"), (taslak.ozet && taslak.ozet.length ? taslak.ozet : ["", ""]).map((x) => [x]), [{ yer: "Madde", cok: true }], "Madde ekle");
  const getEtiket = cipAlani($("#n-etiket"), taslak.etiketler || [], "Etiket yazıp Enter");
  const getKaynak = satirListesi($("#n-kaynak"), (taslak.kaynaklar && taslak.kaynaklar.length ? taslak.kaynaklar : [["", ""]]), [{ yer: "Kaynak adı" }, { yer: "https://", tur: "url", gen: 1.3 }], "Kaynak ekle");
  const topla = () => ({ baslik: $("#n-baslik").value, tur: ($("input[name=tur]:checked") || {}).value, kategoriler: $$("input[name=kat]:checked").map((x) => x.value),
    ozet: getOzet().map((x) => x[0]), govde: $("#n-govde").value, etiketler: getEtiket(), kaynaklar: getKaynak(),
    gorsel: ($("input[name=gorsel]:checked") || {}).value, gorsel_aramalari: $("#n-garama").value.split(",").map((x) => x.trim()).filter(Boolean), x_paylas: $("#n-x").checked });
  const guncelle = () => {
    $("#n-sayac").textContent = `(${$("#n-baslik").value.length}/75)`;
    $("#n-kelime").textContent = `${$("#n-govde").value.replace(/<[^>]+>/g, " ").split(/\s+/).filter(Boolean).length} kelime`;
    try { localStorage.setItem("hh-yeni-taslak", JSON.stringify(topla())); } catch (e) {}
  };
  $("#n-form").addEventListener("input", guncelle); guncelle();
  $("#n-form").addEventListener("change", (e) => { if (e.target.name === "kat" && $$("input[name=kat]:checked").length > 2) { e.target.checked = false; bildir("En fazla iki kategori seçilebilir."); } });
  $("#n-temizle").addEventListener("click", async () => { if (await pencere({ baslik: "Form temizlensin mi?", onay: "Temizle", tehlike: true })) { localStorage.removeItem("hh-yeni-taslak"); yonlendir(); } });
  $("#n-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const r = await api("/yeni-yazi", { veri: topla() });
      isTakip(r.is, "Taslak hazırlanıyor (görsel seçimi bir dakika sürebilir)", (i) => { if (i.durum === "tamam") { localStorage.removeItem("hh-yeni-taslak"); sessionStorage.setItem("hh-taslak-filtre", "bekliyor"); location.hash = "#/taslaklar"; } });
    } catch (er) { hata(er); }
  });
}

// ------------------------------------------------------------ YAZARLAR
async function sYazarlar() {
  baslikYaz("Yazarlar ve hukuki inceleme", "Avukat profilleri, sitede görünen bilgiler ve inceleme kartı atamaları", `<a class="btn btn-ana" href="#/yazar/yeni">${ikon("yeni")}<span class="metin">Yeni yazar</span></a>`);
  const r = await api("/yazarlar");
  DENETLEYEN = Object.fromEntries(r.yazarlar.map((y) => [y.kod, y.ad]));
  const site = (OTURUM.site || "https://hukukihaberler.com");
  const secim = (ad, deger, bos) => `<select name="${ad}" style="width:auto;min-width:220px"><option value="">${esc(bos)}</option>${r.yazarlar.map((y) => `<option value="${esc(y.kod)}" ${deger === y.kod ? "selected" : ""}>${esc(y.ad)}</option>`).join("")}</select>`;
  icerik().innerHTML = `
    <div class="izgara iz-3">${r.yazarlar.map((y) => `<div class="kart"><div class="kart-ic">
      <div class="satir" style="align-items:center;gap:14px"><img src="${esc(y.foto && y.foto.startsWith("/") ? site + y.foto : y.foto || "")}" alt="" width="64" height="64" style="border-radius:50%;object-fit:cover;flex:none;background:var(--zemin-2,#eee)">
        <div style="min-width:0"><b style="font-size:16px">${esc(y.ad)}</b>${y.goster === false ? ' <span class="et">Gizli</span>' : ""}<div class="soluk kucuk">${esc(y.rol || "")}</div><div class="kucuk">${esc(y.alan || "")}</div></div></div>
      <dl class="anahtar-deger mt"><dt>İnceleme kartı</dt><dd>${sayi(y.sayilar.inceleme)} yazı${y.sayilar.elle ? ` <span class="soluk kucuk">(${y.sayilar.elle} elle)</span>` : ""}</dd><dt>Yazar imzası</dt><dd>${sayi(y.sayilar.yazar)} yazı</dd><dt>Adres</dt><dd>/${esc(y.adres)}/</dd></dl></div>
      <div class="yapiskan-alt"><a class="btn btn-ana btn-kucuk" href="#/yazar/${esc(y.kod)}">Düzenle</a><a class="btn btn-kucuk" href="#/yazilar" data-den="${esc(y.kod)}">İncelediği yazılar</a><a class="btn btn-kucuk btn-hayalet" href="${esc(site)}/${esc(y.adres)}/" target="_blank" rel="noopener">Profil ↗</a></div></div>`).join("")}
      <a class="kart" href="#/yazar/yeni" style="display:grid;place-items:center;min-height:180px;text-decoration:none;border-style:dashed"><div style="text-align:center"><b style="font-size:28px;display:block">+</b><span>Yeni yazar ekle</span></div></a></div>
    <form class="kart mt" id="ic-form"><div class="kart-ust"><h2>Hukuki inceleme kartı atamaları</h2><span class="soluk kucuk">${sayi(r.kartsiz)} yazıda kart yok</span></div><div class="kart-ic">
      <p class="soluk" style="margin-top:0">Her yazıda konuya göre "Bu haber ... tarafından hukuki açıdan incelenmiştir" kartı gösterilir. Hangi grubun hangi avukata gideceğini buradan seçin; "Kart gösterme" seçilen grupta kart çıkmaz. Tek bir yazıda farklı bir seçim için yazıyı açıp <i>Sınıflandırma ve inceleme</i> sekmesini kullanın.</p>
      ${r.gruplar.map((g) => `<div class="alan"><label>${esc(g.ad)}</label><small>${esc(g.aciklama)}</small>${secim("g-" + g.kod, r.inceleme[g.kod], "Kart gösterme")}</div>`).join("")}
      <div class="alan"><label>Keşfet sayfasındaki "Hukuki denetim" sorumlusu</label><small>Keşfet sayfasındaki "Nasıl çalışıyoruz" bölümünde adı geçen avukat.</small>${secim("hd", r.hukuki_denetim, "Gösterme")}</div>
      <p class="soluk kucuk">İdare, anayasa, vergi gibi gruplara girmeyen yazılarda kart gösterilmez. Kaydedince tüm site yeniden derlenir (1-2 dakika).</p></div>
      <div class="yapiskan-alt"><button class="btn btn-ana">Atamaları kaydet</button></div></form>`;
  icerik().addEventListener("click", (e) => { const a = e.target.closest("[data-den]"); if (a) sessionStorage.setItem("hh-yazi-filtre", JSON.stringify({ denetleyen: a.dataset.den })); });
  $("#ic-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, veri = { inceleme: Object.fromEntries(r.gruplar.map((g) => [g.kod, f["g-" + g.kod].value || null])), hukuki_denetim: f.hd.value || null };
    try { const x = await api("/yazarlar/inceleme", { veri }); isTakip(x.is, "İnceleme atamaları kaydediliyor", (i) => { if (i.durum === "tamam") yonlendir(); }); } catch (er) { hata(er); }
  });
}

async function sYazar(kod) {
  const yeni = !kod || kod === "yeni";
  const r = await api("/yazarlar");
  const y = yeni ? { unvan: "Av.", kisi: "", rol: "", alan: "", baro: "", kisa: "", giris: "", bolumler: [{ baslik: "Meslek", tur: "liste", satirlar: [["Baro", ""], ["Mesleğe başlama", ""], ["Çalışma alanı", ""]] }, { baslik: "Hukuki Haberler'deki görevi", tur: "metin", metin: "" }], baglantilar: [], buro_sitesi: null, sameas: [], uzmanlik: [], mezuniyet: "", konum: "", diller: ["tr"], goster: true, sayfa_aciklama: "", ld_aciklama: "" }
    : r.yazarlar.find((x) => x.kod === kod);
  if (!y) throw new Error("Yazar bulunamadı.");
  const site = (OTURUM.site || "https://hukukihaberler.com");
  baslikYaz(yeni ? "Yeni yazar" : y.ad, yeni ? "Profil sayfası, yazar kartları ve inceleme kartlarında görünür" : `${site}/${y.adres}/`, `<a class="btn" href="#/yazarlar">← Yazarlar</a>`);
  const sira = yeni ? r.yazarlar.length : r.yazarlar.findIndex((x) => x.kod === kod);
  let bolumler = JSON.parse(JSON.stringify(y.bolumler || [])), fotoVeri = null;
  icerik().innerHTML = `
  <div class="uyari-kutu mavi mb"><b>Yayın kuralı.</b> Avukat sayfalarında telefon, e-posta, ücret, randevu ya da "arayın" gibi çağrılar bulunamaz; yalnızca doğrulanabilir bilgiler yazılır. Kural dışı içerik kaydedilmez. Metin alanlarında bağlantı için <code>&lt;a href="..."&gt;</code>, kalın için <code>&lt;b&gt;</code> kullanılabilir.</div>
  <form id="yz-form">
  <div class="izgara iz-21">
    <div>
      <div class="kart"><div class="kart-ust"><h2>Kimlik</h2></div><div class="kart-ic">
        <div class="satir"><div class="alan" style="flex:0 0 120px"><label for="yz-unvan">Unvan</label><input type="text" id="yz-unvan" value="${esc(y.unvan || "")}" placeholder="Av."></div>
          <div class="alan" style="flex:1"><label for="yz-kisi">Ad soyad</label><input type="text" id="yz-kisi" required value="${esc(y.kisi)}" placeholder="Ör. Ayşe Yılmaz"></div></div>
        <div class="alan"><label for="yz-adres">Profil adresi</label>${yeni ? `<input type="text" id="yz-adres" placeholder="otomatik: av-ad-soyad"><small>Boş bırakılırsa addan oluşturulur. Yayımlandıktan sonra değiştirilemez.</small>` : `<input type="text" id="yz-adres" value="/${esc(y.adres)}/" disabled><small>Adres sabittir; bağlantılar kırılmasın diye değiştirilemez.</small>`}</div>
        <div class="satir"><div class="alan" style="flex:1"><label for="yz-rol">Sitedeki görevi</label><input type="text" id="yz-rol" required value="${esc(y.rol || "")}" placeholder="Ör. Yazar ve editör"></div>
          <div class="alan" style="flex:1"><label for="yz-baro">Baro</label><input type="text" id="yz-baro" value="${esc(y.baro || "")}" placeholder="Ör. İzmir Barosu"></div></div>
        <div class="alan"><label for="yz-alan">Uzmanlık alanı (kartlarda görünür)</label><input type="text" id="yz-alan" value="${esc(y.alan || "")}" placeholder="Ör. Ceza ve ağır ceza hukuku"></div>
        <div class="alan"><label for="yz-kisa">Kısa tanıtım <span class="soluk kucuk" id="yz-kisa-say"></span></label><textarea id="yz-kisa" rows="3" maxlength="420" placeholder="Yazar kutusu ve Yazarlar sayfasındaki 2-3 cümlelik tanıtım">${esc(y.kisa || "")}</textarea></div>
        <div class="alan"><label for="yz-giris">Profil sayfası giriş paragrafı</label><textarea id="yz-giris" rows="3">${esc(y.giris || "")}</textarea></div>
      </div></div>
      <div class="kart mt"><div class="kart-ust"><h2>Profil sayfası bölümleri</h2><button type="button" class="btn btn-kucuk" id="yz-bol-ekle">+ Bölüm</button></div><div class="kart-ic" id="yz-bolumler"></div></div>
      <div class="kart mt"><div class="kart-ust"><h2>Bağlantılar</h2></div><div class="kart-ic">
        <div class="alan"><span>Profil sayfasındaki bağlantılar</span><small>Büro sitesi, LinkedIn gibi. Ad ve https adresi.</small><div id="yz-bag"></div></div>
        <div class="satir"><div class="alan" style="flex:1"><label for="yz-buro-ad">Avukatlık bürosu sitesi (adı)</label><input type="text" id="yz-buro-ad" value="${esc((y.buro_sitesi || [])[0] || "")}" placeholder="ör. ornekhukuk.com"></div>
          <div class="alan" style="flex:2"><label for="yz-buro-url">Adresi</label><input type="text" id="yz-buro-url" type="url" value="${esc((y.buro_sitesi || [])[1] || "")}" placeholder="https://"></div></div>
        <small class="soluk">Büro sitesi Yayın İlkeleri'ndeki "çıkar ilişkisi" açıklamasında adıyla anılır.</small>
      </div></div>
    </div>
    <div>
      <div class="kart"><div class="kart-ust"><h2>Fotoğraf</h2></div><div class="kart-ic" style="text-align:center">
        <img id="yz-foto-on" src="${esc(y.foto ? (y.foto.startsWith("/") ? site + y.foto : y.foto) : "")}" alt="" style="width:160px;height:160px;border-radius:50%;object-fit:cover;background:var(--zemin-2,#eee)${y.foto ? "" : ";visibility:hidden"}">
        <label class="btn mt" style="display:inline-flex">Fotoğraf seç<input type="file" id="yz-foto" accept="image/jpeg,image/png,image/webp" hidden></label>
        <p class="soluk kucuk">Yüzün göründüğü, en az 400x400 piksel bir fotoğraf. Kare kırpılır.</p></div></div>
      <div class="kart mt"><div class="kart-ust"><h2>Görünürlük</h2></div><div class="kart-ic">
        <label class="anahtar mb"><input type="checkbox" id="yz-goster" ${y.goster !== false ? "checked" : ""}> Sitede göster</label>
        <small class="soluk">Kapatılırsa Yazarlar sayfasında ve yan sütunda görünmez; profil sayfası arama motorlarına kapatılır ama bağlantılar çalışır.</small>
        <div class="alan mt"><label for="yz-sira">Sıra</label><select id="yz-sira">${Array.from({ length: r.yazarlar.length + (yeni ? 1 : 0) }, (_, i) => `<option value="${i}" ${i === sira ? "selected" : ""}>${i + 1}.</option>`).join("")}</select></div></div></div>
      <div class="kart mt"><div class="kart-ust"><h2>Arama motorları için</h2></div><div class="kart-ic">
        <div class="alan"><label for="yz-uzm">Uzmanlık konuları</label><small>Virgülle ayırın (ör. Ceza hukuku, Örgüt davaları).</small><input type="text" id="yz-uzm" value="${esc((y.uzmanlik || []).join(", "))}"></div>
        <div class="alan"><label for="yz-mez">Mezun olduğu okul</label><input type="text" id="yz-mez" value="${esc(y.mezuniyet || "")}"></div>
        <div class="alan"><label for="yz-konum">Çalıştığı yer</label><input type="text" id="yz-konum" value="${esc(y.konum || "")}" placeholder="Ör. Bayraklı, İzmir"></div>
        <div class="alan"><label for="yz-dil">Diller</label><small>Kod olarak: tr, en, de...</small><input type="text" id="yz-dil" value="${esc((y.diller || []).join(", "))}"></div>
        <div class="alan"><label for="yz-same">Diğer profil adresleri</label><small>Her satıra bir https adresi (LinkedIn, büro sitesi, yayınlar).</small><textarea id="yz-same" rows="3">${esc((y.sameas || []).join("\n"))}</textarea></div>
        <div class="alan"><label for="yz-sa">Profil sayfası açıklaması</label><input type="text" id="yz-sa" maxlength="200" value="${esc(y.sayfa_aciklama || "")}" placeholder="Boşsa ad ve görevden oluşturulur"></div>
        <div class="alan"><label for="yz-la">Kişi açıklaması (yapılandırılmış veri)</label><input type="text" id="yz-la" maxlength="300" value="${esc(y.ld_aciklama || "")}" placeholder="Boşsa kısa tanıtım kullanılır"></div>
      </div></div>
      ${yeni ? "" : `<div class="kart mt"><div class="kart-ust"><h2>Yazarı kaldır</h2></div><div class="kart-ic"><p class="soluk kucuk" style="margin-top:0">Yalnızca hiçbir yazıda ve inceleme atamasında adı geçmiyorsa kaldırılabilir. Eski profil adresi Yazarlar sayfasına yönlendirilir.</p><button type="button" class="btn btn-cizgi-kirmizi" id="yz-sil">Yazarı kaldır</button></div></div>`}
    </div>
  </div>
  <div class="kart mt"><div class="yapiskan-alt"><span class="soluk kucuk" style="margin-right:auto">Kaydedince site derlenir, denetlenir ve yayına gönderilir (1-2 dakika).</span><a class="btn" href="#/yazarlar">Vazgeç</a><button class="btn btn-ana" type="submit">${yeni ? "Yazarı ekle ve yayınla" : "Kaydet ve yayınla"}</button></div></div>
  </form>`;
  const getBag = satirListesi($("#yz-bag"), (y.baglantilar || []).map((x) => [...x]), [{ yer: "Ad (ör. LinkedIn)" }, { yer: "https://", tur: "url", gen: 2 }], "Bağlantı ekle");
  const kisaSay = () => { $("#yz-kisa-say").textContent = `(${$("#yz-kisa").value.length}/420)`; };
  $("#yz-kisa").addEventListener("input", kisaSay); kisaSay();
  const bolCiz = () => {
    $("#yz-bolumler").innerHTML = bolumler.length ? bolumler.map((b, i) => `<div class="kart mb" style="box-shadow:none" data-b="${i}"><div class="kart-ic">
      <div class="satir"><input type="text" data-bb="${i}" value="${esc(b.baslik)}" placeholder="Bölüm başlığı" style="flex:1;font-weight:600">
        <select data-bt="${i}" style="width:auto"><option value="liste" ${b.tur === "liste" ? "selected" : ""}>Madde listesi</option><option value="metin" ${b.tur !== "liste" ? "selected" : ""}>Paragraf</option></select>
        <button type="button" class="btn btn-kucuk btn-hayalet" data-yukari="${i}" ${i ? "" : "disabled"} aria-label="Yukarı">↑</button><button type="button" class="btn btn-kucuk btn-hayalet" data-bsil="${i}" aria-label="Bölümü sil">✕</button></div>
      ${b.tur === "liste" ? `<div class="mt" data-bl="${i}"></div>` : `<textarea class="mt" rows="4" data-bm="${i}" placeholder="Paragraflar arasında bir boş satır bırakın">${esc(b.metin || "")}</textarea>`}</div></div>`).join("") : '<p class="soluk">Bölüm yok. "+ Bölüm" ile ekleyin (ör. Eğitim ve meslek, Hukuki Haberler\'deki görevi, Çıkar ilişkisi).</p>';
    bolumler.forEach((b, i) => { if (b.tur === "liste") { b.satirlar = b.satirlar || []; b._al = satirListesi($(`[data-bl="${i}"]`), b.satirlar, [{ yer: "Etiket (ör. Baro)" }, { yer: "Bilgi", gen: 3 }], "Satır ekle"); } });
  };
  bolCiz();
  $("#yz-bolumler").addEventListener("input", (e) => {
    const t = e.target;
    if (t.dataset.bb != null) bolumler[+t.dataset.bb].baslik = t.value;
    if (t.dataset.bm != null) bolumler[+t.dataset.bm].metin = t.value;
  });
  $("#yz-bolumler").addEventListener("change", (e) => {
    const t = e.target; if (t.dataset.bt == null) return;
    const b = bolumler[+t.dataset.bt]; b.tur = t.value;
    if (b.tur === "liste" && !b.satirlar) b.satirlar = [["", ""]];
    if (b.tur === "metin" && b.metin == null) b.metin = "";
    bolCiz();
  });
  $("#yz-bolumler").addEventListener("click", (e) => {
    const s_ = e.target.closest("[data-bsil]"), u = e.target.closest("[data-yukari]");
    if (s_) { bolumler.splice(+s_.dataset.bsil, 1); bolCiz(); }
    if (u) { const i = +u.dataset.yukari; [bolumler[i - 1], bolumler[i]] = [bolumler[i], bolumler[i - 1]]; bolCiz(); }
  });
  $("#yz-bol-ekle").addEventListener("click", () => { bolumler.push({ baslik: "", tur: "metin", metin: "" }); bolCiz(); const g = $$("[data-bb]"); g[g.length - 1].focus(); });
  $("#yz-foto").addEventListener("change", async (e) => {
    const f = e.target.files[0]; if (!f) return;
    try {
      const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("Fotoğraf açılamadı.")); i.src = URL.createObjectURL(f); });
      if (Math.min(img.naturalWidth, img.naturalHeight) < 200) throw new Error("Fotoğraf en az 200x200 piksel olmalı.");
      const k = Math.min(1000 / Math.max(img.naturalWidth, img.naturalHeight), 1), c = document.createElement("canvas");
      c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      fotoVeri = c.toDataURL("image/jpeg", 0.9);
      const on = $("#yz-foto-on"); on.src = fotoVeri; on.style.visibility = "visible";
    } catch (er) { hata(er); }
  });
  if ($("#yz-sil")) $("#yz-sil").addEventListener("click", async () => {
    if (!(await pencere({ baslik: "Yazar kaldırılsın mı?", metin: `<p>${esc(y.ad)} sitedeki yazarlardan kaldırılacak ve profil sayfası yayından çıkacak.</p>`, onay: "Kaldır", tehlike: true }))) return;
    try { const x = await api(`/yazar-kayit/${encodeURIComponent(kod)}/sil`, { veri: {} }); isTakip(x.is, "Yazar kaldırılıyor", (i) => { if (i.durum === "tamam") location.hash = "#/yazarlar"; }); } catch (er) { hata(er); }
  });
  $("#yz-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const virgul = (v) => v.split(",").map((x) => x.trim()).filter(Boolean);
    const veri = {
      unvan: $("#yz-unvan").value, kisi: $("#yz-kisi").value, adres: yeni ? $("#yz-adres").value : undefined, rol: $("#yz-rol").value, baro: $("#yz-baro").value,
      alan: $("#yz-alan").value, kisa: $("#yz-kisa").value, giris: $("#yz-giris").value,
      bolumler: bolumler.map((b) => ({ baslik: b.baslik, tur: b.tur, ...(b.tur === "liste" ? { satirlar: b._al ? b._al() : b.satirlar } : { metin: b.metin || "" }) })),
      baglantilar: getBag(), buro_sitesi: $("#yz-buro-url").value.trim() ? [$("#yz-buro-ad").value.trim(), $("#yz-buro-url").value.trim()] : null,
      sameas: $("#yz-same").value.split("\n").map((x) => x.trim()).filter(Boolean), uzmanlik: virgul($("#yz-uzm").value), mezuniyet: $("#yz-mez").value,
      konum: $("#yz-konum").value, diller: virgul($("#yz-dil").value), goster: $("#yz-goster").checked, sira: +$("#yz-sira").value,
      sayfa_aciklama: $("#yz-sa").value, ld_aciklama: $("#yz-la").value, foto_veri: fotoVeri };
    const b = e.submitter || $("#yz-form button[type=submit]"); b.disabled = true;
    try {
      const x = await api(yeni ? "/yazar-kayit" : `/yazar-kayit/${encodeURIComponent(kod)}`, { veri });
      isTakip(x.is, yeni ? "Yazar ekleniyor ve site derleniyor" : "Yazar güncelleniyor ve site derleniyor", (i) => { b.disabled = false; if (i.durum === "tamam") location.hash = "#/yazarlar"; });
    } catch (er) { b.disabled = false; hata(er); }
  });
}

// ------------------------------------------------------------ ELENEN HABERLER
async function sElenenler() {
  baslikYaz("Elenen haberler", "Gelen her paylaşımın akıbeti: ne zaman geldi, hangi aşamada ve neden elendi");
  const GRUP = { resmi: "Resmî", siyasi: "Siyasi", kisi: "Gazeteci", haberci: "Haber hesabı" };
  const KRENK = { elendi: "sari", on_suzgec: "", zaten: "mavi", teyit: "mor", yazilmadi: "sari", denetim: "kirmizi", sinir: "kirmizi", hata: "kirmizi", taslak: "yesil", isleniyor: "mavi", diger: "" };
  const SEKME = ["elenen", "tumu", "elendi", "zaten", "teyit", "yazilmadi", "denetim", "sinir", "hata", "taslak", "on_suzgec"];
  const ARALIK = [["1s", "Son 1 saat", 3600], ["6s", "Son 6 saat", 21600], ["24s", "Son 24 saat", 86400], ["3g", "Son 3 gün", 259200], ["7g", "Son 7 gün", 604800], ["30g", "Son 30 gün", 2592000]];
  let f; try { f = JSON.parse(sessionStorage.getItem("hh-elenen") || "null"); } catch (e) { f = null; }
  f = Object.assign({ aralik: "24s", gun: "", bas: null, bit: null, kat: "elenen", grup: "", q: "", sayfa: 1 }, f || {});
  const kaydet = () => { try { sessionStorage.setItem("hh-elenen", JSON.stringify(f)); } catch (e) {} };
  const zaman = () => {
    if (f.bas && f.bit) return [f.bas, f.bit];
    if (f.gun) { const b = new Date(f.gun + "T00:00:00+03:00").getTime() / 1000; return [b, b + 86400]; }
    const a = ARALIK.find((x) => x[0] === f.aralik) || ARALIK[2]; const n = Date.now() / 1000; return [n - a[2], n];
  };
  const saatYaz = (ts, gunlu) => { const d = new Date(ts * 1000); return (gunlu ? d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" }) + " " : "") + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }); };
  const ciz = async () => {
    const [bas, bit] = zaman();
    let r;
    try { r = await api(`/akis?bas=${bas}&bit=${bit}&kat=${encodeURIComponent(f.kat)}&grup=${encodeURIComponent(f.grup)}&q=${encodeURIComponent(f.q)}&sayfa=${f.sayfa}`); }
    catch (e) { icerik().innerHTML = `<div class="kart"><div class="bos">${esc(e.message)}</div></div>`; return; }
    const S = r.sayilar, elenenSay = ["elendi", "zaten", "teyit", "yazilmadi", "denetim", "sinir", "hata", "diger"].reduce((t, k) => t + (S[k] || 0), 0);
    const gelen = Object.values(S).reduce((t, x) => t + x, 0);
    const say = (k) => k === "elenen" ? elenenSay : k === "tumu" ? gelen : (S[k] || 0);
    const ad = (k) => k === "elenen" ? "Elenenler" : k === "tumu" ? "Tümü" : r.kat_ad[k] || k;
    const enb = Math.max(1, ...r.seri.map((x) => x.gelen));
    const gunlu = !r.saatlik || (r.bit - r.bas) > 86400;
    const ozelAralik = f.bas && f.bit;
    icerik().innerHTML = `
    <div class="kart"><div class="kart-ic">
      <div class="satir" style="flex-wrap:wrap;gap:6px">${ARALIK.map(([k, a]) => `<button class="btn btn-kucuk ${!f.gun && !ozelAralik && f.aralik === k ? "btn-ana" : ""}" data-aralik="${k}">${a}</button>`).join("")}
        <input type="date" id="e-gun" value="${esc(f.gun)}" style="width:auto;height:32px" title="Belirli bir gün">
        ${ozelAralik ? `<span class="et mavi">${esc(saatYaz(f.bas, true))} – ${esc(saatYaz(f.bit, true))}</span><button class="btn btn-kucuk" data-temizle>✕ Aralığı kaldır</button>` : ""}</div>
      <div class="izgara iz-4 mt">
        <div class="kart sayi-kart"><span>Gelen paylaşım</span><b>${sayi(gelen)}</b><small>${esc(saatYaz(r.bas, true))} – ${esc(saatYaz(r.bit, true))}</small></div>
        <div class="kart sayi-kart"><span>Elenen</span><b>${sayi(elenenSay)}</b><small>Eleme, tekrar, teyit, yazım, denetim</small></div>
        <div class="kart sayi-kart"><span>Taslak olan</span><b>${sayi(S.taslak || 0)}</b><small>Onaya gönderilen</small></div>
        <div class="kart sayi-kart"><span>Ön süzgeç</span><b>${sayi(S.on_suzgec || 0)}</b><small>Hukuki kelime içermeyen</small></div></div>
      <div class="mt"><div class="soluk kucuk mb">${r.saatlik ? "Saat saat" : "Gün gün"} gelen paylaşımlar · <span style="color:var(--yesil)">■</span> taslak <span style="color:var(--sari)">■</span> elenen <span style="color:var(--soluk,#999)">■</span> ön süzgeç · bir sütuna tıklayınca o ${r.saatlik ? "saat" : "gün"} süzülür</div>
        <div class="grafik yigin">${r.seri.map((x) => { const h = (n) => Math.max(n ? 2 : 0, n / enb * 100); const et = r.saatlik ? new Date(x.ts * 1000).getHours() + ":00" : new Date(x.ts * 1000).toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
          return `<div data-kova="${x.ts}" title="${esc(et)}: ${x.gelen} gelen, ${x.taslak} taslak, ${x.elenen} elenen, ${x.suzgec} ön süzgeç" style="cursor:pointer"><b>${x.gelen || ""}</b><span class="yg"><i style="height:${h(x.suzgec)}%;background:var(--cizgi,#ccd)"></i><i style="height:${h(x.elenen)}%;background:var(--sari)"></i><i style="height:${h(x.taslak)}%;background:var(--yesil)"></i></span><em>${esc(et)}</em></div>`; }).join("")}</div></div>
    </div></div>
    <div class="sekmeler mt">${SEKME.filter((k) => k === "elenen" || k === "tumu" || say(k)).map((k) => `<button data-kat="${k}" class="${f.kat === k ? "on" : ""}">${esc(ad(k))}<span class="et">${sayi(say(k))}</span></button>`).join("")}</div>
    <div class="kart">
      <div class="kart-ust"><div class="satir" style="flex-wrap:wrap;gap:8px;flex:1"><input type="search" id="e-ara" placeholder="Metin, konu, neden ya da hesapta ara" value="${esc(f.q)}" style="max-width:320px;height:34px">
        <select id="e-grup" style="width:auto;height:34px"><option value="">Tüm hesaplar</option>${Object.entries(GRUP).map(([k, a]) => `<option value="${k}" ${f.grup === k ? "selected" : ""}>${a}</option>`).join("")}</select></div>
        <span class="soluk kucuk">${sayi(r.toplam)} kayıt</span></div>
      ${r.ogeler.length ? `<ul class="liste akis">${r.ogeler.map((o) => `<li style="align-items:flex-start;gap:12px">
        <div class="soluk kucuk" style="flex:0 0 74px;text-align:right;line-height:1.3">${esc(saatYaz(o.ts, gunlu))}</div>
        <div class="ana-satir" style="min-width:0">
          <div class="satir" style="gap:6px;flex-wrap:wrap"><span class="et ${KRENK[o.kat] || ""}">${esc(r.kat_ad[o.kat] || o.durum)}</span>${o.zorla ? '<span class="et mor">Editör isteğiyle</span>' : ""}<b style="font-weight:600">@${esc(o.kullanici || "?")}</b><span class="soluk kucuk">${esc(GRUP[o.grup] || o.grup || "")}</span>${o.oncelik ? `<span class="soluk kucuk">· öncelik ${esc(o.oncelik)}</span>` : ""}</div>
          ${o.konu ? `<div style="font-weight:600;margin-top:4px;white-space:normal">${esc(o.konu)}</div>` : ""}
          <div class="akis-metin" style="white-space:pre-line;margin-top:4px">${esc(o.metin)}</div>
          ${o.neden ? `<div class="kucuk" style="margin-top:6px;white-space:normal"><b style="display:inline">Neden:</b> ${esc(o.neden)}</div>` : ""}
          ${o.kat === "diger" ? `<div class="soluk kucuk">${o.durum === "kayıt yok" ? "Bu paylaşımın işlenme kaydı yok (servis o sırada yeniden başlamış olabilir)." : "Durum: " + esc(o.durum)}</div>` : ""}
        </div>
        <div class="satir" style="flex:none;flex-direction:column;align-items:stretch;gap:6px">
          <a class="btn btn-kucuk" href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">Kaynağı aç ↗</a>
          ${o.tid ? `<a class="btn btn-kucuk" href="#/taslak/${esc(o.tid)}">Taslağı aç</a>` : ""}
          ${!["taslak", "isleniyor"].includes(o.kat) ? `<button class="btn btn-kucuk btn-ana" data-yaz="${esc(o.url)}">Yine de yaz</button>` : ""}</div></li>`).join("")}</ul>`
        : `<div class="bos"><b>Bu aralıkta kayıt yok</b>Başka bir zaman aralığı ya da sekme seçin.</div>`}
      ${r.sayfa_sayisi > 1 ? `<div class="yapiskan-alt"><button class="btn btn-kucuk" data-sayfa="${r.sayfa - 1}" ${r.sayfa <= 1 ? "disabled" : ""}>← Önceki</button><span class="soluk kucuk">${r.sayfa} / ${r.sayfa_sayisi}</span><button class="btn btn-kucuk" data-sayfa="${r.sayfa + 1}" ${r.sayfa >= r.sayfa_sayisi ? "disabled" : ""}>Sonraki →</button></div>` : ""}
    </div>`;
  };
  await ciz();
  let araZ = null;
  icerik().addEventListener("input", (e) => {
    if (e.target.id === "e-ara") { clearTimeout(araZ); araZ = setTimeout(() => { f.q = e.target.value.trim(); f.sayfa = 1; kaydet(); ciz().then(() => { const i = $("#e-ara"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }); }, 400); }
  });
  icerik().addEventListener("change", (e) => {
    if (e.target.id === "e-grup") { f.grup = e.target.value; f.sayfa = 1; kaydet(); ciz(); }
    if (e.target.id === "e-gun") { f.gun = e.target.value; f.bas = f.bit = null; f.sayfa = 1; kaydet(); ciz(); }
  });
  icerik().addEventListener("click", async (e) => {
    const t = e.target.closest("[data-aralik],[data-kat],[data-sayfa],[data-kova],[data-temizle],[data-yaz],.akis-metin");
    if (!t) return;
    if (t.classList.contains("akis-metin")) { t.classList.toggle("acik"); return; }
    if (t.dataset.aralik) { f.aralik = t.dataset.aralik; f.gun = ""; f.bas = f.bit = null; }
    else if (t.dataset.kat) f.kat = t.dataset.kat;
    else if (t.dataset.sayfa) { f.sayfa = +t.dataset.sayfa; kaydet(); await ciz(); window.scrollTo(0, 0); return; }
    else if (t.dataset.kova) { const b = +t.dataset.kova, [b0, b1] = zaman(); f.bas = b; f.bit = b + ((b1 - b0) <= 2 * 86400 ? 3600 : 86400); }
    else if (t.hasAttribute("data-temizle")) { f.bas = f.bit = null; }
    else if (t.dataset.yaz) {
      const ok = await pencere({ baslik: "Bu paylaşım yine de yazılsın mı?", metin: "<p>Eleme kararı, \"yakın zamanda yazıldı\" ve teyit ön kontrolü atlanır; paylaşım araştırılıp yazılır ve taslak olarak onaya düşer. Yazım sırasında doğrulanamazsa yine yazılmayabilir. Bu işlem ücretli yazım modelini kullanır.</p>", onay: "Yaz" });
      if (!ok) return;
      try { const x = await api("/akis/yaz", { veri: { url: t.dataset.yaz } }); t.disabled = true; t.textContent = "Yazılıyor…"; isTakip(x.is, "Paylaşım yazılıyor (1-3 dakika)", () => ciz()); } catch (er) { hata(er); }
      return;
    }
    f.sayfa = 1; kaydet(); ciz();
  });
}

// ------------------------------------------------------------ MESAJLAR
async function sMesajlar(no) {
  let filtre = "gelen", veri = [], baglanti = {};
  baslikYaz("Mesajlar", "Sitedeki iletişim formundan gelen okur mesajları", `<button class="btn" id="m-esitle">Yeni mesajları denetle</button>`);
  const yukle = async () => { const r = await api("/mesajlar"); veri = r.mesajlar; baglanti = r.baglanti; ROZET.okunmamis = veri.filter((m) => m.durum === "yeni").length; menuCiz(); baslikRozet(); };
  const secili = () => veri.find((m) => m.no === no);
  const ciz = () => {
    const L = veri.filter((m) => filtre === "gelen" ? m.durum !== "arşiv" : filtre === "yeni" ? m.durum === "yeni" : filtre === "yanit" ? m.durum === "yanıtlandı" : m.durum === "arşiv");
    const m = secili();
    const say = (f) => veri.filter((x) => f === "gelen" ? x.durum !== "arşiv" : f === "yeni" ? x.durum === "yeni" : f === "yanit" ? x.durum === "yanıtlandı" : x.durum === "arşiv").length;
    const konuAd = (x) => x.konu_ad || OTURUM.konular[x.konu] || x.konu;
    const yanitKonu = m ? `Re: [${m.no}] ${m.baslik}` : "";
    const yanitGovde = m ? `Sayın ${m.ad},\n\n\n\n—\nHukuki Haberler Yazı İşleri\nhttps://hukukihaberler.com\n\n> ${tarihYaz(new Date(m.ts * 1000).toISOString())} tarihli mesajınız:\n> ${m.mesaj.split("\n").join("\n> ")}` : "";
    icerik().innerHTML = `${!baglanti.hazir ? `<div class="uyari-kutu mb">İletişim formu bağlantısı kuruluyor. ${esc(baglanti.hata || "Panel, sitenin mesaj anahtarını Cloudflare'e tanımlıyor; bu birkaç dakika sürebilir.")}</div>` : baglanti.son_hata ? `<div class="uyari-kutu mb">${esc(baglanti.son_hata)}</div>` : ""}
    <div class="sekmeler">${[["gelen", "Gelen kutusu"], ["yeni", "Okunmamış"], ["yanit", "Yanıtlanan"], ["arsiv", "Arşiv"]].map(([f, a]) => `<button data-f="${f}" class="${filtre === f ? "on" : ""}">${a}<span class="et">${say(f)}</span></button>`).join("")}</div>
    <div class="kart posta ${m ? "okuyor" : ""}"><div class="posta-liste">${L.length ? L.map((x) => `<button data-no="${esc(x.no)}" class="${x.no === no ? "on" : ""} ${x.durum === "yeni" ? "yeni" : ""}"><div class="ust-s"><span>${esc(x.ad)}</span><span>${once(x.ts)}</span></div><b>${esc(x.baslik)}</b><p>${esc(konuAd(x))} · ${esc(x.mesaj.slice(0, 90))}</p></button>`).join("") : '<div class="bos"><b>Mesaj yok</b>Bu klasör boş.</div>'}</div>
      <div class="posta-okuma">${m ? `<div class="satir mb"><button class="btn btn-kucuk" id="m-geri">← Liste</button><span class="et ${m.durum === "yeni" ? "mavi" : m.durum === "yanıtlandı" ? "yesil" : ""}">${esc(m.durum)}</span><span class="et lac">${esc(konuAd(m))}</span><span class="soluk kucuk" style="margin-left:auto">${esc(m.no)}</span></div>
        <h2>${esc(m.baslik)}</h2>
        <dl class="posta-bilgi"><dt>Gönderen</dt><dd>${esc(m.ad)}</dd><dt>E-posta</dt><dd><a href="mailto:${esc(m.eposta)}">${esc(m.eposta)}</a></dd>${m.telefon ? `<dt>Telefon</dt><dd>${esc(m.telefon)}</dd>` : ""}
          ${m.adres ? `<dt>İlgili sayfa</dt><dd><a href="${esc(m.adres)}" target="_blank" rel="noopener noreferrer">${esc(m.adres)}</a></dd>` : ""}<dt>Tarih</dt><dd>${new Date(m.ts * 1000).toLocaleString("tr-TR")}</dd>${m.ulke ? `<dt>Ülke</dt><dd>${esc(m.ulke)}</dd>` : ""}</dl>
        <div class="posta-metin">${esc(m.mesaj)}</div>
        <div class="satir mb"><a class="btn btn-ana" id="m-yanit" href="mailto:${esc(m.eposta)}?subject=${encodeURIComponent(yanitKonu)}&body=${encodeURIComponent(yanitGovde)}">E-postayla yanıtla</a>
          ${m.durum !== "yanıtlandı" ? '<button class="btn" data-d="yanıtlandı">Yanıtlandı olarak işaretle</button>' : ""}
          ${m.durum === "yeni" ? '<button class="btn" data-d="okundu">Okundu</button>' : '<button class="btn" data-d="yeni">Okunmadı yap</button>'}
          ${m.durum !== "arşiv" ? '<button class="btn" data-d="arşiv">Arşivle</button>' : '<button class="btn" data-d="okundu">Arşivden çıkar</button>'}
          <button class="btn btn-cizgi-kirmizi" id="m-sil">Sil</button></div>
        <div class="alan"><label for="m-not">İç not (yalnızca panelde görünür)</label><textarea id="m-not" rows="3" placeholder="Ör. düzeltme yapıldı, tekzip yayımlandı…">${esc(m.not || "")}</textarea><div><button class="btn btn-kucuk" id="m-not-kaydet">Notu kaydet</button></div></div>`
      : '<div class="bos" style="padding-top:90px"><b>Bir mesaj seçin</b>Seçtiğiniz mesaj burada açılır.</div>'}</div></div>`;
  };
  const durum = async (d) => { try { await api("/mesaj/" + no, { veri: { durum: d } }); await yukle(); ciz(); } catch (e) { hata(e); } };
  await yukle();
  if (no && secili() && secili().durum === "yeni") await durum("okundu"); else ciz();
  const tik = async (e) => {
    const f = e.target.closest(".sekmeler button"); if (f) { filtre = f.dataset.f; return ciz(); }
    const b = e.target.closest(".posta-liste button[data-no]");
    if (b) { no = b.dataset.no; history.replaceState(null, "", "#/mesajlar/" + no); if (secili().durum === "yeni") await durum("okundu"); else ciz(); return; }
    if (e.target.id === "m-geri") { no = ""; history.replaceState(null, "", "#/mesajlar"); return ciz(); }
    const d = e.target.closest("button[data-d]"); if (d) return durum(d.dataset.d);
    if (e.target.id === "m-yanit") setTimeout(() => { if (secili() && secili().durum !== "yanıtlandı") durum("yanıtlandı"); }, 400);
    if (e.target.id === "m-not-kaydet") { try { await api("/mesaj/" + no, { veri: { not: $("#m-not").value } }); bildir("Not kaydedildi.", "tamam"); await yukle(); } catch (er) { hata(er); } }
    if (e.target.id === "m-sil") {
      if (!(await pencere({ baslik: "Mesaj silinsin mi?", metin: "<p>Mesaj panelden kalıcı olarak silinir. Saklamak istiyorsanız arşivleyin.</p>", onay: "Sil", tehlike: true }))) return;
      try { await api("/mesaj/" + no, { veri: { sil: true } }); no = ""; history.replaceState(null, "", "#/mesajlar"); await yukle(); ciz(); bildir("Silindi.", "tamam"); } catch (er) { hata(er); }
    }
  };
  icerik().addEventListener("click", tik);
  $("#m-esitle").addEventListener("click", async () => { try { const r = await api("/mesajlar/esitle", { veri: {} }); bildir(r.mesaj, "tamam"); await yukle(); ciz(); } catch (er) { hata(er); } });
  const sno = SAYFA_NO;
  const z = setInterval(async () => { if (sno !== SAYFA_NO) return clearInterval(z); if (document.hidden) return; const once_ = veri.length; await yukle().catch(() => {}); if (sno === SAYFA_NO && veri.length !== once_) ciz(); }, 30000);
  sayfaTemizle = () => { clearInterval(z); icerik().removeEventListener("click", tik); };
}

// ------------------------------------------------------------ ZİYARETÇİLER
async function sZiyaret() {
  let gun = +(sessionStorage.getItem("hh-ziyaret-gun") || 14);
  baslikYaz("Ziyaretçiler", "Çerezsiz sayım: IP adresi saklanmaz, ziyaretçi yalnızca o gün içinde ayırt edilir", `<label class="anahtar"><input type="checkbox" id="z-canli" checked> Canlı</label>`);
  const tablo = (L, kolon, deger) => L.length ? `<ul class="liste">${L.map((x) => `<li><div class="ana-satir"><b style="font-weight:550">${esc(x[kolon])}</b></div><span class="soluk">${sayi(x[deger])}</span></li>`).join("")}</ul>` : '<div class="bos">Kayıt yok.</div>';
  const ciz = (z) => {
    icerik().innerHTML = `<div class="sekmeler">${[[1, "Bugün"], [7, "7 gün"], [14, "14 gün"], [30, "30 gün"], [90, "90 gün"], [365, "1 yıl"]].map(([g, a]) => `<button data-g="${g}" class="${g === gun ? "on" : ""}">${a}</button>`).join("")}</div>
    ${!z.ilk_kayit ? '<div class="uyari-kutu mavi mb">Henüz ziyaret kaydı yok. Sayım, site sinyali devreye girdiği andan itibaren başlar; geçmiş günlerin verisi bu sistemde bulunmaz.</div>' : ""}
    <div class="izgara iz-4"><div class="kart sayi-kart vurgu"><span>Şu an sitede</span><b>${sayi(z.su_an)}</b><small>Son 5 dakika</small></div>
      <div class="kart sayi-kart"><span>Bugün</span><b>${sayi(z.bugun.ziyaretci)}</b><small>${sayi(z.bugun.goruntulenme)} görüntüleme</small></div>
      <div class="kart sayi-kart"><span>Dönem ziyaretçi</span><b>${sayi(z.donem.ziyaretci)}</b><small>Seçilen ${gun === 1 ? "gün" : gun + " gün"}</small></div>
      <div class="kart sayi-kart"><span>Dönem görüntüleme</span><b>${sayi(z.donem.goruntulenme)}</b><small>Ziyaretçi başına ${z.donem.ziyaretci ? (z.donem.goruntulenme / z.donem.ziyaretci).toFixed(1) : "0"} sayfa</small></div></div>
    <div class="kart mt"><div class="kart-ust"><h2>${gun === 1 ? "Bugün saat saat görüntüleme" : "Günlük ziyaretçi"}</h2></div><div class="kart-ic">${gun === 1
      ? grafik(z.saatler, "adet", (x) => String(x.saat).padStart(2, "0"))
      : grafik(z.seri.slice(-Math.min(z.seri.length, 31)), "ziyaretci", (x) => { const [, a, gn] = x.gun.split("-"); return `${+gn} ${AYLAR[+a - 1]}`; })}</div></div>
    <div class="izgara iz-21 mt"><div class="kart"><div class="kart-ust"><h2>En çok okunan sayfalar</h2></div>
      ${z.sayfalar.length ? `<div class="tablo-kap"><table><thead><tr><th>Sayfa</th><th>Görüntüleme</th><th>Ziyaretçi</th></tr></thead><tbody>${z.sayfalar.map((s) => `<tr><td class="baslik-hucre"><a href="https://hukukihaberler.com${esc(s.yol)}" target="_blank" rel="noopener">${esc(s.baslik)}</a><small>${esc(s.yol)}</small></td><td>${sayi(s.goruntulenme)}</td><td>${sayi(s.ziyaretci)}</td></tr>`).join("")}</tbody></table></div>` : '<div class="bos">Kayıt yok.</div>'}</div>
      <div><div class="kart"><div class="kart-ust"><h2>Nereden geldiler</h2><span class="soluk kucuk">ziyaretçi</span></div>${tablo(z.kaynaklar, "ad", "ziyaretci")}</div>
        <div class="kart mt"><div class="kart-ust"><h2>Cihaz</h2></div>${tablo(z.cihazlar, "ad", "ziyaretci")}</div>
        <div class="kart mt"><div class="kart-ust"><h2>Ülke</h2></div>${tablo(z.ulkeler, "ad", "ziyaretci")}</div></div></div>
    <div class="kart mt"><div class="kart-ust"><h2>Son ziyaretler</h2><span class="soluk kucuk">canlı</span></div>${z.son.length ? `<div class="tablo-kap"><table><thead><tr><th>Zaman</th><th>Sayfa</th><th>Kaynak</th><th>Cihaz</th><th>Ülke</th></tr></thead><tbody>${z.son.map((s) => `<tr><td class="soluk kucuk" style="white-space:nowrap">${once(s.ts)}</td><td class="baslik-hucre"><a href="https://hukukihaberler.com${esc(s.yol)}" target="_blank" rel="noopener">${esc(s.baslik)}</a></td><td>${esc(s.kaynak)}</td><td>${esc(s.cihaz)}</td><td>${esc(s.ulke || "—")}</td></tr>`).join("")}</tbody></table></div>` : '<div class="bos">Kayıt yok.</div>'}</div>`;
  };
  const no = SAYFA_NO;
  const yukle = async () => { const r = await api("/ziyaret?gun=" + gun); if (no === SAYFA_NO) ciz(r); };
  await yukle();
  icerik().addEventListener("click", (e) => { const b = e.target.closest(".sekmeler button"); if (b) { gun = +b.dataset.g; sessionStorage.setItem("hh-ziyaret-gun", gun); yukle(); } });
  const zz = setInterval(() => { if (!document.hidden && $("#z-canli") && $("#z-canli").checked) yukle().catch(() => {}); }, 20000);
  sayfaTemizle = () => clearInterval(zz);
}

// ------------------------------------------------------------ GOOGLE ARAMA KELİMELERİ
async function sGoogle(sayfaYolu) {
  let gun = +(sessionStorage.getItem("hh-gsc-gun") || 28), siralama = "tiklama", ara = "";
  baslikYaz("Google arama kelimeleri", "Google'da hangi aramalarda göründüğünüz, kaç tıklama aldığınız ve sıranız (Search Console)");
  const durum = await api("/google/durum");
  if (!durum.bagli) return googleKurulum(durum);
  const ciz = (r) => {
    const K = r.kelimeler.filter((k) => !ara || k.kelime.toLowerCase().includes(ara.toLowerCase())).sort((a, b) => siralama === "sira" ? a.sira - b.sira : b[siralama] - a[siralama]);
    const th = (k, a) => `<th><button class="btn btn-kucuk btn-hayalet" data-sira="${k}" style="padding:0;height:auto;font:inherit;text-transform:inherit;letter-spacing:inherit;color:${siralama === k ? "var(--yazi)" : "inherit"}">${a}${siralama === k ? " ↓" : ""}</button></th>`;
    icerik().innerHTML = `<div class="sekmeler">${[[7, "7 gün"], [28, "28 gün"], [90, "3 ay"], [180, "6 ay"], [365, "1 yıl"]].map(([g, a]) => `<button data-g="${g}" class="${g === gun ? "on" : ""}">${a}</button>`).join("")}</div>
    ${r.sayfa ? `<div class="uyari-kutu mavi mb satir"><span style="flex:1">Yalnızca bu sayfanın kelimeleri: <b>${esc(r.sayfa)}</b></span><a class="btn btn-kucuk" href="#/google">Tüm site</a></div>` : ""}
    <div class="izgara iz-4"><div class="kart sayi-kart vurgu"><span>Tıklama</span><b>${sayi(r.toplam.tiklama)}</b><small>Google'dan gelen ziyaret</small></div>
      <div class="kart sayi-kart"><span>Gösterim</span><b>${sayi(r.toplam.gosterim)}</b><small>Arama sonuçlarında görünme</small></div>
      <div class="kart sayi-kart"><span>Tıklama oranı</span><b>%${r.toplam.oran}</b><small>Tıklama / gösterim</small></div>
      <div class="kart sayi-kart"><span>Ortalama sıra</span><b>${r.toplam.sira || "—"}</b><small>Son veri: ${r.son_veri ? tarihYaz(r.son_veri) : "yok"} (Google 2-3 gün gecikmeli)</small></div></div>
    <div class="kart mt"><div class="kart-ust"><h2>Günlük tıklama</h2></div><div class="kart-ic">${r.seri.length ? grafik(r.seri.slice(-31), "tiklama", (x) => { const [, a, gn] = x.tarih.split("-"); return `${+gn} ${AYLAR[+a - 1]}`; }) : '<div class="bos">Bu dönemde veri yok.</div>'}</div></div>
    <div class="mt"><div class="kart"><div class="kart-ust"><h2>Arama kelimeleri</h2><input type="search" id="g-ara" placeholder="Kelimede ara" value="${esc(ara)}" style="max-width:220px;height:32px"></div>
      ${K.length ? `<div class="tablo-kap"><table><thead><tr><th>Kelime</th>${th("tiklama", "Tıklama")}${th("gosterim", "Gösterim")}${th("oran", "Oran")}${th("sira", "Sıra")}</tr></thead><tbody>${K.map((k) => `<tr><td><a href="https://www.google.com/search?q=${encodeURIComponent(k.kelime)}" target="_blank" rel="noopener noreferrer" style="color:var(--yazi);font-weight:550">${esc(k.kelime)}</a>${k.gosterim >= (r.firsat_esik || 5) && (k.tiklama === 0 || k.oran < 5 || k.sira > 8) ? ' <span class="et sari" title="Çok gösteriliyor, az tıklanıyor: yeni yazılarda başlık ve etiket seçerken öncelik verilir">Fırsat</span>' : ""}</td><td>${sayi(k.tiklama)}</td><td>${sayi(k.gosterim)}</td><td>%${k.oran}</td><td><span class="et ${k.sira <= 3 ? "yesil" : k.sira <= 10 ? "mavi" : k.sira <= 20 ? "sari" : ""}">${k.sira}</span></td></tr>`).join("")}</tbody></table></div>` : '<div class="bos"><b>Kelime yok</b>Google, çok az aranan kelimeleri gizlilik nedeniyle göstermez.</div>'}</div>
      ${r.sayfalar ? `<div class="izgara iz-21 mt"><div class="kart"><div class="kart-ust"><h2>Google'dan gelinen sayfalar</h2><span class="soluk kucuk">tıkla: kelimeleri</span></div>${r.sayfalar.length ? `<ul class="liste">${r.sayfalar.slice(0, 25).map((s) => `<li><div class="ana-satir"><a href="#/google/${encodeURIComponent(s.yol)}">${esc(s.baslik)}</a><small>${sayi(s.gosterim)} gösterim · sıra ${s.sira}</small></div><span class="kalin">${sayi(s.tiklama)}</span></li>`).join("")}</ul>` : '<div class="bos">Veri yok.</div>'}</div>
        <div class="kart" style="align-self:start"><div class="kart-ust"><h2>Cihaz</h2></div><ul class="liste">${(r.cihazlar || []).map((c) => `<li><div class="ana-satir"><b style="font-weight:550">${esc({ MOBILE: "Mobil", DESKTOP: "Masaüstü", TABLET: "Tablet" }[c.cihaz] || c.cihaz)}</b></div><span>${sayi(c.tiklama)} tıklama</span></li>`).join("")}</ul></div></div>` : ""}</div>`;
    const g = $("#g-ara"); if (g) g.addEventListener("input", () => { ara = g.value; const pos = g.selectionStart; ciz(r); const y = $("#g-ara"); y.focus(); y.setSelectionRange(pos, pos); });
  };
  let son;
  const yukle = async () => { icerik().innerHTML = '<div class="yukleniyor"></div>'; son = await api(`/google?gun=${gun}${sayfaYolu ? "&sayfa=" + encodeURIComponent(sayfaYolu) : ""}`); ciz(son); };
  await yukle();
  icerik().addEventListener("click", (e) => {
    const b = e.target.closest(".sekmeler button"); if (b) { gun = +b.dataset.g; sessionStorage.setItem("hh-gsc-gun", gun); return yukle().catch(hata); }
    const s = e.target.closest("[data-sira]"); if (s) { siralama = s.dataset.sira; ciz(son); }
  });
}

function googleKurulum(d) {
  const kullaniciUrl = "https://search.google.com/search-console/users?resource_id=" + encodeURIComponent(d.mulk);
  icerik().innerHTML = `<div class="izgara iz-21"><div class="kart"><div class="kart-ust"><h2>Search Console bağlantısını kurun</h2>${d.eposta ? '<span class="et sari">Yarım kaldı</span>' : '<span class="et">Bağlı değil</span>'}</div><div class="kart-ic">
    <p class="soluk" style="margin-top:0">Google, aramada yazılan kelimeyi siteye göndermez; bu veriler yalnızca Search Console'dadır. Panelin bu verileri okuyabilmesi için bir kez aşağıdaki adımları yapın. İşlemler <b>av.yagmuranil@gmail.com</b> hesabıyla yapılmalı.</p>
    <ol style="line-height:1.7;padding-left:20px">
      <li><a href="https://console.cloud.google.com/projectcreate" target="_blank" rel="noopener">Google Cloud'da yeni bir proje oluşturun</a> (ad: <code>hukukihaberler-panel</code>).</li>
      <li>Bu projede <a href="https://console.cloud.google.com/apis/library/searchconsole.googleapis.com" target="_blank" rel="noopener">Google Search Console API</a>'yi <b>Etkinleştir</b>'e basın.</li>
      <li><a href="https://console.cloud.google.com/iam-admin/serviceaccounts/create" target="_blank" rel="noopener">Hizmet hesabı oluşturun</a> (ad: <code>panel-okuyucu</code>; rol vermeden <b>Bitti</b>).</li>
      <li>Hizmet hesabını açın → <b>Anahtarlar</b> → <b>Anahtar ekle</b> → <b>Yeni anahtar oluştur</b> → <b>JSON</b>. İnen dosyayı Not Defteri ile açıp içeriğin tamamını aşağıya yapıştırın.</li>
      <li>Kaydettikten sonra görünen hizmet hesabı e-postasını <a href="${esc(kullaniciUrl)}" target="_blank" rel="noopener">Search Console → Kullanıcılar ve izinler</a> sayfasında <b>Kullanıcı ekle</b> ile <b>Kısıtlanmış</b> izinle ekleyin.</li>
    </ol>
    <div class="alan mt"><label for="g-json">Hizmet hesabı anahtarı (JSON)</label><textarea id="g-json" class="kod" style="min-height:160px" placeholder='{"type": "service_account", ...}' spellcheck="false" autocomplete="off"></textarea><small>Anahtar sunucuda saklanır ve bir daha gösterilmez; yalnızca okuma izniyle kullanılır.</small></div>
    <p class="form-hata" id="g-hata"></p><button class="btn btn-ana" id="g-kaydet">Kaydet ve bağlantıyı dene</button></div></div>
    <div><div class="kart"><div class="kart-ust"><h2>Durum</h2></div><div class="kart-ic"><dl class="anahtar-deger"><dt>Mülk</dt><dd><code>${esc(d.mulk)}</code></dd>
      <dt>Hizmet hesabı</dt><dd>${d.eposta ? `<code style="word-break:break-all">${esc(d.eposta)}</code>` : "—"}</dd></dl>
      ${d.eposta ? `<button class="btn btn-kucuk mt" id="g-kopya">E-postayı kopyala</button>` : ""}
      ${d.hata ? `<div class="uyari-kutu mt">${esc(d.hata)}</div>` : ""}
      ${d.eposta ? `<button class="btn mt" id="g-dene">Bağlantıyı yeniden dene</button>` : ""}</div></div></div></div>`;
  $("#g-kaydet").addEventListener("click", async () => {
    $("#g-hata").textContent = "";
    try { const r = await api("/google/anahtar", { veri: { json: $("#g-json").value } }); $("#g-json").value = ""; bildir("Anahtar kaydedildi: " + r.eposta, "tamam", 8000); yonlendir(); }
    catch (e) { $("#g-hata").textContent = e.message; }
  });
  if ($("#g-kopya")) $("#g-kopya").addEventListener("click", () => { navigator.clipboard.writeText(d.eposta).then(() => bildir("Kopyalandı.", "tamam"), () => bildir(d.eposta)); });
  if ($("#g-dene")) $("#g-dene").addEventListener("click", yonlendir);
}

// ------------------------------------------------------------ KAYNAKLAR
async function sKaynaklar(tur) {
  const x = tur !== "sayfalar";
  const ad = x ? "hesaplar.txt" : "kaynaklar.txt";
  baslikYaz(x ? "X hesapları" : "Resmî sayfalar", x ? "Anlık izlenen X hesapları; resmî kurum ve kişi grupları" : "Her 5 dakikada bir taranan resmî kurum sayfaları");
  const r = await api("/kaynaklar"); const k = r[ad];
  const sayac = (m) => x ? m.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#") && !l.trim().startsWith("[")).length : m.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#")).length;
  icerik().innerHTML = `<div class="izgara iz-21"><div class="kart"><div class="kart-ust"><h2>${esc(ad)}</h2><span class="soluk" id="k-sayi"></span></div>
    <div class="kart-ic"><textarea id="k-metin" class="kod" spellcheck="false" style="min-height:520px">${esc(k.metin)}</textarea><p class="form-hata" id="k-hata"></p></div>
    <div class="yapiskan-alt">${k.ozellestirilmis ? '<button class="btn btn-hayalet" id="k-varsayilan">Varsayılan listeye dön</button>' : ""}<button class="btn btn-ana" id="k-kaydet">Kaydet</button></div></div>
    <div><div class="kart"><div class="kart-ust"><h2>Nasıl yazılır?</h2></div><div class="kart-ic kucuk">${x
      ? `<p style="margin-top:0">Her satıra bir kullanıcı adı (@ olmadan). Gruplar köşeli parantezle başlar:</p><p><code>[resmi]</code> Kurum hesapları: tüm paylaşımlar değerlendirilir; yayımlanan haberde resmî paylaşım alıntılanabilir.</p><p><code>[kisi]</code> Gazeteci ve siyasetçiler: yanıt ve yeniden paylaşımlar hariç, anahtar kelime süzgecinden geçer; hiçbir zaman alıntılanmaz.</p><p># ile başlayan satırlar not olarak yok sayılır.</p>`
      : `<p style="margin-top:0">Her satır: <code>Ad | sayfa adresi | desen</code></p><p>Desen <code>*</code> ise sayfadaki başlık uzunluğundaki tüm yeni bağlantılar alınır; ya da yalnızca eşleşen bağlantılar için düzenli ifade yazılır.</p><p>İlk okumada mevcut bağlantılar yalnızca kaydedilir; sonradan eklenen duyurular işleme girer.</p>`}</div></div>
      <div class="uyari-kutu mt">${x ? "X hesap değişiklikleri servis yeniden başlatılınca uygulanır." : "Değişiklik bir sonraki tarama turunda (en geç 5 dakika) uygulanır."}${x ? ' <button class="btn btn-kucuk mt" id="k-yb">Servisi yeniden başlat</button>' : ""}</div></div></div>`;
  const s = () => { $("#k-sayi").textContent = sayac($("#k-metin").value) + (x ? " hesap" : " kaynak"); };
  $("#k-metin").addEventListener("input", s); s();
  $("#k-kaydet").addEventListener("click", async () => {
    $("#k-hata").textContent = "";
    try { const r2 = await api("/kaynaklar", { veri: { [ad]: $("#k-metin").value } }); bildir(r2.mesaj, "tamam", 7000); } catch (er) { $("#k-hata").textContent = er.message; }
  });
  if ($("#k-varsayilan")) $("#k-varsayilan").addEventListener("click", async () => {
    if (!(await pencere({ baslik: "Varsayılan listeye dönülsün mü?", metin: "<p>Paneldeki değişiklikler yedeklenir ve koddaki varsayılan liste kullanılır.</p>", onay: "Varsayılana dön" }))) return;
    try { const r2 = await api("/kaynaklar/varsayilan", { veri: { ad } }); bildir(r2.mesaj, "tamam"); yonlendir(); } catch (er) { hata(er); }
  });
  if ($("#k-yb")) $("#k-yb").addEventListener("click", servisYenidenBaslat);
}

async function servisYenidenBaslat() {
  if (!(await pencere({ baslik: "Servis yeniden başlatılsın mı?", metin: "<p>Bot ve panel yaklaşık 30 saniye duraklar; açılışta kod GitHub'dan güncellenir. Sürmekte olan yazım işleri kuyruktan devam eder.</p>", onay: "Yeniden başlat" }))) return;
  try {
    const r = await api("/servis/yeniden-baslat", { veri: {} });
    const t = bildir(r.mesaj, "is", 0);
    const bekle = async (n) => { try { await api("/gosterge"); t.remove(); bildir("Servis yeniden açıldı.", "tamam"); yonlendir(); } catch (e) { if (n > 0) setTimeout(() => bekle(n - 1), 5000); else { t.remove(); hata("Servis 2 dakikada açılmadı; kayıtlara bakın."); } } };
    setTimeout(() => bekle(24), 8000);
  } catch (er) { hata(er); }
}

// ------------------------------------------------------------ YAYIN
async function sYayin() {
  baslikYaz("Yayın ve servis", "Derleme, Cloudflare dağıtımı, arama motoru bildirimi ve servis yönetimi");
  const r = await api("/yayin"); const s = r.servis;
  icerik().innerHTML = `<div class="izgara iz-4">
    <div class="kart sayi-kart"><span>Yayın</span><b style="font-size:20px"><span class="et yesil" style="font-size:14px">Editör onayıyla</span></b><small>Hiçbir yazı onaysız yayımlanmaz</small></div>
    <div class="kart sayi-kart"><span>Çalışma süresi</span><b style="font-size:20px">${esc(sure(s.calisma_sn))}</b><small>Son yeniden başlatmadan beri</small></div>
    <div class="kart sayi-kart"><span>Son derleme</span><b style="font-size:20px"><code>${esc(s.site_commit)}</code></b><small>GitHub'daki site deposu</small></div>
    <div class="kart sayi-kart"><span>Cloudflare</span><b style="font-size:20px">${s.cf_esit ? '<span class="et yesil" style="font-size:14px">Güncel</span>' : '<span class="et sari" style="font-size:14px">Eşitleniyor</span>'}</b><small>Yayındaki sürüm: <code>${esc(s.cf_commit || "—")}</code></small></div></div>
  <div class="izgara iz-3 mt">
    <div class="kart"><div class="kart-ust"><h2>Siteyi yeniden derle</h2></div><div class="kart-ic"><p class="soluk kucuk" style="margin-top:0">Tüm sayfalar yeniden üretilir, denetlenir (kırık bağlantı, kimlik, görsel) ve Cloudflare'e yüklenir.</p><button class="btn btn-ana" id="p-derle">Derle ve yayınla</button></div></div>
    <div class="kart"><div class="kart-ust"><h2>Arama motorlarına bildir</h2></div><div class="kart-ic"><form id="p-index" class="satir"><input type="url" class="ara" placeholder="https://hukukihaberler.com/..." required><button class="btn">Bildir</button></form><p class="soluk kucuk">IndexNow (Bing, Yandex). Google'a yayın sonrası otomatik bildirilir.</p></div></div>
    <div class="kart"><div class="kart-ust"><h2>Servis</h2></div><div class="kart-ic"><p class="soluk kucuk" style="margin-top:0">Ayar ve X hesap değişikliklerini uygulamak ya da kodu güncellemek için.</p><button class="btn" id="p-yb">Servisi yeniden başlat</button></div></div></div>
  <div class="kart mt"><div class="kart-ust"><h2>Ek mesai</h2><span class="soluk kucuk" id="m-durum"></span></div><div class="kart-ic">
    <p class="soluk kucuk" style="margin-top:0">X akışından bağımsız olarak web'de hukuki gelişmeleri arar; sitede olmayanlar normal eleme, teyit ve denetimden geçip <b>Onay bekleyenler</b>'e düşer. Kredi kullanılmadan yanacaksa saatte bir kendiliğinden de çalışır (Ayarlar › Otomatik ek mesai).</p>
    <div class="satir"><button class="btn btn-ana" id="m-guncel">Güncel gelişmeleri tara</button><button class="btn" id="m-gecmis">Son 3 haftayı tara</button></div></div></div>
  <div class="izgara iz-2 mt">
    <div class="kart"><div class="kart-ust"><h2>Son site değişiklikleri</h2><a href="https://github.com/personapetrokimya-afk/hukukihaberler/commits/main" target="_blank" rel="noopener">GitHub ↗</a></div><ul class="liste">${r.commitler.map((c) => `<li><div class="ana-satir"><b style="font-weight:550">${esc(c.mesaj)}</b><small><code>${esc(c.kisa)}</code> · ${esc(c.zaman)}</small></div></li>`).join("")}</ul></div>
    <div class="kart"><div class="kart-ust"><h2>Panel işlem günlüğü</h2></div>${r.islemler.length ? `<ul class="liste">${r.islemler.map((i) => `<li><div class="ana-satir"><b style="font-weight:550">${esc(i.islem)}</b><small>${zamanYaz(i.ts)} · ${esc(i.ayrinti)}</small></div></li>`).join("")}</ul>` : '<div class="bos">Henüz işlem yok.</div>'}</div></div>`;
  $("#p-derle").addEventListener("click", async () => {
    if (!(await pencere({ baslik: "Site yeniden derlensin mi?", metin: "<p>İşlem 1-3 dakika sürer. Bu sırada yeni yayınlar sıraya girer.</p>", onay: "Derle ve yayınla" }))) return;
    try { const r2 = await api("/yayin/derle", { veri: {} }); isTakip(r2.is, "Site derleniyor", () => yonlendir()); } catch (er) { hata(er); }
  });
  $("#p-index").addEventListener("submit", async (e) => { e.preventDefault(); try { const r2 = await api("/yayin/indexnow", { veri: { url: $("input", e.target).value } }); bildir(r2.mesaj, "tamam"); } catch (er) { hata(er); } });
  $("#p-yb").addEventListener("click", servisYenidenBaslat);
  const mesaiDurum = async () => { try { const m = await api("/mesai"); $("#m-durum").textContent = (m.calisiyor ? "Tur çalışıyor" : "Boşta") + (m.otomatik ? " · otomatik açık" : "") + (m.son ? " · son tur: " + m.son.ozet : ""); } catch (er) { } };
  mesaiDurum();
  const mesaiBaslat = async (mod) => { try { const r2 = await api("/mesai", { veri: { mod, gun: 21, adet: 8 } }); isTakip(r2.is, "Ek mesai turu", () => mesaiDurum()); } catch (er) { hata(er); } };
  $("#m-guncel").addEventListener("click", () => mesaiBaslat("guncel"));
  $("#m-gecmis").addEventListener("click", () => mesaiBaslat("gecmis"));
}

// ------------------------------------------------------------ MALİYET
async function sMaliyet() {
  baslikYaz("Maliyet", "Yapay zekâ ve arama çağrılarının maliyeti (USD): gün gün, yazı yazı ve aşama aşama");
  const r = await api("/maliyet"); const bugun = r.seri[r.seri.length - 1] || { maliyet: 0 };
  const usd = (v, b = 3) => "$" + Number(v || 0).toFixed(b);
  icerik().innerHTML = `<div class="izgara iz-3"><div class="kart sayi-kart vurgu"><span>Bugün</span><b>$${bugun.maliyet.toFixed(2)}</b><small>${sayi(bugun.yazi)} yazı · ${sayi(bugun.eleme)} eleme</small></div>
    <div class="kart sayi-kart"><span>Son 30 gün</span><b>$${r.toplam_30.toFixed(2)}</b><small>Günlük ortalama $${(r.toplam_30 / Math.max(1, r.seri.length)).toFixed(2)}</small></div>
    <div class="kart sayi-kart"><span>Bugünkü pay</span><b>$${r.butce}</b><small>Aylık krediden her gece hesaplanır</small></div></div>
    <div class="kart mt"><div class="kart-ust"><h2>Servis bakiyeleri</h2><span class="soluk kucuk">Kullandığımız ücretli ve ücretsiz servisler</span></div><div id="m-bakiye"><div class="yukleniyor"></div></div></div>
    <div class="kart mt"><div class="kart-ust"><h2>Günlük maliyet</h2><span class="soluk kucuk">Bir güne tıklayın: ayrıntısı aşağıda açılır</span></div><div class="kart-ic" id="m-grafik">${grafik(r.seri.slice(-30), "maliyet", (x) => (x.gun || "").slice(8, 10) + "." + (x.gun || "").slice(5, 7))}</div></div>
    <div class="kart mt"><div class="tablo-kap"><table><thead><tr><th>Gün</th><th>Maliyet</th><th>Yazı</th><th>Yazı başına</th><th>Eleme</th><th>Paylaşım</th><th></th></tr></thead><tbody>
    ${r.seri.slice().reverse().map((x) => `<tr data-gun="${esc(x.gun)}" style="cursor:pointer"><td>${tarihYaz(x.gun)}</td><td class="kalin">${usd(x.maliyet)}</td><td>${sayi(x.yazi)}</td><td>${x.yazi ? usd(x.maliyet / x.yazi, 2) : "—"}</td><td>${sayi(x.eleme)}</td><td>${sayi(x.tweet)}</td><td><button class="btn btn-kucuk" data-gun="${esc(x.gun)}">Ayrıntı</button></td></tr>`).join("")}</tbody></table></div></div>
    <div id="m-detay" class="mt"></div>`;
  const yuzde = (v, t) => t ? Math.round(v / t * 100) : 0;
  const cubuk = (L, t) => `<ul class="liste">${L.map(([a, v]) => `<li style="display:block"><div class="satir" style="justify-content:space-between"><b style="font-weight:550">${esc(a)}</b><span>${usd(v)} <span class="soluk kucuk">%${yuzde(v, t)}</span></span></div><div class="ilerleme"><i style="width:${yuzde(v, t)}%;background:#2d4b69"></i></div></li>`).join("") || '<li class="soluk">Kayıt yok.</li>'}</ul>`;
  const asamaCip = (o) => Object.entries(o).map(([a, v]) => `<span class="et" title="${esc(a)}">${esc(a)} ${usd(v)}</span>`).join(" ");
  const DURUM = { "yayınlandı": "yesil", "bekliyor": "sari", "reddedildi": "", "yayından kaldırıldı": "kirmizi" };
  const detay = async (gun) => {
    const kutu = $("#m-detay"); kutu.innerHTML = '<div class="yukleniyor"></div>';
    $$("tr[data-gun]").forEach((t) => (t.style.background = t.dataset.gun === gun ? "var(--ana-acik)" : ""));
    let d; try { d = await api("/maliyet/detay?gun=" + encodeURIComponent(gun)); } catch (e) { kutu.innerHTML = ""; return hata(e); }
    const fark = d.toplam_gun - d.toplam_kayit;
    const yayinda = d.yazilar.filter((y) => y.durum === "yayınlandı");
    kutu.innerHTML = `<div class="kart"><div class="kart-ust"><h2>${tarihYaz(d.gun)} ayrıntısı</h2><span class="soluk">Kayıtlı ayrıntı: ${usd(d.toplam_kayit, 2)} / gün toplamı ${usd(d.toplam_gun, 2)}</span></div>
      ${!d.ilk_kayit ? `<div class="kart-ic"><div class="uyari-kutu mavi">Bu gün için yazı başına ayrıntı yok. Ayrıntılı kayıt 21 Ekim 2026 öğleden sonra başladı; önceki günlerde yalnızca gün toplamı tutuluyordu.</div></div>` :
      `${fark > 0.01 ? `<div class="kart-ic" style="padding-bottom:0"><div class="uyari-kutu mavi">Ayrıntılı kayıt ${new Date(d.ilk_kayit * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}'den itibaren tutuluyor; günün bu saatten önceki ${usd(fark, 2)} harcaması ayrıntısız.</div></div>` : ""}
      <div class="kart-ic"><div class="izgara iz-4">
        <div class="sayi-kart" style="padding:0"><span>Yazı/taslak</span><b>${sayi(d.yazilar.length)}</b><small>${usd(d.yazilar.reduce((s, y) => s + y.usd, 0), 2)} · ortalama ${d.yazilar.length ? usd(d.yazilar.reduce((s, y) => s + y.usd, 0) / d.yazilar.length, 3) : "—"}</small></div>
        <div class="sayi-kart" style="padding:0"><span>Yayımlanan</span><b>${sayi(yayinda.length)}</b><small>${usd(yayinda.reduce((s, y) => s + y.usd, 0), 2)} harcandı</small></div>
        <div class="sayi-kart" style="padding:0"><span>Elenen paylaşım</span><b>${sayi(d.elenen.adet)}</b><small>${usd(d.elenen.usd, 3)} · tanesi ${d.elenen.adet ? usd(d.elenen.usd / d.elenen.adet, 4) : "—"}</small></div>
        <div class="sayi-kart" style="padding:0"><span>Yazılmayan / diğer</span><b>${sayi(d.digerleri.length)}</b><small>${usd(d.digerleri.reduce((s, y) => s + y.usd, 0), 3)}</small></div></div></div>`}
    </div>
    ${d.ilk_kayit ? `<div class="izgara iz-2 mt"><div class="kart"><div class="kart-ust"><h2>Aşamalara göre</h2></div>${cubuk(d.asamalar, d.toplam_kayit)}</div>
      <div class="kart"><div class="kart-ust"><h2>Modellere göre</h2></div>${cubuk(d.modeller, d.toplam_kayit)}</div></div>
    <div class="kart mt"><div class="kart-ust"><h2>Yazı başına maliyet</h2><span class="soluk kucuk">Eleme, araştırma, yazım, görsel, denetim ve yayın dahil</span></div>
      ${d.yazilar.length ? `<div class="tablo-kap"><table><thead><tr><th>Yazı</th><th>Durum</th><th>Kaynak</th><th>Maliyet</th><th>Aşamalar</th></tr></thead><tbody>${d.yazilar.map((y) => `<tr>
        <td class="baslik-hucre">${y.slug && y.durum === "yayınlandı" ? `<a href="#/yazi/${esc(y.slug)}">${esc(y.baslik || y.slug)}</a>` : y.tid ? `<a href="#/taslak/${esc(y.tid)}">${esc(y.baslik || y.tid)}</a>` : esc(y.baslik || y.slug)}<small>${y.ts ? zamanYaz(y.ts) : ""}${y.isler > 1 ? ` · ${y.isler} iş` : ""}</small></td>
        <td>${y.durum ? `<span class="et ${DURUM[y.durum] ?? ""}">${esc(y.durum)}</span>` : '<span class="soluk">—</span>'}</td>
        <td class="soluk kucuk">${y.hesap ? "@" + esc(y.hesap) : esc(y.kaynak && !String(y.kaynak).startsWith("http") ? y.kaynak : "")}</td>
        <td class="kalin" style="white-space:nowrap">${usd(y.usd)}</td><td style="min-width:260px">${asamaCip(y.asamalar)}</td></tr>`).join("")}</tbody></table></div>` : '<div class="bos">Bu gün taslak ya da yazı yok.</div>'}</div>
    <div class="izgara iz-2 mt"><div class="kart"><div class="kart-ust"><h2>Elenen paylaşımlar</h2><span class="soluk kucuk">${sayi(d.elenen.adet)} adet · ${usd(d.elenen.usd, 3)}</span></div>
      ${d.elenen.ornekler.length ? `<ul class="liste">${d.elenen.ornekler.map((e) => `<li><div class="ana-satir"><b style="font-weight:550;white-space:normal">${esc(e.konu || "—")}</b><small>${e.hesap ? "@" + esc(e.hesap) + " · " : ""}${esc(e.neden || "")}</small></div><span class="soluk">${usd(e.usd, 4)}</span></li>`).join("")}</ul>` : '<div class="bos">Kayıt yok.</div>'}</div>
      <div class="kart"><div class="kart-ust"><h2>Yazılmayan ve diğer işler</h2></div>
      ${d.digerleri.length ? `<ul class="liste">${d.digerleri.map((e) => `<li><div class="ana-satir"><b style="font-weight:550;white-space:normal">${esc(e.konu)}</b><small>${esc(e.sonuc)}${e.hesap ? " · @" + esc(e.hesap) : ""} · ${Object.keys(e.asamalar).map(esc).join(", ")}</small></div><span class="kalin">${usd(e.usd)}</span></li>`).join("")}</ul>` : '<div class="bos">Kayıt yok.</div>'}</div></div>` : ""}`;
  };
  const RENK = { iyi: "yesil", dusuk: "sari", kritik: "kirmizi", bilinmiyor: "" };
  const DURUM_AD = { iyi: "Yeterli", dusuk: "Azalıyor", kritik: "Kritik", bilinmiyor: "Bakiye girilmedi" };
  const bakiyeCiz = async () => {
    let b; try { b = await api("/bakiyeler"); } catch (e) { $("#m-bakiye").innerHTML = `<div class="bos">${esc(e.message)}</div>`; return; }
    $("#m-bakiye").innerHTML = `<ul class="liste">${b.servisler.map((s) => {
      let ana = "", alt = "";
      if (s.servis === "anthropic") {
        if (s.kalan != null) {
          const o = s.donem ? Math.min(100, Math.round(s.kalan / s.donem * 100)) : 0;
          const po = s.gunluk_pay ? Math.min(100, Math.round(s.bugunku / s.gunluk_pay * 100)) : 100;
          ana = `<b style="font-size:20px">${usd(s.kalan, 2)}</b> <span class="soluk kucuk">aylık kredi kaldı</span><div class="ilerleme" style="max-width:420px"><i class="${o < 5 ? "tehlike" : o < 20 ? "uyari" : ""}" style="width:${o}%"></i></div>`
            + `<div style="margin-top:8px">Bugünkü pay: <b style="display:inline">${usd(s.bugunku, 2)}</b> <span class="soluk kucuk" style="display:inline">/ ${usd(s.gunluk_pay, 2)} kullanıldı</span></div><div class="ilerleme" style="max-width:420px"><i class="${po >= 100 ? "tehlike" : po > 80 ? "uyari" : ""}" style="width:${po}%"></i></div>`;
          const kr = (s.krediler || []).filter((k) => k.aktif || k.bitis >= new Date().toISOString().slice(0, 10)).map((k) => `${tarihYaz(k.verilme)} – ${tarihYaz(k.bitis)}: <b>${usd(Math.max(0, k.kalan), 2)}</b> / ${usd(k.tutar, 0)}${k.dogrulandi ? "" : ' <span class="soluk">(tahmini, konsoldan doğrulanacak)</span>'}`).join("<br>");
          alt = `${kr}<br>Abonelik her ayın ${s.abonelik_gunu}. günü yenilenir, yeni ${usd(200, 0)} kredi ${s.kredi_gunu}. günü gelir · sonraki kredi: <b>${tarihYaz(s.sonraki_kredi)}</b> (${s.sonraki_gun} gün)`
            + `<br>Günlük pay, kredinin kalanının son kullanma tarihine kalan günlere bölünmesiyle her gece yeniden hesaplanır; harcanmayan pay ertesi güne devreder. Günlük ortalama harcama ${usd(s.gunluk_ortalama, 2)}.`;
          if (s.durdu) alt = `<span style="color:var(--kirmizi);font-weight:650">Ücretli çağrılar durdu: ${esc(s.durdu)}</span><br>` + alt;
          else if (s.pay_doldu) alt = `<span style="color:var(--sari);font-weight:650">Bugünkü pay doldu; yeni yazım yarın sürer.</span><br>` + alt;
          else if (s.yanacak > 1) alt += `<br><span class="soluk">Bu hızla ${tarihYaz(s.bitis)} tarihinde yaklaşık ${usd(s.yanacak, 0)} kullanılmadan sona erer.</span>`;
        } else { ana = '<span class="soluk">Kredi girilmedi</span>'; alt = "Konsoldaki aylık kredi bakiyesini ve son kullanma tarihini girin."; }
        alt += `<br>Satın alınmış kredi: <b>${esc(s.satin_alinan)}</b> · <a href="https://platform.claude.com/settings/billing" target="_blank" rel="noopener">Konsolda gör ↗</a> <button class="btn btn-kucuk" data-bakiye="anthropic">Krediyi güncelle</button>`;
      } else if (s.servis === "x") {
        if (s.sinir) { const o = Math.round(s.kullanim / s.sinir * 100);
          ana = `<b style="font-size:20px">${sayi(s.sinir - s.kullanim)}</b> <span class="soluk kucuk">paylaşım kotası kaldı</span>`;
          alt = `Bu dönem ${sayi(s.kullanim)} / ${sayi(s.sinir)} kullanıldı (%${o})${s.yenilenme_gunu ? ` · kota her ayın ${esc(s.yenilenme_gunu)}. günü yenilenir` : ""}<div class="ilerleme" style="max-width:420px"><i class="${o > 95 ? "tehlike" : o > 80 ? "uyari" : ""}" style="width:${o}%"></i></div>`;
        } else { ana = '<span class="soluk">Kullanım bilgisi alınamadı</span>'; alt = esc(s.hata || "") + (s.ayrinti ? ` <span class="soluk">${esc(s.ayrinti)}</span>` : ""); }
        alt += ` · <a href="https://console.x.com/" target="_blank" rel="noopener">X geliştirici konsolu ↗</a>`;
      } else { ana = '<span class="kalin">Ücretsiz</span>'; alt = esc(s.aciklama || ""); }
      return `<li style="align-items:flex-start"><div class="ana-satir"><b style="white-space:normal">${esc(s.ad)}</b><div style="margin:4px 0">${ana}</div><small style="white-space:normal">${alt}</small></div><span class="et ${RENK[s.durum] ?? ""}">${esc(s.tur === "ucretsiz" ? "Ücretsiz" : DURUM_AD[s.durum] || s.durum || "—")}</span></li>`;
    }).join("")}</ul>`;
  };
  bakiyeCiz();
  icerik().addEventListener("click", async (e) => {
    const bb = e.target.closest("[data-bakiye]"); if (!bb) return;
    let bitis = "";
    const v = await pencere({ baslik: "Aylık API kredisini doğrula", metin: '<p>Konsolda Faturalandırma → Promosyon kredileri bölümündeki krediyi girin. Veriliş ya da son kullanma tarihi eşleşen kredi güncellenir, yoksa yeni kredi eklenir. Panel bu andan sonraki harcamayı düşerek kalanı ve günlük payı hesaplar.</p><div class="alan mt"><label for="p-verilme">Veriliş tarihi</label><input id="p-verilme" type="date"></div><div class="alan mt"><label for="p-bitis">Son kullanma tarihi</label><input id="p-bitis" type="date"></div>', onay: "Kaydet", girdi: { etiket: "Kalan kredi (USD)", yer: "ör. 174.71" } });
    bitis = ($("#p-bitis") || {}).value || ""; const verilme = ($("#p-verilme") || {}).value || "";
    if (!v) return;
    try { const r2 = await api("/bakiye", { veri: { servis: "anthropic", bakiye: v, bitis, verilme } }); bildir(r2.mesaj, "tamam"); bakiyeCiz(); } catch (er) { hata(er); }
  });
  icerik().addEventListener("click", (e) => { const t = e.target.closest("[data-gun]"); if (t) { detay(t.dataset.gun); $("#m-detay").scrollIntoView({ behavior: "smooth", block: "start" }); } });
  await detay(bugun.gun || new Date().toISOString().slice(0, 10));
}

// ------------------------------------------------------------ KAYITLAR
async function sKayitlar() {
  baslikYaz("Kayıtlar", "Botun ve yayın hattının çalışma kayıtları (gizli anahtarlar maskelenir)", `<label class="anahtar"><input type="checkbox" id="l-canli" checked> Canlı</label>`);
  const f = { tur: "", q: "", n: 400 };
  icerik().innerHTML = `<div class="kart"><div class="kart-ic"><form class="satir mb" id="l-form"><div class="secim-grubu">${[["", "Tümü"], ["hata", "Hatalar"], ["yayin", "Yayın"]].map(([v, a]) => `<label><input type="radio" name="tur" value="${v}" ${v === "" ? "checked" : ""}>${a}</label>`).join("")}</div>
    <input type="search" name="q" class="ara" placeholder="Kayıtlarda ara"><select name="n" style="width:auto"><option value="200">200 satır</option><option value="400" selected>400 satır</option><option value="1000">1000 satır</option><option value="3000">3000 satır</option></select></form>
    <div class="kayit" id="l-kayit">Yükleniyor…</div></div></div>`;
  const yukle = async () => {
    const r = await api("/kayitlar?" + new URLSearchParams(f));
    const k = $("#l-kayit"); if (!k) return;
    const altta = k.scrollTop + k.clientHeight >= k.scrollHeight - 30;
    k.innerHTML = r.satirlar.map((s) => { const c = /hata|hatası|başarısız|error|traceback/i.test(s) ? "h" : /YAYINDA|yüklendi|BİLDİRİM|TASLAK HAZIR/.test(s) ? "y" : ""; return `<span class="z">${esc(s.slice(0, 19))}</span>${c ? `<span class="${c}">${esc(s.slice(19))}</span>` : esc(s.slice(19))}`; }).join("\n") || "Kayıt yok.";
    if (altta) k.scrollTop = k.scrollHeight;
  };
  let g; $("#l-form").addEventListener("input", () => { const fm = new FormData($("#l-form")); for (const [k, v] of fm) f[k] = v; clearTimeout(g); g = setTimeout(yukle, 250); });
  $("#l-form").addEventListener("submit", (e) => e.preventDefault());
  await yukle(); $("#l-kayit").scrollTop = 1e9;
  const no = SAYFA_NO;
  const z = setInterval(() => { if (no !== SAYFA_NO) return clearInterval(z); if (!document.hidden && $("#l-canli") && $("#l-canli").checked) yukle().catch(() => {}); }, 5000);
  sayfaTemizle = () => clearInterval(z);
}

// ------------------------------------------------------------ AYARLAR
async function sAyarlar() {
  baslikYaz("Ayarlar", "Yayın, bütçe, yazım ve bildirim ayarları");
  const r = await api("/ayarlar");
  const gruplar = [...new Set(r.ayarlar.map((a) => a.grup))];
  const alan = (a) => {
    if (a.tur === "bool") return `<label class="anahtar"><input type="checkbox" data-k="${a.anahtar}" ${a.deger === "1" ? "checked" : ""}>${esc(a.etiket)}</label><small>${esc(a.aciklama)}</small>`;
    if (a.tur.startsWith("secim:")) return `<label>${esc(a.etiket)}</label><select data-k="${a.anahtar}">${a.tur.slice(6).split("|").map((v) => `<option ${a.deger === v ? "selected" : ""}>${v}</option>`).join("")}</select><small>${esc(a.aciklama)}</small>`;
    return `<label>${esc(a.etiket)}</label><input type="${a.tur === "text" ? "text" : "number"}" ${a.tur === "float" ? 'step="0.5"' : ""} min="0" data-k="${a.anahtar}" value="${esc(a.deger)}"><small>${esc(a.aciklama)}</small>`;
  };
  icerik().innerHTML = `<div class="izgara iz-2">${gruplar.map((g) => `<div class="kart"><div class="kart-ust"><h2>${esc(g)}</h2></div><div class="kart-ic">${r.ayarlar.filter((a) => a.grup === g).map((a) => `<div class="alan">${alan(a)}</div>`).join("")}</div></div>`).join("")}
    <div class="kart"><div class="kart-ust"><h2>Anahtarlar ve şifreler</h2></div><div class="kart-ic"><p class="soluk kucuk" style="margin-top:0">Değerler hiçbir zaman gösterilmez. Değiştirmek için yenisini yazın; boş bırakılan alan değişmez. Panel şifresi değişince tüm oturumlar kapanır.</p>
      ${r.gizli.map((g) => `<div class="alan"><label>${esc(g.etiket)} ${g.tanimli ? '<span class="et yesil">tanımlı</span>' : '<span class="et">yok</span>'}</label><input type="password" autocomplete="new-password" data-g="${g.anahtar}" placeholder="${g.tanimli ? "Değiştirmek için yeni değeri yazın" : "Değer yazın"}"></div>`).join("")}</div></div></div>
    <div class="kart mt"><div class="yapiskan-alt" style="position:static"><span class="soluk kucuk">Değişiklikler servis yeniden başlatılınca geçerli olur.</span><button class="btn btn-hayalet" id="a-oturum">Tüm oturumları kapat</button><button class="btn" id="a-yb">Servisi yeniden başlat</button><button class="btn btn-ana" id="a-kaydet">Kaydet</button></div></div>`;
  $("#a-kaydet").addEventListener("click", async () => {
    const ayarlar = {}; $$("[data-k]").forEach((i) => { ayarlar[i.dataset.k] = i.type === "checkbox" ? (i.checked ? "1" : "0") : i.value; });
    const gizli = {}; $$("[data-g]").forEach((i) => { if (i.value.trim()) gizli[i.dataset.g] = i.value.trim(); });
    try {
      const r2 = await api("/ayarlar", { veri: { ayarlar, gizli } }); $$("[data-g]").forEach((i) => (i.value = ""));
      bildir(r2.mesaj, "tamam", 7000);
      if (gizli.PANEL_SIFRE) return girisGoster();
      if (await pencere({ baslik: "Servis şimdi yeniden başlatılsın mı?", metin: "<p>Ayarların geçerli olması için gerekir.</p>", onay: "Yeniden başlat", vazgec: "Sonra" })) {
        const r3 = await api("/servis/yeniden-baslat", { veri: {} }); bildir(r3.mesaj, "", 8000);
      }
    } catch (er) { hata(er); }
  });
  $("#a-yb").addEventListener("click", servisYenidenBaslat);
  $("#a-oturum").addEventListener("click", async () => { if (await pencere({ baslik: "Tüm oturumlar kapatılsın mı?", metin: "<p>Bu cihaz dahil her yerde yeniden giriş gerekir.</p>", onay: "Kapat", tehlike: true })) { try { await api("/oturumlar/kapat", { veri: {} }); } catch (e) {} girisGoster(); } });
}

// ------------------------------------------------------------ başlangıç
async function baslat() {
  try { OTURUM = await api("/oturum"); if (OTURUM.yazarlar && OTURUM.yazarlar.length) DENETLEYEN = Object.fromEntries(OTURUM.yazarlar.map((y) => [y.kod, y.ad])); }
  catch (e) { if (e.message !== "Oturum kapandı.") { $("#giris").hidden = false; $("#giris-hata").textContent = e.message; } return; }
  $("#giris").hidden = true; $("#uygulama").hidden = false;
  if (OTURUM.site) $("#site-bag").href = OTURUM.site + "/";
  await yonlendir();
  rozetGuncelle();
  if (zamanlayici) clearInterval(zamanlayici);
  zamanlayici = setInterval(() => { if (!document.hidden) rozetGuncelle(); }, 15000);
}
baslat();
})();
