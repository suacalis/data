import csv, os, re, sys
from datetime import datetime

# Kullanım: python3 yeniden_adlandir.py <klasor> [--uygula]
# --uygula verilmezse yalnızca ne yapılacağı gösterilir (deneme çalıştırması).

TUR = r"(?:Doktora|Yuksek_Lisans|Tipta_Uzmanlik|Sanatta_Yeterlik|Dis_Hekimligi_Uzmanlik|Uzmanlik)"
# Konu ile danışmanı ayıran sınır: "__" ya da hemen ardından bir unvan gelen "_"
AYRAC = (r"(?:__|_(?=(?:PROF_DR|DOC_DR|DR_OGR_UYESI|DR_OGRETIM_UYESI|OGR_GOR_DR|ARS_GOR_DR)_)"
         r"|(?<=Dal)_(?=DR_))")
DESEN = re.compile(
    rf"^(?P<no>\d+)_(?P<yazar>.+?)_(?P<yil>(?:19|20)\d\d)_(?P<uni>.+?)_(?P<tur>{TUR})_"
    r"(?P<dil>[^_]+)_(?P<konu>.+?)" + AYRAC + r"(?P<danisman>.+)\.pdf$", re.IGNORECASE)
UNVAN = re.compile(r"^(?P<unvan>PROF_DR|DOC_DR|DR_OGR_UYESI|DR_OGRETIM_UYESI|OGR_GOR_DR|ARS_GOR_DR|PROF|DOC|DR)_(?P<ad>.+)$",
                   re.IGNORECASE)

YENI = re.compile(rf"^\d+_[^_]+_(?:19|20)\d\d_[^_]+_{TUR.replace('_', ' ')}_[^_]+_[^_]+_[^_]+_[^_]+\.pdf$", re.IGNORECASE)

def bosluk(s):
    return s.replace("_", " ")

def yeni_ad(ad):
    m = DESEN.match(ad)
    if not m:
        return None
    g = m.groupdict()
    u = UNVAN.match(g["danisman"])
    danisman = f"{bosluk(u['unvan'])}_{bosluk(u['ad'])}" if u else bosluk(g["danisman"])
    return "_".join([g["no"], bosluk(g["yazar"]), g["yil"], bosluk(g["uni"]),
                     g["tur"].replace("_", " "), g["dil"], bosluk(g["konu"]), danisman]) + ".pdf"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Kullanım: python3 yeniden_adlandir.py <klasor> [--uygula]")
    klasor = sys.argv[1].strip().strip("'\"").replace("\\ ", " ")
    uygula = "--uygula" in sys.argv
    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")

    degisecek, uymayan, ayni = [], [], 0
    for ad in sorted(os.listdir(klasor)):
        if not ad.lower().endswith(".pdf") or ad.startswith("."):
            continue
        yeni = yeni_ad(ad)
        if yeni is None and YENI.match(ad):
            ayni += 1
        elif yeni is None:
            uymayan.append(ad)
        elif yeni == ad:
            ayni += 1
        else:
            degisecek.append((ad, yeni))

    # Aynı yeni ada çıkan çakışmaları ve var olan dosyaları ele
    sayac = {}
    for _, y in degisecek:
        sayac[y] = sayac.get(y, 0) + 1
    cakisan = [(a, y) for a, y in degisecek if sayac[y] > 1 or os.path.exists(os.path.join(klasor, y))]
    uygun = [(a, y) for a, y in degisecek if (a, y) not in cakisan]

    print(f"Değişecek: {len(uygun)} | Zaten uygun: {ayni} | Kalıba uymayan: {len(uymayan)} | Çakışan: {len(cakisan)}")
    for a, y in uygun[:5]:
        print(f"  {a}\n  -> {y}\n")
    if uymayan:
        print("Kalıba uymayan dosyalar (dokunulmadı):")
        for a in uymayan[:20]:
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
