"""Türkçe Braille (kısaltmasız) dönüşümü ve 3D Braille noktaları.

Hücre düzeni (nokta numaraları):
    1 4
    2 5
    3 6

ÖNEMLİ: Türkçe harflerin (ç, ğ, ı, ö, ş, ü) karşılıkları yaygın kullanılan Türkçe Braille
tablosundan alınmıştır. Baskıdan önce Braille bilen biri tarafından kontrol edilmelidir.

Ölçüler ayarlar.json'daki 'braille_*' değerlerinden okunur. FDM baskıda noktalar
tasarımdan yaklaşık %20-25 küçük çıktığı için (Żołek-Tryznowska vd., 2024) varsayılan
değerler hedef ölçülerden biraz büyük tutulmuştur.
"""

import numpy as np
import manifold3d as mf

HARFLER = {
    "a": (1,), "b": (1, 2), "c": (1, 4), "ç": (1, 6), "d": (1, 4, 5), "e": (1, 5),
    "f": (1, 2, 4), "g": (1, 2, 4, 5), "ğ": (1, 2, 6), "h": (1, 2, 5), "ı": (3, 5),
    "i": (2, 4), "j": (2, 4, 5), "k": (1, 3), "l": (1, 2, 3), "m": (1, 3, 4),
    "n": (1, 3, 4, 5), "o": (1, 3, 5), "ö": (2, 4, 6), "p": (1, 2, 3, 4),
    "q": (1, 2, 3, 4, 5), "r": (1, 2, 3, 5), "s": (2, 3, 4), "ş": (1, 4, 6),
    "t": (2, 3, 4, 5), "u": (1, 3, 6), "ü": (1, 2, 5, 6), "v": (1, 2, 3, 6),
    "w": (2, 4, 5, 6), "x": (1, 3, 4, 6), "y": (1, 3, 4, 5, 6), "z": (1, 3, 5, 6),
}
SAYI_ISARETI = (3, 4, 5, 6)
RAKAMLAR = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "e",
            "6": "f", "7": "g", "8": "h", "9": "i", "0": "j"}
NOKTALAMA = {".": (2, 5, 6), ",": (2,), "-": (3, 6), ":": (2, 5)}

# Nokta numarası -> hücre içindeki (sütun, satır) konumu
_KONUM = {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (1, 0), 5: (1, 1), 6: (1, 2)}


def _kucult(metin):
    """Türkçe'ye uygun küçük harf dönüşümü (I -> ı, İ -> i)."""
    return metin.replace("I", "ı").replace("İ", "i").lower()


def metinden_hucreler(metin):
    """Metni Braille hücrelerine çevirir. Her hücre bir nokta numarası demetidir; boşluk = ()."""
    hucreler, atlanan = [], set()
    sayi_modu = False
    for ch in _kucult(metin):
        if ch.isdigit():
            if not sayi_modu:
                hucreler.append(SAYI_ISARETI)
                sayi_modu = True
            hucreler.append(HARFLER[RAKAMLAR[ch]])
            continue
        sayi_modu = False
        if ch == " ":
            hucreler.append(())
        elif ch in HARFLER:
            hucreler.append(HARFLER[ch])
        elif ch in NOKTALAMA:
            hucreler.append(NOKTALAMA[ch])
        else:
            atlanan.add(ch)
    return hucreler, atlanan


def unicode_goster(metin):
    """Kontrol için Braille'i Unicode karakterleriyle gösterir (ör. ⠃⠕⠵⠕⠅)."""
    hucreler, _ = metinden_hucreler(metin)
    sonuc = ""
    for h in hucreler:
        kod = 0x2800 + sum(1 << (n - 1) for n in h)
        sonuc += chr(kod)
    return sonuc


def hucre_boyutu(ayar):
    """Bir hücrenin kapladığı genişlik ve yükseklik (mm), aralıklar dahil."""
    return ayar["braille_hucre_aralik_mm"], 2 * ayar["braille_nokta_aralik_mm"] + ayar["braille_nokta_cap_mm"]


def metin_genisligi(metin, ayar):
    hucreler, _ = metinden_hucreler(metin)
    if not hucreler:
        return 0.0
    return (len(hucreler) - 1) * ayar["braille_hucre_aralik_mm"] + ayar["braille_nokta_aralik_mm"] + ayar["braille_nokta_cap_mm"]


def _nokta(ayar):
    """Tek bir kubbe biçimli Braille noktası (taban çapı, yüksekliği ayarlardan)."""
    r = ayar["braille_nokta_cap_mm"] / 2
    h = ayar["braille_nokta_yukseklik_mm"]
    kure = mf.Manifold.sphere(r, 32).scale([1, 1, h / r])
    return kure.trim_by_plane([0, 0, 1], 0.0)


