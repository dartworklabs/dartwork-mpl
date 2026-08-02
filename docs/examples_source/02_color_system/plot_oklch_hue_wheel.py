"""
OKLCH Hue Wheel
===============

A polar scatter plot that sweeps through 360° of hue in the OKLCH color space
at fixed Lightness and Chroma. Each ring represents a different lightness level,
demonstrating a smooth cylindrical hue traversal without the muddy coordinate
dead zones typical of HSL/HSV. The wheel is diagnostic, not proof that equal
numeric hue steps are perceived as exactly equal color differences.

Use ``dm.oklch(L, C, h)`` to construct colors directly from perceptual
coordinates.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

fig, ax = plt.subplots(
    figsize=dm.figsize("13.5cm", "square"), subplot_kw={"projection": "polar"}
)

n_hues = 72  # 5° steps
hues = np.linspace(0, 360, n_hues, endpoint=False)
theta = np.radians(hues)

# Three concentric rings at different lightness levels
lightness_levels = [
    (0.80, 0.14, 2.8, "L = 0.80 (light)"),
    (0.65, 0.18, 3.6, "L = 0.65 (mid)"),
    (0.50, 0.16, 2.8, "L = 0.50 (dark)"),
]

for radius, (L, C, marker_size, label) in enumerate(lightness_levels, start=1):
    colors = [dm.oklch(L, C, h).to_hex() for h in hues]
    r_values = np.full(n_hues, radius)
    ax.scatter(
        theta,
        r_values,
        c=colors,
        s=(marker_size * 30),
        edgecolors="white",
        linewidths=0.3,
        zorder=3,
        label=label,
    )

# Styling
ax.set_ylim(0, 4)
ax.set_yticks([1, 2, 3])
ax.set_yticklabels([])
ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
ax.set_xticklabels(
    ["0°", "45°", "90°", "135°", "180°", "225°", "270°", "315°"],
    fontsize=dm.fs(-0.5),
)
ax.set_title(
    "OKLCH Hue Wheel\u2009\u2014\u2009Fixed L and C",
    fontsize=dm.fs(1),
    weight="bold",
    pad=30,
)
ax.legend(
    loc="lower right",
    bbox_to_anchor=(1.25, -0.05),
    fontsize=dm.fs(-0.5),
    framealpha=0.9,
    edgecolor="white",
)
ax.grid(True, alpha=0.2)
dm.simple_layout(fig)
plt.show()
