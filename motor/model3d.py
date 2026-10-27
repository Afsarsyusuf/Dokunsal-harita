"""2D katmanlardan 3D basılabilir model üretimi (manifold3d ile).

Katman düzeni (alttan üste):
- Taban plakası
- Araç yolları: tabana oyulmuş kanal
- Yaya yolları: tabandan hafif kabartma çizgi
- Binalar: en yüksek kabartma
- Çerçeve ve kuzey işareti: yön bulmayı kolaylaştıran kenar kabartması

manifold3d, boolean işlemlerden sonra modelin her zaman kapalı ve basılabilir
(su geçirmez) kalmasını sağlar.
"""

import numpy as np
import manifold3d as mf
import trimesh

from . import braille

mf.set_circular_segments(24)
_E = 0.01  # birleşim yerlerinde boşluk kalmaması için küçük bindirme


def _kesit(geom):
    """Shapely alan geometrisini manifold3d CrossSection'a çevirir."""
    halkalar = []
    parcalar = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
    for p in parcalar:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        halkalar.append(np.asarray(p.exterior.coords)[:-1, :2])
        for ic in p.interiors:
            halkalar.append(np.asarray(ic.coords)[:-1, :2])
    if not halkalar:
        return None
    return mf.CrossSection(halkalar, mf.FillRule.EvenOdd)


def _yukselt(geom, z_alt, yukseklik):
    k = _kesit(geom)
    if k is None:
        return None
    return k.extrude(yukseklik).translate([0, 0, z_alt])


def plaka_olculeri(ayar):
    """Plakanın genişliği ve yüksekliği (mm): harita + çerçeve + üst bant."""
    g = ayar["cerceve_genislik_mm"]
    H = ayar["harita_mm"]
    return H + 2 * g, H + 3 * g + ayar["ust_bant_mm"]


def model_olustur(katmanlar, ayar, baslik=None, anahtarlar=None):
    g = ayar["cerceve_genislik_mm"]
    H = ayar["harita_mm"]
    W, L = plaka_olculeri(ayar)
    T = ayar["taban_kalinlik_mm"]
    h = ayar["cerceve_yukseklik_mm"]

    model = mf.Manifold.cube([W, L, T])

    # Araç yolları: kanal
    d = ayar["arac_yolu_derinlik_mm"]
    if not katmanlar["arac_yollari"].is_empty:
        kanal = _yukselt(katmanlar["arac_yollari"], T - d, d + 1.0)
        if kanal is not None:
            model = model - kanal

    # Yaya yolları: hafif kabartma
    if not katmanlar["yaya_yollari"].is_empty:
        y = _yukselt(katmanlar["yaya_yollari"], T - _E, ayar["yaya_yolu_yukseklik_mm"] + _E)
        if y is not None:
            model = model + y

    # Binalar
    if not katmanlar["binalar"].is_empty:
        b = _yukselt(katmanlar["binalar"], T - _E, ayar["bina_yukseklik_mm"] + _E)
        if b is not None:
            model = model + b

    # Çerçeve ve harita ile üst bandı ayıran çizgi
    cerceve = (mf.CrossSection.square([W, L])
               - mf.CrossSection.square([H, H]).translate([g, g])
               - mf.CrossSection.square([H, ayar["ust_bant_mm"]]).translate([g, H + 2 * g]))
    model = model + cerceve.extrude(h + _E).translate([0, 0, T - _E])

    # Kuzey işareti: üst bandın sol tarafında, yukarıyı gösteren üçgen
    if ayar.get("kuzey_isareti", True):
        y0 = H + 2 * g
        b_ = ayar["ust_bant_mm"]
        ucgen = mf.CrossSection([np.array([[g + 4, y0 + 2], [g + 12, y0 + 2], [g + 8, y0 + b_ - 2]])])
        model = model + ucgen.extrude(h + _E).translate([0, 0, T - _E])

    # Braille başlık: üst bantta, kuzey işaretinin sağında
    if baslik:
        y0 = H + 2 * g
        b_ = ayar["ust_bant_mm"]
        _, hh = braille.hucre_boyutu(ayar)
        x0 = g + 18
        bas = braille.braille_modeli(baslik, x0, y0 + b_ - (b_ - hh) / 2, T, ayar)
        if braille.metin_genisligi(baslik, ayar) > W - g - x0:
            print("  Uyarı: başlık üst banda sığmıyor, kısaltın.")
        if bas is not None:
            model = model + bas

    # Bina anahtarları: binanın üst yüzeyinde tek harf
    if anahtarlar:
        z = T + ayar["bina_yukseklik_mm"]
        for k, _, (x, y) in anahtarlar:
            nk = braille.braille_modeli(k, x, y, z, ayar)
            if nk is not None:
                model = model + nk

    return model


def stl_kaydet(model, dosya_yolu):
    mesh = model.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                         faces=np.asarray(mesh.tri_verts), process=True)
    tm.export(dosya_yolu)
    return tm
