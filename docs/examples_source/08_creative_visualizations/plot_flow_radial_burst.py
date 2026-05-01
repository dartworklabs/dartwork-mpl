"""
Radial Burst Pattern
====================

Eight concentric layers of petals built directly in polar coordinates,
each layer using its own monochrome OKLCH gradient. The result is a
sunburst-like pattern that demonstrates how to combine
``ax.fill_between`` with ``dm.cspace`` colour ramps.

The piece also shows two practical idioms:

- The ``Circle`` patch uses ``transform=ax.transData._b`` to be drawn
  in cartesian space on top of the polar axes.
- ``dm.fs(6)`` keeps the centrepiece glyph proportional to the active
  style preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = dm.subplots(width="18cm", aspect="square", subplot_kw={"projection": "polar"})

theta = np.linspace(0, 2 * np.pi, 360)
r_layers = 8

ring_palette = ["blue", "teal", "green", "yellow", "orange", "red", "pink", "violet"]

for layer in range(r_layers):
    r_base = 0.5 + layer * 0.5
    r = r_base + 0.3 * np.sin(6 * theta + layer * np.pi / 4)

    layer_colors = dm.cspace(
        f"oc.{ring_palette[layer]}5",
        f"oc.{ring_palette[layer]}8",
        n=len(theta),
    )

    for i in range(len(theta) - 1):
        ax.fill_between(
            [theta[i], theta[i + 1]],
            0,
            [r[i], r[i + 1]],
            color=layer_colors[i].to_hex(),
            alpha=0.3 + 0.05 * layer,
        )

# Radial spokes
for angle in np.linspace(0, 2 * np.pi, 12, endpoint=False):
    ax.plot([angle, angle], [0, 4], color="white", alpha=0.2, lw=0.5)

ax.set_ylim(0, 4)
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)
dm.hide_all_spines(ax)
ax.set_xticks([])
ax.set_yticks([])
ax.set_facecolor("oc.gray9")

center = plt.Circle(
    (0, 0), 0.3, transform=ax.transData._b, color="white", zorder=10
)
ax.add_patch(center)

ax.text(
    0,
    0,
    "✦",
    fontsize=dm.fs(6),
    ha="center",
    va="center",
    color="oc.gray9",
    weight="bold",
    zorder=11,
)

dm.simple_layout(fig)
plt.show()
