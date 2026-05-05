"""
Publication Styles
===================

Different venues have different house conventions for spines and
grids. This 2×2 grid shows four widely-seen patterns: a
Nature/Science-like minimal plot with a faint y-grid, an IEEE-like
framed plot with a dotted major grid, a clean un-gridded framed plot
common in economics journals, and a web/presentation style with a
very low-contrast grid for high-DPI reading.

The data in every panel is a synthetic signal — only the axis style
varies.
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

# Nature / Science: minimal axes + faint y-grid.
ax1 = axes[0, 0]
ax1.plot(x, y1, "o-", color="black", markersize=3, lw=dm.lw(0.8))
for s in ["top", "right"]:
    ax1.spines[s].set_visible(False)
dm.add_grid(ax1, alpha=0.2, axis="y", linestyle="-")
ax1.set_title("Nature/Science Style", fontsize=dm.fs(1))
ax1.set_xlabel("Variable X", fontsize=dm.fs(0))
ax1.set_ylabel("Variable Y", fontsize=dm.fs(0))

# IEEE: thin full frame + dotted major grid.
ax2 = axes[0, 1]
ax2.plot(x, y2, color="oc.blue6", lw=dm.lw(1))
dm.add_frame(ax2, color="black", linewidth=0.5)
dm.add_grid(ax2, which="major", alpha=0.3, linestyle=":")
ax2.set_title("IEEE Style", fontsize=dm.fs(1))
ax2.set_xlabel("Time (s)", fontsize=dm.fs(0))
ax2.set_ylabel("Signal", fontsize=dm.fs(0))

# Economics journals: thicker black frame, no grid.
ax3 = axes[1, 0]
ax3.plot(x, y3, color="oc.gray7", lw=dm.lw(1.5))
dm.add_frame(ax3, color="black", linewidth=1)
ax3.set_title("Economics Style", fontsize=dm.fs(1))
ax3.set_xlabel("Period", fontsize=dm.fs(0))
ax3.set_ylabel("Value", fontsize=dm.fs(0))

# Web / presentation: minimal axes + very faint grid.
ax4 = axes[1, 1]
ax4.plot(x, y1, color="oc.teal5", lw=dm.lw(2))
dm.minimal_axes(ax4)
dm.add_grid(ax4, alpha=0.1, linestyle="-", color="gray")
ax4.set_title("Web/Presentation Style", fontsize=dm.fs(1))
ax4.set_xlabel("X", fontsize=dm.fs(0))
ax4.set_ylabel("Y", fontsize=dm.fs(0))

dm.label_axes(axes.flat)
dm.simple_layout(fig)
plt.show()
