"""
Custom Colormaps
================

Build sequential, diverging, and discrete colormaps and compare them side by side.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

import dartwork_mpl as dm

dm.style.use("presentation")

# Generate data
x = y = np.linspace(-3, 3, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(np.sqrt(X**2 + Y**2))

fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.95,
    top=0.95,
    bottom=0.08,
    wspace=0.35,
    hspace=0.4,
)

# Panel A: Custom sequential colormap
ax1 = fig.add_subplot(gs[0, 0])
colors_seq = ["white", "oc.blue3", "oc.blue5", "oc.blue7"]
n_bins = 100
cmap_custom = LinearSegmentedColormap.from_list(
    "custom_blue", colors_seq, N=n_bins
)
im1 = ax1.contourf(X, Y, Z, levels=20, cmap=cmap_custom)
plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
ax1.set_xlabel("X", fontsize=dm.fs(0))
ax1.set_ylabel("Y", fontsize=dm.fs(0))
ax1.set_title("Custom Sequential", fontsize=dm.fs(1))

# Panel B: Custom diverging colormap
ax2 = fig.add_subplot(gs[0, 1])
colors_div = ["oc.blue7", "oc.blue5", "white", "oc.red5", "oc.red7"]
cmap_div = LinearSegmentedColormap.from_list("custom_div", colors_div, N=256)
im2 = ax2.contourf(X, Y, Z, levels=20, cmap=cmap_div)
plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
ax2.set_xlabel("X", fontsize=dm.fs(0))
ax2.set_ylabel("Y", fontsize=dm.fs(0))
ax2.set_title("Custom Diverging", fontsize=dm.fs(1))

# Panel C: Discrete colormap
ax3 = fig.add_subplot(gs[1, 0])
colors_discrete = [
    "oc.red5",
    "oc.orange5",
    "oc.yellow5",
    "oc.green5",
    "oc.blue5",
    "oc.violet5",
]
cmap_discrete = ListedColormap(colors_discrete)
im3 = ax3.contourf(X, Y, Z, levels=6, cmap=cmap_discrete)
plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, ticks=np.linspace(-1, 1, 6))
ax3.set_xlabel("X", fontsize=dm.fs(0))
ax3.set_ylabel("Y", fontsize=dm.fs(0))
ax3.set_title("Discrete Colors", fontsize=dm.fs(1))

# Panel D: Gradient demonstration
ax4 = fig.add_subplot(gs[1, 1])
gradient = np.linspace(0, 1, 256).reshape(1, -1)
cmaps_demo = [
    (cmap_custom, "Custom Seq"),
    (cmap_div, "Custom Div"),
    (cmap_discrete, "Discrete"),
    ("viridis", "Viridis"),
    ("plasma", "Plasma"),
    ("cividis", "Cividis"),
]
n_gradients = len(cmaps_demo)
# Extend gradient length to match the axes width and add label column outside the axes.
for spine in ax4.spines.values():
    spine.set_visible(True)
for i, (cmap, label) in enumerate(cmaps_demo):
    ax4.imshow(
        gradient,
        aspect="auto",
        cmap=cmap,
        extent=[0, 1, i, i + 1],
        origin="lower",
    )
    ax4.text(1.02, i + 0.5, label, ha="left", va="center", fontsize=dm.fs(-1))
ax4.set_xlim(0, 1.1)
ax4.set_ylim(0, n_gradients)
ax4.set_xticks([])
ax4.set_xlabel("")
ax4.set_title("Colormap Comparison", fontsize=dm.fs(1), pad=10)
ax4.set_yticks([])

dm.simple_layout(fig, gs=gs)
plt.show()
