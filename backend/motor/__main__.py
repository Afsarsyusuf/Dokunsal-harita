"""Dokunsal harita motoru - komut satırı.

Örnekler:
  python -m motor --yer "Yozgat Bozok Üniversitesi" --cikti cikti/kampus.stl
  python -m motor --merkez 39.775 34.796 --alan 600 --baslik "bozok kampüs" --cikti cikti/kampus.stl
  python -m motor --geojson ornek/ornek_veri.geojson --merkez 39.0 35.0 --cikti cikti/ornek.stl
"""

import argparse
from pathlib import Path

from . import veri
from .uretim import KOK, ayarlari_yukle, harita_uret


def main():
    p = argparse.ArgumentParser(description="Coğrafi veriden 3D basılabilir dokunsal harita üretir.")
    kaynak = p.add_mutually_exclusive_group()
    kaynak.add_argument("--yer", help="Yer adı (OpenStreetMap'te aranır)")
    kaynak.add_argument("--geojson", help="İnternetsiz test için GeoJSON dosyası")
    p.add_argument("--merkez", nargs=2, type=float, metavar=("ENLEM", "BOYLAM"), help="Harita merkezi")
    p.add_argument("--alan", type=float, help="Kare alanın kenarı (metre). Varsayılan ayarlar.json")
    p.add_argument("--baslik", help="Üst bantta Braille ile yazılacak başlık (ör. 'bozok kampüs')")
    p.add_argument("--adlar", help="Bina adı dosyası (CSV: enlem, boylam, ad). Varsayılan: bina_adlari.csv varsa o kullanılır")
    p.add_argument("--ayarlar", default=str(KOK / "ayarlar.json"))
    p.add_argument("--cikti", default=str(KOK / "cikti" / "harita.stl"))
    a = p.parse_args()

    if not a.merkez and not a.yer:
        p.error("--merkez veya --yer verilmelidir.")
    if a.geojson and not a.merkez:
        p.error("--geojson ile birlikte --merkez verilmelidir.")

    adlar_yolu = Path(a.adlar) if a.adlar else KOK / "bina_adlari.csv"
    bina_adlari = []
    if adlar_yolu.exists():
        bina_adlari = veri.bina_adlarini_oku(adlar_yolu)
        print(f"Bina adı dosyası: {adlar_yolu.name} ({len(bina_adlari)} ad)")
    elif a.adlar:
        p.error(f"Bina adı dosyası bulunamadı: {adlar_yolu}")

    cikti = Path(a.cikti)
    enlem, boylam = (a.merkez if a.merkez else (None, None))
    print("Harita üretiliyor...")
    sonuc = harita_uret(cikti.parent, enlem=enlem, boylam=boylam, yer=a.yer, alan_m=a.alan,
                        baslik=a.baslik, bina_adlari=bina_adlari, geojson=a.geojson,
                        ayar=ayarlari_yukle(a.ayarlar), dosya_adi=cikti.stem)

    o = sonuc["ozet"]
    print(f"Merkez: {o['merkez']['enlem']:.6f}, {o['merkez']['boylam']:.6f} | Alan: {o['alan_m']:.0f} m | "
          f"Plaka: {o['plaka_mm'][0]:.0f} x {o['plaka_mm'][1]:.0f} mm | Ölçek {o['olcek']}")
    print(f"Bina: {o['bina_sayisi']} | Basılabilir model: {o['basilabilir']} | Üçgen: {o['ucgen_sayisi']}")
    if sonuc["baslik"]:
        print(f"Başlık: {sonuc['baslik']}  ->  {sonuc['baslik_braille']}")
    for k in sonuc["anahtarlar"]:
        print(f"  {k['anahtar']}: {k['ad']}")
    for u in sonuc["uyarilar"]:
        print(f"Uyarı: {u}")
    for ad, yol in sonuc["dosyalar"].items():
        print(f"Dosya ({ad}): {yol}")


if __name__ == "__main__":
    main()
