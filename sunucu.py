"""Dokunsal Harita Üretici - Web sunucusu (FastAPI).

Çalıştırma:
    .venv\\Scripts\\python.exe -m uvicorn sunucu:app --reload

Ardından tarayıcıda:
    http://127.0.0.1:8000/docs   -> tüm uç noktaları deneyebileceğin otomatik test sayfası

Web arayüzü bu sunucuya JSON ile istek gönderir. Ayrıntılar: API_BELGESI.docx
"""

import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from motor import braille, veri
from motor.uretim import KOK, ayarlari_yukle, harita_uret

SURUM = "0.4"
CIKTI = KOK / "sunucu_cikti"
ORNEK_VERI = KOK / "ornek" / "ornek_veri.geojson"
DOSYA_TURLERI = {
    "harita_stl": "model/stl",
    "lejant_stl": "model/stl",
    "onizleme_png": "image/png",
    "lejant_txt": "text/plain; charset=utf-8",
}
_kilit = threading.Semaphore(2)  # aynı anda en fazla 2 harita üretilir


class UTF8JSONResponse(JSONResponse):
    """Türkçe karakterlerin her istemcide doğru görünmesi için kodlamayı açıkça belirtir."""
    media_type = "application/json; charset=utf-8"

app = FastAPI(
    title="Dokunsal Harita Üretici API",
    version=SURUM,
    description="OpenStreetMap verisinden 3D basılabilir, Braille etiketli dokunsal harita üretir.",
    default_response_class=UTF8JSONResponse,
)
# Geliştirme aşamasında web arayüzü farklı bir adresten çalışabilsin diye tüm kaynaklara izin verilir.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _turkce_sorun(h):
    t, ctx = h.get("type", ""), h.get("ctx", {}) or {}
    sablon = {
        "missing": "Bu alan zorunludur.",
        "greater_than_equal": "En az {ge} olmalıdır.",
        "less_than_equal": "En fazla {le} olmalıdır.",
        "string_too_long": "En fazla {max_length} karakter olabilir.",
        "string_too_short": "En az {min_length} karakter olmalıdır.",
        "float_parsing": "Sayı olmalıdır.",
        "float_type": "Sayı olmalıdır.",
        "string_type": "Metin olmalıdır.",
        "bool_parsing": "true ya da false olmalıdır.",
        "list_type": "Liste olmalıdır.",
        "dict_type": "Nesne (sözlük) olmalıdır.",
        "json_invalid": "Geçerli bir JSON değil.",
    }.get(t)
    try:
        return sablon.format(**ctx) if sablon else h.get("msg", "Geçersiz değer.")
    except (KeyError, IndexError):
        return h.get("msg", "Geçersiz değer.")


@app.exception_handler(RequestValidationError)
def _dogrulama_hatasi(istek: Request, hata: RequestValidationError):
    """Geçersiz istekleri de diğer hatalarla aynı biçimde ve Türkçe döndürür."""
    alanlar = []
    for h in hata.errors():
        alan = ".".join(str(x) for x in h.get("loc", []) if x != "body")
        alanlar.append({"alan": alan, "sorun": _turkce_sorun(h)})
    return UTF8JSONResponse(status_code=400, content={"detail": {
        "kod": "gecersiz_istek",
        "mesaj": "İstekteki bazı alanlar geçersiz: " + ", ".join(a["alan"] for a in alanlar),
        "alanlar": alanlar,
    }})


def _hata(durum, kod, mesaj):
    raise HTTPException(status_code=durum, detail={"kod": kod, "mesaj": mesaj})


# ---------- Veri modelleri ----------

class Konum(BaseModel):
    enlem: float = Field(..., ge=-90, le=90, examples=[39.775014])
    boylam: float = Field(..., ge=-180, le=180, examples=[34.796303])


class BinaAdi(BaseModel):
    enlem: float = Field(..., ge=-90, le=90)
    boylam: float = Field(..., ge=-180, le=180)
    ad: str = Field(..., min_length=1, max_length=80, examples=["mühendislik fakültesi"])


class HaritaIstegi(BaseModel):
    merkez: Optional[Konum] = Field(None, description="Harita merkezi. 'yer' verilmezse zorunlu.")
    yer: Optional[str] = Field(None, description="Yer adı (ör. 'Yozgat Bozok Üniversitesi'). 'merkez' verilmezse kullanılır.")
    alan_m: float = Field(600, ge=100, le=2000, description="Kare alanın kenarı (metre).")
    baslik: Optional[str] = Field(None, max_length=40, description="Üst bantta Braille ile yazılacak başlık.")
    bina_adlari: list[BinaAdi] = Field(default_factory=list, description="Binalara verilecek adlar. Sırayla a, b, c... anahtarlarını alır.")
    ayarlar: dict = Field(default_factory=dict, description="İsteğe bağlı ölçü değişiklikleri (ör. {\"bina_yukseklik_mm\": 3.5}).")
    ornek_veri: bool = Field(False, description="true: internet kullanmadan yapay örnek veriyle üretir (geliştirme ve test için).")


class BrailleIstegi(BaseModel):
    metin: str = Field(..., min_length=1, max_length=200, examples=["bozok kampüs"])


# ---------- Uç noktalar ----------

@app.get("/api/saglik", summary="Sunucu çalışıyor mu?")
def saglik():
    return {"durum": "calisiyor", "surum": SURUM}


