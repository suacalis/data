import csv, os, sys

# Kullanım: python3 dosyalardan_csv.py <klasor> [cikti.csv]
# Hem eski (alt çizgili) hem yeni (boşluklu) dosya adı biçimini okur.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yeniden_adlandir import DESEN, UNVAN, bosluk, YENI

BASLIK = ["TezNo", "Adı Soyadı", "Yıl", "Üniversite", "Tür", "Dil",
          "Anabilim Dalı", "Danışman Unvan", "Danışman Ad Soyad", "Dosya Adı"]

def ayristir(ad):
    if YENI.match(ad):                      # yeni biçim: 9 alan, "_" ile ayrılmış
        p = ad[:-4].split("_")
        if len(p) == 9:
            return p + [ad]
    m = DESEN.match(ad)                     # eski biçim
    if m:
        g = m.groupdict()
        u = UNVAN.match(g["danisman"])
        unvan, isim = (bosluk(u["unvan"]), bosluk(u["ad"])) if u else ("", bosluk(g["danisman"]))
        return [g["no"], bosluk(g["yazar"]), g["yil"], bosluk(g["uni"]), g["tur"].replace("_", " "),
                g["dil"], bosluk(g["konu"]), unvan, isim, ad]
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanım: python3 dosyalardan_csv.py <klasor> [cikti.csv]")
    klasor = sys.argv[1].strip().strip("'\"").replace("\\ ", " ")
    cikti = sys.argv[2] if len(sys.argv) > 2 else "doktora_tez_listesi.csv"
    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")

    satirlar, ayrismayan = [], []
    for ad in sorted(os.listdir(klasor)):
        if not ad.lower().endswith(".pdf") or ad.startswith("."):
            continue
        s = ayristir(ad)
        (satirlar if s else ayrismayan).append(s or ad)

    with open(cikti, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(BASLIK)
        w.writerows(satirlar)

    print(f"{len(satirlar)} dosya ayrıştırıldı -> {cikti}")
    if ayrismayan:
        print(f"Ayrıştırılamayan {len(ayrismayan)} dosya (CSV'ye eklenmedi):")
        for a in ayrismayan[:30]:
            print("  ", a)
