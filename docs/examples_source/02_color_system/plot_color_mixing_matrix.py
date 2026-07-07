"""
Perceptual Color Mixing Matrix
==============================

``dm.mix_colors()`` blends two colors in OKLab space (perceptually
uniform), avoiding the muddy saturation dip that naive sRGB
interpolation produces. This 6×6 matrix shows every pairwise 50/50 blend of the
default ``dc.blue6``\u2013``dc.violet8`` color cycle, creating a comprehensive
cross-reference of the library's default palette.

The diagonal shows the original pure colors; off-diagonal cells reveal
how naturally each pair blends — useful for designing cohesive multi-series
charts.
"""

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("presentation")

# The first 6 default dartwork-mpl cycle colors
palette = [
    "dc.blue6",
    "dc.orange9",
    "dc.green5",
    "dc.pink3",
    "dc.amber7",
    "dc.violet8",
]
n = len(palette)

fig, ax = plt.subplots(figsize=dm.figsize("11.7cm", "square"))

for i in range(n):
    for j in range(n):
        if i == j:
            # Pure color on diagonal
            color = palette[i]
        else:
            color = dm.mix_colors(palette[i], palette[j], alpha=0.5)

        rect = mpatches.FancyBboxPatch(
            (j, n - 1 - i),
            1,
            1,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor="white",
            linewidth=dm.lw(0),
        )
        ax.add_patch(rect)

        # Label the diagonal
        if i == j:
            ax.text(
                j + 0.5,
                n - 1 - i + 0.5,
                palette[i],
                ha="center",
                va="center",
                fontsize=dm.fs(-0.5),
                weight="bold",
                color="white" if i >= 3 else "black",
            )

ax.set_xlim(0, n)
ax.set_ylim(0, n)
ax.set_aspect("equal")
ax.set_xticks([i + 0.5 for i in range(n)])
ax.set_xticklabels(palette, fontsize=dm.fs(-0.5), rotation=35, ha="right")
ax.set_yticks([i + 0.5 for i in range(n)])
ax.set_yticklabels([palette[n - 1 - i] for i in range(n)], fontsize=dm.fs(-0.5))
ax.tick_params(
    bottom=False, left=False, labelbottom=True, labelleft=True, pad=8
)

ax.set_title(
    "50/50 Color Mixing Matrix (Octave cycle)",
    fontsize=dm.fs(1),
    weight="bold",
    pad=24,
)

for spine in ax.spines.values():
    spine.set_visible(False)

dm.simple_layout(fig)
plt.show()
