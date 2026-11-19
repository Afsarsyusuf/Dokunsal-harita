"""Üretilen haritaların kaydı (SQLite).

SQLite Python ile birlikte gelir; ayrı bir sunucu ya da kurulum gerekmez.
Tüm kayıtlar tek bir dosyada tutulur: backend/haritalar.db

Her haritanın bilgileri (yer, başlık, merkez, alan, bina anahtarları, dosya adresleri)
burada saklanır. STL ve diğer dosyalar yine sunucu_cikti/<id>/ klasöründedir.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from motor.uretim import KOK

DB = KOK / "haritalar.db"

_TABLO = """
CREATE TABLE IF NOT EXISTS haritalar (
    id              TEXT PRIMARY KEY,
    olusturma       TEXT NOT NULL,
    yer             TEXT,
    baslik          TEXT,
    enlem           REAL,
    boylam          REAL,
    alan_m          REAL,
    bina_sayisi     INTEGER,
    istek_anahtari  TEXT,
    aranacak        TEXT,
    sonuc           TEXT NOT NULL
)
"""


def _kucuk(metin):
    """Türkçeye uygun küçük harf (I -> ı, İ -> i)."""
    return (metin or "").replace("I", "ı").replace("İ", "i").lower()


@contextmanager
def _baglan():
    """Bağlantı açar; iş bitince kaydeder ve kapatır."""
    baglanti = sqlite3.connect(DB)
    baglanti.row_factory = sqlite3.Row
    try:
        baglanti.execute(_TABLO)
        baglanti.execute("CREATE INDEX IF NOT EXISTS ix_istek ON haritalar(istek_anahtari)")
        yield baglanti
        baglanti.commit()
    finally:
        baglanti.close()


def istek_anahtari(enlem, boylam, alan_m, baslik, bina_adlari, ayarlar, ornek_veri):
    """Aynı isteği tanımak için kısa bir özet üretir.

    Aynı merkez, alan, başlık, bina adları ve ayarlarla gelen istek aynı anahtarı alır.
    """
    veri = {
        "enlem": round(float(enlem), 6), "boylam": round(float(boylam), 6),
        "alan_m": float(alan_m), "baslik": baslik or "",
        "bina_adlari": [[round(a, 6), round(b, 6), ad] for a, b, ad in bina_adlari],
        "ayarlar": ayarlar or {}, "ornek_veri": bool(ornek_veri),
    }
    metin = json.dumps(veri, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def kaydet(cevap, yer=None, anahtar=None):
    """Üretilen haritanın bilgilerini kaydeder."""
    ozet = cevap["ozet"]
    aranacak = " ".join([yer or "", cevap.get("baslik") or ""] +
                        [k["ad"] for k in cevap.get("anahtarlar", [])])
    with _baglan() as b:
        b.execute(
            "INSERT OR REPLACE INTO haritalar VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cevap["id"], cevap["olusturma"], yer, cevap.get("baslik"),
             ozet["merkez"]["enlem"], ozet["merkez"]["boylam"], ozet["alan_m"],
             ozet["bina_sayisi"], anahtar, _kucuk(aranacak),
             json.dumps(cevap, ensure_ascii=False)),
        )


def getir(harita_id):
    """Bir haritanın tam bilgisini döndürür, yoksa None."""
    with _baglan() as b:
        satir = b.execute("SELECT sonuc FROM haritalar WHERE id = ?", (harita_id,)).fetchone()
    return json.loads(satir["sonuc"]) if satir else None


def istekle_bul(anahtar):
    """Aynı istekle daha önce üretilmiş haritayı döndürür, yoksa None."""
    with _baglan() as b:
        satir = b.execute(
            "SELECT sonuc FROM haritalar WHERE istek_anahtari = ? ORDER BY olusturma DESC, rowid DESC LIMIT 1",
            (anahtar,)).fetchone()
    return json.loads(satir["sonuc"]) if satir else None


def listele(ara=None, adet=20, atla=0):
    """Kayıtlı haritaları en yeniden eskiye listeler. 'ara' yer, başlık ve bina adlarında aranır."""
    kosul, degerler = "", []
    if ara:
        kosul = "WHERE aranacak LIKE ?"
        degerler.append(f"%{_kucuk(ara)}%")
    with _baglan() as b:
        toplam = b.execute(f"SELECT COUNT(*) FROM haritalar {kosul}", degerler).fetchone()[0]
        satirlar = b.execute(
            f"SELECT sonuc, yer FROM haritalar {kosul} ORDER BY olusturma DESC, rowid DESC LIMIT ? OFFSET ?",
            degerler + [adet, atla]).fetchall()
    haritalar = []
    for s in satirlar:
        c = json.loads(s["sonuc"])
        haritalar.append({
            "id": c["id"], "olusturma": c.get("olusturma"), "yer": s["yer"],
            "baslik": c.get("baslik"), "merkez": c["ozet"]["merkez"],
            "alan_m": c["ozet"]["alan_m"], "bina_sayisi": c["ozet"]["bina_sayisi"],
            "anahtarlar": [{"anahtar": k["anahtar"], "ad": k["ad"]} for k in c.get("anahtarlar", [])],
            "dosyalar": c["dosyalar"],
        })
    return toplam, haritalar


def sil(harita_id):
    """Kaydı siler. Silindiyse True döner."""
    with _baglan() as b:
        return b.execute("DELETE FROM haritalar WHERE id = ?", (harita_id,)).rowcount > 0


def eski_ciktilari_ekle(cikti_klasoru: Path):
    """Veritabanından önce üretilmiş (sadece sonuc.json'u olan) haritaları kayda ekler."""
    if not cikti_klasoru.exists():
        return
    for dosya in cikti_klasoru.glob("*/sonuc.json"):
        if getir(dosya.parent.name):
            continue
        try:
            cevap = json.loads(dosya.read_text(encoding="utf-8"))
            cevap.setdefault("olusturma", datetime.fromtimestamp(dosya.stat().st_mtime).isoformat(timespec="seconds"))
            kaydet(cevap)
        except (ValueError, KeyError):
            pass
