"""Tez PDF dosya adlarını ayrıştırır ve standart biçimde yeniden kurar.

Ayrıştırma "_" ya da boşluğa bakmaz, sözcüklere bakar; bu yüzden eski (alt çizgili),
yeni (boşluklu) ve karışık adların hepsi okunur.
"""
import re
import sys

sys.dont_write_bytecode = True

ONEK = "tasi_"
TURLER = {("DOKTORA",): "Doktora", ("YUKSEK", "LISANS"): "Yuksek Lisans",
          ("TIPTA", "UZMANLIK"): "Tipta Uzmanlik", ("SANATTA", "YETERLIK"): "Sanatta Yeterlik",
          ("DIS", "HEKIMLIGI", "UZMANLIK"): "Dis Hekimligi Uzmanlik", ("UZMANLIK",): "Uzmanlik"}
# Danışman unvanları (uzundan kısaya) ve standart yazımları
UNVANLAR = [(("YRD", "DOC", "DR"), "YRD DOC DR"), (("YRD", "DOC"), "YRD DOC"),
            (("DR", "OGR", "UYESI"), "DR OGR UYESI"), (("DR", "OGRETIM", "UYESI"), "DR OGRETIM UYESI"),
            (("OGR", "GOR", "DR"), "OGR GOR DR"), (("ARS", "GOR", "DR"), "ARS GOR DR"),
            (("PROF", "DR"), "PROF DR"), (("DOC", "DR"), "DOC DR"),
            (("PROFDR",), "PROF DR"), (("DOCDR",), "DOC DR"), (("YDOCDR",), "YRD DOC DR"),
            (("YDOC",), "YRD DOC"), (("PROF",), "PROF"), (("DOC",), "DOC"), (("DR",), "DR")]
YIL = re.compile(r"^(?:19|20)\d\d$")


def _unvan_at(kelimeler, i):
    """i konumunda unvan varsa (uzunluk, standart_yazım) döndürür."""
    for dizi, standart in UNVANLAR:
        if tuple(k.upper() for k in kelimeler[i:i + len(dizi)]) == dizi:
            return len(dizi), standart
    return None


def _danismanlar(kelimeler):
    sonuc, i = [], 0
    while i < len(kelimeler):
        u = _unvan_at(kelimeler, i)
        unvan = ""
        if u:
            unvan, i = u[1], i + u[0]
        ad = []
        while i < len(kelimeler) and not _unvan_at(kelimeler, i):
            ad.append(kelimeler[i])
            i += 1
        if unvan or ad:
            sonuc.append((unvan, " ".join(ad)))
    return sonuc


def ayristir(dosya_adi):
    """Dosya adından alanları sözlük olarak döndürür; ayrıştırılamazsa None."""
    govde = dosya_adi[:-4] if dosya_adi.lower().endswith(".pdf") else dosya_adi
    onek = govde.startswith(ONEK)
    if onek:
        govde = govde[len(ONEK):]
    kelimeler = [k for k in re.split(r"[_ ]+", govde.replace("__", "_|_")) if k]
    if not kelimeler or not kelimeler[0].isdigit():
        return None
    yil_i = next((i for i in range(2, len(kelimeler)) if YIL.match(kelimeler[i])), None)
    if yil_i is None:
        return None
    tur_i = tur = None
    for i in range(yil_i + 1, len(kelimeler)):
        for dizi, standart in TURLER.items():
            if tuple(k.upper() for k in kelimeler[i:i + len(dizi)]) == dizi:
                tur_i, tur, tur_uz = i, standart, len(dizi)
                break
        if tur:
            break
    if tur is None or tur_i + tur_uz >= len(kelimeler):
        return None
    dil = kelimeler[tur_i + tur_uz]
    kuyruk = kelimeler[tur_i + tur_uz + 1:]
    if "|" in kuyruk:                                   # "__" ile ayrılmış
        b = kuyruk.index("|")
        konu, dan_k = kuyruk[:b], kuyruk[b + 1:]
    else:
        b = next((i for i in range(len(kuyruk)) if _unvan_at(kuyruk, i)), None)
        konu, dan_k = (kuyruk, []) if b is None else (kuyruk[:b], kuyruk[b:])
    return {"no": kelimeler[0], "yazar": " ".join(kelimeler[1:yil_i]), "yil": kelimeler[yil_i],
            "uni": " ".join(kelimeler[yil_i + 1:tur_i]), "tur": tur, "dil": dil,
            "konu": " ".join(konu), "danismanlar": _danismanlar(dan_k), "onek": onek}


def kur(a):
    """Ayrıştırılmış alanlardan standart dosya adını üretir."""
    parca = [a["no"], a["yazar"], a["yil"], a["uni"], a["tur"], a["dil"]]
    if a["konu"]:
        parca.append(a["konu"])
    for unvan, ad in a["danismanlar"]:
        parca += [p for p in (unvan, ad) if p]
    return (ONEK if a["onek"] else "") + "_".join(parca) + ".pdf"