def braille_modeli(metin, sol_ust_x, sol_ust_y, z, ayar):
    """Metnin Braille noktalarını 3D olarak üretir.

    (sol_ust_x, sol_ust_y): ilk hücrenin 1 numaralı noktasının dış sol üst köşesi.
    z: noktaların oturduğu yüzeyin yüksekliği.
    """
    hucreler, atlanan = metinden_hucreler(metin)
    if atlanan:
        print(f"  Uyarı: Braille'e çevrilemeyen karakterler atlandı: {''.join(sorted(atlanan))}")
    r = ayar["braille_nokta_cap_mm"] / 2
    a = ayar["braille_nokta_aralik_mm"]
    s = ayar["braille_hucre_aralik_mm"]
    tek = _nokta(ayar)
    parcalar = []
    for i, h in enumerate(hucreler):
        for n in h:
            sx, sy = _KONUM[n]
            x = sol_ust_x + r + i * s + sx * a
            y = sol_ust_y - r - sy * a
            parcalar.append(tek.translate([x, y, z - 0.05]))
    if not parcalar:
        return None
    return mf.Manifold.batch_boolean(parcalar, mf.OpType.Add)


ANAHTARLAR = list("abcdefghijklmnoprstuvyz")  # tek hücrelik harf anahtarları


def anahtar_yerlestir(binalar, isimli_binalar, ayar):
    """Adı olan binaların üzerine sığıyorsa tek harflik anahtar yerleştirir.

    Döner: [(anahtar, ad, (x, y) hücrenin sol üst köşesi), ...]
    Aynı ada sahip birden çok parça varsa yalnızca biri etiketlenir.
    """
    from shapely.geometry import box
    from shapely.ops import polylabel

    w = ayar["braille_nokta_aralik_mm"] + ayar["braille_nokta_cap_mm"]
    _, h = hucre_boyutu(ayar)
    m = ayar.get("anahtar_kenar_boslugu_mm", 1.0)
    sonuc, gorulen = [], set()
    for ad, poligon in isimli_binalar:
        if len(sonuc) >= len(ANAHTARLAR):
            break
        anahtar_ad = ad.casefold()
        if anahtar_ad in gorulen:
            continue
        bolge = binalar.intersection(poligon)
        parcalar = [bolge] if bolge.geom_type == "Polygon" else [p for p in getattr(bolge, "geoms", []) if p.geom_type == "Polygon"]
        for parca in sorted(parcalar, key=lambda p: -p.area):
            merkez = polylabel(parca, tolerance=0.1)
            kutu = box(merkez.x - w / 2 - m, merkez.y - h / 2 - m, merkez.x + w / 2 + m, merkez.y + h / 2 + m)
            if parca.contains(kutu):
                sonuc.append((ANAHTARLAR[len(sonuc)], ad, (merkez.x - w / 2, merkez.y + h / 2)))
                gorulen.add(anahtar_ad)
                break
    return sonuc


def satirlara_bol(metin, en_fazla_hucre):
    """Metni kelime bütünlüğünü bozmadan satırlara böler."""
    satirlar, mevcut = [], ""
    for kelime in metin.split():
        aday = f"{mevcut} {kelime}".strip()
        if len(metinden_hucreler(aday)[0]) <= en_fazla_hucre:
            mevcut = aday
        else:
            if mevcut:
                satirlar.append(mevcut)
            mevcut = kelime
    if mevcut:
        satirlar.append(mevcut)
    return satirlar


def lejant_modeli(anahtarlar, genislik, ayar, baslik="anahtar"):
    """Anahtar listesinin Braille lejant plakasını üretir. Döner: (model, satır listesi)."""
    T = ayar["taban_kalinlik_mm"]
    kenar = 6.0
    en_fazla = int((genislik - 2 * kenar - ayar["braille_nokta_aralik_mm"] - ayar["braille_nokta_cap_mm"]) // ayar["braille_hucre_aralik_mm"]) + 1
    satirlar = [baslik]
    for k, ad, _ in anahtarlar:
        satirlar.extend(satirlara_bol(f"{k} {ad}", en_fazla))
    yukseklik = 2 * kenar + len(satirlar) * ayar["braille_satir_aralik_mm"]
    model = mf.Manifold.cube([genislik, yukseklik, T])
    for i, satir in enumerate(satirlar):
        y = yukseklik - kenar - i * ayar["braille_satir_aralik_mm"]
        b = braille_modeli(satir, kenar, y, T, ayar)
        if b is not None:
            model = model + b
    return model, satirlar
