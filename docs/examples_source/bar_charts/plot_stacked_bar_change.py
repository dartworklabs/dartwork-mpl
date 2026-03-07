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

dm.style.use("presentation")


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
    ("Category 1", 20, 15, 18),
    ("Category 2", 10, 25, 20),
    ("Category 3", 25, 10, 15),
    ("Category 4", 30, 30, 25),
    ("Category 5", 15, 20, 22),
]

colors = [
    "tw.slate800",
    "tw.slate600",
    "tw.gray500",
    "tw.teal500",
    "tw.emerald600",
]

years = ["2020", "2023", "2026"]

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
n_years = len(years)
x_pos = np.linspace(0, 1.2, n_years)
bar_width = 0.2
label_offset = 0.02

# Extract values and bottoms per year
all_values = []
all_bottoms = []
all_totals = []
for y_idx in range(n_years):
    vals = [c[y_idx + 1] for c in categories]
    all_values.append(vals)
    bots, tot = stack_bottoms(vals)
    all_bottoms.append(bots)
    all_totals.append(tot)

fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
fig.suptitle("Category Mix Shift (2020–2026)", fontsize=dm.fs(1), weight="bold", y=1.05)

for idx, cat_data in enumerate(categories):
    label = cat_data[0]
    vals = cat_data[1:]
    color = colors[idx]

    # Draw bars and value labels
    for y_idx in range(n_years):
        bx = x_pos[y_idx]
        b_val = vals[y_idx]
        b_bot = all_bottoms[y_idx][idx]

        ax.add_patch(
            plt.Rectangle((bx, b_bot), bar_width, b_val, color=color, lw=0)
        )

        ax.text(
            bx + bar_width / 2,
            b_bot + b_val / 2,
            str(b_val),
            ha="center",
            va="center",
            fontsize=dm.fs(-0.5),
            color=text_color(color),
            weight=dm.fw(1),
        )

    # Category label on the far right
    ax.text(
        x_pos[-1] + bar_width + label_offset,
        all_bottoms[-1][idx] + vals[-1] / 2,
        label,
        ha="left",
        va="center",
        fontsize=dm.fs(0),
        color=color,
        weight=dm.fw(1),
    )

    # Connecting polygons and change labels
    for y_idx in range(n_years - 1):
        x1, x2 = x_pos[y_idx], x_pos[y_idx + 1]
        v1, v2 = vals[y_idx], vals[y_idx + 1]
        b1, b2 = all_bottoms[y_idx][idx], all_bottoms[y_idx + 1][idx]

        lt, lb_ = b1 + v1, max(0, b1)
        rt, rb_ = b2 + v2, max(0, b2)
        
        polygon = Polygon(
            [
                [x1 + bar_width, lt],
                [x2, rt],
                [x2, rb_],
                [x1 + bar_width, lb_],
            ],
            closed=True,
            color=dm.pseudo_alpha(color, alpha=0.35),
            zorder=0,
            linewidth=0,
        )
        ax.add_patch(polygon)

        # Change label
        pct = (v2 - v1) / v1 * 100
        label_text = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
        mid_x = np.mean([x1 + bar_width, x2])
        mid_y = (lt + rt + lb_ + rb_) / 4
        ax.text(
            mid_x, mid_y, label_text, ha="center", va="center", fontsize=dm.fs(-0.5)
        )

# Year labels
for y_idx, year_str in enumerate(years):
    ax.text(
        x_pos[y_idx] + bar_width / 2,
        -3,
        year_str,
        ha="center",
        va="top",
        fontsize=dm.fs(-0.5),
        weight="bold",
    )

ax.set_xlim(x_pos[0] - 0.05, x_pos[-1] + bar_width + label_offset + 0.5)
ax.set_ylim(-6, max(all_totals) * 1.05)
ax.axis("off")

dm.simple_layout(fig, margins=(0.05, 0.05, 0.05, 0.05))
plt.show()
