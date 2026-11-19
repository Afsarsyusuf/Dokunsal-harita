"""Harita üretiminin tamamını tek fonksiyonda toplar.

Hem komut satırı (__main__.py) hem de web sunucusu (sunucu.py) bu fonksiyonu kullanır.
"""

import contextlib
import copy
import io
import json
from pathlib import Path

from . import veri, sadelestir, model3d, onizleme, braille

KOK = Path(__file__).resolve().parent.parent


def ayarlari_yukle(yol=None, degisiklikler=None):
    """ayarlar.json dosyasını okur; verilen değişiklikleri üzerine uygular."""
    yol = Path(yol) if yol else KOK / "ayarlar.json"
    ayar = json.loads(yol.read_text(encoding="utf-8"))
    for k, v in (degisiklikler or {}).items():
        if k not in ayar or k.startswith("_"):
            raise KeyError(f"Bilinmeyen ayar: {k}")
        ayar[k] = v
    return ayar


def _aciklama(ozet, anahtarlar, baslik):
    """Ekran okuyucular için haritanın kısa metin açıklaması."""
    parcalar = []
    if baslik:
        parcalar.append(f"{baslik} haritası.")
    parcalar.append(
        f"Harita {ozet['alan_m']:.0f} metreye {ozet['alan_m']:.0f} metrelik bir alanı gösteriyor, "
        f"plaka boyutu {ozet['plaka_mm'][0]:.0f} milimetreye {ozet['plaka_mm'][1]:.0f} milimetre."
    )
    parcalar.append(
        f"Haritada {ozet['bina_sayisi']} bina kabartması, araç yolları kanal olarak"
        + (", yaya yolları ince kabartma olarak" if ozet["yaya_yolu_var"] else "")
        + " yer alıyor. Kuzey, plakanın üst kenarındaki üçgen işaretle gösteriliyor."
    )
    if anahtarlar:
        liste = ", ".join(f"{k}: {ad}" for k, ad, _ in anahtarlar)
        parcalar.append(f"Braille anahtarlı binalar: {liste}.")
    else:
        parcalar.append("Haritada Braille anahtarlı bina yok.")
    return " ".join(parcalar)


def harita_uret(cikti_klasoru, enlem=None, boylam=None, yer=None, alan_m=None, baslik=None,
                bina_adlari=None, geojson=None, ayar=None, dosya_adi="harita"):
    """Haritayı üretir, dosyaları cikti_klasoru'na yazar ve sonuç özetini döndürür.

    bina_adlari: [(enlem, boylam, ad), ...]
    Döner: sözlük (özet, anahtarlar, uyarılar, dosya yolları, erişilebilir açıklama).
    """
    ayar = copy.deepcopy(ayar) if ayar else ayarlari_yukle()
    if alan_m:
        ayar["alan_m"] = float(alan_m)
    cikti_klasoru = Path(cikti_klasoru)
    cikti_klasoru.mkdir(parents=True, exist_ok=True)

    gunluk = io.StringIO()  # program mesajları; uyarılar buradan ayıklanır
    with contextlib.redirect_stdout(gunluk):
        if enlem is None or boylam is None:
            if not yer:
                raise ValueError("Merkez koordinatı ya da yer adı verilmelidir.")
            enlem, boylam = veri.yer_adindan_koordinat(yer)

        gdf = veri.geojson_dan_oku(geojson) if geojson else veri.osm_den_cek(enlem, boylam, ayar["alan_m"])
        katmanlar = sadelestir.katmanlari_hazirla(gdf, enlem, boylam, ayar, ek_adlar=bina_adlari or [])
        anahtarlar = (braille.anahtar_yerlestir(katmanlar["binalar"], katmanlar["isimli_binalar"], ayar)
                      if ayar.get("bina_anahtarlari", True) else [])
        model = model3d.model_olustur(katmanlar, ayar, baslik=baslik, anahtarlar=anahtarlar)

        dosyalar = {}
        stl = cikti_klasoru / f"{dosya_adi}.stl"
        tm = model3d.stl_kaydet(model, stl)
        dosyalar["harita_stl"] = stl
        png = cikti_klasoru / f"{dosya_adi}.png"
        onizleme.ciz(katmanlar, ayar, png, anahtarlar=anahtarlar)
        dosyalar["onizleme_png"] = png

        if anahtarlar:
            lejant, _ = braille.lejant_modeli(anahtarlar, model3d.plaka_olculeri(ayar)[0], ayar)
            lstl = cikti_klasoru / f"{dosya_adi}_lejant.stl"
            tl = model3d.stl_kaydet(lejant, lstl)
            dosyalar["lejant_stl"] = lstl
            txt = cikti_klasoru / f"{dosya_adi}_lejant.txt"
            with open(txt, "w", encoding="utf-8") as f:
                f.write("Anahtar | Bina adı | Braille\n")
                for k, ad, _ in anahtarlar:
                    f.write(f"{k} | {ad} | {braille.unicode_goster(k + ' ' + ad)}\n")
            dosyalar["lejant_txt"] = txt
        else:
            tl = None

    mesajlar = [s.strip() for s in gunluk.getvalue().splitlines() if s.strip()]
    uyarilar = [s.replace("Uyarı: ", "") for s in mesajlar if s.startswith("Uyarı")]
    etiketsiz = len(katmanlar["isimli_binalar"]) - len(anahtarlar)
    if etiketsiz > 0:
        uyarilar.append(f"Adı olan {etiketsiz} bina, üzerine anahtar sığmadığı veya aynı ad tekrar ettiği için etiketlenmedi.")

    W, L = model3d.plaka_olculeri(ayar)
    binalar = katmanlar["binalar"]
    ozet = {
        "merkez": {"enlem": enlem, "boylam": boylam},
        "alan_m": ayar["alan_m"],
        "plaka_mm": [round(W, 1), round(L, 1)],
        "olcek": f"1:{ayar['alan_m'] * 1000 / ayar['harita_mm']:.0f}",
        "bina_sayisi": len(sadelestir._poligonlar(binalar)) if not binalar.is_empty else 0,
        "yaya_yolu_var": not katmanlar["yaya_yollari"].is_empty,
        "basilabilir": bool(tm.is_watertight and (tl is None or tl.is_watertight)),
        "ucgen_sayisi": int(len(tm.faces)),
    }
    return {
        "ozet": ozet,
        "baslik": baslik,
        "baslik_braille": braille.unicode_goster(baslik) if baslik else None,
        "anahtarlar": [{"anahtar": k, "ad": ad, "braille": braille.unicode_goster(f"{k} {ad}")} for k, ad, _ in anahtarlar],
        "uyarilar": uyarilar,
        "aciklama": _aciklama(ozet, anahtarlar, baslik),
        "dosyalar": dosyalar,
        "mesajlar": mesajlar,
    }
