"""
Color Catalog
=============

dartwork-mpl bundles two extended palettes — **Open Color** (``oc.*``)
and **Tailwind CSS** (``tw.*``) — registered automatically on import.
This gallery shows the full catalog so you can pick colours by name.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("presentation")


def _swatch_row(ax, colors, labels, y, box_h=0.8, box_w=1.0):
    """Draw a row of color swatches with labels."""
    for i, (c, lbl) in enumerate(zip(colors, labels, strict=False)):
        try:
            rgb = mcolors.to_rgb(c)
        except ValueError:
            continue
        ax.add_patch(plt.Rectangle(
            (i * (box_w + 0.15), y), box_w, box_h,
            facecolor=rgb, edgecolor="white", linewidth=0.5,
        ))
        # Choose text color for contrast
        luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        text_color = "white" if luminance < 0.5 else "oc.gray8"
        ax.text(
            i * (box_w + 0.15) + box_w / 2, y + box_h / 2,
            lbl, ha="center", va="center",
            fontsize=dm.fs(-2.5), color=text_color,
        )


# %%
# Open Color palette
# -------------------
# The ``oc.*`` namespace provides 13 hue families × 10 shades each.

oc_families = [
    "gray", "red", "pink", "grape", "violet",
    "indigo", "blue", "cyan", "teal", "green",
    "lime", "yellow", "orange",
]
shades = list(range(10))  # 0..9

fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(14)), dpi=300
)
ax.set_xlim(-3.5, len(shades) * 1.15 + 0.5)
ax.set_ylim(-0.5, len(oc_families) * 1.1 + 0.5)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Open Color Palette (oc.*)", fontsize=dm.fs(1))

for row, family in enumerate(reversed(oc_families)):
    y = row * 1.1
    colors = [f"oc.{family}{s}" for s in shades]
    labels = [str(s) for s in shades]
    _swatch_row(ax, colors, labels, y)
    ax.text(-0.3, y + 0.4, f"oc.{family}",
            ha="right", va="center", fontsize=dm.fs(-1.5),
            fontweight="bold", color="oc.gray7")

ax.axis("off")
dm.simple_layout(fig)
plt.show()

# %%
# Tailwind CSS palette (selected families)
# ------------------------------------------
# The ``tw.*`` namespace provides Tailwind's extended colour palette.

tw_families = [
    "slate", "red", "orange", "amber", "yellow",
    "lime", "green", "emerald", "teal", "cyan",
    "sky", "blue", "indigo", "violet", "purple",
    "fuchsia", "pink", "rose",
]
tw_shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]

fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(17)), dpi=300
)
ax.set_xlim(-3.5, len(tw_shades) * 1.15 + 0.5)
ax.set_ylim(-0.5, len(tw_families) * 1.1 + 0.5)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Tailwind CSS Palette (tw.*)", fontsize=dm.fs(1))

for row, family in enumerate(reversed(tw_families)):
    y = row * 1.1
    colors = [f"tw.{family}{s}" for s in tw_shades]
    labels = [str(s) for s in tw_shades]
    _swatch_row(ax, colors, labels, y)
    ax.text(-0.3, y + 0.4, f"tw.{family}",
            ha="right", va="center", fontsize=dm.fs(-1.5),
            fontweight="bold", color="oc.gray7")

ax.axis("off")
dm.simple_layout(fig)
plt.show()
