import csv, os, re, sys

sys.dont_write_bytecode = True   # __pycache__ klasörü oluşmasın
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tez_ad import ayristir

# Kullanım: python3 dosyalardan_csv.py <klasor> [cikti.csv] [yok_tez_listesi.csv]
# Üçüncü argüman verilirse eşleşen tezlerin bilgileri (Türkçe karakterli) YÖK künyesinden alınır.

BASLIK = ["TezNo", "Adı Soyadı", "Yıl", "Üniversite", "Tür", "Dil", "Anabilim Dalı",
          "Danışman Unvan", "Danışman Ad Soyad", "2. Danışman Unvan", "2. Danışman Ad Soyad", "Dosya Adı"]
ETIKET = re.compile(r"(Yazar|Yıl|Tür|Dil|Konu|Yer Bilgisi|Danışman):\s*")
UNVAN_TR = re.compile(r"^((?:[^\W\d_]+\.\s*)+(?:ÜYESİ\s+)?)(.*)$")

def kunye_oku(yol):
    """YÖK CSV'sinden {tez_no: {alan: deger}} sözlüğü üretir."""
    sonuc = {}
    with open(yol, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            parcalar = ETIKET.split(r.get("Tez Künye Bilgisi", ""))
            alan = {parcalar[i]: parcalar[i + 1].strip(" |\n") for i in range(1, len(parcalar) - 1, 2)}
            yer = [x.strip() for x in alan.get("Yer Bilgisi", "").split(" / ")]
            u = UNVAN_TR.match(alan.get("Danışman", ""))
            sonuc[r["Tez No"].strip()] = {
                "Adı Soyadı": alan.get("Yazar", ""), "Yıl": alan.get("Yıl", ""),
                "Üniversite": yer[0] if yer else "", "Tür": alan.get("Tür", ""),
                "Dil": alan.get("Dil", ""), "Anabilim Dalı": yer[2] if len(yer) > 2 else "",
                "Danışman Unvan": u.group(1).strip() if u else "",
                "Danışman Ad Soyad": u.group(2).strip() if u else alan.get("Danışman", "")}
    return sonuc

def satir(a, dosya):
    d = (a["danismanlar"] + [("", ""), ("", "")])[:2]
    return {"TezNo": a["no"], "Adı Soyadı": a["yazar"], "Yıl": a["yil"], "Üniversite": a["uni"],
            "Tür": a["tur"], "Dil": a["dil"], "Anabilim Dalı": a["konu"],
            "Danışman Unvan": d[0][0], "Danışman Ad Soyad": d[0][1],
            "2. Danışman Unvan": d[1][0], "2. Danışman Ad Soyad": d[1][1], "Dosya Adı": dosya}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanım: python3 dosyalardan_csv.py <klasor> [cikti.csv] [yok_tez_listesi.csv]")
    klasor = sys.argv[1].strip().strip("'\"").replace("\\ ", " ")
    cikti = sys.argv[2] if len(sys.argv) > 2 else "doktora_tez_listesi.csv"
    kunye = kunye_oku(sys.argv[3].strip().strip("'\"").replace("\\ ", " ")) if len(sys.argv) > 3 else {}
    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")

    satirlar, ayrismayan, eslesen, bulunamayan = [], [], 0, []
    for ad in sorted(os.listdir(klasor)):
        if not ad.lower().endswith(".pdf") or ad.startswith("."):
            continue
        a = ayristir(ad)
        if a is None:
            ayrismayan.append(ad)
            continue
        s = satir(a, ad)
        if a["no"] in kunye:                 # YÖK künyesiyle düzelt (boş değerleri dosya adından bırak)
            s.update({k: v for k, v in kunye[a["no"]].items() if v})
            eslesen += 1
        elif kunye:
            bulunamayan.append(s)
        satirlar.append(s)

    with open(cikti, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BASLIK, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(satirlar)

    print(f"{len(satirlar)} dosya ayrıştırıldı -> {cikti}")
    if kunye:
        print(f"YÖK künyesiyle düzeltilen: {eslesen} | listede bulunamayan (dosya adındaki değerler kaldı): {len(bulunamayan)}")
    if kunye and bulunamayan:
        with open("kunyesi_bulunamayan.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["TezNo", "Adı Soyadı", "Yıl", "Üniversite", "Dosya Adı"],
                               delimiter=";", quoting=csv.QUOTE_ALL, extrasaction="ignore")
            w.writeheader()
            w.writerows(bulunamayan)
        print(f"YÖK listesinde olmayan tezler -> kunyesi_bulunamayan.csv ({len(bulunamayan)} satır)")
    if ayrismayan:
        print(f"Ayrıştırılamayan {len(ayrismayan)} dosya (CSV'ye eklenmedi):")
        for a in ayrismayan[:30]:
            print("  ", a)
