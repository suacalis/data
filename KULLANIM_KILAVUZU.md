# Türkiye İş Kazaları Harita Görselleştirme Sistemi

## Genel Bakış

Bu sistem, Türkiye genelinde işçi seviyesinde meydana gelen iş kazalarını ilçe bazında interaktif bir harita üzerinde görselleştirmenizi sağlar.

## Özellikler

✓ **İlçe Seviyesinde Detay**: Her ilçe için kaza sayıları ayrı ayrı gösterilir
✓ **Renkli Görselleştirme**: Kaza sayısına göre farklı renk kodları
✓ **İnteraktif Harita**: Yakınlaştırma, marker üzerine gelme, cluster desteği
✓ **Detaylı İstatistikler**: Her ilçe için popup içinde detaylı bilgiler
✓ **Ölümlü Kaza Vurgusu**: Ölümlü kazaların özel circle marker ile gösterimi
✓ **Canlı İstatistikler**: Sağ üst köşede genel istatistik kutusu

## Kurulum

### 1. Gerekli Kütüphaneleri Yükleyin

```bash
pip install -r requirements.txt
```

veya manuel olarak:

```bash
pip install pandas folium
```

## Veri Formatı

İş kazası verileriniz CSV formatında olmalı ve şu sütunları içermelidir:

| Sütun | Açıklama | Örnek |
|-------|----------|-------|
| `il` | İl adı | İstanbul |
| `ilce` | İlçe adı | Kadıköy |
| `kaza_sayisi` | Kaza sayısı | 15 |
| `olumlu_kaza` | Ölümlü kaza sayısı | 1 |
| `yaralanma` | Yaralanma sayısı | 14 |
| `kaza_tarihi` | Kaza tarihi (YYYY-MM formatında) | 2024-01 |
| `sektor` | Sektör bilgisi | İnşaat |
| `is_seviyesi` | İş seviyesi | İşçi |

### Örnek CSV Formatı

```csv
il,ilce,kaza_sayisi,olumlu_kaza,yaralanma,kaza_tarihi,sektor,is_seviyesi
İstanbul,Kadıköy,15,0,15,2024-01,İnşaat,İşçi
İstanbul,Şişli,8,1,7,2024-01,İmalat,İşçi
Ankara,Çankaya,12,0,12,2024-01,İnşaat,İşçi
```

## Kullanım

### 1. Kendi Verilerinizle Kullanım

Kendi iş kazası verilerinizi `is_kazalari_ornek.csv` dosyasının yerine koyun veya script içinde dosya adını değiştirin:

```python
df = kaza_verilerini_yukle('kendi_verileriniz.csv')
```

### 2. Scripti Çalıştırın

```bash
python3 turkiye_is_kazalari_harita.py
```

### 3. Haritayı Görüntüleyin

Script başarıyla çalıştıktan sonra `turkiye_is_kazalari_harita.html` dosyası oluşturulacaktır. Bu dosyayı herhangi bir web tarayıcısında açarak interaktif haritayı görüntüleyebilirsiniz:

```bash
# Linux/Mac
open turkiye_is_kazalari_harita.html

# Windows
start turkiye_is_kazalari_harita.html
```

## Renk Kodları

Haritada kullanılan renk kodları:

- 🔴 **Koyu Kırmızı** (darkred): 15+ kaza
- 🔴 **Kırmızı** (red): 10-14 kaza
- 🟠 **Turuncu** (orange): 7-9 kaza
- 🔴 **Açık Kırmızı** (lightred): 5-6 kaza
- 🔵 **Açık Mavi** (lightblue): 1-4 kaza

## Harita Özellikleri

### 1. Marker'lar
Her ilçe için bir marker (işaretleyici) görüntülenir. Marker üzerine geldiğinizde ilçe adı ve toplam kaza sayısı gösterilir.

### 2. Popup Bilgileri
Marker'a tıkladığınızda açılan popup'ta şu bilgiler görüntülenir:
- Toplam kaza sayısı
- Ölümlü kaza sayısı
- Yaralanmalı sayısı
- Sektör bilgisi
- İş seviyesi

### 3. Ölümlü Kaza Circle'ları
Ölümlü kazanın olduğu bölgelerde, marker'ın etrafında kırmızı bir circle (daire) gösterilir. Circle'ın büyüklüğü ölümlü kaza sayısı ile orantılıdır.

### 4. Cluster Özelliği
Çok sayıda marker yakın konumda olduğunda, harita otomatik olarak bunları gruplar (cluster). Zoom yapıldıkça cluster'lar açılır.

### 5. İstatistik Kutusu
Sağ üst köşede bulunan istatistik kutusunda:
- Toplam kaza sayısı
- Toplam ölümlü kaza
- Toplam yaralanma
- Renk açıklamaları

## Özelleştirme

