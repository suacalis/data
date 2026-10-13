#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Folium haritasına istemci tarafı arama ekler.

Arama motoru (arama_motoru.js) ve arayüz (arama_arayuzu.js) üretilen HTML dosyasının içine
gömülür; harita tek dosya olarak çalışmaya devam eder, sunucu gerekmez.
"""

import json
from pathlib import Path

import folium

_DIZIN = Path(__file__).resolve().parent


def arama_kayitlari(df, isaretciler):
    """
    Arama indeksine girecek kayıtları üretir (il + ilçe başına bir kayıt).

    df: kaza verisi (il, ilce, kaza_sayisi, olumlu_kaza, yaralanma, kaza_tarihi, sektor)
    isaretciler: {(il, ilce): (isaretci_degisken_adi, [enlem, boylam])}
        Haritaya gerçekten marker eklenen ilçeler; koordinatı olmayan ilçeler aranamaz,
        çünkü seçildiğinde gidilecek bir yer yoktur.
    """
    kayitlar = []
    for (il, ilce), grup in df.groupby(['il', 'ilce'], sort=True):
        if (il, ilce) not in isaretciler:
            continue
        isaretci_adi, (enlem, boylam) = isaretciler[(il, ilce)]
        kayitlar.append({
            'il': il,
            'ilce': ilce,
            'sektorler': sorted({str(s) for s in grup['sektor'].dropna()}),
            'tarihler': sorted({str(t) for t in grup['kaza_tarihi'].dropna()}),
            'kaza_sayisi': int(grup['kaza_sayisi'].sum()),
            'olumlu_kaza': int(grup['olumlu_kaza'].sum()),
            'yaralanma': int(grup['yaralanma'].sum()),
            'enlem': float(enlem),
            'boylam': float(boylam),
            'isaretci': isaretci_adi,
        })
    return kayitlar


def _betik_icin_json(veri):
    # "</script>" dizisi bir <script> bloğunu erken kapatır; "{%" ise Jinja etiketi başlatır.
    # CSV'den gelen metin için güvenlik önlemi; her iki dizi de JSON dizeleri içinde kaçışlanır.
    return (json.dumps(veri, ensure_ascii=False)
            .replace('</', '<\\/')
            .replace('{%', '{\\u0025'))


def _jinja_disi(js):
    # Folium, Element içeriğini Jinja şablonu olarak işler; JS içindeki "{{", "{#" gibi dizilerin
    # şablon sözdizimi sanılmaması için ham blok içine alınır.
    return '{% raw %}' + js + '{% endraw %}'


def haritaya_arama_ekle(harita, df, isaretciler, kume):
    """Haritaya arama kutusunu ve arama indeksini ekler."""
    kayitlar = arama_kayitlari(df, isaretciler)
    motor_js = (_DIZIN / 'arama_motoru.js').read_text(encoding='utf-8')
    arayuz_js = (_DIZIN / 'arama_arayuzu.js').read_text(encoding='utf-8')

    # Folium kendi harita betiğini render sırasında, bizim eklediğimiz bloklardan SONRA yazar.
    # Harita ve işaretçi değişkenleri o zamana kadar tanımsız olduğundan başlatma DOM
    # yüklendikten sonraya ertelenir.
    baslat_js = f"""
    document.addEventListener('DOMContentLoaded', function () {{
        AramaArayuzu.ekle({{
            harita: {harita.get_name()},
            kume: {kume.get_name()},
            kayitlar: {_betik_icin_json(kayitlar)}
        }});
    }});
    """

    betik = harita.get_root().script
    betik.add_child(folium.Element(_jinja_disi(motor_js)), name='arama_motoru')
    betik.add_child(folium.Element(_jinja_disi(arayuz_js)), name='arama_arayuzu')
    betik.add_child(folium.Element(_jinja_disi(baslat_js)), name='arama_baslat')
    return len(kayitlar)
