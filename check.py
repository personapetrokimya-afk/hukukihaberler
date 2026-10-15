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
