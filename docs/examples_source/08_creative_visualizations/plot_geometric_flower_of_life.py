"""
Sacred Geometry: Flower of Life
================================

Recreate the ancient Flower of Life pattern with modern OKLCH gradients.
The construction is recursive: a centre circle, a ring of six tangent
circles, and a second ring of twelve circles whose centres lie on
intersections of the first ring.

This example pairs precise geometric primitives with
``dm.cspace("oc.violet9", "oc.cyan3", n=19, space="oklch")`` so the
colour ramp is perceptually uniform.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = dm.subplots(width="20cm", aspect="square")


def draw_flower_of_life(ax, center, radius, levels, colors):
    """Draw flower of life pattern recursively."""
    circles = []

    # Center circle
    circles.append((center[0], center[1], radius))

    # First ring - 6 circles
    for i in range(6):
        angle = i * np.pi / 3
        x = center[0] + radius * np.cos(angle)
        y = center[1] + radius * np.sin(angle)
        circles.append((x, y, radius))

    # Second ring - 12 circles
    if levels >= 2:
        for i in range(6):
            angle1 = i * np.pi / 3
            x = center[0] + radius * np.sqrt(3) * np.cos(angle1 + np.pi / 6)
            y = center[1] + radius * np.sqrt(3) * np.sin(angle1 + np.pi / 6)
            circles.append((x, y, radius))

    for i, (cx, cy, r) in enumerate(circles):
        color = colors[i % len(colors)]
        ax.add_patch(
            Circle(
                (cx, cy),
                r,
                fill=False,
                edgecolor=color.to_hex(),
                linewidth=1.5,
                alpha=0.8,
            )
        )

        for j in range(6):
            angle = j * np.pi / 3
            inner_x = cx + r / 2 * np.cos(angle)
            inner_y = cy + r / 2 * np.sin(angle)
            ax.add_patch(
                Circle(
                    (inner_x, inner_y),
                    r / 3,
                    fill=False,
                    edgecolor=color.to_hex(),
                    linewidth=0.5,
                    alpha=0.4,
                )
            )


colors_sacred = dm.cspace("oc.violet9", "oc.cyan3", n=19, space="oklch")

draw_flower_of_life(ax, (0, 0), 1, 2, colors_sacred)

# Add central seed of life
for i in range(7):
    if i == 0:
        x, y = 0, 0
    else:
        angle = (i - 1) * np.pi / 3
        x, y = 0.33 * np.cos(angle), 0.33 * np.sin(angle)

    ax.add_patch(
        Circle(
            (x, y),
            0.33,
            fill=True,
            facecolor=colors_sacred[i].to_hex(),
            alpha=0.2,
            edgecolor="white",
            linewidth=0.5,
        )
    )

ax.set_xlim(-3, 3)
ax.set_ylim(-3, 3)
ax.set_aspect("equal")
dm.hide_all_spines(ax)
ax.set_facecolor("black")

ax.text(
    0,
    -3.5,
    "Flower of Life",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)
ax.text(
    0,
    -3.8,
    "Sacred Geometry",
    ha="center",
    fontsize=dm.fs(0),
    color="oc.gray5",
    style="italic",
)

dm.simple_layout(fig)
plt.show()
