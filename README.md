# Dokunsal Harita Üretici: Motor ve Sunucu (v0.4)

Bir bölgenin OpenStreetMap verisinden 3D yazıcıda basılabilir dokunsal harita (STL) üretir.

## Bu sürümde neler var?

- OpenStreetMap'ten bina ve yol verisini otomatik çekme (yer adıyla ya da koordinatla); sunucu meşgulse otomatik yeniden deneme ve alternatif sunucuya geçme
- Metreden baskı milimetresine ölçekleme
- Yolların sınıflandırılması: ana yol, tali yol, yaya yolu; çift şeritli yolların tek kanalda birleştirilmesi
- Sadeleştirme: yakın binaları birleştirme, köşeleri sadeleştirme (Douglas-Peucker), çok küçük binaları eleme
- Binaları yollardan belli bir boşluk kadar uzak tutma
- 3D katmanlar:
  - Taban plakası
  - Araç yolları: tabana oyulmuş kanal
  - Yaya yolları: hafif kabartma çizgi
  - Binalar: en yüksek kabartma
  - Çerçeve
  - Üst bantta kuzey işareti (bu bant ileride Braille başlık için de kullanılacak)
- Türkçe Braille (ç, ğ, ı, ö, ş, ü ve sayılar dahil), kubbe biçimli noktalar
  - Üst bantta Braille başlık (`--baslik`)
  - Adı olan binaların üzerinde tek harflik Braille anahtar (a, b, c...)
  - Bina adı dosyası (`bina_adlari.csv`): OpenStreetMap'te adı olmayan binalara ad verme, uzun adları kısaltma
  - Anahtarların açıklamalarını içeren ayrı Braille lejant plakası (`_lejant.stl`) ve metin listesi (`_lejant.txt`)
- Web sunucusu (FastAPI): web arayüzünün motoru kullanabilmesi için API
- Basılabilir (kapalı) model kontrolü
- 2D katman önizlemesi ve 3D görüntü (rapor için)

**Henüz yok:** AutoCAD/DXF iç mekân (ileride).

**Uyarı:** Türkçe harflerin Braille karşılıkları baskıdan önce Braille bilen biri tarafından kontrol edilmelidir. Kontrol için `_lejant.txt` dosyasında Braille karşılıkları Unicode karakterlerle (⠃⠕⠵⠕⠅) yazılıdır.

## Kurulum (Windows)

1. Python 3.10 veya üstünü kur: https://www.python.org/downloads/
   (Kurulumda **"Add Python to PATH"** kutusunu işaretle.)
2. Bu klasörde bir komut satırı aç: klasörün adres çubuğuna `cmd` yazıp Enter'a bas.
3. Sanal ortam oluşturup gerekli kütüphaneleri kur:

