"""
helpers.colors — Automatic Colour Selection
============================================

``dm.helpers.colors.auto_select_colors`` picks a palette appropriate
for the shape of the data. The 2×2 grid below demonstrates the four
most common cases: categorical (with a highlight), sequential for
continuous series, diverging for bipolar values, and categorical with
a single-item highlight.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)

dm.style.use("scientific")
fig, axes = dm.subplots(2, 2, width="16cm", aspect="standard")

# Categorical palette, one item highlighted.
ax1 = axes[0, 0]
n_categories = 5
colors_qual = dm.helpers.colors.auto_select_colors(
    n_series=n_categories, color_type="categorical", highlight_index=2
)
for i, color in enumerate(colors_qual):
    height = np.random.rand() * 50 + 50
    ax1.bar(
        i,
        height,
        color=color,
        alpha=0.8 if i != 2 else 1.0,
        edgecolor="black" if i == 2 else "none",
        linewidth=2 if i == 2 else 0,
    )
ax1.set_title("Categorical (Item 3 Highlighted)", fontsize=dm.fs(1))
ax1.set_xlabel("Category", fontsize=dm.fs(0))
ax1.set_ylabel("Value", fontsize=dm.fs(0))
dm.minimal_axes(ax1)

# Sequential palette for a family of continuous curves.
ax2 = axes[0, 1]
n_series = 6
colors_seq = dm.helpers.colors.auto_select_colors(
    n_series=n_series, color_type="sequential"
)
x = np.linspace(0, 10, 100)
for i, color in enumerate(colors_seq):
    y = np.sin(x + i * 0.5) * (1 - i * 0.15)
    ax2.plot(x, y, color=color, lw=dm.lw(1.5), label=f"Series {i + 1}")
ax2.set_title("Sequential", fontsize=dm.fs(1))
ax2.set_xlabel("X", fontsize=dm.fs(0))
ax2.set_ylabel("Y", fontsize=dm.fs(0))
ax2.legend(fontsize=dm.fs(-2), ncol=2)
dm.minimal_axes(ax2)

# Diverging palette for bipolar data.
ax3 = axes[1, 0]
n_diverging = 7
colors_div = dm.helpers.colors.auto_select_colors(
    n_series=n_diverging, color_type="diverging"
)
values = np.array([-3, -2, -1, 0, 1, 2, 3])
ax3.bar(range(len(values)), values, color=colors_div)
ax3.axhline(y=0, color="black", linestyle="-", lw=0.5)
ax3.set_title("Diverging", fontsize=dm.fs(1))
ax3.set_xlabel("Item", fontsize=dm.fs(0))
ax3.set_ylabel("Value", fontsize=dm.fs(0))
dm.minimal_axes(ax3)

# Categorical palette with a single-item highlight on a circular layout.
ax4 = axes[1, 1]
n_mixed = 8
colors_mixed = dm.helpers.colors.auto_select_colors(
    n_series=n_mixed, color_type="categorical", highlight_index=0
)
for i, color in enumerate(colors_mixed):
    angle = i * 45
    radius = 0.8 if i != 0 else 1.0
    ax4.bar(
        angle,
        radius,
        width=40,
        color=color,
        alpha=0.6 if i != 0 else 1.0,
        bottom=0.2,
    )
ax4.set_title("Categorical + Highlight", fontsize=dm.fs(1))
dm.minimal_axes(ax4)

dm.label_axes(axes.flat)
dm.simple_layout(fig)
plt.show()
