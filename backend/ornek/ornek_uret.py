"""İnternetsiz test için kampüse benzeyen yapay bir GeoJSON üretir (gerçek veri değildir)."""
import json, math
LAT, LON = 39.0, 35.0
mx = 1 / (111320 * math.cos(math.radians(LAT)))  # metre -> boylam
my = 1 / 110540                                 # metre -> enlem
def p(x, y): return [LON + x * mx, LAT + y * my]
def rect(x, y, w, h): return [[p(x, y), p(x + w, y), p(x + w, y + h), p(x, y + h), p(x, y)]]
F = []
def bina(x, y, w, h, t="university", ad=None):
    pr = {"building": t}
    if ad: pr["name"] = ad
    F.append({"type": "Feature", "properties": pr, "geometry": {"type": "Polygon", "coordinates": rect(x, y, w, h)}})
def yol(pts, t): F.append({"type": "Feature", "properties": {"highway": t}, "geometry": {"type": "LineString", "coordinates": [p(*q) for q in pts]}})
# Ana yol (kampüsün güneyinden geçen), tali yollar, yaya yolları
yol([(-250, -150), (250, -140)], "secondary")
yol([(-60, -145), (-60, 220)], "service")
yol([(-60, 60), (180, 60), (180, -142)], "service")
yol([(-200, -148), (-200, 120), (-60, 120)], "residential")
yol([(-60, 0), (20, 0), (20, 140), (120, 140)], "footway")
yol([(60, 60), (60, 180)], "footway")
yol([(-150, 120), (-150, 200)], "path")
# Binalar: fakülteler, kütüphane, yemekhane, yurt, küçük ek binalar
bina(-40, 10, 50, 35, ad="Mühendislik Fakültesi"); bina(30, 10, 60, 30); bina(100, 10, 60, 35, ad="Fen Edebiyat Fakültesi")
bina(30, 80, 25, 45); bina(75, 80, 80, 40, "library", ad="Merkez Kütüphane")
bina(-180, 0, 40, 90, "dormitory", ad="Öğrenci Yurdu"); bina(-130, 0, 40, 90, "dormitory", ad="Öğrenci Yurdu")
bina(-40, 150, 70, 40, ad="Yemekhane"); bina(80, 160, 40, 25)
bina(130, -100, 30, 30); bina(165, -100, 8, 6, "shed")  # çok küçük bina: elenmeli
bina(-30, -110, 22, 18); bina(-6, -110, 22, 18)          # birbirine yakın: birleşmeli
json.dump({"type": "FeatureCollection", "features": F}, open("ornek/ornek_veri.geojson", "w"))
print(len(F), "öğe yazıldı")
