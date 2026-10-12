import csv, os, re, sys

sys.dont_write_bytecode = True   # __pycache__ klasörü oluşmasın

# Kullanım: python3 dosyalardan_csv.py <klasor> [cikti.csv] [yok_tez_listesi.csv]
# Üçüncü argüman verilirse eşleşen tezlerin bilgileri (Türkçe karakterli) YÖK künyesinden alınır.
# Hem eski (alt çizgili) hem yeni (boşluklu) dosya adı biçimini okur.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yeniden_adlandir import DESEN, UNVAN, bosluk, YENI

BASLIK = ["TezNo", "Adı Soyadı", "Yıl", "Üniversite", "Tür", "Dil",
          "Anabilim Dalı", "Danışman Unvan", "Danışman Ad Soyad", "Dosya Adı"]

ETIKET = re.compile(r"(Yazar|Yıl|Tür|Dil|Konu|Yer Bilgisi|Danışman):\s*")
UNVAN_TR = re.compile(r"^((?:[^\W\d_]+\.\s*)+(?:ÜYESİ\s+)?)(.*)$")

def kunye_oku(yol):
    """YÖK CSV'sinden {tez_no: {alan: deger}} sözlüğü üretir."""
    sonuc = {}
    with open(yol, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            metin = r.get("Tez Künye Bilgisi", "")
            parcalar = ETIKET.split(metin)          # ['', 'Yazar', 'X | ', 'Yıl', ...]
            alan = {parcalar[i]: parcalar[i + 1].strip(" |\n") for i in range(1, len(parcalar) - 1, 2)}
            yer = [x.strip() for x in alan.get("Yer Bilgisi", "").split(" / ")]
            u = UNVAN_TR.match(alan.get("Danışman", ""))
            sonuc[r["Tez No"].strip()] = {
                "Adı Soyadı": alan.get("Yazar", ""), "Yıl": alan.get("Yıl", ""),
                "Üniversite": yer[0] if yer else "", "Tür": alan.get("Tür", ""),
                "Dil": alan.get("Dil", ""), "Anabilim Dalı": yer[2] if len(yer) > 2 else "",
                "Danışman Unvan": u.group(1).strip() if u else "",
                "Danışman Ad Soyad": u.group(2).strip() if u else alan.get("Danışman", ""),
                "Konu": alan.get("Konu", "")}
    return sonuc

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
    kunye = kunye_oku(sys.argv[3].strip().strip("'\"").replace("\\ ", " ")) if len(sys.argv) > 3 else {}
    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")

    satirlar, ayrismayan, eslesen = [], [], 0
    for ad in sorted(os.listdir(klasor)):
        if not ad.lower().endswith(".pdf") or ad.startswith("."):
            continue
        s = ayristir(ad)
        if s and s[0] in kunye:             # YÖK künyesiyle düzelt
            k = kunye[s[0]]
            s = [s[0]] + [k[b] or s[i] for i, b in enumerate(BASLIK[1:9], start=1)] + [s[9]]
            eslesen += 1
        (satirlar if s else ayrismayan).append(s or ad)

    with open(cikti, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(BASLIK)
        w.writerows(satirlar)

    print(f"{len(satirlar)} dosya ayrıştırıldı -> {cikti}")
    if kunye:
        print(f"YÖK künyesiyle düzeltilen: {eslesen} | listede bulunamayan (dosya adındaki değerler kaldı): {len(satirlar) - eslesen}")
    if ayrismayan:
        print(f"Ayrıştırılamayan {len(ayrismayan)} dosya (CSV'ye eklenmedi):")
        for a in ayrismayan[:30]:
            print("  ", a)
