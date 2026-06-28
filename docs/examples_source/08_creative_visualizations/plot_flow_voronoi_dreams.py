"""
Voronoi Dreams
==============

A Voronoi tessellation built from clustered seed points, with each cell
recoloured using ``dm.oklch`` so that hue rotates with angular position
and lightness modulates per cell. Boundary points keep the outer cells
finite for clean polygon clipping.

Demonstrates how to mix ``scipy.spatial.Voronoi`` with dartwork-mpl's
OKLCH colour primitives for generative art.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from scipy.spatial import Voronoi

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("16cm", "square"))

n_clusters = 5
n_points_per_cluster = 8
points = []

for _ in range(n_clusters):
    center_x = np.random.uniform(-8, 8)
    center_y = np.random.uniform(-8, 8)
    cluster_points = np.random.randn(n_points_per_cluster, 2) * 1.5 + [
        center_x,
        center_y,
    ]
    points.extend(cluster_points)

points = np.array(points)

boundary_points = []
for x in np.linspace(-10, 10, 10):
    boundary_points.append([x, -10])
    boundary_points.append([x, 10])
for y in np.linspace(-10, 10, 10):
    boundary_points.append([-10, y])
    boundary_points.append([10, y])

all_points = np.vstack([points, boundary_points])
vor = Voronoi(all_points)

for i, region in enumerate(vor.regions):
    if not region or -1 in region:
        continue

    polygon = [vor.vertices[j] for j in region]
    if len(polygon) <= 2:
        continue

    polygon_array = np.array(polygon)
    if (
        polygon_array[:, 0].min() < -10
        or polygon_array[:, 0].max() > 10
        or polygon_array[:, 1].min() < -10
        or polygon_array[:, 1].max() > 10
    ):
        continue

    center = polygon_array.mean(axis=0)
    hue = (np.arctan2(center[1], center[0]) + np.pi) / (2 * np.pi) * 360
    color = dm.oklch(0.6 + 0.2 * np.sin(i), 0.2, hue)

    ax.add_patch(
        Polygon(
            polygon,
            facecolor=color.to_hex(),
            edgecolor="white",
            linewidth=0.5,
            alpha=0.8,
        )
    )

for point in points[: n_clusters * n_points_per_cluster]:
    ax.scatter(
        *point, s=20, c="white", edgecolors="dc.muted3", linewidths=1, zorder=10
    )

ax.set_xlim(-10, 10)
ax.set_ylim(-10, 10)
ax.set_aspect("equal")
for s in ax.spines.values():
    s.set_visible(False)
ax.set_facecolor("dc.muted0")

ax.text(
    0,
    -11,
    "Voronoi Dreams",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
    alpha=0.9,
)

dm.simple_layout(fig)
plt.show()
