// Cloudflare Pages Function: okur iletişim formu (KV: ANKET, "msg:" önekiyle)
// POST   /api/iletisim            -> okur mesajı bırakır (herkese açık; doğrulama + spam koruması)
// GET    /api/iletisim            -> yönetim paneli bekleyen mesajları alır (Authorization: Bearer <MESAJ_ANAHTAR>)
// DELETE /api/iletisim?k=a,b,c    -> yönetim paneli aldığı mesajları KV'den siler (aynı yetki)
const JSONH = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" };
const yanit = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: JSONH });

const KONULAR = {
  ihbar: "Haber ihbarı",
  duzeltme: "Düzeltme talebi",
  cevap: "Cevap ve düzeltme hakkı",
  icerik: "Kişilik hakkı / içerik kaldırma talebi",
  kvkk: "KVKK başvurusu",
  teknik: "Teknik sorun",
  diger: "Diğer",
};
const SAKLAMA_SN = 180 * 86400;   // panel almazsa bile 180 gün sonra kendiliğinden silinir
const SAATLIK_SINIR = 5;           // aynı bağlantıdan saatte en fazla 5 mesaj

const temiz = (s, n) => String(s ?? "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim().slice(0, n);
const EPOSTA = /^[^\s@<>()",;:]{1,64}@[^\s@<>()",;:]{1,190}\.[a-zA-ZğüşıöçĞÜŞİÖÇ]{2,24}$/;

async function ozet(metin) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(metin));
  return [...new Uint8Array(h)].slice(0, 12).map((x) => x.toString(16).padStart(2, "0")).join("");
}

function yetkili(request, env) {
  const beklenen = env.MESAJ_ANAHTAR || "";
  const gelen = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (beklenen.length < 24 || gelen.length !== beklenen.length) return false;
  let fark = 0;
  for (let i = 0; i < gelen.length; i++) fark |= gelen.charCodeAt(i) ^ beklenen.charCodeAt(i);
  return fark === 0;
}

export async function onRequestPost({ request, env, waitUntil }) {
  if (!env.ANKET) return yanit({ hata: "Form şu an kullanılamıyor. Lütfen e-posta ile yazın." }, 503);
  const tur = request.headers.get("content-type") || "";
  let b = {};
  try {
    b = tur.includes("application/json") ? await request.json() : Object.fromEntries(await request.formData());
  } catch { return yanit({ hata: "Form okunamadı." }, 400); }

  // bot tuzakları: görünmez alan dolu ya da form 4 saniyeden kısa sürede gönderilmişse sessizce kabul edilmiş gibi yanıt verilir
  const acilis = Number(b.t || 0);
  if (temiz(b.web, 200) || !acilis || Date.now() - acilis < 4000) return yanit({ tamam: true });

  const m = {
    ad: temiz(b.ad, 80),
    eposta: temiz(b.eposta, 160).toLowerCase(),
    telefon: temiz(b.telefon, 30),
    konu: KONULAR[b.konu] ? b.konu : "",
    adres: temiz(b.adres, 400),
    baslik: temiz(b.baslik, 140),
    mesaj: temiz(b.mesaj, 4000),
  };
  const hatalar = [];
  if (m.ad.length < 3) hatalar.push("Ad soyad en az 3 karakter olmalı.");
  if (!EPOSTA.test(m.eposta)) hatalar.push("Geçerli bir e-posta adresi yazın.");
  if (!m.konu) hatalar.push("Bir konu seçin.");
  if (m.baslik.length < 5) hatalar.push("Başlık en az 5 karakter olmalı.");
  if (m.mesaj.length < 30) hatalar.push("Mesaj en az 30 karakter olmalı.");
  if (m.adres && !/^https?:\/\//i.test(m.adres)) hatalar.push("İlgili haber adresi http:// ya da https:// ile başlamalı.");
  if ((m.konu === "duzeltme" || m.konu === "cevap" || m.konu === "icerik") && !m.adres) hatalar.push("Bu konu için ilgili haberin adresini yazın.");
  if (m.telefon && !/^[0-9 +()-]{7,30}$/.test(m.telefon)) hatalar.push("Telefon yalnızca rakam, boşluk, +, ( ) ve - içerebilir.");
  if (b.onay !== true && b.onay !== "1" && b.onay !== "on") hatalar.push("Aydınlatma metnini okuduğunuzu onaylayın.");
  if ((m.mesaj.match(/https?:\/\//gi) || []).length > 5) hatalar.push("Mesajda en fazla 5 bağlantı olabilir.");
  if (hatalar.length) return yanit({ hata: hatalar.join(" "), hatalar }, 422);

  // aynı bağlantıdan gelen yoğun gönderimi sınırla (IP saklanmaz; saatlik, kısa ömürlü özet anahtar)
  const ip = request.headers.get("cf-connecting-ip") || "";
  const sk = "ml:" + (await ozet(ip + "|" + new Date().toISOString().slice(0, 13)));
  const sayi = Number((await env.ANKET.get(sk)) || 0);
  if (sayi >= SAATLIK_SINIR) return yanit({ hata: "Kısa sürede çok sayıda mesaj gönderildi. Lütfen bir saat sonra yeniden deneyin ya da e-posta ile yazın." }, 429);
  await env.ANKET.put(sk, String(sayi + 1), { expirationTtl: 3700 });

  const zaman = Date.now();
  const no = "HH-" + new Date(zaman + 3 * 3600e3).toISOString().slice(2, 10).replace(/-/g, "") + "-" + Math.random().toString(36).slice(2, 7).toUpperCase();
  const kayit = { no, ts: zaman, ...m, konu_ad: KONULAR[m.konu], ulke: request.headers.get("cf-ipcountry") || "", tarayici: temiz(request.headers.get("user-agent"), 200) };
  await env.ANKET.put("msg:" + zaman + "-" + no, JSON.stringify(kayit), { expirationTtl: SAKLAMA_SN });
  // yönetim paneline haber ver: mesaj hemen alınır (panel kapalıysa yedek denetim birkaç dakika içinde alır)
  if (env.MESAJ_ANAHTAR && waitUntil) {
    waitUntil(fetch("https://panel.hukukihaberler.com/yonetim/api/mesaj-bildir", {
      method: "POST", headers: { Authorization: "Bearer " + env.MESAJ_ANAHTAR, "Content-Type": "application/json" }, body: "{}",
    }).catch(() => {}));
  }
  return yanit({ tamam: true, no });
}

export async function onRequestGet({ request, env }) {
  if (!yetkili(request, env)) return yanit({ hata: "yetkisiz" }, 401);
  const liste = await env.ANKET.list({ prefix: "msg:", limit: 200 });
  const mesajlar = [];
  for (const k of liste.keys) {
    const v = await env.ANKET.get(k.name);
    if (v) { try { mesajlar.push({ anahtar: k.name, ...JSON.parse(v) }); } catch {} }
  }
  return yanit({ mesajlar, devami: !liste.list_complete });
}

export async function onRequestDelete({ request, env }) {
  if (!yetkili(request, env)) return yanit({ hata: "yetkisiz" }, 401);
  const k = (new URL(request.url).searchParams.get("k") || "").split(",").filter((x) => /^msg:\d{13}-HH-[0-9]{6}-[A-Z0-9]{3,8}$/.test(x)).slice(0, 200);
  await Promise.all(k.map((x) => env.ANKET.delete(x)));
  return yanit({ silinen: k.length });
}
