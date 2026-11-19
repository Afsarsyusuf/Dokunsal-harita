"""Coğrafi veriyi baskı ölçeğine dönüştürme ve dokunsal okumaya uygun hâle getirme.

Adımlar:
1. Veriyi metrik koordinat sistemine (UTM) çevir.
2. Merkez etrafındaki kare alanı kırp.
3. Metreden baskı milimetresine ölçekle (harita alanı: çerçevenin içi).
4. Yolları sınıflandır (ana / tali / yaya), çizgi genişliği ver, çok yakın kanalları birleştir.
5. Yakın binaları birleştir, köşeleri sadeleştir (Douglas-Peucker), çok küçükleri at.
6. Binaları yollardan belli bir boşluk kadar uzak tut.
"""

from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union
import geopandas as gpd


def _olcekle(geom, merkez_x, merkez_y, olcek, harita_mm, kenar):
    geom = affinity.translate(geom, xoff=-merkez_x, yoff=-merkez_y)
    geom = affinity.scale(geom, xfact=olcek, yfact=olcek, origin=(0, 0))
    return affinity.translate(geom, xoff=kenar + harita_mm / 2, yoff=kenar + harita_mm / 2)


def _poligonlar(geom):
    """Geometriden yalnızca alan (poligon) parçalarını döndürür."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if hasattr(geom, "geoms"):
        return [g for g in geom.geoms if g.geom_type == "Polygon"]
    return []


def katmanlari_hazirla(gdf, enlem, boylam, ayar, ek_adlar=None):
    """GeoDataFrame'den baskı ölçeğinde katmanlar üretir.

    Dönen sözlük: 'binalar', 'arac_yollari', 'yaya_yollari' (shapely alan geometrisi, mm) ve
    'isimli_binalar' (adı olan binaların [(ad, poligon), ...] listesi).

    ek_adlar: kullanıcının bina adı dosyasından gelen [(enlem, boylam, ad), ...] listesi.
    Bu adlar OpenStreetMap'teki adlardan önceliklidir ve dosyadaki sırayla anahtar alır.
    """
    alan_m = ayar["alan_m"]
    H = ayar["harita_mm"]
    g = ayar["cerceve_genislik_mm"]
    olcek = H / alan_m  # 1 metre kaç mm

    # 1. Metrik koordinat sistemi
    utm = gdf.estimate_utm_crs()
    gdf = gdf.to_crs(utm)
    merkez = gpd.GeoSeries([Point(boylam, enlem)], crs="EPSG:4326").to_crs(utm).iloc[0]

    # 2. Kırpma alanı
    yarim = alan_m / 2
    kare = box(merkez.x - yarim, merkez.y - yarim, merkez.x + yarim, merkez.y + yarim)
    gdf = gdf[gdf.geometry.intersects(kare)].copy()
    gdf["geometry"] = gdf.geometry.intersection(kare)

    sinif = ayar["yol_siniflari"]
    ana, tali, yaya = [], [], []
    bina_ham = []
    bina_kayit = []  # (poligon, OpenStreetMap adı)

    for _, satir in gdf.iterrows():
        geom = _olcekle(satir.geometry, merkez.x, merkez.y, olcek, H, g)
        if geom.is_empty:
            continue
        bina = satir.get("building")
        yol = satir.get("highway")
        if isinstance(bina, str) and bina and bina != "no":
            parcalar = _poligonlar(geom)
            bina_ham.extend(parcalar)
            if parcalar:
                ad = satir.get("name")
                ad = ad.strip() if isinstance(ad, str) and ad.strip() else None
                bina_kayit.append((unary_union(parcalar), ad))
        elif isinstance(yol, str):
            if geom.geom_type in ("LineString", "MultiLineString"):
                if yol in sinif["ana"]:
                    ana.append(geom)
                elif yol in sinif["tali"]:
                    tali.append(geom)
                elif yol in sinif["yaya"]:
                    yaya.append(geom)

    # Bina adları: önce kullanıcının dosyası, sonra OpenStreetMap
    isimli, kullanilan = [], set()
    tolerans = ayar.get("ad_eslesme_toleransi_m", 5) * olcek
    for e, b, ad in (ek_adlar or []):
        nokta_utm = gpd.GeoSeries([Point(b, e)], crs="EPSG:4326").to_crs(utm).iloc[0]
        nokta = _olcekle(nokta_utm, merkez.x, merkez.y, olcek, H, g)
        adaylar = [(i, p.distance(nokta)) for i, (p, _) in enumerate(bina_kayit) if p.distance(nokta) <= tolerans]
        if not adaylar:
            print(f"  Uyarı: '{ad}' için verilen nokta harita alanında bir binaya denk gelmiyor ({e}, {b}).")
            continue
        i = min(adaylar, key=lambda x: x[1])[0]
        if i in kullanilan:
            print(f"  Uyarı: '{ad}' ile aynı binaya daha önce bir ad verilmiş, atlandı.")
            continue
        kullanilan.add(i)
        isimli.append((ad, bina_kayit[i][0]))
    if ayar.get("osm_adlarini_kullan", True):
        for i, (p, ad) in enumerate(bina_kayit):
            if ad and i not in kullanilan:
                isimli.append((ad, p))

    # 4. Yollara genişlik ver (çizgiyi alana çevir)
    arac = unary_union(
        [c.buffer(ayar["ana_yol_genislik_mm"] / 2) for c in ana]
        + [c.buffer(ayar["tali_yol_genislik_mm"] / 2) for c in tali]
    )
    # Çift şeritli yollar gibi birbirine çok yakın kanalları tek kanalda birleştir
    yb = ayar.get("yol_birlestirme_mm", 0)
    if yb and not arac.is_empty:
        arac = arac.buffer(yb, join_style="round").buffer(-yb, join_style="round")
    yaya_alan = unary_union([c.buffer(ayar["yaya_yolu_genislik_mm"] / 2) for c in yaya])
    if not arac.is_empty:
        yaya_alan = yaya_alan.difference(arac.buffer(0.5))

    # 5. Bina sadeleştirme
    k = ayar["bina_birlestirme_mm"]
    binalar = unary_union(bina_ham).buffer(k, join_style="mitre").buffer(-k, join_style="mitre")
    binalar = binalar.simplify(ayar["sadelestirme_tolerans_mm"], preserve_topology=True)

    # 6. Binaları yollardan uzak tut
    bosluk = ayar["bina_yol_boslugu_mm"]
    tum_yollar = unary_union([arac, yaya_alan])
    if not tum_yollar.is_empty:
        binalar = binalar.difference(tum_yollar.buffer(bosluk))

    binalar = unary_union(
        [p for p in _poligonlar(binalar) if p.area >= ayar["min_bina_alan_mm2"]]
    )

    # Çerçevenin içinde kalan kısım
    ic = box(g, g, g + H, g + H)
    binalar = binalar.intersection(ic)
    return {
        "binalar": binalar,
        "isimli_binalar": [(ad, p) for ad, p in isimli if p.intersects(binalar)],
        "arac_yollari": arac.intersection(ic) if not arac.is_empty else arac,
        "yaya_yollari": yaya_alan.intersection(ic) if not yaya_alan.is_empty else yaya_alan,
    }
