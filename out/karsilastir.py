import csv, os, re, shutil, sys

# Kullanım: python3 karsilastir.py [csv_yolu] [pdf_klasoru]
# Argüman verilmezse yollar sorulur (dosyayı Terminal'e sürükleyip bırakabilirsiniz).
def temiz(yol):
    return yol.strip().strip("'\"").replace("\\ ", " ")

if len(sys.argv) > 1:
    CSV_YOLU = temiz(sys.argv[1])
else:
    CSV_YOLU = temiz(input("CSV dosyasının yolu: "))

if len(sys.argv) > 2:
    PDF_KLASOR = temiz(sys.argv[2])
else:
    PDF_KLASOR = temiz(input("PDF klasörü [Enter = /Volumes/toshiba2023/ceko_tezler_son]: ")) \
        or "/Volumes/toshiba2023/ceko_tezler_son"

for yol, ad in ((CSV_YOLU, "CSV dosyası"), (PDF_KLASOR, "PDF klasörü")):
    if not os.path.exists(yol):
        sys.exit(f"{ad} bulunamadı: {yol}")

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

# --- Eşleşen (var) PDF'leri başka klasöre taşı / kopyala ---
dosyalar = [ad for no in sorted(var) for ad in pdf_no[no]]
print(f"\nEşleşen PDF dosyası sayısı: {len(dosyalar)}")
hedef = temiz(input("Eşleşenlerin gideceği klasör (boş bırakırsanız işlem yapılmaz): "))
if hedef:
    mod = input("[T]aşı mı [K]opyala mı? (t/k, varsayılan k): ").strip().lower() or "k"
    os.makedirs(hedef, exist_ok=True)
    islem = shutil.move if mod == "t" else shutil.copy2
    atlanan = 0
    for ad in dosyalar:
        hedef_yol = os.path.join(hedef, ad)
        if os.path.exists(hedef_yol):
            atlanan += 1
            continue
        islem(os.path.join(PDF_KLASOR, ad), hedef_yol)
    print(f"{len(dosyalar) - atlanan} dosya {'taşındı' if mod == 't' else 'kopyalandı'}, "
          f"{atlanan} dosya hedefte zaten olduğu için atlandı. Hedef: {hedef}")
