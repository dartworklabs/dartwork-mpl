"""
Smart Layout Solver (L-BFGS-B)
==============================

``dm.simple_layout(fig)`` replaces ``dm.simple_layout(fig)`` using an L-BFGS-B
numerical optimizer to find the optimal margins that prevent label clipping
without excessive whitespace — especially when titles span multiple lines
or y-axis labels are very wide.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.7))

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x) * 10000, color="tw.blue500", lw=dm.lw(1))

ax.set_title(
    "A Very Long and Descriptive Title\nThat Spans Multiple Lines to Test\nMargin Calculations Thoroughly"
)
ax.set_xlabel("Time Axis Label (with unit)")
ax.set_ylabel("Extremely Large Amplitude (units)")

# dm.simple_layout handles multi-line titles and wide labels better than tight_layout
dm.simple_layout(fig)
plt.show()
