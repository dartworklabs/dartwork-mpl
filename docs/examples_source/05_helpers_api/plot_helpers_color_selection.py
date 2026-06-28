"""
helpers.colors — Curated Palette Lookup
========================================

``dm.make_palette`` returns a curated dartwork palette sized to the
data. The 2×2 grid below demonstrates the four most common cases:
categorical (with a highlight), sequential for continuous series,
diverging for bipolar values, and categorical with a single-item
highlight.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm


def _minimal(ax: plt.Axes) -> None:
    """Inline minimal-axes recipe (top/right hidden + light dashed y-grid)."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(
        True,
        axis="y",
        alpha=0.2,
        color="dc.muted1",
        linestyle="--",
        linewidth=0.5,
    )
    ax.set_axisbelow(True)


np.random.seed(42)

dm.style.use("scientific")
fig, axes = plt.subplots(
    2,
    2,
    figsize=dm.figsize("16cm", "standard"),
    gridspec_kw={"hspace": 0.55, "wspace": 0.3},
)

# Categorical palette, one item highlighted.
ax1 = axes[0, 0]
n_categories = 5
colors_qual = dm.make_palette(n_categories, kind="categorical", highlight=2)
for i, color in enumerate(colors_qual):
    height = np.random.rand() * 50 + 50
    ax1.bar(
        i,
        height,
        color=color,
        alpha=0.8 if i != 2 else 1.0,
        edgecolor="black" if i == 2 else "none",
        linewidth=dm.lw(0) if i == 2 else 0,
    )
ax1.set_title("Categorical (Item 3 Highlighted)", fontsize=dm.fs(1))
ax1.set_xlabel("Category", fontsize=dm.fs(0))
ax1.set_ylabel("Value", fontsize=dm.fs(0))
_minimal(ax1)

# Sequential palette for a family of continuous curves.
ax2 = axes[0, 1]
n_series = 6
colors_seq = dm.make_palette(n_series, kind="sequential")
x = np.linspace(0, 10, 100)
for i, color in enumerate(colors_seq):
    y = np.sin(x + i * 0.5) * (1 - i * 0.15)
    ax2.plot(x, y, color=color, lw=dm.lw(1.5), label=f"Series {i + 1}")
ax2.set_title("Sequential", fontsize=dm.fs(1))
ax2.set_xlabel("X", fontsize=dm.fs(0))
ax2.set_ylabel("Y", fontsize=dm.fs(0))
ax2.legend(fontsize=dm.fs(-2), ncol=2)
_minimal(ax2)

# Diverging palette for bipolar data.
ax3 = axes[1, 0]
n_diverging = 7
colors_div = dm.make_palette(n_diverging, kind="diverging")
values = np.array([-3, -2, -1, 0, 1, 2, 3])
ax3.bar(range(len(values)), values, color=colors_div)
ax3.axhline(y=0, color="black", linestyle="-", lw=0.5)
ax3.set_title("Diverging", fontsize=dm.fs(1))
ax3.set_xlabel("Item", fontsize=dm.fs(0))
ax3.set_ylabel("Value", fontsize=dm.fs(0))
_minimal(ax3)

# Categorical palette with a single-item highlight on a circular layout.
ax4 = axes[1, 1]
n_mixed = 8
colors_mixed = dm.make_palette(n_mixed, kind="categorical", highlight=0)
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
_minimal(ax4)

dm.label_axes(axes.flat)
dm.simple_layout(fig)
plt.show()
