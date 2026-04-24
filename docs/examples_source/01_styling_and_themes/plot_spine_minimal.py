"""
Minimal Axes (Tufte Style)
===========================

The most common pattern when building a clean scientific plot with
dartwork-mpl is to keep only the essential spines (left and bottom) —
the so-called Tufte style. ``dm.minimal_axes(ax)`` applies this
convention in one call.

The sample data is a synthetic damped signal; the content is
incidental, the point is the axis styling.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y = np.sin(x) + 0.1 * np.random.randn(100)

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=(dm.cm2in(12), dm.cm2in(8)))

ax.plot(x, y, color="oc.blue5", lw=dm.lw(1), label="Signal")
ax.scatter(x[::10], y[::10], color="oc.red5", s=30, zorder=5, label="Samples")

# Apply minimal style — keeps only left and bottom spines.
dm.minimal_axes(ax)

ax.set_xlabel("Time (s)", fontsize=dm.fs(0))
ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax.set_title("Minimal Axes (Tufte Style)", fontsize=dm.fs(2))
ax.legend(fontsize=dm.fs(-1), frameon=False)

dm.simple_layout(fig)
plt.show()
