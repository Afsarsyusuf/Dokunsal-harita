"""Katmanların renkli 2D önizlemesi (rapor ve kontrol için)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPolygon


def _ciz_alan(ax, geom, **stil):
    parcalar = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
    for p in parcalar:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, **stil))
        for ic in p.interiors:
            ax.add_patch(MplPolygon(list(ic.coords), closed=True, facecolor="#e8e4da", edgecolor="none"))


def ciz(katmanlar, ayar, dosya_yolu, anahtarlar=None):
    from .model3d import plaka_olculeri
    g = ayar["cerceve_genislik_mm"]
    H = ayar["harita_mm"]
    W, L = plaka_olculeri(ayar)
    y0 = H + 2 * g
    b = ayar["ust_bant_mm"]
    fig, ax = plt.subplots(figsize=(7, 7.5), dpi=130)
    ax.add_patch(Rectangle((0, 0), W, L, facecolor="#444", edgecolor="none"))
    ax.add_patch(Rectangle((g, g), H, H, facecolor="#e8e4da", edgecolor="none"))
    ax.add_patch(Rectangle((g, y0), H, b, facecolor="#e8e4da", edgecolor="none"))
    _ciz_alan(ax, katmanlar["arac_yollari"], facecolor="#8a8a8a", edgecolor="none")
    _ciz_alan(ax, katmanlar["yaya_yollari"], facecolor="#c98b3b", edgecolor="none")
    _ciz_alan(ax, katmanlar["binalar"], facecolor="#2f4f6f", edgecolor="none")
    ax.add_patch(MplPolygon([[g + 4, y0 + 2], [g + 12, y0 + 2], [g + 8, y0 + b - 2]], color="#444"))
    for k, _, (x, y) in (anahtarlar or []):
        ax.text(x + 2, y - 3.3, k, color="white", fontsize=7, ha="center", va="center", fontweight="bold")
    ax.set_xlim(0, W); ax.set_ylim(0, L); ax.set_aspect("equal")
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    ax.set_title("Katmanlar - lacivert: bina, gri: araç yolu (kanal), turuncu: yaya yolu, koyu: çerçeve", fontsize=8)
    fig.tight_layout()
    fig.savefig(dosya_yolu)
    plt.close(fig)
