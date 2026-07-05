"""
Fibonacci Spiral Galaxy
=======================

A simulated galaxy assembled from three rotated copies of a Fibonacci
spiral. Each "arm" gets its own OKLCH gradient so the disk reads as a
cohesive whole. Random jitter on a population of background stars adds
the speckled stellar field.

Notable techniques:

- Rotating point clouds with a 2D rotation matrix to share one source
  spiral across multiple arms.
- Stacking three faint ``Circle`` patches at the centre to fake a soft
  galactic core glow.
"""

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "square"))


def fibonacci_spiral(n_points=1000):
    golden_ratio = (1 + np.sqrt(5)) / 2
    theta = np.linspace(0, 8 * np.pi, n_points)
    r = np.exp(theta / (2 * np.pi / np.log(golden_ratio)))
    return r * np.cos(theta), r * np.sin(theta), theta


x, y, theta = fibonacci_spiral(1500)

arm_palettes = [
    ("dc.teal5", "dc.teal1"),
    ("dc.violet5", "dc.green1"),
    ("dc.teal5", "dc.green1"),
]

for arm in range(3):
    angle_offset = arm * 2 * np.pi / 3
    x_arm = x * np.cos(angle_offset) - y * np.sin(angle_offset)
    y_arm = x * np.sin(angle_offset) + y * np.cos(angle_offset)

    arm_colors = dm.cspace(*arm_palettes[arm], n=len(x))

    for i in range(0, len(x), 2):
        size = 0.5 + 20 * np.exp(-theta[i] / 10)
        alpha = 0.8 * np.exp(-theta[i] / 15)
        ax.scatter(
            x_arm[i],
            y_arm[i],
            s=size,
            c=[arm_colors[i].to_hex()],
            alpha=alpha,
            edgecolors="none",
        )

n_stars = 500
star_theta = np.random.uniform(0, 8 * np.pi, n_stars)
star_r = np.exp(star_theta / (2 * np.pi / np.log((1 + np.sqrt(5)) / 2)))
star_r *= np.random.uniform(0.8, 1.2, n_stars)
star_x = star_r * np.cos(star_theta)
star_y = star_r * np.sin(star_theta)

ax.scatter(
    star_x,
    star_y,
    s=np.random.uniform(0.1, 2, n_stars),
    c="white",
    alpha=np.random.uniform(0.3, 1, n_stars),
)

ax.add_patch(plt.Circle((0, 0), 30, color="white", alpha=0.05))
ax.add_patch(plt.Circle((0, 0), 20, color="dc.orange1", alpha=0.1))
ax.add_patch(plt.Circle((0, 0), 10, color="dc.orange2", alpha=0.3))

for s in ax.spines.values():
    s.set_visible(False)
ax.set_xlim(-150, 150)
ax.set_ylim(-150, 150)
ax.set_aspect("equal")
ax.set_facecolor("black")

title_text = ax.text(
    0,
    -170,
    "Fibonacci Galaxy M-" + str(np.random.randint(100, 999)),
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    alpha=0.8,
)
title_text.set_path_effects(
    [path_effects.withStroke(linewidth=dm.lw(0), foreground="dc.teal5")]
)

dm.simple_layout(fig)
plt.show()
