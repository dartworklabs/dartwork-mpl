"""
Grid Squares
=============

Visualize percentages as proportional filled squares in a matrix layout.
Each cell's filled area represents its value; row/column labels add context.
Inspired by McKinsey-style survey visualizations.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import dartwork_mpl as dm

dm.style.use("scientific")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
col_labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
row_labels = [
    "Has extensive\nfamiliarity with gen AI",
    "Is comfortable using\ngen AI at work",
    "Provides feedback\non gen AI tools",
    "Wants to participate\nin the design of\ngen AI tools",
]

values = np.array(
    [
        [50, 49, 62, 47, 26, 22],
        [80, 87, 90, 82, 70, 71],
        [58, 58, 68, 55, 48, 43],
        [72, 73, 72, 59, 39, 38],
    ]
)

# Color per column
cell_colors = [
    "oc.blue5",
    "oc.blue5",
    "oc.blue5",
    "oc.blue5",
    "oc.blue5",
    "oc.blue5",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def contrast_color(color, threshold=0.55):
    """Choose white or dark text for readability."""
    r, g, b = mcolors.to_rgb(color)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "white" if luminance < threshold else "#0f172a"


def draw_cell(ax, pct, facecolor, x, y, w, h, align="center"):
    """Draw a single proportional-area square cell."""
    pct = float(np.clip(pct, 0, 100))
    side = np.sqrt(pct / 100.0)

    pad = 0.04
    inner_w, inner_h = w - 2 * pad, h - 2 * pad
    sq_w, sq_h = inner_w * side, inner_h * side

    if align == "center":
        sx = x + pad + (inner_w - sq_w) / 2
        sy = y + pad + (inner_h - sq_h) / 2
    else:
        sx, sy = x + pad, y + pad

    # Border
    ax.add_patch(
        Rectangle(
            (x + pad, y + pad),
            inner_w,
            inner_h,
            fill=False,
            edgecolor="oc.gray3",
            lw=0.3,
        )
    )
    # Filled square
    ax.add_patch(
        Rectangle((sx, sy), sq_w, sq_h, facecolor=facecolor, edgecolor="none")
    )
    # Value label
    ax.text(
        x + w / 2,
        y + h / 2,
        f"{pct:.0f}",
        ha="center",
        va="center",
        fontsize=dm.fs(-0.5),
        color=contrast_color(facecolor),
        weight="bold",
    )


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
nrows, ncols = values.shape
cell_w, cell_h = 1.0, 1.0
row_label_width = 2.5

fig_w = row_label_width + ncols * cell_w + 0.5
fig_h = ncols * 0.3 + nrows * cell_h + 0.5

fig, ax = plt.subplots(
    figsize=(dm.cm2in(fig_w * 2.5), dm.cm2in(fig_h * 2.5)), dpi=300
)

for r in range(nrows):
    for c in range(ncols):
        x = row_label_width + c * cell_w
        y = (nrows - 1 - r) * cell_h
        draw_cell(ax, values[r, c], cell_colors[c], x, y, cell_w, cell_h)

# Row labels
for r, label in enumerate(row_labels):
    y = (nrows - 1 - r) * cell_h + cell_h / 2
    ax.text(
        row_label_width - 0.1,
        y,
        label,
        ha="right",
        va="center",
        fontsize=dm.fs(-0.5),
    )

# Column labels
for c, label in enumerate(col_labels):
    x = row_label_width + c * cell_w + cell_w / 2
    y = nrows * cell_h + 0.15
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="bottom",
        fontsize=dm.fs(-0.5),
        weight="bold",
    )

ax.set_xlim(0, row_label_width + ncols * cell_w)
ax.set_ylim(-0.3, nrows * cell_h + 0.5)
ax.axis("off")
ax.set_title(
    "US employee sentiment on gen AI, by age group", fontsize=dm.fs(1), pad=15
)

dm.simple_layout(fig)
plt.show()
