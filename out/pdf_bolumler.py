import csv, os, re, sys

sys.dont_write_bytecode = True

# Kullanım:
#   python3 pdf_bolumler.py <pdf_veya_klasor> [cikti_klasoru] [--yontem otomatik|toc|baslik] [--seviye N] [--yeniden]
#   (python3 pdf_bolumler.py -h ile yardım)
#
# Her PDF için <cikti_klasoru>/<pdf adı>/ altına bölüm başına bir .txt yazar (00_..., 01_ÖZET, 02_GİRİŞ ...).
# Yöntem 1 (toc)   : PDF'in yer imleri / içindekiler (bookmark) bilgisi varsa onu kullanır. En güvenilir olan budur.
# Yöntem 2 (baslik): Yer imi yoksa sayfa metnindeki başlıkları (ÖZET, GİRİŞ, ... BÖLÜM, KAYNAKÇA) arar.
# Metin katmanı olmayan (taranmış) PDF'ler atlanır ve raporlanır; bunlar için önce OCR gerekir.
try:
    import pymupdf
except ImportError:
    sys.exit("pymupdf gerekli: pip3 install pymupdf")

TR = str.maketrans("İıŞşĞğÜüÖöÇç", "IiSsGgUuOoCc")

def norm(s):
    return re.sub(r"\s+", " ", s.translate(TR).upper()).strip()

BILINEN = ["OZET", "ABSTRACT", "ONSOZ", "TESEKKUR", "ICINDEKILER", "TABLOLAR LISTESI", "SEKILLER LISTESI",
           "TABLOLAR DIZINI", "SEKILLER DIZINI", "KISALTMALAR", "SIMGELER VE KISALTMALAR", "KISALTMALAR LISTESI",
           "GIRIS", "YONTEM", "ARASTIRMA YONTEMI", "BULGULAR", "TARTISMA", "BULGULAR VE TARTISMA",
           "SONUC", "SONUC VE ONERILER", "KAYNAKCA", "KAYNAKLAR", "EKLER", "EK", "OZGECMIS"]
BILINEN_RE = re.compile(r"^(?:(?:\d{1,2}|[IVX]{1,4})[\.\)]?\s+)?(?:" + "|".join(BILINEN) + r")$")
BOLUM_RE = re.compile(r"^(?:(?:BIRINCI|IKINCI|UCUNCU|DORDUNCU|BESINCI|ALTINCI|YEDINCI|SEKIZINCI|DOKUZUNCU|ONUNCU)"
                      r"\s+BOLUM|BOLUM\s+\d+|\d+\.?\s*BOLUM)\b")
NUMARALI_RE = re.compile(r"^\d{1,2}\.?\s+[A-Z][A-Z ,\-/&']{3,80}$")      # "2. KAVRAMSAL CERCEVE" (üst düzey)
ICINDEKILER_SATIRI = re.compile(r"(?:\.{3,}|…|\s{3,})\s*\d{1,3}\s*$")

def satirlari_oku(doc):
    """[(sayfa_no, satir_metni)] listesi döndürür (sayfa_no 1'den başlar)."""
    satirlar = []
    for i, sayfa in enumerate(doc, start=1):
        for s in sayfa.get_text("text").splitlines():
            s = s.rstrip()
            satirlar.append((i, s))
    return satirlar

def toc_sayfalari(satirlar):
    """İçindekiler sayfalarını (başlık adayı çıkarılmayacak sayfalar) bulur."""
    sayac = {}
    for sayfa, s in satirlar:
        if ICINDEKILER_SATIRI.search(s):
            sayac[sayfa] = sayac.get(sayfa, 0) + 1
    return {p for p, n in sayac.items() if n >= 5}

def baslik_yontemi(satirlar):
    atla = toc_sayfalari(satirlar)
    adaylar = []
    for idx, (sayfa, s) in enumerate(satirlar):
        n = norm(s)
        if not n or len(n) > 90 or sayfa in atla or ICINDEKILER_SATIRI.search(s):
            continue
        if BILINEN_RE.match(n) or BOLUM_RE.match(n) or (NUMARALI_RE.match(n) and s.strip() == s.strip().upper()):
            ad = s.strip()
            if BOLUM_RE.match(n):                      # "BİRİNCİ BÖLÜM" + sonraki dolu satır = başlık
                for _, sonraki in satirlar[idx + 1: idx + 4]:
                    if sonraki.strip():
                        if len(sonraki.strip()) < 90 and sonraki.strip() == sonraki.strip().upper():
                            ad += " " + sonraki.strip()
                        break
            adaylar.append((idx, ad, n))
    tekrar = {}
    for _, _, n in adaylar:
        tekrar[n] = tekrar.get(n, 0) + 1
    # Sayfa üstbilgisi gibi çok tekrar eden satırları ele
    return [(i, ad) for i, ad, n in adaylar if tekrar[n] <= 3]

