"""
Spines on Dark Theme
=====================

Spine utilities layer on top of any matplotlib rcParams, including the
``dark`` theme. This 1×2 figure compares a minimal-axes variant with
light grey spines on a dark background and a framed variant with a
coloured orange border.

Axis labels and tick colours are set explicitly to white so they
remain visible on the dark face colour regardless of the enclosing
rcParams.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.exp(-x / 5) * np.cos(2 * x)

dm.style.use("dark")
dm.style.use("scientific")
fig, (ax1, ax2) = dm.subplots(1, 2, width="16cm", aspect="cinema", facecolor="#1a1a1a")

# Minimal axes with light grey spines.
ax1.plot(x, y1, color="oc.blue4", lw=dm.lw(1))
dm.minimal_axes(ax1)
dm.style_spines(ax1, color="#CCCCCC", linewidth=0.8)
dm.add_grid(ax1, alpha=0.1, color="white", linestyle=":")
ax1.set_title("Dark Theme — Minimal", fontsize=dm.fs(1), color="white")
ax1.set_xlabel("X", fontsize=dm.fs(0), color="white")
ax1.set_ylabel("Y", fontsize=dm.fs(0), color="white")
ax1.tick_params(colors="white")
ax1.set_facecolor("#1a1a1a")

# Framed with coloured orange border.
ax2.plot(x, y2, color="oc.orange4", lw=dm.lw(1))
dm.add_frame(ax2, color="oc.orange6", linewidth=2)
dm.add_grid(ax2, alpha=0.15, color="white", linestyle="-", linewidth=0.5)
ax2.set_title("Dark Theme — Framed", fontsize=dm.fs(1), color="white")
ax2.set_xlabel("X", fontsize=dm.fs(0), color="white")
ax2.set_ylabel("Y", fontsize=dm.fs(0), color="white")
ax2.tick_params(colors="white")
ax2.set_facecolor("#1a1a1a")

dm.simple_layout(fig)
plt.show()
