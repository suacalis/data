#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tezara PDF Toplu İndirici — v3
==============================
YÖK'ün gerçek akışı (örnek sayfadan çözüldü):
  1) TezGoster?key=...  -> görüntüleyici HTML; içinde ŞİFRELİ
        data-kayitno="..."  ve  data-tezno="..."  (düz Tez No değil)
  2) getTezPdf.jsp?kayitNo=<opak>&tezNo=<opak>  (jQuery GET, aynı oturum)
        -> asıl PDF bağlantısını içeren küçük HTML parçası
  3) O parçadaki bağlantıdan PDF indirilir.

Bu betik tam bu zinciri izler. İlk tez için hem görüntüleyici sayfasını
(_ornek_sayfa.html) hem getTezPdf parçasını (_ornek_pdf_parcasi.html) kaydeder;
sorun kalırsa ikincisini paylaş.

KULLANIM
--------
  pip install requests
  python tezara_pdf_indir_v3.py tezara_export.json
PDF'ler ./tezler/ içine
  {TezNo}_{Yazar}_{Yıl}_{Üniversite}_{TezTürü}_{Dil}_{AnaBilimDalı}_{Danışmanlar}.pdf
olarak iner (alanlar "_" ile, alan içi boşlukla; boş/[[[[Yok]]]] alanlar atlanır,
dosya adı 200 karakterde kırpılır),
tekrar çalıştırınca kaldığı yerden devam eder.
KENDİ bilgisayarında çalıştır (sunucuda 403 olası).

BİLGİ NOTU — v3.1 düzeltmesi (dosya adı)
----------------------------------------
SORUN
  Beklenen:  {TezNo}_{Yazar}_{Yıl}_{Üniversite}_{TezTürü}_{Dil}_{AnaBilimDalı}_{Danışmanlar}.pdf
  Üretilen:  18000_TURGAY_MERINC_1991_Gazi_Universitesi_Yuksek_Lisans_Turkce_PROF_DR_ALI_CUBUK.pdf
  -> {AnaBilimDalı} parçası hiç yok. Ayrıca Türkçe "ı" harfi sessizce siliniyordu.

NEDENLER
  1) Sütun adı eşleşmiyordu. Tezara/YÖK dışa aktarımında başlık çoğunlukla
     "Anabilim Dalı" (bitişik) olarak gelir; eski kod yalnızca "Ana Bilim Dalı",
     "Ana Bilim Dali", "anabilimDali" ... gibi BİREBİR adları arıyordu. Eşleşme
     olmayınca alan boş sayıldı ve "boş alanları atla" kuralı onu dosya adından
     düşürdü.
  2) slug() içindeki NFKD + ASCII dönüşümü, ayrıştırılamayan "ı" (noktasız i)
     harfini siliyordu: "Dalı" -> "Dal", "Kırıkkale" -> "Krkkale".

