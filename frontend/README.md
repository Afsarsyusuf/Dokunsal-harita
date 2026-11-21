# Web Arayüzü (frontend)

Sunucu `backend` klasöründe çalıştırıldığında bu site otomatik olarak http://127.0.0.1:8000 adresinden açılır. Ayrı bir sunucu gerekmez.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `index.html` | Sayfa yapısı: harita formu, önizleme ve sonuç, önceki haritalar, proje hakkında |
| `stil.css` | Görünüm (renk teması, yazı tipi, düzen) |
| `uygulama.js` | Backend bağlantısı: konum arama, Braille önizleme, harita üretme, sonuç ekranı, önceki haritalar |
| `ses.js` | Ses katmanı: sesli rehber, sesli komut, sayfayı sesli okuma, haritayı sesli anlatma |
| `fonts/` | Atkinson Hyperlegible yazı tipi (Braille Institute, SIL OFL lisansı) |
| `gorseller/` | Örnek çıktı görseli |

## Backend'e bağlanma

API isteklerinde göreli adres kullanılır (`/api/harita` gibi). Uç noktalar, istek/yanıt biçimleri ve hata kodları: `backend/API_BELGESI.docx`. Denemek için: http://127.0.0.1:8000/docs (internetsiz deneme için istekte `"ornek_veri": true`).

## Erişilebilirlik ilkeleri

- Asıl kullanım ekran okuyucu (NVDA, JAWS, VoiceOver, TalkBack) ve klavyeyle. Her alanın görünür etiketi var, durum mesajları `role="status"` ile bildirilir, hatalı alan işaretlenip odak oraya taşınır.
- Sesli rehber isteğe bağlıdır ve kendiliğinden başlamaz (ekran okuyucuyla üst üste konuşmaması için).
- Sesli komut: <kbd>Alt</kbd>+<kbd>K</kbd> (Chrome / Edge). Yeni komut eklemek için `uygulama.js` içindeki `Ses.komutEkle(...)` satırlarına bakın.
- Yeni bir alan eklenirse `data-rehber="..."` özelliğiyle sesli rehberin okuyacağı açıklama yazılır.
