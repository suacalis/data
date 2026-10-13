# Joplin Notes arama sistemi: nasıl çalışır, kanıtlar ve bu projeye uyarlama

Bu belge `REA` (rea-agents 6.4.0) ile yapılan incelemenin kaydıdır. Amaç, bir not uygulamasındaki
aramanın nasıl çalıştığını **kaynak koduna bakmadan, dağıtılan paketten** çıkarmak ve benzer bir
özelliği bu projenin haritasına eklemekti.

## 1. İncelenen hedef

| | |
|---|---|
| Uygulama | Joplin Desktop 3.7.21 (Electron, açık kaynak) |
| Dosya | `Joplin-3.7.21.AppImage` (github.com/laurent22/joplin/releases/tag/v3.7.21) |
| AppImage SHA-256 | `5d202dcaca31e14206826aa3f04125e7c218dbc3dc3d98479d811efbd6b856c1` |
| İncelenen artefakt | `resources/app.asar`, SHA-256 `767df409…a33a` |
| Lisans | AGPL-3.0-or-later (`package.json`) |

`app.asar` AppImage çalıştırılmadan, squashfs olarak açılarak (`unsquashfs -o 944632`) çıkarıldı.

## 2. REA ne yaptı, neyi yapamadı

Komut:

```bash
npx -y rea-agents@latest analyze-javascript-application app.asar \
  --format json --full-output --max-heap-mb 4096 --integrity-policy record-and-continue
```

Süre 438 sn; çıktı 247 MB kanıt paketi (`predicate_type: rea.javascript-application-analysis`,
`authority: shipped-artifact`). `root_artifact_sha256` yukarıdaki `app.asar` özetiyle aynı.

REA'nın bulduğu: 5.379 dosya, 3.368 ayrıştırılan JS dosyası, 1.218 modül, 6 `BrowserWindow`,
71 IPC işlemi. Ayrıca paketin gömülü kaynak haritasından, arama ile ilgili 13 **özgün kaynak
modülünün yolunu** kurtardı (aşağıda seçilmiş olanlar) ve `gui/` altında arama arayüzü dosyalarını
çözümledi:

```
../lib/services/search/SearchEngine.ts        ../lib/services/search/filterParser.ts
../lib/services/search/SearchEngineUtils.ts   ../lib/services/search/queryBuilder.ts
../lib/services/search/gotoAnythingStyleQuery.ts   ../lib/services/ai/SearchService.ts
gui/SearchBar/SearchBar.tsx   gui/lib/SearchInput/SearchInput.tsx   gui/NoteSearchBar.tsx   …
```

