"""Harita verisinin alınması.

İki kaynak desteklenir:
- OpenStreetMap (internet gerekir): bir merkez noktası veya yer adı verilir.
- GeoJSON dosyası (internetsiz test için): 'building' ve 'highway' özelliklerini içeren bir dosya.

Açık Overpass sunucuları zaman zaman yoğun olur. Bu yüzden istek başarısız olursa
bekleyip yeniden denenir ve sırayla alternatif sunuculara geçilir.
"""

import time
import geopandas as gpd

OVERPASS_SUNUCULARI = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
]


def osm_den_cek(enlem, boylam, alan_m, deneme=3):
    """Merkez noktası çevresindeki binaları ve yolları OpenStreetMap'ten çeker.

    Kare alanın köşelerini kaçırmamak için yarıçap, karenin yarı köşegeni kadar alınır.
    """
    import osmnx as ox

    ox.settings.use_cache = True  # aynı bölge tekrar istendiğinde internete gitmez
    ox.settings.requests_timeout = 180
    yaricap = alan_m / 2 * 1.45
    etiketler = {"building": True, "highway": True}

    son_hata = None
    for sunucu in OVERPASS_SUNUCULARI:
        ox.settings.overpass_url = sunucu
        bekle = 10
        for i in range(deneme):
            try:
                print(f"Veri isteniyor: {sunucu} (deneme {i + 1}/{deneme})")
                gdf = ox.features_from_point((enlem, boylam), tags=etiketler, dist=yaricap)
                return gdf.reset_index()
            except Exception as hata:  # sunucu meşgul, zaman aşımı vb.
                son_hata = hata
                ilk_satir = str(hata).splitlines()[0][:120]
                print(f"  Başarısız: {ilk_satir}")
                if i < deneme - 1:
                    print(f"  {bekle} sn sonra yeniden denenecek...")
                    time.sleep(bekle)
                    bekle *= 2
    raise RuntimeError(f"OpenStreetMap verisi alınamadı. Son hata: {son_hata}")


def yer_adindan_koordinat(yer_adi):
    """Yer adını (ör. 'Yozgat Bozok Üniversitesi') enlem/boylama çevirir."""
    import osmnx as ox

    enlem, boylam = ox.geocode(yer_adi)
    return enlem, boylam


def geojson_dan_oku(dosya_yolu):
    """GeoJSON dosyasını okur. Koordinatlar WGS84 (enlem/boylam) olmalıdır."""
    gdf = gpd.read_file(dosya_yolu)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


def bina_adlarini_oku(dosya_yolu):
    """Bina adı dosyasını okur. Sütunlar: enlem, boylam, ad.

    Hem virgülle (39.77380,34.79512,mühendislik) hem de Türkçe Excel'in kaydettiği
    noktalı virgül ve ondalık virgül biçimiyle (39,77380;34,79512;mühendislik) çalışır.
    '#' ile başlayan satırlar açıklama olarak atlanır.
    """
    import csv
    from pathlib import Path

    ham = Path(dosya_yolu).read_bytes()
    try:
        metin = ham.decode("utf-8-sig")
    except UnicodeDecodeError:
        metin = ham.decode("cp1254")  # Türkçe Excel'in varsayılan kodlaması
    satirlar = [s for s in metin.splitlines() if s.strip() and not s.lstrip().startswith("#")]
    if not satirlar:
        return []
    ayirici = ";" if satirlar[0].count(";") >= 2 else ","
    sonuc = []
    for no, kayit in enumerate(csv.reader(satirlar, delimiter=ayirici), start=1):
        if len(kayit) < 3:
            continue
        e, b, ad = kayit[0].strip(), kayit[1].strip(), ayirici.join(kayit[2:]).strip()
        if no == 1 and e.lower() in ("enlem", "lat", "latitude"):
            continue  # başlık satırı
        try:
            sonuc.append((float(e.replace(",", ".")), float(b.replace(",", ".")), ad))
        except ValueError:
            print(f"  Uyarı: bina adı dosyasında okunamayan satır atlandı: {kayit}")
    return sonuc