def toc_yontemi(doc, satirlar, seviye):
    toc = [t for t in doc.get_toc(simple=True) if t[0] <= seviye and t[2] >= 1]
    if not 3 <= len(toc) <= 60:
        return None
    ilk_satir = {}
    for idx, (sayfa, _) in enumerate(satirlar):
        ilk_satir.setdefault(sayfa, idx)
    basliklar, son = [], -1
    for _, baslik, sayfa in toc:
        if sayfa not in ilk_satir:
            continue
        hedef = norm(baslik)[:30]
        idx = ilk_satir[sayfa]
        sonraki = ilk_satir.get(sayfa + 1, len(satirlar))
        for j in range(ilk_satir[sayfa], sonraki):          # başlığı sayfa içinde bul
            if hedef and norm(satirlar[j][1]).startswith(hedef[:20]):
                idx = j
                break
        idx = max(idx, son)
        if basliklar and idx == basliklar[-1][0]:
            basliklar[-1] = (idx, baslik.strip())
        else:
            basliklar.append((idx, baslik.strip()))
        son = idx
    return basliklar if len(basliklar) >= 3 else None

def guvenli(ad, uzunluk=60):
    ad = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", ad)
    return re.sub(r"\s+", " ", ad).strip(" .")[:uzunluk] or "bolum"

def isle(pdf_yolu, cikti_kok, yontem, seviye):
    doc = pymupdf.open(pdf_yolu)
    satirlar = satirlari_oku(doc)
    karakter = sum(len(s) for _, s in satirlar)
    if doc.page_count == 0 or karakter / doc.page_count < 50:
        return "metin yok (taranmış, OCR gerekli)", 0
    basliklar, kullanilan = None, ""
    if yontem in ("otomatik", "toc"):
        basliklar, kullanilan = toc_yontemi(doc, satirlar, seviye), "toc"
    if not basliklar and yontem in ("otomatik", "baslik"):
        basliklar, kullanilan = baslik_yontemi(satirlar), "baslik"
    if not basliklar:
        return "bölüm bulunamadı", 0

    hedef = os.path.join(cikti_kok, guvenli(os.path.splitext(os.path.basename(pdf_yolu))[0], 120))
    os.makedirs(hedef, exist_ok=True)
    sinirlar = [(0, "On Kisim")] + basliklar if basliklar[0][0] > 0 else basliklar
    n = 0
    for k, (bas, ad) in enumerate(sinirlar):
        son = sinirlar[k + 1][0] if k + 1 < len(sinirlar) else len(satirlar)
        metin = "\n".join(s for _, s in satirlar[bas:son]).strip()
        if not metin:
            continue
        n += 1
        with open(os.path.join(hedef, f"{n:02d}_{guvenli(ad)}.txt"), "w", encoding="utf-8") as f:
            f.write(metin + "\n")
    return f"tamam ({kullanilan})", n

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="PDF'leri bölümlerine ayırıp her bölümü ayrı .txt olarak yazar.")
    ap.add_argument("kaynak", help="PDF dosyası ya da PDF klasörü")
    ap.add_argument("cikti", nargs="?", default="tez_bolumleri", help="çıktı klasörü (varsayılan: tez_bolumleri)")
    ap.add_argument("--yontem", choices=["otomatik", "toc", "baslik"], default="otomatik")
    ap.add_argument("--seviye", type=int, default=1, help="yer imlerinde kullanılacak en derin seviye (varsayılan 1)")
    ap.add_argument("--yeniden", action="store_true", help="çıktısı olan PDF'leri de yeniden işle")
    o = ap.parse_args()
    yontem, seviye, cikti, yeniden = o.yontem, o.seviye, o.cikti, o.yeniden
    kaynak = o.kaynak.strip().strip("'\"").replace("\\ ", " ")
    if os.path.isdir(kaynak):
        pdfler = sorted(os.path.join(kaynak, f) for f in os.listdir(kaynak)
                        if f.lower().endswith(".pdf") and not f.startswith("."))
    elif os.path.isfile(kaynak):
        pdfler = [kaynak]
    else:
        sys.exit(f"Bulunamadı: {kaynak}")
    os.makedirs(cikti, exist_ok=True)

    rapor = []
    for i, p in enumerate(pdfler, start=1):
        ad = os.path.basename(p)
        hedef = os.path.join(cikti, guvenli(os.path.splitext(ad)[0], 120))
        if os.path.isdir(hedef) and not yeniden:
            durum, n = "atlandı (çıktı zaten var)", 0
        else:
            try:
                durum, n = isle(p, cikti, yontem, seviye)
            except Exception as e:                      # bozuk PDF tüm işi durdurmasın
                durum, n = f"hata: {e}", 0
        print(f"[{i}/{len(pdfler)}] {ad[:70]} -> {durum} ({n} bölüm)")
        rapor.append([ad, durum, n])
    with open(os.path.join(cikti, "bolum_ozeti.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Dosya Adı", "Durum", "Bölüm Sayısı"])
        w.writerows(rapor)
    print(f"\nÖzet: {cikti}/bolum_ozeti.csv")