YAPILAN DEĞİŞİKLİKLER
  a) _anahtar(): sütun adlarını Türkçe harfleri katlayıp, küçük harfe çevirip,
     boşluk/altçizgi/noktalama silerek karşılaştırır. Böylece "Anabilim Dalı",
     "Ana Bilim Dalı", "ANABİLİM DALI", "anabilim_dali", "anaBilimDali" hepsi
     aynı sütun olarak bulunur. alan() önce birebir, sonra bu normalize adla
     arar. (Diğer tüm alanlar da bundan yararlanır.)
  b) Ana Bilim Dalı aday listesine "Anabilim Dalı", "ABD", "department",
     "Bölüm" eklendi.
  c) slug() artık önce Türkçe harfleri çevirir (ı->i, İ->I, ş->s, ğ->g, ç->c,
     ö->o, ü->u), sonra ASCII'ye indirger; hiçbir harf kaybolmaz.
  d) dosya_adi_uret(): adı üreten kod tek fonksiyonda toplandı. Sıra her zaman
     TezNo, Yazar, Yıl, Üniversite, TezTürü, Dil, AnaBilimDalı, Danışmanlar.
     200 karakter sınırı aşılırsa ÖNCE Danışmanlar kısaltılır; böylece Ana Bilim
     Dalı dahil önceki alanlar kesilmez.
  e) Kayıtlarda Ana Bilim Dalı hiç bulunamazsa betik başta uyarı verir ve
     dosyadaki gerçek sütun adlarını yazdırır (teşhis için).
  f) Eski sürümle inmiş (ABD'siz adlı) bir PDF varsa yeniden indirilmez;
     yeni ada taşınır (yeniden adlandırılır).

BİLGİ NOTU — v3.2 düzeltmesi (ayraç kuralı)
-------------------------------------------
SORUN
  v3.1 alanların İÇİNDEKİ boşlukları da "_" yapıyordu; bu yüzden alan sınırı
  belli olmuyordu ("TURGAY_MERINC" iki alan mı, tek alan mı?).

YENİ KURAL
  * Alanlar arasında "_", alan İÇİNDE boşluk (" ") kullanılır.
  * Noktalama (., ', ( ) vb.) boşluğa çevrilir, art arda boşluk teke indirilir.
  * Alan içindeki "_" karakteri boşluğa çevrilir (ayraçla karışmasın diye).
  * Danışmanlar: baştaki akademik unvan (Prof, Doç, Dr, Yrd, Öğr Üyesi, Arş Gör,
    Uzm ...) addan "_" ile ayrılır:  "PROF. DR. ALİ ÇUBUK" -> "PROF DR_ALI CUBUK".
    Birden çok danışman (";", ",", "/", "|" ile ayrılmış) yine "_" ile eklenir:
    "Doç. Dr. Mehmet Işık; Dr. Öğr. Üyesi Can Öz"
      -> "Doc Dr_Mehmet Isik_Dr Ogr Uyesi_Can Oz"
  * v3 ve v3.1 ile inmiş dosyalar (her yerde "_" olan adlar) bulunursa yeniden
    indirilmez, yeni ada taşınır.

SONUÇ (aynı kayıt için)
  v3   : 18000_TURGAY_MERINC_1991_Gazi_Universitesi_Yuksek_Lisans_Turkce_PROF_DR_ALI_CUBUK.pdf
  v3.2 : 18000_TURGAY MERINC_1991_Gazi Universitesi_Yuksek Lisans_Turkce_Isletme Anabilim Dali_PROF DR_ALI CUBUK.pdf
  (Ana Bilim Dalı kaydın kendisinde boşsa/[[[[Yok]]]] ise o parça atlanır.)
"""

import sys, os, re, csv, json, time, unicodedata
from urllib.parse import urljoin, urlparse, parse_qs

try:
    import requests
except ImportError:
    sys.exit("Önce paketi kur:  pip install requests")

CIKTI_KLASORU = "tezler"
BEKLEME_SN    = 2.0
ZAMAN_ASIMI   = 60
TARAYICI_UA   = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/124.0.0.0 Safari/537.36")
YOK_KOK       = "https://tez.yok.gov.tr/UlusalTezMerkezi/"
BOS_ISARET    = "[[[[Yok]]]]"


AD_SINIRI     = 200
# NFKD "ı"yı ayrıştıramaz ve ASCII'ye inerken siler; önce elle çeviriyoruz.
TR_HARF = str.maketrans("ıİşŞğĞçÇöÖüÜâÂîÎûÛ", "iIsSgGcCoOuUaAiIuU")


def _ascii(metin, tr=True):
    metin = str(metin)
    if tr:  # tr=False yalnızca v3'ün ("ı"yı silen) eski adlarını yeniden üretmek için
        metin = metin.translate(TR_HARF)
    metin = unicodedata.normalize("NFKD", metin)
    return metin.encode("ascii", "ignore").decode("ascii")


def slug(metin, uzunluk=60, bosluk=" ", tr=True):
    """Alanı dosya adına uygun ASCII metne çevirir; alan içindeki boşluklar korunur
    (bosluk=" "). Alanlar arası ayraç "_" olduğundan alan içinde "_" kullanılmaz."""
    if not metin:
        return ""
    metin = _ascii(metin, tr)
    metin = re.sub(r"[^A-Za-z0-9 _-]", " " if bosluk == " " else "", metin)
    if bosluk == " ":
        metin = metin.replace("_", " ")
    metin = re.sub(r"\s+", bosluk, metin.strip())
    return metin[:uzunluk].strip().rstrip("_-")


# Danışman adının başındaki akademik unvan sözcükleri (nokta/Türkçe harf temizlenmiş)
UNVANLAR = {"PROF", "DR", "DOC", "YRD", "YARD", "OGR", "UYESI", "GOR", "ARS",
            "UZM", "ASSOC", "ASST", "ASSIST", "PHD"}


def danisman_parcasi(metin, bosluk=" ", tr=True):
    """'PROF. DR. ALİ ÇUBUK' -> 'PROF DR_ALI CUBUK' (unvan ile ad '_' ile ayrılır).
    Birden çok danışman (; , / | ile ayrılmış) da '_' ile birleştirilir."""
    if not metin:
        return ""
    if bosluk != " ":                      # eski (v3/v3.1) biçim: her şey '_' ile
        return slug(metin, 10_000 if tr else 50, bosluk, tr)  # v3 danışmanı 50 karakterde kesiyordu
    sonuc = []
    for kisi in re.split(r"[;,/|\n]+", str(metin)):
        sozler = slug(kisi, 10_000).split()
        i = 0
        while i < len(sozler) and sozler[i].upper() in UNVANLAR:
            i += 1
        unvan, ad = " ".join(sozler[:i]), " ".join(sozler[i:])
        sonuc.append("_".join(x for x in (unvan, ad) if x))
    return "_".join(x for x in sonuc if x)


def _anahtar(ad):
    """Sütun adını karşılaştırma için sadeleştirir: 'Anabilim Dalı' == 'Ana Bilim Dali'."""
    return re.sub(r"[^a-z0-9]", "", _ascii(ad).lower())


def alan(kayit, *adaylar):
    def dolu(v):
        return v not in (None, "", BOS_ISARET) and str(v).strip() not in ("", BOS_ISARET)
    # 1) birebir ad
    for ad in adaylar:
        if ad in kayit and dolu(kayit[ad]):
            return str(kayit[ad]).strip()
    # 2) sadeleştirilmiş ad (büyük/küçük harf, boşluk, Türkçe karakter farkı yok)
    norm = {}
    for k, v in kayit.items():
        if isinstance(k, str):
            norm.setdefault(_anahtar(k), v)
    for ad in adaylar:
        v = norm.get(_anahtar(ad))
        if dolu(v):
            return str(v).strip()
    return ""


def kayitlari_oku(yol):
    with open(yol, "r", encoding="utf-8-sig") as f:
        icerik = f.read()
    ham = []
    if yol.lower().endswith(".json"):
        veri = json.loads(icerik)
        if isinstance(veri, dict):
            for k in ("theses", "data", "results", "items"):
                if isinstance(veri.get(k), list):
                    veri = veri[k]; break
        ham = veri if isinstance(veri, list) else [veri]
    else:
        ilk = icerik.splitlines()[0]
        ayirac = "\t" if "\t" in ilk else ","
        ham = list(csv.DictReader(icerik.splitlines(), delimiter=ayirac))
    kayitlar = []
    for k in ham:
        if not isinstance(k, dict):
            continue
        tezno = alan(k, "Tez No", "thesisId", "thesis_no", "tezNo", "id", "No")
        pdf   = alan(k, "PDF Linki", "PDF İndirme Linki", "pdfUrl", "pdf_link",
                        "pdfLink", "PDF Linki (varsa)")
        yazar = alan(k, "Yazar", "author", "authorName", "Yazar Adı")
        yil      = alan(k, "Yıl", "Yil", "year", "yil")
        uni      = alan(k, "Üniversite", "Universite", "university", "universite")
        tur      = alan(k, "Tez Türü", "Tez Turu", "thesisType", "tezTuru", "type")
        dil      = alan(k, "Dil", "language", "lang", "dil")
        abd      = alan(k, "Ana Bilim Dalı", "Anabilim Dalı", "Ana Bilim Dali",
                           "anabilimDali", "anaBilimDali", "ABD", "department",
                           "Bölüm")
        danisman = alan(k, "Danışmanlar", "Danismanlar", "Danışman", "advisor",
                           "advisors", "danisman")
        if not pdf:
            hepsi = " ".join(str(v) for v in k.values())
            m = re.search(r"https://tez\.yok\.gov\.tr/UlusalTezMerkezi/TezGoster\?[^\s\"']+", hepsi)
            if m:
                pdf = m.group(0)
        kayitlar.append({"tezno": tezno, "pdf": pdf, "yazar": yazar,
                         "yil": yil, "uni": uni, "tur": tur, "dil": dil,
                         "abd": abd, "danisman": danisman})
    if kayitlar and not any(k["abd"] for k in kayitlar):
        ilk = next((k for k in ham if isinstance(k, dict)), {})
        print("UYARI: Hiçbir kayıtta 'Ana Bilim Dalı' bulunamadı; dosya adında yer almayacak.")
        print("       Dosyadaki sütun adları:", ", ".join(map(str, ilk.keys())))
    return kayitlar


def dosya_adi_uret(tezno, k, abd_dahil=True, bosluk=" ", tr=True):
    """{TezNo}_{Yazar}_{Yıl}_{Üniversite}_{TezTürü}_{Dil}_{AnaBilimDalı}_{Danışmanlar}.pdf
    Alanlar '_' ile ayrılır, alan içindeki boşluklar korunur. bosluk="_" ve
    abd_dahil=False eski sürümlerin ürettiği adları verir (yeniden adlandırma için)."""
    parcalar = [
        slug(tezno, 30, bosluk, tr),
        slug(k["yazar"], 40, bosluk, tr),
        slug(k["yil"], 10, bosluk, tr),
        slug(k["uni"], 40, bosluk, tr),
        slug(k["tur"], 20, bosluk, tr),
        slug(k["dil"], 15, bosluk, tr),
        slug(k["abd"], 40, bosluk, tr) if abd_dahil else "",
    ]
    # boş (Yok) alanları atla, kalanları _ ile birleştir
    bas = "_".join(p for p in parcalar if p)
    # sınır aşılırsa yalnızca en sondaki Danışmanlar kısaltılır
    kalan = AD_SINIRI - len(bas) - 1
    dan = danisman_parcasi(k["danisman"], bosluk, tr)[:max(kalan, 0)].strip().rstrip("_-")
    govde = f"{bas}_{dan}" if dan else bas
    return govde[:AD_SINIRI].strip().rstrip("_-") + ".pdf"


def pdf_mi(resp):
    ct = resp.headers.get("Content-Type", "").lower()
    return resp.status_code == 200 and (resp.content[:4] == b"%PDF" or "application/pdf" in ct)


def parcadan_pdf_linkleri(html, taban_url):
    """getTezPdf.jsp parçasından ya da görüntüleyiciden olası PDF adreslerini toplar."""
    adaylar = []
    adaylar += re.findall(r'''(?:href|src|data|data-url|data-src)\s*=\s*["']([^"']+)["']''', html, re.I)
    # window.open('...') / location.href='...' gibi JS içindeki adresler
    adaylar += re.findall(r'''(?:window\.open|location\.href|open)\s*\(\s*["']([^"']+)["']''', html, re.I)
    # islem=pdfIndir içeren her şey
    adaylar += re.findall(r'''["'(]([^"'()\s]*islem=[^"'()\s]*)''', html, re.I)

    puanli = []
    gorulen = set()
    for a in adaylar:
        a = a.replace("&amp;", "&").strip()
        if not a or a.lower().startswith(("javascript:", "#", "mailto:")):
            continue
        tam = urljoin(taban_url, a)
        if "tez.yok.gov.tr" not in tam or tam in gorulen:
            continue
        gorulen.add(tam)
        s = tam.lower()
        # PDF olma ihtimaline göre sırala
        puan = 0
        if ".pdf" in s: puan += 5
        if "pdfindir" in s or "islem=pdf" in s: puan += 4
        if "gettezpdf" in s: puan += 2
        if "tezgoster" in s: puan += 1
        puanli.append((puan, tam))
    puanli.sort(reverse=True)
    return [t for _, t in puanli]


def tezi_indir(s, kayit, ornek):
    key_url = kayit["pdf"]

    # 1) görüntüleyici sayfası
    try:
        r = s.get(key_url, timeout=ZAMAN_ASIMI)
    except Exception as e:
        return None, f"istek hatası: {e}"
    if pdf_mi(r):
        return r.content, None
    html = r.content.decode("utf-8", "ignore")

    if ornek["sayfa"]:
        _yaz("_ornek_sayfa.html", html); ornek["sayfa"] = False

    if "Geçersiz" in html:
        return None, "key geçersiz (Tezara'da aramayı yenile)"
    if "bulunamadı" in html.lower() and "result-card" not in html:
        return None, "kayıt bulunamadı"

    m_k = re.search(r'data-kayitno\s*=\s*"([^"]+)"', html)
    m_t = re.search(r'data-tezno\s*=\s*"([^"]+)"', html)
    if not (m_k and m_t):
        return None, "kayitno/tezno bulunamadı (yapı değişmiş olabilir)"
    kayitNo, tezNo = m_k.group(1), m_t.group(1)

    # 2) getTezPdf.jsp — asıl PDF bağlantısını veren parça
    pdf_jsp = urljoin(key_url, "getTezPdf.jsp")
    try:
        r2 = s.get(pdf_jsp, params={"kayitNo": kayitNo, "tezNo": tezNo},
                   headers={"Referer": key_url, "X-Requested-With": "XMLHttpRequest"},
                   timeout=ZAMAN_ASIMI)
    except Exception as e:
        return None, f"getTezPdf hatası: {e}"

    if pdf_mi(r2):
        return r2.content, None
    parca = r2.content.decode("utf-8", "ignore")

    if ornek["parca"]:
        _yaz("_ornek_pdf_parcasi.html", parca); ornek["parca"] = False

    # 3) parçadaki (yoksa görüntüleyicideki) bağlantılardan PDF çek
    linkler = parcadan_pdf_linkleri(parca, pdf_jsp) or parcadan_pdf_linkleri(html, key_url)
    for aday in linkler:
        try:
            r3 = s.get(aday, headers={"Referer": key_url}, timeout=ZAMAN_ASIMI)
            if pdf_mi(r3):
                return r3.content, None
        except Exception:
            continue

    if not linkler:
        return None, "getTezPdf parçasında bağlantı yok (parçayı paylaş)"
    return None, "bağlantılar PDF vermedi (parçayı paylaş)"


def _yaz(ad, icerik):
    try:
        with open(os.path.join(CIKTI_KLASORU, ad), "w", encoding="utf-8") as f:
            f.write(icerik)
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        sys.exit("Kullanım:  python tezara_pdf_indir_v3.py <tezara_export.json|.csv>")
    girdi = sys.argv[1]
    if not os.path.exists(girdi):
        sys.exit(f"Dosya bulunamadı: {girdi}")

    kayitlar = kayitlari_oku(girdi)
    linkli = [k for k in kayitlar if k["pdf"].startswith("http")]
    print(f"Toplam kayıt: {len(kayitlar)} | PDF linki olan: {len(linkli)} "
          f"| linki olmayan: {len(kayitlar) - len(linkli)}")

    os.makedirs(CIKTI_KLASORU, exist_ok=True)
    s = requests.Session()
    s.headers.update({
        "User-Agent": TARAYICI_UA,
        "Referer": YOK_KOK,
        "Accept": "text/html,application/pdf,*/*",
        "Accept-Language": "tr-TR,tr;q=0.9",
    })
    try:
        s.get(YOK_KOK, timeout=ZAMAN_ASIMI)
    except Exception as e:
        print(f"UYARI: YÖK ana sayfası açılamadı ({e}).")

    ornek = {"sayfa": True, "parca": True}
    basarili = atlanan = basarisiz = 0
    hatalar = []

    for i, k in enumerate(linkli, 1):
        tezno = k["tezno"] or f"kayit{i}"
        # {TezNo}_{Yazar}_{Yıl}_{Üniversite}_{Tez Türü}_{Dil}_{Ana Bilim Dalı}_{Danışmanlar}
        ad = dosya_adi_uret(tezno, k)
        hedef = os.path.join(CIKTI_KLASORU, ad)
        if os.path.exists(hedef) and os.path.getsize(hedef) > 1000:
            atlanan += 1
            continue
        # eski sürümlerle (v3: '_'li ve ABD'siz, v3.1: '_'li) inmiş dosya varsa yeni ada taşı
        eskiler = [os.path.join(CIKTI_KLASORU, dosya_adi_uret(tezno, k, abd, "_", tr))
                   for abd, tr in ((False, False), (True, True))]
        eski = next((e for e in eskiler if e != hedef and os.path.exists(e)
                     and os.path.getsize(e) > 1000), None)
        if eski:
            os.replace(eski, hedef)
            print(f"[{i}/{len(linkli)}] {tezno} — yeniden adlandırıldı -> {ad}")
            atlanan += 1
            continue

        print(f"[{i}/{len(linkli)}] {tezno} — {k['yazar'][:38]} ... ", end="", flush=True)
        govde, hata = tezi_indir(s, k, ornek)
        if govde:
            with open(hedef, "wb") as f:
                f.write(govde)
            print(f"OK ({len(govde)//1024} KB)")
            basarili += 1
        else:
            print(f"BAŞARISIZ [{hata}]")
            hatalar.append({"tezno": tezno, "yazar": k["yazar"],
                            "pdf": k["pdf"], "neden": hata})
            basarisiz += 1
        time.sleep(BEKLEME_SN)

    if hatalar:
        hyol = os.path.join(CIKTI_KLASORU, "_basarisiz.csv")
        with open(hyol, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["tezno", "yazar", "pdf", "neden"])
            w.writeheader(); w.writerows(hatalar)
        print(f"\nBaşarısızlar: {hyol}")

    print(f"\nBitti. İnen: {basarili} | Zaten vardı: {atlanan} | Başarısız: {basarisiz}")
    print(f"PDF'ler: ./{CIKTI_KLASORU}/")
    if basarisiz:
        print("Sorun sürerse tezler/_ornek_pdf_parcasi.html dosyasını paylaş.")


if __name__ == "__main__":
    main()
