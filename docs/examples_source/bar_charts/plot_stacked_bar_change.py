"""
Stacked Bar Change
==================

Compare two stacked bar compositions side-by-side with connecting polygons and
percentage-change labels.  Useful for showing how a category mix shifted from
one period to another.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

import dartwork_mpl as dm

dm.style.use("scientific")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def stack_bottoms(values):
    """Return bottom y-coordinates so bars stack from bottom to top."""
    bottoms = [0] * len(values)
    y = 0
    for i in range(len(values) - 1, -1, -1):
        bottoms[i] = y
        y += values[i]
    return bottoms, y


def text_color(fill, threshold=0.6):
    """Choose black or white text for readability on *fill*."""
    r, g, b = mcolors.to_rgb(fill)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "black" if luminance > threshold else "white"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
categories = [
    ("Category 1", 20, 15),
    ("Category 2", 10, 25),
    ("Category 3", 25, 10),
    ("Category 4", 30, 30),
    ("Category 5", 15, 20),
]

colors = [
    "tw.slate800",
    "tw.slate600",
    "tw.gray500",
    "tw.teal500",
    "tw.emerald600",
]

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
left_x, right_x = 0.0, 0.7
bar_width = 0.2
label_offset = 0.02

values_left = [c[1] for c in categories]
values_right = [c[2] for c in categories]
left_bottoms, left_total = stack_bottoms(values_left)
right_bottoms, right_total = stack_bottoms(values_right)

fig, ax = plt.subplots(figsize=(dm.cm2in(8), dm.cm2in(7)), dpi=300)

for idx, (label, left_val, right_val) in enumerate(categories):
    lb, rb = left_bottoms[idx], right_bottoms[idx]
    color = colors[idx]

    # Bars
    ax.add_patch(
        plt.Rectangle((left_x, lb), bar_width, left_val, color=color, lw=0)
    )
    ax.add_patch(
        plt.Rectangle((right_x, rb), bar_width, right_val, color=color, lw=0)
    )

    # Value labels
    for cx, cy, val in [
        (left_x + bar_width / 2, lb + left_val / 2, left_val),
        (right_x + bar_width / 2, rb + right_val / 2, right_val),
    ]:
        ax.text(
            cx,
            cy,
            str(val),
            ha="center",
            va="center",
            fontsize=dm.fs(-0.5),
            color=text_color(color),
            weight=dm.fw(1),
        )

    # Category label
    ax.text(
        right_x + bar_width + label_offset,
        rb + right_val / 2,
        label,
        ha="left",
        va="center",
        fontsize=dm.fs(0),
        color=color,
        weight=dm.fw(1),
    )

    # Connecting polygon
    lt, lb_ = lb + left_val, max(0, lb)
    rt, rb_ = rb + right_val, max(0, rb)
    polygon = Polygon(
        [
            [left_x + bar_width, lt],
            [right_x, rt],
            [right_x, rb_],
            [left_x + bar_width, lb_],
        ],
        closed=True,
        color=dm.pseudo_alpha(color, alpha=0.35),
        zorder=0,
        linewidth=0,
    )
    ax.add_patch(polygon)

    # Change label
    pct = (right_val - left_val) / left_val * 100
    label_text = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
    mid_x = np.mean([left_x + bar_width, right_x])
    mid_y = (lt + rt + lb_ + rb_) / 4
    ax.text(
        mid_x, mid_y, label_text, ha="center", va="center", fontsize=dm.fs(0)
    )

# Year labels
ax.text(
    left_x + bar_width / 2,
    -3,
    "2022",
    ha="center",
    va="top",
    fontsize=dm.fs(-0.5),
    weight=dm.fw(1),
)
ax.text(
    right_x + bar_width / 2,
    -3,
    "2025",
    ha="center",
    va="top",
    fontsize=dm.fs(-0.5),
    weight=dm.fw(1),
)

ax.set_xlim(left_x, right_x + bar_width + label_offset + 0.05)
ax.set_ylim(-6, max(left_total, right_total))
ax.axis("off")

dm.simple_layout(fig)
plt.show()
