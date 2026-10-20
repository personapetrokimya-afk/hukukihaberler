import os, re, sys, urllib.parse
OUT="site"
rules=[]
for l in open(f"{OUT}/_redirects",encoding="utf-8"):
    a,b,c=l.split(); rules.append((a,b))
def resolve(path):
    p=urllib.parse.unquote(path.split("?")[0]) or "/"
    # Pages: direct file match first, then redirects
    def exists(p):
        f=os.path.join(OUT,p.lstrip("/"))
        return os.path.isfile(f) or os.path.isfile(os.path.join(f,"index.html")) or (p.endswith(".html") is False and os.path.isfile(f+".html"))
    if exists(p): return 200,p
    for a,b in rules:
        if a.endswith("*"):
            if p.startswith(a[:-1]): return 301,b
        elif ":" in a:
            pa=a.rstrip("/").split("/"); pp=p.rstrip("/").split("/")
            if len(pa)==len(pp) and all(x.startswith(":") or x==y for x,y in zip(pa,pp)):
                d={x[1:]:y for x,y in zip(pa,pp) if x.startswith(":")}
                t=b
                for kk,v in d.items(): t=t.replace(":"+kk,v)
                return 301,t
        elif a==p or a.rstrip("/")==p.rstrip("/"): return 301,b
    return 404,p
bad=[];res={}
urls=[l.rstrip("\n").split("\t")[-1] for l in open("urls.tsv",encoding="utf-8") if l.strip()]
urls=[u if u.startswith("/") else "/"+u.split("/",3)[-1] for u in urls]
for u in urls:
    code,t=resolve(u)
    res[code]=res.get(code,0)+1
    if code==404: bad.append(u)
    elif code==301:
        c2,_=resolve(t)
        if c2!=200: bad.append(f"{u} -> {t} ({c2})")
print(res); print("\n".join(bad)); print("toplam",len(urls),"kırık",len(bad))

# yayın kimliği denetimi: commit'ler yalnızca site adıyla atılır
import subprocess, sys
def _git(*a):
    try: return subprocess.check_output(["git", *a], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return ""
_ad, _ep = _git("config", "user.name"), _git("config", "user.email")
if (_ad, _ep) != ("Hukuki Haberler", "yayin@hukukihaberler.com"):
    print('HATA: commit kimliği yanlış. Önce: git config user.name "Hukuki Haberler" && git config user.email "yayin@hukukihaberler.com"')
    sys.exit(1)
_izler = [s for s in _git("log", "-20", "--format=%an %ae %cn %ce%n%B").splitlines() if any(k in s.lower() for k in ("anthropic", "claude", "co-authored-by"))]
if _izler:
    print("HATA: son commit'lerde yayın kimliği dışında iz var:", _izler[:3]); sys.exit(1)
print("kimlik tamam")

# başlık ve sss uzunluk denetimi (17 Ekim 2026 ve sonrası yazılar)
try:
    import content6 as _c6
    _uz = [(p["slug"], len(p["title"])) for p in _c6.POSTS if p.get("date", "") >= "2026-10-17" and len(p["title"]) > 75]
    _sq = [(p["slug"], q) for p in _c6.POSTS if p.get("date", "") >= "2026-10-17" for q, _ in p.get("sss", []) if len(q) > 45]
    for s, n in _uz: print(f"UZUN BAŞLIK ({n} karakter, en fazla 75): {s}")
    for s, q in _sq: print(f"UZUN SORU ({len(q)} karakter, en fazla 45): {s}: {q}")
    if _uz or _sq: sys.exit(1)
except ImportError:
    pass

# kaynak etiketi (cite) kalıntısı yayına çıkmasın
import runpy as _rp
_k = [p["slug"] for p in _rp.run_path("content6.py")["POSTS"] if "cite index" in str(p) or "</cite>" in str(p)]
if _k:
    print("HATA: cite etiketi kalıntısı:", _k); raise SystemExit(1)

# görsel denetimi: sayfalardaki her <img src> ve srcset dosyası gerçekten var olmalı
import glob
_eksik={}
for _f in glob.glob(OUT+"/**/*.html",recursive=True):
    _t=open(_f,encoding="utf-8").read()
    _u=re.findall(r'<img[^>]+?src="(/[^"]+)"',_t)+[x.strip().split()[0] for s in re.findall(r'srcset="([^"]+)"',_t) for x in s.split(",") if x.strip().startswith("/")]
    for u in _u:
        if not os.path.isfile(os.path.join(OUT,urllib.parse.unquote(u.split("?")[0]).lstrip("/"))): _eksik.setdefault(u.split("?")[0],_f)
for k,v in list(_eksik.items())[:20]: print("EKSİK GÖRSEL",k,"<-",v)
print("görsel eksik",len(_eksik))
if _eksik: sys.exit(1)
