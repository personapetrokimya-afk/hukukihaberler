# -*- coding: utf-8 -*-
"""Hukuki inceleme kuralı: bir yazıyı hangi avukatın (kural grubu) inceleyeceği. Site derleyicisi (build.py) ve editör botu
aynı kuralı kullanır; taslakta görünen otomatik editör sitede çıkacak inceleme kartıyla aynı olur.
Ceza hukuku (suç, soruşturma, kovuşturma, ceza yargılaması) -> "ceza"; aile ve miras -> "aile" (her durumda);
icra ve diğer özel hukuk (kira, tüketici, iş, tazminat) -> "ozel". İdare, anayasa, vergi gibi alanlarda grup yoktur (kart çıkmaz)."""
import re

def _tr_kucuk(s): return s.replace("İ", "i").replace("I", "ı").lower()
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

def grup(baslik, etiketler=(), konular=()):
    """yazının inceleme grubu: "aile" | "ceza" | "ozel" | None"""
    _t = _tr_kucuk(baslik or ""); _h = _t + " | " + _tr_kucuk(" | ".join(etiketler or []))
    if "adli tatil" in _t: return None
    if "aile-hukuku" in (konular or ()) or _AILE_RE.search(_h): return "aile"
    if _UT_RE.search(_h) and not _CEZA_DEGIL.search(_t): return "ceza"
    if _ICRA_RE.search(_h) or _OZEL_RE.search(_h): return "ozel"
    return None
