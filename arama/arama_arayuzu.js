/*
 * Leaflet haritasına arama kutusu ve sonuç listesi ekler.
 *
 * Joplin Notes'un SearchBar bileşeninin davranışını izler:
 *   - yazdıkça arama (debounce ile), boş kutu aramadan çıkar
 *   - Escape aramadan çıkar ve önceki görünümü geri getirir
 *   - sonuç listesinden seçim, ilgili öğeyi açar
 *
 * Bağımlılık: window.L (Leaflet), window.AramaMotoru
 */
(function (kok) {
  'use strict';

  var GECIKME_MS = 250; // Joplin 500 ms bekler; burada veri bellek içinde olduğu için daha kısa.
  var EN_COK_SONUC = 12;

  var ALAN_ETIKETLERI = { il: 'il', ilce: 'ilçe', sektor: 'sektör', tarih: 'tarih' };

  var CSS =
    '.arama-kutusu{background:#fff;padding:8px;border-radius:6px;box-shadow:0 1px 6px rgba(0,0,0,.35);' +
    'width:min(320px,calc(100vw - 32px));font:13px Arial,sans-serif}' +
    '.arama-kutusu input{box-sizing:border-box;width:100%;padding:7px 28px 7px 8px;border:1px solid #999;' +
    'border-radius:4px;font:inherit}' +
    '.arama-kutusu .arama-temizle{position:absolute;right:14px;top:12px;border:0;background:none;' +
    'cursor:pointer;font-size:16px;line-height:1;color:#666;display:none}' +
    '.arama-kutusu .arama-giris{position:relative}' +
    '.arama-kutusu ul{list-style:none;margin:6px 0 0;padding:0;max-height:min(50vh,360px);overflow:auto}' +
    '.arama-kutusu li{padding:6px 8px;border-radius:4px;cursor:pointer}' +
    '.arama-kutusu li:hover,.arama-kutusu li[aria-selected=true]{background:#ffe9e7}' +
    '.arama-kutusu li b{color:#d32f2f}' +
    '.arama-kutusu li small{display:block;color:#555;margin-top:2px}' +
    '.arama-kutusu li .arama-alan{display:inline-block;margin-left:4px;padding:0 5px;border-radius:8px;' +
    'background:#eee;color:#444;font-size:11px}' +
    '.arama-kutusu .arama-durum{margin:6px 2px 0;color:#555;font-size:12px}' +
    '.arama-kutusu .arama-durum.arama-hata{color:#b71c1c}' +
    '.arama-kutusu .arama-ipucu{margin:6px 2px 0;color:#777;font-size:11px;line-height:1.4}';

  function stilEkle() {
    if (document.getElementById('arama-stili')) return;
    var stil = document.createElement('style');
    stil.id = 'arama-stili';
    stil.textContent = CSS;
    document.head.appendChild(stil);
  }

  function eleman(etiket, ozellikler, metin) {
    var e = document.createElement(etiket);
    Object.keys(ozellikler || {}).forEach(function (k) {
      e.setAttribute(k, ozellikler[k]);
    });
    if (metin != null) e.textContent = metin;
    return e;
  }

  /**
   * @param {Object} secenek
   * @param {L.Map} secenek.harita
   * @param {L.MarkerClusterGroup} [secenek.kume] - işaretçileri kümeleyen katman
   * @param {Array} secenek.kayitlar - { il, ilce, sektorler, tarihler, kaza_sayisi, olumlu_kaza,
   *   yaralanma, enlem, boylam, isaretci } ; isaretci: window üzerindeki L.Marker değişken adı
   */
  function ekle(secenek) {
    var L = kok.L;
    var harita = secenek.harita;
    var kume = secenek.kume;
    var motor = kok.AramaMotoru.olustur(secenek.kayitlar);
    var ilkGorunum = { merkez: harita.getCenter(), yakinlik: harita.getZoom() };
    var sonuclar = [];
    var secili = -1;
    var zamanlayici = null;
    var bekliyor = false; // gecikmeli bir arama henüz çalışmadı

    stilEkle();

    var kutu = eleman('div', { class: 'arama-kutusu', role: 'search' });
    var giris = eleman('div', { class: 'arama-giris' });
    var girdi = eleman('input', {
      type: 'text',
      role: 'searchbox',
      placeholder: 'İl, ilçe veya sektör ara…',
      'aria-label': 'Haritada ara',
      autocomplete: 'off',
      spellcheck: 'false',
    });
    var temizle = eleman('button', { type: 'button', class: 'arama-temizle', 'aria-label': 'Aramayı temizle' }, '×');
    var durum = eleman('div', { class: 'arama-durum', 'aria-live': 'polite' });
    var liste = eleman('ul', { role: 'listbox' });
    var ipucu = eleman(
      'div',
      { class: 'arama-ipucu' },
      'Örn: kad* · il:ankara · sektor:insaat -il:istanbul · "iş kolu" · tarih:2024-03 · olumlu:1 · any:1 a b'
    );

    giris.appendChild(girdi);
    giris.appendChild(temizle);
    kutu.appendChild(giris);
    kutu.appendChild(durum);
    kutu.appendChild(liste);
    kutu.appendChild(ipucu);

    function isaretciBul(kayit) {
      return kayit.isaretci ? kok[kayit.isaretci] : null;
    }

    function sonuclariCiz() {
      liste.textContent = '';
      sonuclar.forEach(function (sonuc, sira) {
        var k = sonuc.kayit;
        var li = eleman('li', { role: 'option', 'aria-selected': String(sira === secili) });
        var baslik = eleman('span');
        baslik.appendChild(eleman('b', {}, k.il));
        baslik.appendChild(document.createTextNode(' – ' + k.ilce));
        sonuc.alanlar.forEach(function (alan) {
          baslik.appendChild(eleman('span', { class: 'arama-alan' }, ALAN_ETIKETLERI[alan] || alan));
        });
        li.appendChild(baslik);
        li.appendChild(
          eleman(
            'small',
            {},
            k.kaza_sayisi + ' kaza · ' + k.olumlu_kaza + ' ölümlü · ' + (k.sektorler || []).join(', ')
          )
        );
        li.addEventListener('mousedown', function (olay) {
          olay.preventDefault(); // girdinin odağını kaybetme
          sec(sira);
        });
        liste.appendChild(li);
      });
    }

    function sec(sira) {
      var sonuc = sonuclar[sira];
      if (!sonuc) return;
      secili = sira;
      sonuclariCiz();
      var k = sonuc.kayit;
      var isaretci = isaretciBul(k);
      if (kume && isaretci && kume.zoomToShowLayer) {
        kume.zoomToShowLayer(isaretci, function () {
          isaretci.openPopup();
        });
      } else if (isaretci) {
        harita.setView(isaretci.getLatLng(), Math.max(harita.getZoom(), 10));
        isaretci.openPopup();
      } else if (k.enlem != null) {
        harita.setView([k.enlem, k.boylam], Math.max(harita.getZoom(), 10));
      }
    }

    function ara() {
      bekliyor = false;
      var sorgu = girdi.value;
      temizle.style.display = sorgu ? 'block' : 'none';
      if (!sorgu.trim()) {
        cik(false);
        return;
      }
      durum.className = 'arama-durum';
      try {
        sonuclar = motor.ara(sorgu, { jokerEkle: true, sinir: EN_COK_SONUC });
        durum.textContent = sonuclar.length ? sonuclar.length + ' sonuç' : 'Sonuç bulunamadı';
      } catch (hata) {
        sonuclar = [];
        durum.className = 'arama-durum arama-hata';
        durum.textContent = hata && hata.message ? hata.message : 'Geçersiz sorgu';
      }
      secili = -1;
      sonuclariCiz();
    }

    // Aramadan çık: kutuyu ve listeyi boşalt, haritayı ilk görünüme döndür.
    function cik(gorunumuGeriYukle) {
      clearTimeout(zamanlayici);
      bekliyor = false;
      girdi.value = '';
      temizle.style.display = 'none';
      sonuclar = [];
      secili = -1;
      durum.textContent = '';
      durum.className = 'arama-durum';
      liste.textContent = '';
      if (gorunumuGeriYukle) {
        harita.closePopup();
        harita.setView(ilkGorunum.merkez, ilkGorunum.yakinlik);
      }
    }

    girdi.addEventListener('input', function () {
      clearTimeout(zamanlayici);
      if (!girdi.value.trim()) {
        ara();
        return;
      }
      bekliyor = true;
      zamanlayici = setTimeout(ara, GECIKME_MS);
    });

    girdi.addEventListener('keydown', function (olay) {
      if (olay.key === 'Escape') {
        cik(true);
        girdi.blur();
      } else if (olay.key === 'ArrowDown' && sonuclar.length) {
        olay.preventDefault();
        secili = (secili + 1) % sonuclar.length;
        sonuclariCiz();
      } else if (olay.key === 'ArrowUp' && sonuclar.length) {
        olay.preventDefault();
        secili = (secili - 1 + sonuclar.length) % sonuclar.length;
        sonuclariCiz();
      } else if (olay.key === 'Enter') {
        olay.preventDefault();
        if (bekliyor) {
          clearTimeout(zamanlayici);
          ara();
        }
        if (sonuclar.length) sec(secili >= 0 ? secili : 0);
      }
    });

    temizle.addEventListener('click', function () {
      cik(true);
      girdi.focus();
    });

    var Kontrol = L.Control.extend({
      options: { position: 'topleft' },
      onAdd: function () {
        // Harita sürükleme/kaydırma olaylarını kutuya sızdırma.
        L.DomEvent.disableClickPropagation(kutu);
        L.DomEvent.disableScrollPropagation(kutu);
        return kutu;
      },
    });
    new Kontrol().addTo(harita);

    return { motor: motor, ara: ara, cik: cik, girdi: girdi };
  }

  kok.AramaArayuzu = { ekle: ekle };
})(typeof self !== 'undefined' ? self : this);
