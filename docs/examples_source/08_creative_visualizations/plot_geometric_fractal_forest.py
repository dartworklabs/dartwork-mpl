"""
Fractal Forest
==============

A small forest of recursive fractal trees. Each branch picks its
colour from a depth-indexed gradient so trunks read as warm orange
while leaves bloom into greens and yellows. Random angle perturbations
keep no two trees identical.

Key dartwork helpers used here:

- ``dm.cspace`` for the trunk-to-leaf and leaf colour ramps.
- ``dm.hide_all_spines`` for the immersive, full-bleed canvas.
- ``dm.fs`` for proportional title sizing.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
dm.style.use("scientific")

fig, ax = dm.subplots(width="18cm", aspect=1.111)


def draw_fractal_tree(ax, x, y, angle, length, depth, max_depth, colors):
    if depth > max_depth:
        return

    x_end = x + length * np.cos(angle)
    y_end = y + length * np.sin(angle)
    color = colors[depth % len(colors)]
    lw = max(0.5, 3 - depth * 0.3)

    ax.plot(
        [x, x_end],
        [y, y_end],
        color=color.to_hex(),
        linewidth=lw,
        alpha=0.9 - depth * 0.08,
        solid_capstyle="round",
    )

    if depth >= max_depth - 1:
        leaf_colors = dm.cspace("oc.green5", "oc.yellow5", n=10)
        leaf_color = leaf_colors[np.random.randint(0, 10)]
        ax.scatter(
            x_end,
            y_end,
            s=50,
            c=[leaf_color.to_hex()],
            alpha=0.6,
            edgecolors="white",
            linewidths=0.3,
        )

    branch_angle = np.pi / 6 + np.random.uniform(-np.pi / 12, np.pi / 12)
    length_factor = 0.7 + np.random.uniform(-0.1, 0.1)

    draw_fractal_tree(
        ax,
        x_end,
        y_end,
        angle - branch_angle,
        length * length_factor,
        depth + 1,
        max_depth,
        colors,
    )
    draw_fractal_tree(
        ax,
        x_end,
        y_end,
        angle + branch_angle,
        length * length_factor,
        depth + 1,
        max_depth,
        colors,
    )

    if np.random.random() > 0.7:
        draw_fractal_tree(
            ax,
            x_end,
            y_end,
            angle + np.random.uniform(-np.pi / 8, np.pi / 8),
            length * length_factor * 0.8,
            depth + 1,
            max_depth,
            colors,
        )


branch_colors = dm.cspace("oc.orange8", "oc.green6", n=10)
tree_positions = [(-3, -5), (0, -5), (3, -5), (-1.5, -5), (1.5, -5)]

for x_pos, y_pos in tree_positions:
    max_depth = np.random.randint(7, 10)
    initial_length = np.random.uniform(2.5, 3.5)
    initial_angle = np.pi / 2 + np.random.uniform(-np.pi / 12, np.pi / 12)
    draw_fractal_tree(
        ax,
        x_pos,
        y_pos,
        initial_angle,
        initial_length,
        0,
        max_depth,
        branch_colors,
    )

# Ground and stars
ax.fill_between([-6, 6], -5, -6, color="oc.orange9", alpha=0.8)
for _ in range(50):
    x = np.random.uniform(-6, 6)
    y = np.random.uniform(-5, 5)
    size = np.random.uniform(1, 5)
    ax.scatter(x, y, s=size, c="white", alpha=0.1)

ax.set_xlim(-6, 6)
ax.set_ylim(-6, 6)
ax.set_aspect("equal")
dm.hide_all_spines(ax)
ax.set_facecolor("oc.gray1")

ax.text(
    0,
    -6.5,
    "Fractal Forest",
    ha="center",
    fontsize=dm.fs(3),
    color="white",
    weight="bold",
)

dm.simple_layout(fig)
plt.show()
