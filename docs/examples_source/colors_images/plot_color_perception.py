"""
Color Perception
================

Check contrast, color-blind safety, and luminance ramps before you pick a palette.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.98,
    top=0.95,
    bottom=0.08,
    wspace=0.4,
    hspace=0.5,
)

# Panel A: Perceptually uniform colormap
ax1 = fig.add_subplot(gs[0, 0])
x = np.linspace(0, 1, 256).reshape(1, -1)
gradient = np.vstack([x] * 50)
ax1.imshow(gradient, aspect="auto", cmap="viridis")
ax1.set_title("Perceptually Uniform (Viridis)", fontsize=dm.fs(1))
ax1.set_xticks([0, 64, 128, 192, 255])
ax1.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=dm.fs(-1))
ax1.set_yticks([])
ax1.set_xlabel("Value", fontsize=dm.fs(0))

# Panel B: Non-uniform colormap
ax2 = fig.add_subplot(gs[0, 1])
ax2.imshow(gradient, aspect="auto", cmap="jet")
ax2.set_title("Non-uniform (Jet - Not Recommended)", fontsize=dm.fs(1))
ax2.set_xticks([0, 64, 128, 192, 255])
ax2.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=dm.fs(-1))
ax2.set_yticks([])
ax2.set_xlabel("Value", fontsize=dm.fs(0))

# Panel C: Colorblind-friendly palette
ax3 = fig.add_subplot(gs[1, 0])
x_plot = np.arange(6)
values = [5, 7, 3, 8, 4, 6]
# Colorblind-friendly colors
cb_colors = [
    "oc.blue5",
    "oc.orange5",
    "oc.green5",
    "oc.red5",
    "oc.violet5",
    "oc.gray5",
]
bars = ax3.bar(
    x_plot, values, color=cb_colors, alpha=0.7, edgecolor="black", linewidth=0.5
)
ax3.set_xlabel("Category", fontsize=dm.fs(0))
ax3.set_ylabel("Value", fontsize=dm.fs(0))
ax3.set_title("Colorblind-Friendly Palette", fontsize=dm.fs(1))
ax3.set_xticks(x_plot)
ax3.set_xticklabels(["A", "B", "C", "D", "E", "F"], fontsize=dm.fs(-1))

# Panel D: Lightness progression
ax4 = fig.add_subplot(gs[1, 1])
# Show different lightness levels
colors_lightness = [
    ("oc.blue2", "Light"),
    ("oc.blue4", "Medium-Light"),
    ("oc.blue5", "Medium"),
    ("oc.blue6", "Medium-Dark"),
    ("oc.blue8", "Dark"),
]
y_pos = np.arange(len(colors_lightness))
for i, (color, label) in enumerate(colors_lightness):
    ax4.barh(i, 1, color=color, alpha=0.8, edgecolor="black", linewidth=0.3)
    ax4.text(
        0.5,
        i,
        label,
        ha="center",
        va="center",
        fontsize=dm.fs(-1),
        color="white",
        weight="bold",
    )
ax4.set_xlim(0, 1)
ax4.set_ylim(-0.5, len(colors_lightness) - 0.5)
ax4.set_yticks([])
ax4.set_xticks([])
ax4.set_title("Lightness Progression", fontsize=dm.fs(1))
ax4.spines["top"].set_visible(False)
ax4.spines["right"].set_visible(False)
ax4.spines["bottom"].set_visible(False)
ax4.spines["left"].set_visible(False)

dm.simple_layout(fig, gs=gs)
plt.show()
