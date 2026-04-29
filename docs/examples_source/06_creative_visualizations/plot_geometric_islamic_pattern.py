"""
Islamic Geometric Pattern
==========================

A tessellation of 8-pointed stars on a half-offset grid, with each star
coloured by its distance from the centre. The radial gradient comes
from ``dm.cspace("oc.indigo9", "oc.yellow5", n=100, space="oklch")``,
giving the pattern its dusk-to-dawn feel.

White connectors link adjacent stars, and a yellow inner frame nods to
the metallic detailing typical of traditional Islamic tile work.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(20), dm.cm2in(20)))


def create_islamic_star(center, size, n_points=8):
    outer_points = []
    inner_points = []
    for i in range(n_points):
        angle_outer = i * 2 * np.pi / n_points
        outer_points.append(
            [
                center[0] + size * np.cos(angle_outer),
                center[1] + size * np.sin(angle_outer),
            ]
        )
        angle_inner = (i + 0.5) * 2 * np.pi / n_points
        inner_points.append(
            [
                center[0] + size * 0.4 * np.cos(angle_inner),
                center[1] + size * 0.4 * np.sin(angle_inner),
            ]
        )

    star_points = []
    for i in range(n_points):
        star_points.append(outer_points[i])
        star_points.append(inner_points[i])
    return star_points


grid_size = 4
centers = []
for i in range(-grid_size, grid_size + 1):
    for j in range(-grid_size, grid_size + 1):
        if (i + j) % 2 == 0:
            centers.append((i * 2, j * 2))

max_dist = np.sqrt(2 * grid_size**2) * 2
colors_islamic = dm.cspace("oc.indigo9", "oc.yellow5", n=100, space="oklch")

for center in centers:
    dist = np.sqrt(center[0] ** 2 + center[1] ** 2)
    color_idx = int((dist / max_dist) * 99)
    color = colors_islamic[min(color_idx, 99)]

    star_points = create_islamic_star(center, 0.8, 8)
    ax.add_patch(
        Polygon(
            star_points,
            facecolor=color.to_hex(),
            edgecolor="white",
            linewidth=1,
            alpha=0.8,
        )
    )

    inner_star_points = create_islamic_star(center, 0.4, 8)
    ax.add_patch(
        Polygon(
            inner_star_points,
            facecolor="white",
            edgecolor=color.to_hex(),
            linewidth=0.5,
            alpha=0.3,
        )
    )

    for i in range(8):
        angle = i * 2 * np.pi / 8
        x1 = center[0] + 0.8 * np.cos(angle)
        y1 = center[1] + 0.8 * np.sin(angle)
        x2 = center[0] + 1.2 * np.cos(angle)
        y2 = center[1] + 1.2 * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color="white", lw=0.5, alpha=0.3)

# Frames
ax.add_patch(
    Rectangle((-8.5, -8.5), 17, 17, fill=False, edgecolor="white", linewidth=2)
)
ax.add_patch(
    Rectangle((-8, -8), 16, 16, fill=False, edgecolor="oc.yellow5", linewidth=1)
)

ax.set_xlim(-9, 9)
ax.set_ylim(-9, 9)
ax.set_aspect("equal")
dm.hide_all_spines(ax)
ax.set_facecolor("oc.indigo9")

ax.text(
    0,
    -9.5,
    "Islamic Geometric Pattern",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
