"""
Dashboard with Mixed Spine Styles
==================================

A single figure that combines several spine presets on a 3×3
GridSpec: a minimal main panel (2×2), a framed bar panel, a pie
distribution with no spines, and a bottom row of three variants
(minimal / framed / floating) so the contrast between presets is
visible side by side.

The data is synthetic; this is a styling showcase, not a data
visualisation.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.exp(-x / 5) * np.cos(2 * x)
y3 = x + 0.5 * np.random.randn(100)

dm.style.use("report")
fig = dm.figure(width="20cm", aspect="standard")
gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.4)

# Main plot — 2×2 minimal axes with two overlaid series.
ax_main = fig.add_subplot(gs[:2, :2])
ax_main.plot(x, y1, color="oc.blue6", lw=dm.lw(1.5), label="Primary")
ax_main.plot(x, y2, color="oc.red6", lw=dm.lw(1.5), label="Secondary")
dm.minimal_axes(ax_main)
dm.add_grid(ax_main, alpha=0.2)
ax_main.set_title("Main Analysis", fontsize=dm.fs(2))
ax_main.legend(fontsize=dm.fs(-1))

# Top-right — a spineless bar chart.
ax_tr = fig.add_subplot(gs[0, 2])
ax_tr.bar(range(5), np.random.rand(5), color="oc.green5")
dm.hide_all_spines(ax_tr)
ax_tr.set_title("Metrics", fontsize=dm.fs(1))

# Middle-right — pie chart needs no spine styling.
ax_mr = fig.add_subplot(gs[1, 2])
ax_mr.pie([30, 25, 20, 15, 10], colors=[f"oc.purple{i}" for i in range(3, 8)])
ax_mr.set_title("Distribution", fontsize=dm.fs(1))

# Bottom row — three variants side by side: minimal, frame, floating.
for i, spine_style in enumerate(["minimal", "frame", "floating"]):
    ax = fig.add_subplot(gs[2, i])
    ax.plot(x[:50], y3[:50], color=f"oc.{['cyan', 'orange', 'pink'][i]}5")

    if spine_style == "minimal":
        dm.minimal_axes(ax)
    elif spine_style == "frame":
        dm.add_frame(ax, color="black", linewidth=0.8)
    else:  # floating
        dm.hide_all_spines(ax)
        dm.add_grid(ax, alpha=0.15)

    ax.set_title(f"{spine_style.capitalize()} Style", fontsize=dm.fs(0))

plt.suptitle("Dashboard with Mixed Spine Styles", fontsize=dm.fs(3), y=0.98)
dm.simple_layout(fig)
plt.show()
