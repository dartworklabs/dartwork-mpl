"""
Directional Axes & Tick Formatting
==================================

Clean up standard matplotlib axes with exact decimal control via ``dm.set_decimal()``
and directional arrows via ``dm.arrow_axis()`` for conceptual or data-ink optimized plots.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("minimal")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "golden"))

x = np.linspace(-5, 5, 100)
y = np.exp(-(x**2))

ax.plot(x, y, color="tw.rose500", lw=dm.lw(2))

# Convert traditional axes to semantic directional arrows
# Note: Default offset has been improved to -0.10 to avoid overlap
dm.arrow_axis(ax, "x", "Standard Deviation")
dm.arrow_axis(ax, "y", "Probability Density")

# Arrow axes extend past the standard plot area — give the bottom and
# left edges extra inset so the arrowheads don't kiss the canvas.
dm.simple_layout(
    fig, ml=dm.inch(0.12), mr=dm.inch(0.08), mb=dm.inch(0.12), mt=dm.inch(0.08)
)
plt.show()
