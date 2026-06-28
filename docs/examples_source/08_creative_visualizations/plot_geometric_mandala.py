"""
Generative Mandala
==================

A polar-projection mandala with eight nested rings of petals. Each
ring uses its own OKLCH gradient sweep, computed from a hue offset
proportional to the ring index, so the mandala feels coordinated yet
varied.

The example shows how to combine:

- ``subplot_kw={"projection": "polar"}`` for radial layouts.
- ``dm.oklch`` to construct individual colours.
- ``dm.cspace`` to interpolate between them in the OKLCH space.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(
    figsize=dm.figsize("16cm", "square"), subplot_kw={"projection": "polar"}
)

n_rings = 8
n_petals = [6, 12, 18, 24, 30, 36, 42, 48]
radii = np.linspace(0.5, 4, n_rings)

ring_colors = []
for i in range(n_rings):
    start_hue = i * 45
    end_hue = start_hue + 60
    start_color = dm.oklch(0.6, 0.3, start_hue % 360)
    end_color = dm.oklch(0.7, 0.25, end_hue % 360)
    colors = dm.cspace(
        start_color.to_hex(), end_color.to_hex(), n=n_petals[i], space="oklch"
    )
    ring_colors.append(colors)

for ring_idx, (radius, n_petal, colors) in enumerate(
    zip(radii, n_petals, ring_colors, strict=False)
):
    for petal_idx in range(n_petal):
        theta = petal_idx * 2 * np.pi / n_petal
        petal_width = 2 * np.pi / n_petal * 0.8
        theta_range = np.linspace(
            theta - petal_width / 2, theta + petal_width / 2, 50
        )
        r_inner = radius - 0.3
        r_outer = radius + 0.3 * np.sin(3 * (theta_range - theta))

        ax.fill_between(
            theta_range,
            r_inner,
            r_outer,
            color=colors[petal_idx].to_hex(),
            alpha=0.7,
            edgecolor="white",
            linewidth=0.3,
        )

        if ring_idx % 2 == 0:
            ax.scatter(
                theta,
                radius,
                s=20,
                c="white",
                edgecolors=colors[petal_idx].to_hex(),
                linewidths=1,
                zorder=10,
            )

# Center ornament
theta_center = np.linspace(0, 2 * np.pi, 100)
for r, alpha in [(0.3, 0.8), (0.2, 0.6), (0.1, 0.4)]:
    r_center = r * (1 + 0.2 * np.sin(6 * theta_center))
    ax.fill(theta_center, r_center, color="dc.earth2", alpha=alpha)

# Radial guide lines
for angle in np.linspace(0, 2 * np.pi, 12, endpoint=False):
    ax.plot([angle, angle], [0, 4.5], color="white", lw=0.3, alpha=0.2)

ax.set_ylim(0, 4.5)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_xticks([])
ax.set_yticks([])
ax.set_facecolor("black")

fig.text(
    0.5,
    0.05,
    "Generative Mandala",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