@app.get("/api/ayarlar", summary="Varsayılan ölçü ayarları")
def ayarlar():
    return {k: v for k, v in ayarlari_yukle().items() if not k.startswith("_")}


@app.get("/api/konum", summary="Yer adını koordinata çevir")
def konum(yer: str):
    try:
        enlem, boylam = veri.yer_adindan_koordinat(yer)
    except Exception:
        _hata(404, "yer_bulunamadi", f"'{yer}' için konum bulunamadı.")
    return {"yer": yer, "enlem": enlem, "boylam": boylam}


@app.post("/api/braille", summary="Metni Braille'e çevir (önizleme)")
def braille_cevir(istek: BrailleIstegi):
    ayar = ayarlari_yukle()
    hucreler, atlanan = braille.metinden_hucreler(istek.metin)
    from motor.model3d import plaka_olculeri
    W, _ = plaka_olculeri(ayar)
    genislik = braille.metin_genisligi(istek.metin, ayar)
    baslik_sigar = genislik <= W - ayar["cerceve_genislik_mm"] - (ayar["cerceve_genislik_mm"] + 18)
    return {
        "metin": istek.metin,
        "braille": braille.unicode_goster(istek.metin),
        "hucre_sayisi": len(hucreler),
        "genislik_mm": round(genislik, 1),
        "baslik_olarak_sigar": baslik_sigar,
        "cevrilemeyen_karakterler": sorted(atlanan),
    }


def _dosya_adresleri(harita_id, dosyalar):
    return {tur: f"/api/harita/{harita_id}/dosya/{tur}" for tur in dosyalar}


@app.post("/api/harita", summary="Dokunsal harita üret")
def harita(istek: HaritaIstegi):
    if istek.ornek_veri:
        enlem, boylam, geojson = 39.0, 35.0, ORNEK_VERI
    elif istek.merkez:
        enlem, boylam, geojson = istek.merkez.enlem, istek.merkez.boylam, None
    elif istek.yer:
        try:
            enlem, boylam = veri.yer_adindan_koordinat(istek.yer)
        except Exception:
            _hata(404, "yer_bulunamadi", f"'{istek.yer}' için konum bulunamadı.")
        geojson = None
    else:
        _hata(400, "konum_eksik", "'merkez' ya da 'yer' alanlarından biri verilmelidir.")

    try:
        ayar = ayarlari_yukle(degisiklikler=istek.ayarlar)
    except KeyError as e:
        _hata(400, "gecersiz_ayar", str(e).strip("'\""))

    harita_id = uuid.uuid4().hex[:12]
    klasor = CIKTI / harita_id
    with _kilit:
        try:
            sonuc = harita_uret(
                klasor, enlem=enlem, boylam=boylam, alan_m=istek.alan_m, baslik=istek.baslik,
                bina_adlari=[(b.enlem, b.boylam, b.ad) for b in istek.bina_adlari],
                geojson=geojson, ayar=ayar, dosya_adi="harita",
            )
        except RuntimeError as e:  # OpenStreetMap'e ulaşılamadı
            _hata(503, "veri_alinamadi", f"Harita verisi alınamadı, biraz sonra tekrar deneyin. ({str(e)[:150]})")
        except Exception as e:
            _hata(500, "uretim_hatasi", f"Harita üretilirken hata oluştu: {str(e)[:200]}")

    cevap = {
        "id": harita_id,
        "durum": "tamam",
        "ozet": sonuc["ozet"],
        "baslik": sonuc["baslik"],
        "baslik_braille": sonuc["baslik_braille"],
        "anahtarlar": sonuc["anahtarlar"],
        "uyarilar": sonuc["uyarilar"],
        "aciklama": sonuc["aciklama"],
        "dosyalar": _dosya_adresleri(harita_id, sonuc["dosyalar"]),
    }
    (klasor / "sonuc.json").write_text(json.dumps(cevap, ensure_ascii=False, indent=2), encoding="utf-8")
    return cevap


@app.get("/api/harita/{harita_id}", summary="Daha önce üretilen haritanın bilgileri")
def harita_bilgisi(harita_id: str):
    yol = CIKTI / harita_id / "sonuc.json"
    if not harita_id.isalnum() or not yol.exists():
        _hata(404, "harita_bulunamadi", "Bu kimlikle üretilmiş bir harita yok.")
    return json.loads(yol.read_text(encoding="utf-8"))


@app.get("/api/harita/{harita_id}/dosya/{tur}", summary="Üretilen dosyayı indir")
def dosya(harita_id: str, tur: str):
    if tur not in DOSYA_TURLERI or not harita_id.isalnum():
        _hata(404, "dosya_bulunamadi", "Geçersiz dosya türü.")
    adlar = {"harita_stl": "harita.stl", "lejant_stl": "harita_lejant.stl",
             "onizleme_png": "harita.png", "lejant_txt": "harita_lejant.txt"}
    yol = CIKTI / harita_id / adlar[tur]
    if not yol.exists():
        _hata(404, "dosya_bulunamadi", "Bu harita için bu dosya yok (ör. anahtar yoksa lejant üretilmez).")
    indirme_adi = f"dokunsal_harita_{harita_id}_{adlar[tur]}"
    return FileResponse(yol, media_type=DOSYA_TURLERI[tur], filename=indirme_adi)
