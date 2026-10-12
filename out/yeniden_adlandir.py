import csv, os, sys
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tez_ad import ayristir, kur

# Kullanım: python3 yeniden_adlandir.py <klasor> [--uygula]
# --uygula verilmezse yalnızca ne yapılacağı gösterilir (deneme çalıştırması).
# Standart biçim: TezNo_Ad Soyad_Yıl_Üniversite_Tür_Dil_Konu_Unvan_Danışman Ad Soyad[_Unvan2_Danışman2]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanım: python3 yeniden_adlandir.py <klasor> [--uygula]")
    klasor = sys.argv[1].strip().strip("'\"").replace("\\ ", " ")
    uygula = "--uygula" in sys.argv
    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")

    degisecek, uymayan, belirsiz, ayni = [], [], [], 0
    for ad in sorted(os.listdir(klasor)):
        if not ad.lower().endswith(".pdf") or ad.startswith("."):
            continue
        alanlar = ayristir(ad)
        if alanlar is None:
            uymayan.append(ad)
            continue
        yeni = kur(alanlar)
        if kur(ayristir(yeni)) != yeni:      # dönüşüm kararlı değilse dokunma
            belirsiz.append(ad)
        elif yeni == ad:
            ayni += 1
        else:
            degisecek.append((ad, yeni))

    sayac = {}
    for _, y in degisecek:
        sayac[y] = sayac.get(y, 0) + 1
    cakisan = [(a, y) for a, y in degisecek if sayac[y] > 1 or os.path.exists(os.path.join(klasor, y))]
    uygun = [(a, y) for a, y in degisecek if (a, y) not in cakisan]

    print(f"Değişecek: {len(uygun)} | Zaten uygun: {ayni} | Kalıba uymayan: {len(uymayan)} | "
          f"Belirsiz: {len(belirsiz)} | Çakışan: {len(cakisan)}")
    for a, y in uygun[:5]:
        print(f"  {a}\n  -> {y}\n")
    for baslik, liste in (("Kalıba uymayan dosyalar (dokunulmadı):", uymayan),
                          ("Belirsiz dosyalar (dokunulmadı):", belirsiz)):
        if liste:
            print(baslik)
            for a in liste[:20]:
                print("  ", a)
    if cakisan:
        print("Çakışan dosyalar (dokunulmadı):")
        for a, y in cakisan[:20]:
            print("  ", a, "->", y)

    if uygula:
        gunluk = f"yeniden_adlandirma_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(gunluk, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["eski_ad", "yeni_ad"])
            for a, y in uygun:
                os.rename(os.path.join(klasor, a), os.path.join(klasor, y))
                w.writerow([a, y])
        print(f"\n{len(uygun)} dosya yeniden adlandırıldı. Geri alma kaydı: {gunluk}")
    else:
        print("\nDeneme çalıştırması: hiçbir dosya değiştirilmedi. Uygulamak için sonuna --uygula ekleyin.")
