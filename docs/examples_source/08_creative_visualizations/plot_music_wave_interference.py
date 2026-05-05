"""
Wave Interference Patterns
==========================

Four panels of two-dimensional sound interference, each driven by a
different number of point sources. The intensity field comes from the
sum of distance-attenuated sine waves, then rescaled to [0, 1] before
being painted with a 256-colour OKLCH ``contourf``.

Useful pattern: turn ``dm.cspace(..., space="oklch")`` output into a
real Matplotlib colormap with
``LinearSegmentedColormap.from_list("name", [c.to_hex() for c in ramp])``.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, axes = dm.subplots(2, 2, width="18cm", aspect="square")

x = np.linspace(-5, 5, 500)
y = np.linspace(-5, 5, 500)
X, Y = np.meshgrid(x, y)

patterns = [
    ("Dual Source", 2),
    ("Triple Source", 3),
    ("Quad Source", 4),
    ("Circular Array", 8),
]

for ax, (name, n_sources) in zip(axes.flat, patterns, strict=False):
    if name == "Circular Array":
        angles = np.linspace(0, 2 * np.pi, n_sources, endpoint=False)
        sources = [(3 * np.cos(a), 3 * np.sin(a)) for a in angles]
    else:
        sources = [
            (np.random.uniform(-3, 3), np.random.uniform(-3, 3))
            for _ in range(n_sources)
        ]

    Z = np.zeros_like(X)
    for sx, sy in sources:
        R = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
        Z += np.sin(2 * np.pi * R) / (1 + 0.5 * R)

    Z = (Z - Z.min()) / (Z.max() - Z.min())

    colors_wave = dm.cspace("oc.indigo9", "oc.cyan3", n=256, space="oklch")
    wave_cmap = LinearSegmentedColormap.from_list(
        "wave", [c.to_hex() for c in colors_wave]
    )

    ax.contourf(X, Y, Z, levels=20, cmap=wave_cmap, alpha=0.9)

    for sx, sy in sources:
        ax.scatter(
            sx,
            sy,
            s=50,
            c="white",
            edgecolors="oc.red5",
            linewidths=2,
            zorder=10,
        )

    ax.set_xlim(-5, 5)
    ax.set_ylim(-5, 5)
    ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(name, fontsize=dm.fs(1), color="white", pad=10)
    ax.set_facecolor("black")

fig.suptitle(
    "Wave Interference Patterns",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)
fig.patch.set_facecolor("black")

dm.simple_layout(fig)
plt.show()
