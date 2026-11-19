"""STL dosyasının gölgelendirilmiş 3D görüntüsünü üretir (rapor ekran görüntüsü için).

Model yukarıdan ışın atılarak yükseklik haritasına çevrilir, sonra ışık-gölge ile çizilir.
"""
import sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource


def yukseklik_haritasi(tm, adim=0.4):
    mn, mx = tm.bounds
    xs = np.arange(mn[0] + adim / 2, mx[0], adim)
    ys = np.arange(mn[1] + adim / 2, mx[1], adim)
    X, Y = np.meshgrid(xs, ys)
    bas = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, mx[2] + 5)])
    yon = np.tile([0, 0, -1.0], (X.size, 1))
    Z = np.zeros(X.size)
    konum, ray_id, _ = tm.ray.intersects_location(bas, yon, multiple_hits=False)
    Z[ray_id] = konum[:, 2]
    return X, Y, Z.reshape(X.shape)


def ciz(stl_yolu, png_yolu, abart=2.0):
    tm = trimesh.load(stl_yolu)
    X, Y, Z = yukseklik_haritasi(tm)
    ls = LightSource(azdeg=315, altdeg=40)
    golge = ls.shade(Z * abart, cmap=plt.cm.Greys_r, vert_exag=1, blend_mode="soft", vmin=-2, vmax=Z.max() * abart + 4)
    fig = plt.figure(figsize=(13, 6.2), dpi=120)
    ax1 = fig.add_subplot(1, 2, 1)
    ax1.imshow(golge, origin="lower", extent=[X.min(), X.max(), Y.min(), Y.max()])
    ax1.set_title("Üstten görünüm (gölgelendirilmiş)"); ax1.set_xlabel("mm"); ax1.set_ylabel("mm")
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    s = 2
    ax2.plot_surface(X[::s, ::s], Y[::s, ::s], Z[::s, ::s] * abart, facecolors=golge[::s, ::s],
                     rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    ax2.set_box_aspect((1, 1, 0.25)); ax2.view_init(elev=55, azim=-65); ax2.axis("off")
    ax2.set_title(f"Perspektif görünüm (yükseklik {abart:g} kat abartılı)")
    fig.tight_layout(); fig.savefig(png_yolu); plt.close(fig)


if __name__ == "__main__":
    ciz(sys.argv[1], sys.argv[2])