### 1. Yeni İl/İlçe Koordinatları Ekleme

Eğer verilerinizde sistemde olmayan bir il veya ilçe varsa, script içindeki `il_koordinatlari()` ve `ilce_koordinat_offset()` fonksiyonlarına yeni koordinatlar ekleyebilirsiniz:

```python
def il_koordinatlari():
    return {
        'İstanbul': [41.0082, 28.9784],
        'YeniIl': [xx.xxxx, yy.yyyy],  # Yeni il koordinatları
        # ...
    }
```

### 2. Renk Kodlarını Değiştirme

`renk_belirle()` fonksiyonunda kaza sayısı eşik değerlerini ve renkleri değiştirebilirsiniz:

```python
def renk_belirle(kaza_sayisi):
    if kaza_sayisi >= 20:  # Eşik değerini değiştir
        return 'darkred'
    # ...
```

### 3. Harita Merkezi ve Zoom

`harita_olustur()` fonksiyonunda Türkiye merkez koordinatlarını ve başlangıç zoom seviyesini değiştirebilirsiniz:

```python
m = folium.Map(
    location=[39.0, 35.0],  # Merkez koordinatları
    zoom_start=6,           # Zoom seviyesi (1-18)
    tiles='OpenStreetMap'
)
```

### 4. Popup İçeriği

Popup HTML içeriğini `harita_olustur()` fonksiyonundaki `popup_html` değişkenini düzenleyerek özelleştirebilirsiniz.

## Sorun Giderme

### Problem: CSV dosyası bulunamadı hatası
**Çözüm**: CSV dosyanızın script ile aynı dizinde olduğundan emin olun veya tam dosya yolunu belirtin.

### Problem: Koordinatlar eksik
**Çözüm**: Yeni il/ilçeler için koordinatları `il_koordinatlari()` ve `ilce_koordinat_offset()` fonksiyonlarına ekleyin.

### Problem: Harita görüntülenmiyor
**Çözüm**: HTML dosyasını modern bir web tarayıcısı (Chrome, Firefox, Edge) ile açın. İnternet bağlantınızın olduğundan emin olun (OpenStreetMap tile'ları için).

### Problem: Türkçe karakterler bozuk görünüyor
**Çözüm**: CSV dosyanızın UTF-8 encoding ile kaydedildiğinden emin olun.

## Örnek Çıktı

Script başarıyla çalıştığında şu şekilde bir çıktı göreceksiniz:

```
============================================================
Türkiye İş Kazaları Harita Görselleştirme
============================================================

[1/3] İş kazası verileri yükleniyor...
✓ 40 kayıt yüklendi
✓ 29 farklı il
✓ 39 farklı ilçe

[2/3] Harita oluşturuluyor...
✓ Harita başarıyla oluşturuldu

[3/3] Harita kaydediliyor...
✓ Harita 'turkiye_is_kazalari_harita.html' dosyasına kaydedildi

============================================================
İşlem tamamlandı!
============================================================

Özet İstatistikler:
----------------------------------------
Toplam kaza sayısı    : 340
Ölümlü kaza           : 19
Yaralanmalı           : 321
En çok kaza olan il   : İstanbul
----------------------------------------
```

## Gelişmiş Kullanım

### 1. Belirli Bir Dönemi Filtreleme

Scripti değiştirerek belirli bir döneme ait verileri filtreleyebilirsiniz:

```python
# Belirli bir aya ait verileri filtrele
df_filtered = df[df['kaza_tarihi'] == '2024-01']
harita = harita_olustur(df_filtered)
```

### 2. Sektöre Göre Filtreleme

```python
# Sadece inşaat sektörünü göster
df_insaat = df[df['sektor'] == 'İnşaat']
harita = harita_olustur(df_insaat)
```

### 3. Toplu Harita Oluşturma

Aylara göre ayrı ayrı haritalar oluşturmak için:

```python
for tarih in df['kaza_tarihi'].unique():
    df_ay = df[df['kaza_tarihi'] == tarih]
    harita = harita_olustur(df_ay)
    harita.save(f'harita_{tarih}.html')
```

## Teknik Detaylar

- **Python Versiyonu**: 3.7+
- **Pandas**: Veri manipülasyonu için
- **Folium**: İnteraktif harita oluşturma için (Leaflet.js tabanlı)
- **Harita Kaynağı**: OpenStreetMap

## Lisans ve Yasal Uyarı

Bu sistem yalnızca görselleştirme amaçlıdır. İş kazası verileri gizlilik ve yasal düzenlemelere uygun şekilde kullanılmalıdır.

## Destek ve Katkı

Sorularınız veya önerileriniz için issue açabilirsiniz.

---

**Not**: Örnek veriler rastgele oluşturulmuş ve gerçek değildir. Kendi verilerinizi kullanarak sistemi çalıştırabilirsiniz.
