#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Türkiye İş Kazaları Harita Görselleştirme
İlçe seviyesinde iş kazalarını interaktif harita üzerinde gösterir
"""

import pandas as pd
import folium
from folium import plugins
import json

def il_koordinatlari():
    """Türkiye illerinin koordinatları"""
    return {
        'İstanbul': [41.0082, 28.9784],
        'Ankara': [39.9334, 32.8597],
        'İzmir': [38.4237, 27.1428],
        'Bursa': [40.1826, 29.0665],
        'Antalya': [36.8969, 30.7133],
        'Adana': [37.0000, 35.3213],
        'Konya': [37.8667, 32.4833],
        'Gaziantep': [37.0662, 37.3833],
        'Şanlıurfa': [37.1591, 38.7969],
        'Kocaeli': [40.8533, 29.8815],
        'Mersin': [36.8121, 34.6415],
        'Diyarbakır': [37.9144, 40.2306],
        'Hatay': [36.4018, 36.3498],
        'Manisa': [38.6191, 27.4289],
        'Kayseri': [38.7312, 35.4787],
        'Samsun': [41.2867, 36.3300],
        'Balıkesir': [39.6484, 27.8826],
        'Van': [38.4891, 43.4089],
        'Aydın': [37.8560, 27.8416],
        'Denizli': [37.7765, 29.0864],
        'Tekirdağ': [40.9833, 27.5167],
        'Malatya': [38.3552, 38.3095],
        'Trabzon': [41.0015, 39.7178],
        'Ordu': [40.9839, 37.8764],
        'Erzurum': [39.9000, 41.2700],
        'Sakarya': [40.7569, 30.3783],
        'Kahramanmaraş': [37.5858, 36.9371],
        'Mardin': [37.3212, 40.7245],
        'Muğla': [37.2153, 28.3636]
    }

def ilce_koordinat_offset():
    """İlçeler için koordinat offset değerleri (il merkezine göre)"""
    return {
        'Kadıköy': [0.05, 0.15],
        'Şişli': [-0.05, -0.05],
        'Çankaya': [0.05, 0.05],
        'Konak': [0.02, 0.02],
        'Osmangazi': [0.03, 0.03],
        'Muratpaşa': [0.05, 0.05],
        'Seyhan': [0.02, 0.02],
        'Selçuklu': [0.05, 0.05],
        'Şahinbey': [0.03, 0.03],
        'Eyyübiye': [0.05, 0.05],
        'İzmit': [0.02, 0.02],
        'Akdeniz': [0.03, 0.03],
        'Bağlar': [0.02, 0.02],
        'Antakya': [0.02, 0.02],
        'Yunusemre': [0.03, 0.03],
        'Kocasinan': [0.05, 0.05],
        'İlkadım': [0.03, 0.03],
        'Karesi': [0.02, 0.02],
        'İpekyolu': [0.03, 0.03],
        'Efeler': [0.02, 0.02],
        'Pamukkale': [0.03, 0.03],
        'Süleymanpaşa': [0.02, 0.02],
        'Yeşilyurt': [0.03, 0.03],
        'Ortahisar': [0.02, 0.02],
        'Altınordu': [0.02, 0.02],
        'Yakutiye': [0.03, 0.03],
        'Adapazarı': [0.02, 0.02],
        'Onikişubat': [0.02, 0.02],
        'Artuklu': [0.02, 0.02],
        'Menteşe': [0.02, 0.02],
        'Keçiören': [-0.05, 0.05],
        'Bornova': [0.05, 0.05],
        'Nilüfer': [0.05, -0.05],
        'Kepez': [-0.05, 0.05],
        'Çukurova': [0.05, 0.05],
        'Meram': [-0.05, 0.05],
        'Şehitkamil': [0.05, 0.05],
        'Haliliye': [-0.05, 0.05],
        'Gebze': [0.10, 0.10]
    }

def kaza_verilerini_yukle(dosya_yolu='is_kazalari_ornek.csv'):
    """İş kazası verilerini yükle"""
    try:
        df = pd.read_csv(dosya_yolu, encoding='utf-8')
        return df
    except FileNotFoundError:
        print(f"Hata: {dosya_yolu} dosyası bulunamadı!")
        return None
    except Exception as e:
        print(f"Veri yükleme hatası: {e}")
        return None

def koordinat_hesapla(il, ilce, il_koord_dict, ilce_offset_dict):
    """İl ve ilçe için koordinat hesapla"""
    if il in il_koord_dict:
        il_lat, il_lon = il_koord_dict[il]
        if ilce in ilce_offset_dict:
            offset_lat, offset_lon = ilce_offset_dict[ilce]
            return [il_lat + offset_lat, il_lon + offset_lon]
        return [il_lat, il_lon]
    return None

def renk_belirle(kaza_sayisi):
    """Kaza sayısına göre marker rengi belirle"""
    if kaza_sayisi >= 15:
        return 'darkred'
    elif kaza_sayisi >= 10:
        return 'red'
    elif kaza_sayisi >= 7:
        return 'orange'
    elif kaza_sayisi >= 5:
        return 'lightred'
    else:
        return 'lightblue'

def harita_olustur(df):
    """İş kazaları haritasını oluştur"""
    # Türkiye merkez koordinatları
    turkiye_merkez = [39.0, 35.0]

    # Folium haritası oluştur
    m = folium.Map(
        location=turkiye_merkez,
        zoom_start=6,
        tiles='OpenStreetMap'
    )

    # İl ve ilçe koordinatları
    il_koord = il_koordinatlari()
    ilce_offset = ilce_koordinat_offset()

    # İlçe bazında verileri grupla
    ilce_grup = df.groupby(['il', 'ilce']).agg({
        'kaza_sayisi': 'sum',
        'olumlu_kaza': 'sum',
        'yaralanma': 'sum',
        'sektor': lambda x: ', '.join(set(x)),
        'is_seviyesi': 'first'
    }).reset_index()

    # Marker cluster oluştur
    marker_cluster = plugins.MarkerCluster().add_to(m)

    # Her ilçe için marker ekle
    for _, row in ilce_grup.iterrows():
        koord = koordinat_hesapla(row['il'], row['ilce'], il_koord, ilce_offset)

        if koord:
            # Popup içeriği
            popup_html = f"""
            <div style="font-family: Arial; width: 250px;">
                <h4 style="margin-bottom: 10px; color: #d32f2f;">{row['il']} - {row['ilce']}</h4>
                <hr style="margin: 5px 0;">
                <table style="width: 100%; font-size: 12px;">
                    <tr>
                        <td><b>Toplam Kaza:</b></td>
                        <td style="text-align: right; font-weight: bold; color: #d32f2f;">
                            {int(row['kaza_sayisi'])}
                        </td>
                    </tr>
                    <tr>
                        <td><b>Ölümlü Kaza:</b></td>
                        <td style="text-align: right; color: #c62828;">
                            {int(row['olumlu_kaza'])}
                        </td>
                    </tr>
                    <tr>
                        <td><b>Yaralanmalı:</b></td>
                        <td style="text-align: right; color: #f57c00;">
                            {int(row['yaralanma'])}
                        </td>
                    </tr>
                    <tr>
                        <td><b>Sektör:</b></td>
                        <td style="text-align: right; font-size: 11px;">
                            {row['sektor']}
                        </td>
                    </tr>
                    <tr>
                        <td><b>İş Seviyesi:</b></td>
                        <td style="text-align: right;">
                            {row['is_seviyesi']}
                        </td>
                    </tr>
                </table>
            </div>
            """

            # Marker rengi
            renk = renk_belirle(row['kaza_sayisi'])

            # Marker ekle
            folium.Marker(
                location=koord,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['il']} - {row['ilce']}: {int(row['kaza_sayisi'])} kaza",
                icon=folium.Icon(color=renk, icon='warning-sign', prefix='glyphicon')
            ).add_to(marker_cluster)

            # Ölümlü kaza varsa circle marker ekle
            if row['olumlu_kaza'] > 0:
                folium.CircleMarker(
                    location=koord,
                    radius=row['olumlu_kaza'] * 3,
                    color='darkred',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.3,
                    popup=f"Ölümlü kaza: {int(row['olumlu_kaza'])}",
                    tooltip=f"Ölümlü: {int(row['olumlu_kaza'])}"
                ).add_to(m)

    # İstatistik kutusu ekle
    toplam_kaza = df['kaza_sayisi'].sum()
    toplam_olumlu = df['olumlu_kaza'].sum()
    toplam_yaralanma = df['yaralanma'].sum()

    legend_html = f"""
    <div style="position: fixed;
                top: 10px; right: 10px; width: 280px; height: auto;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px; border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <h4 style="margin-top: 0; color: #d32f2f;">İş Kazaları İstatistikleri</h4>
        <hr style="margin: 5px 0;">
        <p><b>Toplam Kaza Sayısı:</b> <span style="color: #d32f2f; font-weight: bold;">{int(toplam_kaza)}</span></p>
        <p><b>Ölümlü Kaza:</b> <span style="color: #c62828; font-weight: bold;">{int(toplam_olumlu)}</span></p>
        <p><b>Yaralanmalı:</b> <span style="color: #f57c00; font-weight: bold;">{int(toplam_yaralanma)}</span></p>
        <hr style="margin: 5px 0;">
        <p style="font-size: 12px; margin: 5px 0;"><b>Renk Açıklaması:</b></p>
        <p style="font-size: 11px; margin: 2px 0;">
            <span style="color: darkred;">⬤</span> 15+ kaza<br>
            <span style="color: red;">⬤</span> 10-14 kaza<br>
            <span style="color: orange;">⬤</span> 7-9 kaza<br>
            <span style="color: lightcoral;">⬤</span> 5-6 kaza<br>
            <span style="color: lightblue;">⬤</span> 1-4 kaza
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

