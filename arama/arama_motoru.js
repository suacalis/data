/*
 * Arama motoru: tarayıcıda ve Node.js'te çalışan, bağımlılığı olmayan, bellek içi tam metin araması.
 *
 * Joplin Notes'un arama hattının davranışına göre tasarlandı (bkz. ARAMA_KANITLARI.md):
 *   1. Metin normalleştirme: küçük harf + aksan/diakritik silme (Türkçe İ/I/ı katlaması dahil)
 *   2. Sorgu sözdizimi: boşlukla ayrılmış terimler, "tırnaklı ifade", -olumsuzlama,
 *      sözcük*  (önek joker), alan:değer filtreleri, any:1 (VEYA)
 *   3. Eşleşme: tüm sözcük (token) eşleşmesi; öneki joker ile açılır
 *   4. Sıralama: başlık alanında eşleşenler önce, sonra BM25 ağırlığı
 *
 * Kod Joplin'den kopyalanmadı; gözlenen davranıştan yeniden yazıldı.
 */
(function (kok, fabrika) {
  if (typeof module === 'object' && module.exports) module.exports = fabrika();
  else kok.AramaMotoru = fabrika();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const BM25_K1 = 1.2;
  const BM25_B = 0.75;

  // Joplin'deki "title" sütununa karşılık gelen alanlar ve "body" sütununa karşılık gelenler.
  const BASLIK_ALANLARI = ['il', 'ilce'];
  const GOVDE_ALANLARI = ['sektor', 'tarih'];
  const SUTUNLAR = [BASLIK_ALANLARI, GOVDE_ALANLARI];

  const FILTRE_ADLARI = new Set(['any', 'il', 'ilce', 'sektor', 'tarih', 'olumlu']);
  const TAM_ESLESME_FILTRELERI = new Set(['il', 'ilce', 'sektor']);

  class SorguHatasi extends Error {}

  // --- 1. Normalleştirme --------------------------------------------------------------

  function normalize(metin) {
    return String(metin == null ? '' : metin)
      .normalize('NFKC')
      // Türkçe: İ, I ve ı hepsi "i" olur ki "Isparta" ile "ısparta" ile "İsparta" eşleşsin.
      .replace(/[İIı]/g, 'i')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function sozcuklereAyir(normalMetin) {
    return normalMetin.split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  }

  // --- 2. Sorgu ayrıştırma ------------------------------------------------------------

  function terim(ad, deger) {
    return ad.startsWith('-')
      ? { ad: ad.slice(1).toLowerCase(), deger, olumsuz: true }
      : { ad: ad.toLowerCase(), deger, olumsuz: false };
  }

  // Karakter karakter ilerleyen bir durum makinesi: tırnak içindeki boşluklar terimi bölmez,
  // yalnızca bilinen bir filtre adından sonraki ilk ":" filtre ayırıcısıdır.
  function terimlereBol(sorgu) {
    const terimler = [];
    let tirnakta = false;
    let filtreAdiAlindi = false;
    let ad = '_';
    let deger = '';

    for (const c of sorgu) {
      if (c === '"') {
        deger += c;
        if (tirnakta) {
          terimler.push(terim(ad, deger));
          deger = '';
          ad = '_';
          tirnakta = false;
        } else {
          tirnakta = true;
        }
        continue;
      }
      if (c === ' ' && !tirnakta) {
        filtreAdiAlindi = false;
        if (!deger) continue;
        terimler.push(terim(ad, deger));
        ad = '_';
        deger = '';
        continue;
      }
      if (c === ':' && !tirnakta && !filtreAdiAlindi) {
        const aday = deger.toLowerCase();
        const bilinen =
          FILTRE_ADLARI.has(aday) || (aday[0] === '-' && FILTRE_ADLARI.has(aday.slice(1)));
        if (bilinen) {
          ad = aday;
          deger = '';
          filtreAdiAlindi = true;
          continue;
        }
      }
      deger += c;
    }
    if (tirnakta) deger += '"';
    if (deger) terimler.push(terim(ad, deger));
    return terimler;
  }

  function tirnaklariSil(deger) {
    return deger.length >= 2 && deger.startsWith('"') && deger.endsWith('"')
      ? deger.slice(1, -1)
      : deger;
  }

  function jokerliDeseneCevir(normalDeger) {
    const kacis = normalDeger.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*');
    return new RegExp('^' + kacis + '$');
  }

  function tarihiCozumle(deger) {
    const d = normalize(deger).replace(/[^0-9]/g, '');
    if (/^\d{4}$/.test(d)) return d;
    if (/^\d{6}$/.test(d)) return d.slice(0, 4) + '-' + d.slice(4);
    throw new SorguHatasi('Geçersiz tarih biçimi! YYYY veya YYYY-AA kullanın.');
  }

  /**
   * Sorgu metnini yapılandırılmış koşullara çevirir.
   * @returns {{metinler: Array, filtreler: Array, veya: boolean}}
   */
  function sorguCozumle(sorgu, secenekler = {}) {
    const jokerEkle = !!secenekler.jokerEkle;
    const ham = terimlereBol(String(sorgu || '').trim());
    const metinler = [];
    const filtreler = [];
    let veya = false;

    for (const t of ham) {
      if (t.ad === 'any') {
        veya = tirnaklariSil(t.deger) === '1';
        continue;
      }

      if (t.ad === '_') {
        // Düz metin; "-sözcük" olumsuzlama.
        let deger = t.deger;
        let olumsuz = false;
        if (deger.startsWith('-') && deger.length > 1) {
          olumsuz = true;
          deger = deger.slice(1);
        }
        const tirnakli = deger.startsWith('"') && deger.endsWith('"') && deger.length >= 2;
        const joker = deger.includes('*') || jokerEkle;
        const sozcukler = sozcuklereAyir(normalize(tirnaklariSil(deger).replace(/\*/g, ' ')));
        if (sozcukler.length === 0) continue;
        metinler.push({ sozcukler, tirnakli, joker, olumsuz });
        continue;
      }

      const deger = tirnaklariSil(t.deger);
      if (t.ad === 'olumlu') {
        if (t.olumsuz) throw new SorguHatasi('"olumlu" filtresi olumsuzlanamaz.');
        if (deger !== '1' && deger !== '0') {
          throw new SorguHatasi('"olumlu" filtresinin değeri "1" veya "0" olmalıdır.');
        }
        filtreler.push({ ad: 'olumlu', deger: deger === '1', olumsuz: false });
      } else if (t.ad === 'tarih') {
        filtreler.push({ ad: 'tarih', deger: tarihiCozumle(deger), olumsuz: t.olumsuz });
      } else if (TAM_ESLESME_FILTRELERI.has(t.ad)) {
        const normalDeger = normalize(deger);
        if (!normalDeger) continue;
        filtreler.push({
          ad: t.ad,
          deger: normalDeger,
          desen: jokerliDeseneCevir(normalDeger),
          olumsuz: t.olumsuz,
        });
      } else {
        throw new SorguHatasi('Geçersiz filtre: ' + t.ad);
      }
    }
    return { metinler, filtreler, veya };
  }

  // --- 3. İndeks ----------------------------------------------------------------------

  function degerListesi(deger) {
    if (Array.isArray(deger)) return deger;
    return deger == null || deger === '' ? [] : [deger];
  }

  // Arama alanı -> kayıttaki sütun adı
  const KAYIT_SUTUNU = { il: 'il', ilce: 'ilce', sektor: 'sektorler', tarih: 'tarihler' };

  function belgeHazirla(kayit) {
    const normalDegerler = {};
    const sozcukler = {};
    for (const [alan, sutun] of Object.entries(KAYIT_SUTUNU)) {
      normalDegerler[alan] = degerListesi(kayit[sutun]).map(normalize);
      sozcukler[alan] = normalDegerler[alan].map(sozcuklereAyir);
    }
    const sutunUzunluk = SUTUNLAR.map((alanlar) =>
      alanlar.reduce((toplam, a) => toplam + sozcukler[a].reduce((s, dizi) => s + dizi.length, 0), 0)
    );
    return { kayit, normalDegerler, sozcukler, sutunUzunluk };
  }

  // Bir sözcük dizisinde terimin kaç kez geçtiğini sayar. Tırnaklı ifade ardışık sözcük ister;
  // joker, terimin son sözcüğünü önek olarak eşler (tam sözcük eşleşmesi varsayılandır).
  function gecisSayisi(sozcukDizisi, terimSozcukleri, joker) {
    const n = terimSozcukleri.length;
    let say = 0;
    for (let i = 0; i + n <= sozcukDizisi.length; i++) {
      let uyuyor = true;
      for (let j = 0; j < n; j++) {
        const hedef = terimSozcukleri[j];
        const aday = sozcukDizisi[i + j];
        const sonSozcukJoker = joker && j === n - 1;
        if (sonSozcukJoker ? !aday.startsWith(hedef) : aday !== hedef) {
          uyuyor = false;
          break;
        }
      }
      if (uyuyor) say++;
    }
    return say;
  }

  function alanGecisi(belge, alan, metinTerimi) {
    // Çok sözcüklü, tırnaksız terim ("kadikoy insaat" tek terim olamaz; bölünür). Burada
    // sozcukler yalnızca tırnaklı ifadede 1'den fazladır.
    return belge.sozcukler[alan].reduce(
      (toplam, dizi) => toplam + gecisSayisi(dizi, metinTerimi.sozcukler, metinTerimi.joker),
      0
    );
  }

  function metinTerimleriniBol(metinler) {
    // Tırnaksız düz metin "a b" tek bir ham terim olarak gelmez (boşlukta bölündü), ama
    // koruma olarak tırnaksız çok sözcüklü terimleri sözcüklerine ayırırız.
    const sonuc = [];
    for (const m of metinler) {
      if (m.tirnakli || m.sozcukler.length === 1) sonuc.push(m);
      else {
        m.sozcukler.forEach((s, i) =>
          sonuc.push({ ...m, sozcukler: [s], joker: m.joker && i === m.sozcukler.length - 1 })
        );
      }
    }
    return sonuc;
  }

  function filtreEslesiyorMu(belge, filtre) {
    let eslesti;
    if (filtre.ad === 'olumlu') {
      const olumluVar = Number(belge.kayit.olumlu_kaza) > 0;
      return filtre.deger ? olumluVar : !olumluVar;
    }
    if (filtre.ad === 'tarih') {
      eslesti = belge.normalDegerler.tarih.some((t) => t.startsWith(filtre.deger));
    } else {
      eslesti = belge.normalDegerler[filtre.ad].some((d) => filtre.desen.test(d));
    }
    return filtre.olumsuz ? !eslesti : eslesti;
  }

  function idf(eslesenBelge, toplamBelge) {
    return Math.max(Math.log((toplamBelge - eslesenBelge + 0.5) / (eslesenBelge + 0.5) + 1), 0);
  }

  function bm25(idfDegeri, tf, sutunUzunlugu, ortalamaUzunluk) {
    if (ortalamaUzunluk === 0) return 0;
    return (idfDegeri * (tf * (BM25_K1 + 1))) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * (sutunUzunlugu / ortalamaUzunluk)));
  }

  function turkceKarsilastir(a, b) {
    return String(a).localeCompare(String(b), 'tr');
  }

  /**
   * @param {Array<{il, ilce, sektorler?, tarihler?, kaza_sayisi?, olumlu_kaza?}>} kayitlar
   */
  function olustur(kayitlar) {
    const belgeler = kayitlar.map(belgeHazirla);
    const toplamBelge = belgeler.length;
    const ortalamaUzunluk = SUTUNLAR.map((_, s) =>
      toplamBelge === 0 ? 0 : belgeler.reduce((t, b) => t + b.sutunUzunluk[s], 0) / toplamBelge
    );

    /**
     * @param {string} sorgu
     * @param {{jokerEkle?: boolean, sinir?: number}} [secenekler]
     *   jokerEkle: her metin terimine önek jokeri ekler (yazarken arama için).
     * @returns {Array<{kayit, agirlik: number, alanlar: string[]}>}
     * @throws {SorguHatasi} geçersiz filtre veya değer için
     */
    function ara(sorgu, secenekler = {}) {
      const cozum = sorguCozumle(sorgu, secenekler);
      const olumluMetinler = metinTerimleriniBol(cozum.metinler.filter((m) => !m.olumsuz));
      const olumsuzMetinler = metinTerimleriniBol(cozum.metinler.filter((m) => m.olumsuz));
      const olumluFiltreler = cozum.filtreler.filter((f) => !f.olumsuz);
      const olumsuzFiltreler = cozum.filtreler.filter((f) => f.olumsuz);

      const kosulSayisi = olumluMetinler.length + olumluFiltreler.length;
      if (kosulSayisi === 0 && olumsuzMetinler.length === 0 && olumsuzFiltreler.length === 0) return [];

      // IDF için: her (terim, sütun) çiftinde kaç belgede geçiş var?
      const belgeSayilari = olumluMetinler.map((m) =>
        SUTUNLAR.map(
          (alanlar) => belgeler.filter((b) => alanlar.some((a) => alanGecisi(b, a, m) > 0)).length
        )
      );

      const sonuc = [];
      for (const belge of belgeler) {
        // Olumsuz koşullar her zaman dışlar.
        if (olumsuzMetinler.some((m) => [...BASLIK_ALANLARI, ...GOVDE_ALANLARI].some((a) => alanGecisi(belge, a, m) > 0))) continue;
        if (olumsuzFiltreler.some((f) => !filtreEslesiyorMu(belge, f))) continue;

        const metinSonuclari = olumluMetinler.map((m) =>
          [...BASLIK_ALANLARI, ...GOVDE_ALANLARI].filter((a) => alanGecisi(belge, a, m) > 0)
        );
        const metinEslesti = metinSonuclari.map((alanlar) => alanlar.length > 0);
        const filtreEslesti = olumluFiltreler.map((f) => filtreEslesiyorMu(belge, f));
        const tumKosullar = [...metinEslesti, ...filtreEslesti];

        if (kosulSayisi > 0) {
          const gecti = cozum.veya ? tumKosullar.some(Boolean) : tumKosullar.every(Boolean);
          if (!gecti) continue;
        }

        const alanlar = new Set();
        metinSonuclari.forEach((l) => l.forEach((a) => alanlar.add(a)));
        olumluFiltreler.forEach((f, i) => {
          if (filtreEslesti[i] && f.ad !== 'olumlu') alanlar.add(f.ad);
        });

        let agirlik = 0;
        olumluMetinler.forEach((m, mi) => {
          SUTUNLAR.forEach((sutunAlanlari, s) => {
            const tf = sutunAlanlari.reduce((t, a) => t + alanGecisi(belge, a, m), 0);
            if (tf > 0) agirlik += bm25(idf(belgeSayilari[mi][s], toplamBelge), tf, belge.sutunUzunluk[s], ortalamaUzunluk[s]);
          });
        });

        sonuc.push({ kayit: belge.kayit, agirlik, alanlar: [...alanlar] });
      }

      // Joplin'deki gibi: başlıkta eşleşenler önce, sonra ağırlık; eşitlikte "yenilik" yerine
      // kaza sayısı (bu verinin en anlamlı ikincil ölçütü), en son alfabetik.
      const baslikta = (r) => r.alanlar.some((a) => BASLIK_ALANLARI.includes(a));
      sonuc.sort(
        (a, b) =>
          Number(baslikta(b)) - Number(baslikta(a)) ||
          b.agirlik - a.agirlik ||
          (Number(b.kayit.kaza_sayisi) || 0) - (Number(a.kayit.kaza_sayisi) || 0) ||
          turkceKarsilastir(a.kayit.il, b.kayit.il) ||
          turkceKarsilastir(a.kayit.ilce, b.kayit.ilce)
      );
      return secenekler.sinir ? sonuc.slice(0, secenekler.sinir) : sonuc;
    }

    return { ara, belgeSayisi: toplamBelge };
  }

  return { olustur, sorguCozumle, normalize, sozcuklereAyir, SorguHatasi };
});
