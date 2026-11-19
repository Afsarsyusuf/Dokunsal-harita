# Dokunsal Harita Üretici

Görme engelli bireyler için OpenStreetMap verisinden 3D yazıcıda basılabilir, Türkçe Braille etiketli dokunsal (kabartma) harita üreten sistem.

Yozgat Bozok Üniversitesi, Bilgisayar Mühendisliği, Tasarım Uygulama Projesi.

## Klasörler

| Klasör | İçerik |
|---|---|
| `backend/` | Harita üretim motoru (Python) ve web sunucusu (FastAPI) |
| `frontend/` | Görme engelli kullanıcıların da kullanabileceği web arayüzü |

## Çalıştırma

1. Backend kurulumu: `backend/README.md` dosyasındaki adımlar (bir kere yapılır).
2. `backend` klasöründe sunucuyu başlat:

```
.venv\Scripts\python.exe -m uvicorn sunucu:app --reload
```

3. Tarayıcıda aç:
   - http://127.0.0.1:8000 : web arayüzü (`frontend/index.html` varsa)
   - http://127.0.0.1:8000/docs : API test sayfası

Arayüz ile sunucu aynı adresten çalıştığı için arayüz API'ye doğrudan `/api/...` adresleriyle istek gönderir. API'nin ayrıntıları: `backend/API_BELGESI.docx`.

## Ortak çalışma

- Çalışmaya başlamadan önce: `git pull`
- Herkes kendi klasöründe çalışır (backend: `backend/`, arayüz: `frontend/`).
- Göndermek için: `git add .` → `git commit -m "ne yapıldı"` → `git push`