def main():
    """Ana program"""
    print("=" * 60)
    print("Türkiye İş Kazaları Harita Görselleştirme")
    print("=" * 60)

    # Veriyi yükle
    print("\n[1/3] İş kazası verileri yükleniyor...")
    df = kaza_verilerini_yukle('is_kazalari_ornek.csv')

    if df is None:
        print("Program sonlandırılıyor...")
        return

    print(f"✓ {len(df)} kayıt yüklendi")
    print(f"✓ {df['il'].nunique()} farklı il")
    print(f"✓ {df['ilce'].nunique()} farklı ilçe")

    # Harita oluştur
    print("\n[2/3] Harita oluşturuluyor...")
    harita = harita_olustur(df)
    print("✓ Harita başarıyla oluşturuldu")

    # Haritayı kaydet
    print("\n[3/3] Harita kaydediliyor...")
    cikti_dosyasi = 'turkiye_is_kazalari_harita.html'
    harita.save(cikti_dosyasi)
    print(f"✓ Harita '{cikti_dosyasi}' dosyasına kaydedildi")

    print("\n" + "=" * 60)
    print("İşlem tamamlandı!")
    print(f"Haritayı görüntülemek için '{cikti_dosyasi}' dosyasını")
    print("bir web tarayıcısında açın.")
    print("=" * 60)

    # Özet istatistikler
    print("\nÖzet İstatistikler:")
    print("-" * 40)
    print(f"Toplam kaza sayısı    : {df['kaza_sayisi'].sum()}")
    print(f"Ölümlü kaza           : {df['olumlu_kaza'].sum()}")
    print(f"Yaralanmalı           : {df['yaralanma'].sum()}")
    print(f"En çok kaza olan il   : {df.groupby('il')['kaza_sayisi'].sum().idxmax()}")
    print("-" * 40)

if __name__ == "__main__":
    main()
