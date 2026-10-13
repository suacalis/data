# -*- coding: utf-8 -*-
"""Çalıştırma: python3 -m unittest discover -s arama -p "test_*.py" """

import json
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arama.harita_arama import _betik_icin_json, arama_kayitlari  # noqa: E402


def ornek_df():
    return pd.DataFrame([
        {'il': 'İstanbul', 'ilce': 'Kadıköy', 'kaza_sayisi': 15, 'olumlu_kaza': 0, 'yaralanma': 15,
         'kaza_tarihi': '2024-01', 'sektor': 'İnşaat'},
        {'il': 'İstanbul', 'ilce': 'Kadıköy', 'kaza_sayisi': 18, 'olumlu_kaza': 1, 'yaralanma': 17,
         'kaza_tarihi': '2024-02', 'sektor': 'İmalat'},
        {'il': 'Ankara', 'ilce': 'Çankaya', 'kaza_sayisi': 12, 'olumlu_kaza': 0, 'yaralanma': 12,
         'kaza_tarihi': '2024-01', 'sektor': 'İnşaat'},
        {'il': 'Bilinmeyen', 'ilce': 'Yok', 'kaza_sayisi': 1, 'olumlu_kaza': 0, 'yaralanma': 1,
         'kaza_tarihi': '2024-01', 'sektor': 'Tarım'},
    ])


ISARETCILER = {
    ('İstanbul', 'Kadıköy'): ('marker_a', [41.06, 29.13]),
    ('Ankara', 'Çankaya'): ('marker_b', [39.98, 32.91]),
}


class AramaKayitlariTest(unittest.TestCase):
    def test_il_ilce_basina_bir_kayit_ve_toplamlar(self):
        kayitlar = arama_kayitlari(ornek_df(), ISARETCILER)
        kadikoy = next(k for k in kayitlar if k['ilce'] == 'Kadıköy')
        self.assertEqual(kadikoy['kaza_sayisi'], 33)
        self.assertEqual(kadikoy['olumlu_kaza'], 1)
        self.assertEqual(kadikoy['sektorler'], ['İmalat', 'İnşaat'])
        self.assertEqual(kadikoy['tarihler'], ['2024-01', '2024-02'])
        self.assertEqual(kadikoy['isaretci'], 'marker_a')

    def test_haritada_isaretcisi_olmayan_ilce_aranamaz(self):
        kayitlar = arama_kayitlari(ornek_df(), ISARETCILER)
        self.assertEqual({k['ilce'] for k in kayitlar}, {'Kadıköy', 'Çankaya'})

    def test_kayitlar_json_serilestirilebilir(self):
        json.dumps(arama_kayitlari(ornek_df(), ISARETCILER))  # numpy türü sızmamalı


class BetikJsonTest(unittest.TestCase):
    def test_script_kapatma_ve_jinja_etiketi_kacislanir(self):
        cikti = _betik_icin_json([{'ilce': '</script><script>alert(1)</script>', 'x': '{% raw %}'}])
        self.assertNotIn('</', cikti)
        self.assertNotIn('{%', cikti)
        # Kaçışlar JS içinde asıl metne geri dönmeli.
        self.assertEqual(json.loads(cikti)[0]['ilce'], '<\\/script><script>alert(1)<\\/script>'.replace('\\/', '/'))
        self.assertEqual(json.loads(cikti)[0]['x'], '{% raw %}')


if __name__ == '__main__':
    unittest.main()