**Sınırlama (önemli):** REA'nın sonuç bütçesi bu uygulama için yetmedi. Arama motorunun içinde
bulunduğu iki büyük pakette (`main.bundle.js`, `main-html.bundle.js`) REA'nın anlamsal analizi
**başlatılmadı** (`coverage.status: "partial"`, "semantic analysis of main.bundle.js was not
started"). Yani REA arama modüllerinin **varlığını ve dosya yapısını** kanıtladı, ama
algoritmanın içini bu çalıştırmada kendisi çıkarmadı. Algoritma aşağıdaki kanıtlar için
`main.bundle.js`'nin (esbuild ile minify edilmiş) ilgili bölümü okunarak çıkarıldı; REA'nın
kurtardığı modül yolları bu bölümün hangi özgün dosyalara karşılık geldiğini doğruluyor.

## 3. Arama hattı ve kanıtlar

Konumlar `main.bundle.js` (SHA-256 `4f7d939b…9a37`) içindeki bayt ofsetleridir. Değişken
adları minify edildiği için kısa alıntılar sadeleştirilmiştir.

### 3.1 İndeks: SQLite FTS4 + normalleştirilmiş kopya tablo
- `notes_fts`, FTS4 sanal tablosudur ve **ham `notes` değil, `notes_normalized` tablosunu** indeksler
  (ofset 11803302):
  `CREATE VIRTUAL TABLE notes_fts USING fts4(content="notes_normalized", …)`
- Metin indekslenmeden önce normalleştirilir (`normalizeText_`): Unicode normalize, bir ek metin
  temizleme adımı, HTML varlıklarını çöz, boşlukları tek tipe indir, **küçük harfe çevir ve aksan
  sil** (`removeDiacritics`, ofset 7036425). Sorgu da aynı işlevden geçer, bu yüzden aksan duyarsızdır.
- İndeks güncelliği: `item_changes` tablosu `id > lastProcessedChangeId` ile 10'ar satır okunur;
  oluştur/güncelle → satırı sil + yeniden ekle, sil → satırı sil
  (`searchEngine.lastProcessedChangeId`, ofset 9646156). Senkron `setTimeout(…, 1e4)` ile 10 sn
  gecikmeli planlanır (`scheduleSyncTables`).

### 3.2 Sorgu sözdizimi (`filterParser.ts`)
- Terimler boşlukla ayrılır; tırnak içindeki boşluk bölmez; yalnızca **bilinen** bir filtre
  adından sonraki ilk `:` filtre ayırıcısıdır (ofset 11695402):
  `any, title, body, tag, notebook, created, updated, type, iscompleted, due, latitude,
  longitude, altitude, resource, sourceurl, id`.
- `-terim` ve `-filtre:değer` olumsuzlama; `type` ve `iscompleted` olumsuzlanamaz ve değerleri
  doğrulanır (`"iscompleted" must be "1" or "0"`).
- `any:1` varsayılan ilişkiyi AND'den OR'a çevirir (`getDefaultRelation`, ofset 11704473).

### 3.3 Eşleşme (`queryBuilder.ts`)
- Metin terimleri `notes_fts MATCH ?` ile eşleşir; birden çok terim AND, `any:1` ile OR.
- `tag`/`notebook`/`resource` filtreleri `LIKE ?` ile, `*` → `%` çevrilerek eşleşir;
  defter filtresi `WITH RECURSIVE` ile alt defterleri de kapsar.
- SQLite FTS4 jeton (sözcük) eşleştirir; önek eşleşmesi için terime `*` eklenmesi gerekir
  (FTS4'ün belgelenmiş davranışı; Joplin koduna ayrıca bir önek mantığı eklenmemiş).
- Yazarken arama yolunda `appendWildCards: true` verilir (ofset 13087971), yani kullanıcı
  `kad` yazınca `kad*` aranır.

### 3.4 Sıralama (`SearchEngine.ts`)
- SQL, FTS `matchinfo(notes_fts, 'pcnalx')` ve `offsets(notes_fts)` döndürür (ofset 11704728).
- BM25 elle hesaplanır: `k1 = 1.2`, `b = 0.75`,
  `IDF = max(ln((N − n + 0.5)/(n + 0.5) + 1), 0)`; **başlık ve gövde sütunları ayrı** hesaplanıp
  toplanır. Üzerine güncellik terimi eklenir: `200 · ln(1 + 1/max(gün, 0.5))` (ofset 11717074).
- Sonuç sıralaması: **başlıkta eşleşen önce**, sonra ağırlık, tamamlanmış yapılacaklar sona,
  eşitlikte `user_updated_time`.
- Hangi alanda eşleştiği `offsets` içindeki sütun numarasından çıkarılır (sonuçta
  `fields: ['title'|'body']`).

### 3.5 Arama türü seçimi
`determineSearchType_`: FTS kapalıysa `basic` (LIKE); metin Japonca/Çince/Korece/Tayca ise
`nonlatin`; aksi halde `fts`. Ek olarak, bayrak açık ve yapay zekâ sağlayıcısı varsa
`semantic` (gömme vektörleri, kosinüs benzerliği) sonuçlara eklenip tekilleştirilir.

### 3.6 Arayüz (`gui/SearchBar/SearchBar.tsx`, `app.asar` içinde gönderilen kaynak)
- Her tuş vuruşunda değil, **500 ms debounce** ile arar (`debounce(search, 500)`).
- Kutu boşalınca aramadan çıkar ve önceki seçime/klasöre döner (`onExitSearch`).
- `Escape` aramadan çıkar ve odağı bırakır.
- Sonuçlar `SEARCH_UPDATE` + `SEARCH_SELECT` eylemleriyle Redux'a gider; sorgu daha sonra
  `notesForQuery(query, true, { appendWildCards: true })` ile çalıştırılır.

## 4. Bu projeye uyarlama

| Joplin | Burada | Not |
|---|---|---|
| SQLite FTS4 (`notes_fts`) | Bellek içi sözcük indeksi (`arama/arama_motoru.js`) | Veri küçük (il/ilçe sayısı); sunucu ve veritabanı gerekmez, HTML tek dosya kalır |
| `normalizeText_` + aksan silme | `normalize()`; **Türkçe `İ/I/ı → i`** katlaması | Joplin'de bu yok; `Isparta` ↔ `ısparta` ↔ `İsparta` için eklendi |
| Alan filtreleri | `il:` `ilce:` `sektor:` `tarih:` `olumlu:` `any:` | `tarih` eşitlik/önek (Joplin `created:` ≥ karşılaştırır) |
| `-olumsuz`, `"ifade"`, `*` | Aynı | |
| `appendWildCards` | `jokerEkle` seçeneği, arayüz her zaman açar | |
| BM25 (başlık/gövde sütunu) | Aynı formül; başlık = il+ilçe, gövde = sektör+tarih | |
| Güncellik ağırlığı | **Yok**; eşitlikte `kaza_sayisi` büyük olan önce | Veride zaman damgası yerine ay bilgisi var |
| Debounce 500 ms | 250 ms | Bellek içi olduğu için kısaltıldı |
| `any:1` | Pozitif koşullar OR, olumsuzlar her zaman dışlar | Joplin OR'da olumsuzları da birleştirir; daha sezgisel olan seçildi |
| `onExitSearch` / Escape | Aynı; harita ilk görünüme döner | |
| Anlamsal arama, OCR, spellfix | Yok | Kapsam dışı |

**Lisans notu:** Joplin AGPL-3.0'dır. Buradaki motor Joplin kodundan kopyalanmadı; yukarıdaki
gözlenen davranıştan sıfırdan yazıldı. Algoritmalar (BM25, FTS tarzı eşleşme) bilinen
yöntemlerdir.

## 5. Doğrulama

- `node --test arama/arama_motoru.test.js`: 16 test (Türkçe katlama, önek, VE/VEYA, olumsuzlama,
  filtreler, hata durumları, sıralama). Motorda kasıtlı hata yapılınca 8 test düşüyor.
- `python3 -m unittest discover -s arama -p "test_*.py"`: 4 test (kayıt üretimi, JSON/Jinja kaçışı).
- Gerçek Chromium'da uçtan uca 13 senaryo geçti: debounce, önek, aksan duyarsızlığı, sonuca
  tıklayınca popup, filtre sözdizimi, hata mesajı, ok tuşları + Enter, Escape ile görünüme dönüş,
  HTML enjeksiyonu, konsol hatası yok.

## 6. Yeniden üretme

```bash
# 1. İndir ve çıkar (AppImage'ı çalıştırmadan)
curl -L -o Joplin.AppImage https://github.com/laurent22/joplin/releases/download/v3.7.21/Joplin-3.7.21.AppImage
unsquashfs -o 944632 -d joplin -f Joplin.AppImage resources/app.asar   # ofset bu dosyaya özgü: ELF bölüm tablosunun sonu

# 2. REA ile analiz et
npx -y rea-agents@latest analyze-javascript-application joplin/resources/app.asar --format json --full-output
```
