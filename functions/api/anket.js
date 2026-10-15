// Cloudflare Pages Function: okur anketi sayaçları (KV: ANKET)
const ok = (o) => new Response(JSON.stringify(o), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
const valid = (id) => /^[a-z0-9-]{3,140}$/.test(id || "");
async function counts(env, id, n) {
  const raw = await env.ANKET.get("a:" + id);
  const c = raw ? JSON.parse(raw) : [];
  while (c.length < n) c.push(0);
  return c;
}
export async function onRequestGet({ request, env }) {
  const u = new URL(request.url); const id = u.searchParams.get("id");
  if (!valid(id)) return ok({ c: [] });
  const raw = await env.ANKET.get("a:" + id);
  return ok({ c: raw ? JSON.parse(raw) : [] });
}
export async function onRequestPost({ request, env }) {
  let b; try { b = await request.json(); } catch { return ok({ error: "bad" }); }
  const id = b.id, o = Number(b.o), n = Math.min(Number(b.n) || 0, 8);
  if (!valid(id) || !(o >= 0 && o < n)) return ok({ error: "bad" });
  // aynı IP'den aynı ankete 24 saatte bir oy (IP saklanmaz, kısa ömürlü özet anahtar)
  const ip = request.headers.get("cf-connecting-ip") || "";
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip + "|" + id));
  const key = "v:" + [...new Uint8Array(h)].slice(0, 12).map(x => x.toString(16).padStart(2, "0")).join("");
  const c = await counts(env, id, n);
  if (await env.ANKET.get(key)) return ok({ c, tekrar: true });
  c[o] += 1;
  await env.ANKET.put("a:" + id, JSON.stringify(c));
  await env.ANKET.put(key, "1", { expirationTtl: 86400 });
  return ok({ c });
}