```
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Aşağıdaki komutlarda `python` yerine `.venv\Scripts\python.exe` yaz.

## Çalıştırma

Yer adıyla:

```
python -m motor --yer "Yozgat Bozok Üniversitesi" --cikti cikti/kampus.stl
```

Koordinatla (Google Haritalar'da bir noktaya sağ tıklayınca çıkan ilk satır enlem, boylamdır):

```
python -m motor --merkez 39.80 34.80 --cikti cikti/kampus.stl
```

Alanı değiştirmek için (örneğin 600 m × 600 m):

```
python -m motor --merkez 39.80 34.80 --alan 600 --cikti cikti/kampus600.stl
```

İnternetsiz deneme (yapay örnek veriyle):

```
python -m motor --geojson ornek/ornek_veri.geojson --merkez 39.0 35.0 --cikti cikti/ornek.stl
```

Braille başlıkla:

```
python -m motor --merkez 39.775 34.796 --alan 600 --baslik "bozok kampüs" --cikti cikti/kampus.stl
```

Her çalıştırmada şu dosyalar oluşur:
- `kampus.stl`: 3D yazıcı için harita modeli (Cura veya PrusaSlicer'da açılır)
- `kampus.png`: katmanların renkli önizlemesi (bina anahtarları harflerle gösterilir)
- `kampus_lejant.stl` ve `kampus_lejant.txt`: adı olan bina varsa Braille lejant plakası ve liste

## Web sunucusu

Web arayüzü motoru bu sunucu üzerinden kullanır. Ayrıntılı belge: `API_BELGESI.docx`.

```
.venv\Scripts\python.exe -m uvicorn sunucu:app --reload
```

- Sunucu adresi: http://127.0.0.1:8000
- Tarayıcıda test sayfası: http://127.0.0.1:8000/docs
  (Her uç noktayı "Try it out" düğmesiyle deneyebilirsin. İnternetsiz deneme için isteğe `"ornek_veri": true` ekle.)
- Üretilen dosyalar `sunucu_cikti/` klasörüne kaydedilir.
- Sunucuyu durdurmak için komut satırında Ctrl+C.

## Bina adı dosyası

OpenStreetMap'te çoğu binanın adı girilmemiştir. Haritada hangi binaların hangi adla etiketleneceğini kendin belirleyebilirsin:

1. `bina_adlari_ornek.csv` dosyasını kopyala ve adını `bina_adlari.csv` yap.
2. Her bina için bir satır yaz: `enlem,boylam,ad`
   - Enlem/boylam: binanın içinde herhangi bir nokta. Google Haritalar'da binaya sağ tıklayınca çıkan ilk satır.
   - Ad: haritada görünecek kısa ad (ör. `mühendislik fakültesi`).
3. Programı normal şekilde çalıştır. `bina_adlari.csv` klasörde varsa otomatik kullanılır. Başka bir dosya için: `--adlar dosya.csv`

Kurallar:
- Dosyadaki adlar OpenStreetMap'teki adlardan önceliklidir ve dosyadaki sırayla anahtar alır (ilk satır a, ikinci b...).
- Nokta binanın tam içinde değilse en fazla 5 metre uzaklıktaki bina kabul edilir (`ad_eslesme_toleransi_m`).
- Sadece kendi adlarını kullanmak istersen `ayarlar.json` içinde `"osm_adlarini_kullan": false` yap.
- Dosya Excel'de açılıp kaydedilebilir (noktalı virgüllü Türkçe biçim de okunur).
- Bir nokta haritadaki bir binaya denk gelmezse program uyarı verir.
- Bina çok küçükse üzerine anahtar sığmaz; bu durumda da uyarı verilir.

## 3D görüntü

Rapor için (yaklaşık 20 saniye sürer):

```
python -m motor.render3d cikti/kampus.stl cikti/kampus_3d.png
```

## Ayarlar

Tüm ölçüler `ayarlar.json` dosyasında, baskı üzerindeki milimetre cinsindendir. Kodu değiştirmeden buradan ayarlanır:

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| alan_m | 400 | Haritadaki kare alanın kenarı (metre) |
| harita_mm | 170 | Baskıdaki harita alanının kenarı (mm) |
| taban_kalinlik_mm | 3.0 | Taban plakası kalınlığı |
| bina_yukseklik_mm | 3.0 | Binaların tabandan yüksekliği |
| arac_yolu_derinlik_mm | 1.0 | Araç yolu kanalının derinliği |
| ana_yol_genislik_mm / tali_yol_genislik_mm | 2.5 / 1.8 | Yol kanalı genişlikleri |
| yol_birlestirme_mm | 1.5 | Bu mesafeden yakın yol kanalları (ör. çift şeritli yollar) tek kanalda birleşir |
| yaya_yolu_yukseklik_mm / genislik_mm | 0.8 / 1.0 | Yaya yolu kabartması |
| bina_birlestirme_mm | 1.0 | Bu mesafeden yakın binalar birleştirilir |
| min_bina_alan_mm2 | 16 | Bundan küçük binalar elenir (yaklaşık 4 × 4 mm) |
| bina_yol_boslugu_mm | 1.0 | Bina ile yol arasındaki en az boşluk |
| braille_nokta_cap_mm / yukseklik_mm | 1.6 / 0.6 | Braille nokta ölçüleri (baskıdaki küçülmeyi telafi için biraz büyük) |
| braille_nokta_aralik_mm | 2.5 | Hücre içindeki noktalar arası mesafe |
| braille_hucre_aralik_mm | 6.2 | Harfler (hücreler) arası mesafe |
| braille_satir_aralik_mm | 10.0 | Lejant satırları arası mesafe |
| bina_anahtarlari | true | Bina anahtarları eklensin mi |
| osm_adlarini_kullan | true | OpenStreetMap'teki bina adları da kullanılsın mı |
| ad_eslesme_toleransi_m | 5 | Bina adı noktası binanın en fazla kaç metre dışında olabilir |

Bu değerler başlangıç önerisidir. Kesin değerler test baskıları ve mimarların sembol çalışmasına göre güncellenecek.

## Klasör yapısı

```
dokunsal-harita/
├── ayarlar.json        Tüm ölçü ayarları
├── bina_adlari_ornek.csv  Bina adı dosyası şablonu
├── requirements.txt    Gerekli kütüphaneler
├── sunucu.py           Web sunucusu (FastAPI)
├── API_BELGESI.docx    Web arayüzü için API belgesi (Kader)
├── motor/
│   ├── __main__.py     Komut satırı (programı başlatan dosya)
│   ├── uretim.py       Harita üretiminin tüm adımları (komut satırı ve sunucu ortak kullanır)
│   ├── veri.py         OpenStreetMap / GeoJSON veri alma
│   ├── sadelestir.py   Ölçekleme, sınıflandırma, sadeleştirme
│   ├── model3d.py      3D model üretimi ve STL kaydetme
│   ├── braille.py      Türkçe Braille, bina anahtarları, lejant plakası
│   ├── onizleme.py     2D katman önizlemesi
│   └── render3d.py     3D görüntü (rapor için)
├── ornek/              İnternetsiz test verisi
├── cikti/              Komut satırıyla üretilen dosyalar
├── sunucu_cikti/       Sunucuyla üretilen dosyalar
└── cache/              İndirilen OpenStreetMap verisinin önbelleği
```
