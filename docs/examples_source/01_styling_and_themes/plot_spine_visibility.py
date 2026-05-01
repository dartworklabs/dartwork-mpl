"""
Custom Spine Visibility
========================

Control which spines are visible for different visual effects. The
four panels below compare: hiding top + right (the most common
minimal preset), keeping only the bottom spine, removing every spine
and leaning on a grid for reference, and finally a full rectangular
frame.

The four samples are three synthetic 1D signals; the axis styling is
the point.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.exp(-x / 5) * np.cos(2 * x)
y3 = x + 0.5 * np.random.randn(100)

dm.style.use("scientific")
fig, axes = dm.subplots(2, 2, width="16cm", aspect="standard")

# Top-left: hide top and right (same as minimal_axes).
ax1 = axes[0, 0]
ax1.plot(x, y1, color="oc.green5", lw=dm.lw(1))
dm.hide_spines(ax1, ["top", "right"])
ax1.set_title("Hide Top & Right", fontsize=dm.fs(1))

# Top-right: show only the bottom spine.
ax2 = axes[0, 1]
ax2.plot(x, y2, color="oc.purple5", lw=dm.lw(1))
dm.show_only_spines(ax2, ["bottom"])
ax2.set_title("Bottom Spine Only", fontsize=dm.fs(1))

# Bottom-left: hide all spines — rely on the grid.
ax3 = axes[1, 0]
ax3.plot(x, y3, color="oc.orange5", lw=dm.lw(1))
dm.hide_all_spines(ax3)
dm.add_grid(ax3, alpha=0.2)
ax3.set_title("No Spines (Floating)", fontsize=dm.fs(1))

# Bottom-right: full rectangular frame.
ax4 = axes[1, 1]
ax4.plot(x, y1, color="oc.cyan5", lw=dm.lw(1))
dm.add_frame(ax4, color="black", linewidth=1.5)
ax4.set_title("Full Frame", fontsize=dm.fs(1))

dm.label_axes(axes.flat)
dm.simple_layout(fig)
plt.show()
