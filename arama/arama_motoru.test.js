// Çalıştırma: node --test arama/
const test = require('node:test');
const assert = require('node:assert/strict');
const { olustur, sorguCozumle, normalize, SorguHatasi } = require('./arama_motoru.js');

const kayit = (il, ilce, sektorler, tarihler, kaza, olumlu) => ({
  il,
  ilce,
  sektorler,
  tarihler,
  kaza_sayisi: kaza,
  olumlu_kaza: olumlu,
});

const VERI = [
  kayit('İstanbul', 'Kadıköy', ['İnşaat'], ['2024-01', '2024-02'], 15, 0),
  kayit('İstanbul', 'Şişli', ['İmalat'], ['2024-01'], 8, 1),
  kayit('Ankara', 'Çankaya', ['İnşaat'], ['2024-01'], 12, 0),
  kayit('Isparta', 'Merkez', ['Tarım'], ['2024-03'], 4, 2),
  kayit('Kocaeli', 'Gebze', ['İmalat', 'Lojistik'], ['2024-02'], 9, 0),
  kayit('Kahramanmaraş', 'Onikişubat', ['İnşaat'], ['2023-12'], 6, 0),
];
const motor = olustur(VERI);
const adlar = (sonuc) => sonuc.map((r) => `${r.kayit.il}/${r.kayit.ilce}`);

test('normalize: Türkçe harfleri ve büyük/küçük harfi katlar', () => {
  assert.equal(normalize('İSTANBUL'), 'istanbul');
  assert.equal(normalize('Isparta'), 'isparta');
  assert.equal(normalize('ısparta'), 'isparta');
  assert.equal(normalize('Şanlıurfa'), 'sanliurfa');
  assert.equal(normalize('Kahramanmaraş'), 'kahramanmaras');
  assert.equal(normalize('  ÇANKAYA   '), 'cankaya');
});

test('aksan duyarsız ve büyük/küçük harf duyarsız eşleşir', () => {
  assert.deepEqual(adlar(motor.ara('sisli')), ['İstanbul/Şişli']);
  assert.deepEqual(adlar(motor.ara('ISPARTA')), ['Isparta/Merkez']);
  assert.deepEqual(adlar(motor.ara('kahramanmaras')), ['Kahramanmaraş/Onikişubat']);
});

test('varsayılan tam sözcük eşleşir; önek yalnızca * ile gelir', () => {
  assert.deepEqual(adlar(motor.ara('kad')), []);
  assert.deepEqual(adlar(motor.ara('kad*')), ['İstanbul/Kadıköy']);
  assert.deepEqual(adlar(motor.ara('kad', { jokerEkle: true })), ['İstanbul/Kadıköy']);
});

test('birden çok terim VE ile birleşir; any:1 ile VEYA olur', () => {
  assert.deepEqual(adlar(motor.ara('istanbul insaat')), ['İstanbul/Kadıköy']);
  const veya = adlar(motor.ara('any:1 sisli gebze')).sort();
  assert.deepEqual(veya, ['Kocaeli/Gebze', 'İstanbul/Şişli']);
});

test('olumsuzlama: -sözcük ve -alan:değer', () => {
  assert.deepEqual(adlar(motor.ara('istanbul -kadikoy')), ['İstanbul/Şişli']);
  assert.deepEqual(
    adlar(motor.ara('sektor:insaat -il:istanbul')).sort(),
    ['Ankara/Çankaya', 'Kahramanmaraş/Onikişubat']
  );
});

test('alan filtreleri: il, ilce, sektor (joker destekli)', () => {
  assert.deepEqual(adlar(motor.ara('il:ankara')), ['Ankara/Çankaya']);
  assert.deepEqual(adlar(motor.ara('ilce:kad*')), ['İstanbul/Kadıköy']);
  assert.deepEqual(adlar(motor.ara('sektor:lojistik')), ['Kocaeli/Gebze']);
  assert.deepEqual(adlar(motor.ara('il:"kahramanmaraş"')), ['Kahramanmaraş/Onikişubat']);
});

test('tarih filtresi: YYYY, YYYYMM ve YYYY-AA', () => {
  assert.equal(motor.ara('tarih:2023').length, 1);
  assert.equal(motor.ara('tarih:2024').length, 5);
  assert.deepEqual(adlar(motor.ara('tarih:202403')), ['Isparta/Merkez']);
  assert.deepEqual(adlar(motor.ara('tarih:2024-03')), ['Isparta/Merkez']);
  assert.equal(motor.ara('-tarih:2024').length, 1);
});

test('olumlu filtresi', () => {
  assert.deepEqual(adlar(motor.ara('olumlu:1')).sort(), ['Isparta/Merkez', 'İstanbul/Şişli']);
  assert.equal(motor.ara('olumlu:0').length, 4);
});

test('geçersiz filtre değerleri SorguHatasi fırlatır', () => {
  assert.throws(() => motor.ara('olumlu:2'), SorguHatasi);
  assert.throws(() => motor.ara('-olumlu:1'), SorguHatasi);
  assert.throws(() => motor.ara('tarih:dun'), SorguHatasi);
});

test('bilinmeyen "ad:" bir filtre değil, düz metindir', () => {
  const c = sorguCozumle('foo:bar');
  assert.equal(c.filtreler.length, 0);
  assert.deepEqual(c.metinler[0].sozcukler, ['foo', 'bar']);
});

test('tırnaklı ifade ardışık sözcük ister', () => {
  const veri = olustur([
    kayit('Mersin', 'Akdeniz', ['Gemi Söküm'], ['2024-01'], 3, 0),
    kayit('Mersin', 'Toroslar', ['Söküm', 'Gemi'], ['2024-01'], 5, 0),
  ]);
  assert.equal(veri.ara('sektor:gemi').length, 1);
  assert.deepEqual(adlar(veri.ara('"gemi sokum"')), ['Mersin/Akdeniz']);
  assert.equal(veri.ara('gemi sokum').length, 2);
});

test('başlıkta (il/ilçe) eşleşenler gövdede (sektör/tarih) eşleşenden önce gelir', () => {
  const veri = olustur([
    kayit('Ankara', 'Merkez', ['Kocaeli Tersanesi'], ['2024-01'], 99, 0),
    kayit('Kocaeli', 'Gebze', ['İmalat'], ['2024-01'], 1, 0),
  ]);
  assert.deepEqual(adlar(veri.ara('kocaeli')), ['Kocaeli/Gebze', 'Ankara/Merkez']);
});

test('eşit ağırlıkta kaza sayısı büyük olan önce gelir', () => {
  assert.deepEqual(adlar(motor.ara('sektor:insaat')), [
    'İstanbul/Kadıköy',
    'Ankara/Çankaya',
    'Kahramanmaraş/Onikişubat',
  ]);
});

test('sonuçlar hangi alanlarda eşleştiğini bildirir', () => {
  const [r] = motor.ara('insaat kadikoy');
  assert.deepEqual(r.alanlar.sort(), ['ilce', 'sektor']);
});

test('boş / yalnızca boşluk sorgusu sonuç döndürmez', () => {
  assert.deepEqual(motor.ara(''), []);
  assert.deepEqual(motor.ara('   '), []);
  assert.deepEqual(motor.ara('*'), []);
});

test('sinir seçeneği sonucu kısaltır', () => {
  assert.equal(motor.ara('tarih:2024', { sinir: 2 }).length, 2);
});
