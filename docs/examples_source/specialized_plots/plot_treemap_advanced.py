"""
Advanced Treemap
================

Build a multi-column treemap with proportional block areas and readable
labels.  Each column's width reflects its share of the total; blocks within
a column are stacked vertically.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import dartwork_mpl as dm

dm.style.use("scientific")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
product_data = [
    ("Electronics", 34, "tw.blue800"),
    ("Clothing", 21, "tw.blue400"),
    ("Food", 16, "tw.blue500"),
    ("Books", 15, "tw.cyan500"),
    ("Toys", 6, "tw.teal700"),
    ("Sports", 4, "tw.blue600"),
    ("Home", 4, "tw.teal400"),
]

region_data = [
    ("North America", 38, "oc.blue7"),
    ("Europe", 25, "oc.blue5"),
    ("Asia", 22, "oc.blue3"),
    ("Other", 15, "oc.gray5"),
]

# Treemap layouts: list of columns, each column is a list of items
product_columns = [
    [product_data[0]],
    [product_data[1], product_data[3]],
    [product_data[2], product_data[4], product_data[5], product_data[6]],
]
region_columns = [
    [region_data[0]],
    [region_data[1], region_data[2]],
    [region_data[3]],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def text_color(fill, threshold=0.55):
    """White or dark text based on background luminance."""
    r, g, b = mcolors.to_rgb(fill)
    return (
        "white" if 0.299 * r + 0.587 * g + 0.114 * b < threshold else "#0f172a"
    )


def draw_treemap(ax, columns, total, title, padding=0.008):
    """Draw a proportional-area treemap with labeled blocks."""
    col_totals = [sum(v for _, v, _ in col) for col in columns]
    x = 0

    for col, col_total in zip(columns, col_totals, strict=False):
        col_width = col_total / total
        y = 0
        for name, val, color in col:
            h = val / col_total
            ax.add_patch(
                Rectangle(
                    (x + padding, y + padding),
                    col_width - 2 * padding,
                    h - 2 * padding,
                    facecolor=color,
                    edgecolor="white",
                    lw=1.5,
                )
            )
            # Label
            label = (
                f"{name}\n{val}%"
                if col_width > 0.15 and h > 0.15
                else f"{val}%"
            )
            ax.text(
                x + col_width / 2,
                y + h / 2,
                label,
                ha="center",
                va="center",
                fontsize=dm.fs(-1),
                color=text_color(color),
                weight="bold",
            )
            y += h
        x += col_width

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=dm.fs(1), weight="bold", pad=12)


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(dm.cm2in(18), dm.cm2in(8)), dpi=300
)

draw_treemap(ax1, product_columns, 100, "Product Mix")
draw_treemap(ax2, region_columns, 100, "Regional Split")

dm.simple_layout(fig, margins=(0.05, 0.05, 0.05, 0.05))
plt.show()
