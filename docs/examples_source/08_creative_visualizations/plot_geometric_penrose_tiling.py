"""
Penrose Tiling Pattern
======================

A simplified Penrose-inspired aperiodic tiling. Two triangle types
("acute" and "obtuse") radiate outward from the origin, alternating in
colour through two complementary OKLCH gradients.

The pattern leans on ``dm.cspace`` to keep the colour transitions
perceptually smooth, and on ``dm.hide_all_spines`` to clear away the
default matplotlib chrome.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.cm2in(20), dm.cm2in(20)))


def create_penrose_triangles():
    """Generate Penrose-inspired wheel of triangles."""
    triangles = []
    for i in range(10):
        angle = i * 2 * np.pi / 10
        p1 = (0, 0)
        p2 = (5 * np.cos(angle), 5 * np.sin(angle))
        p3 = (
            5 * np.cos(angle + 2 * np.pi / 10),
            5 * np.sin(angle + 2 * np.pi / 10),
        )
        kind = "A" if i % 2 == 0 else "B"
        triangles.append((kind, [p1, p2, p3]))
    return triangles


triangles = create_penrose_triangles()

colors_type_a = dm.cspace("oc.blue9", "oc.teal3", n=len(triangles) // 2)
colors_type_b = dm.cspace("oc.orange9", "oc.pink3", n=len(triangles) // 2)

a_count, b_count = 0, 0
for tri_type, points in triangles:
    if tri_type == "A":
        color = colors_type_a[a_count % len(colors_type_a)]
        a_count += 1
        edge_color = "white"
    else:
        color = colors_type_b[b_count % len(colors_type_b)]
        b_count += 1
        edge_color = "oc.gray7"

    triangle = Polygon(
        points,
        facecolor=color.to_hex(),
        edgecolor=edge_color,
        linewidth=0.5,
        alpha=0.7,
    )
    ax.add_patch(triangle)

    center = np.mean(points, axis=0)
    ax.scatter(*center, s=10, c="white", alpha=0.3)

# Radial gradient overlay
for r in np.linspace(0.5, 5, 10):
    ax.add_patch(
        Circle(
            (0, 0), r, fill=False, edgecolor="white", linewidth=0.2, alpha=0.1
        )
    )

ax.set_xlim(-6, 6)
ax.set_ylim(-6, 6)
ax.set_aspect("equal")
dm.hide_all_spines(ax)
ax.set_facecolor("oc.gray9")

ax.text(
    0,
    -6.5,
    "Penrose Tiling",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)
ax.text(
    0,
    -6.9,
    "Aperiodic Pattern",
    ha="center",
    fontsize=dm.fs(0),
    color="oc.gray5",
    style="italic",
)

dm.simple_layout(fig)
plt.show()
