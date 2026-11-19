# Web Arayüzü (frontend)

Web arayüzü dosyaları bu klasöre konur. Giriş sayfası `index.html` olmalıdır.

## Backend'e bağlanma

- Sunucu `backend` klasöründe çalıştırıldığında bu klasördeki site otomatik olarak http://127.0.0.1:8000 adresinden açılır. Ayrı bir sunucu gerekmez.
- API isteklerinde tam adres yerine göreli adres kullanılır, örneğin:

```js
const cevap = await fetch("/api/harita", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ yer: "Yozgat Bozok Üniversitesi", alan_m: 600, baslik: "bozok kampüs" }),
});
const sonuc = await cevap.json();
```

- Uç noktalar, istek/yanıt biçimleri, hata kodları ve erişilebilirlik gereksinimleri: `backend/API_BELGESI.docx`
- Uç noktaları denemek için: http://127.0.0.1:8000/docs (internetsiz deneme için istekte `"ornek_veri": true`)

## Derleme aracı kullanılırsa

React, Vite vb. kullanılırsa derlenmiş çıktı `frontend/dist/` klasörüne alınmalıdır. Sunucu önce `dist/index.html` dosyasına bakar. Bu durumda `node_modules/` klasörü GitHub'a gönderilmez (`.gitignore` içinde var).
