import csv, os, re, sys

# Kullanım: python3 karsilastir.py <csv_yolu> [pdf_klasoru]
CSV_YOLU = sys.argv[1]
PDF_KLASOR = sys.argv[2] if len(sys.argv) > 2 else "/Volumes/toshiba2023/ceko_tezler_son"

with open(CSV_YOLU, encoding="utf-8-sig", newline="") as f:
    okuyucu = csv.DictReader(f, delimiter=";")
    alanlar = okuyucu.fieldnames
    satirlar = list(okuyucu)
csv_no = {r["Tez No"].strip() for r in satirlar}

pdf_no = {}
for ad in os.listdir(PDF_KLASOR):
    if ad.lower().endswith(".pdf") and not ad.startswith("."):
        no = ad.split("_", 1)[0].strip()
        if re.fullmatch(r"\d+", no):
            pdf_no.setdefault(no, []).append(ad)

var = csv_no & pdf_no.keys()
yok = csv_no - pdf_no.keys()
fazla = pdf_no.keys() - csv_no

print(f"CSV'deki tez sayısı          : {len(csv_no)}")
print(f"Klasördeki PDF (benzersiz no): {len(pdf_no)}")
print(f"Her ikisinde olan (var)      : {len(var)}")
print(f"CSV'de olup PDF'i olmayan    : {len(yok)}")
print(f"PDF'i olup CSV'de olmayan    : {len(fazla)}")

with open("eksik_tezler.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=alanlar, delimiter=";", quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(r for r in satirlar if r["Tez No"].strip() in yok)

with open("eksik_tez_no.txt", "w") as f:
    f.write("\n".join(sorted(yok)))
print("Yazıldı: eksik_tezler.csv, eksik_tez_no.txt")
