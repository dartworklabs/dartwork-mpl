"""
Smart Layout Solver (L-BFGS-B)
==============================

``dm.simple_layout(fig)`` runs an L-BFGS-B optimizer on the GridSpec
margins to keep multi-line titles and wide y-labels from clipping —
without bleeding excessive whitespace.

In 0.4 the everyday entry point for layout is ``dm.simple_layout(fig)``,
which wraps ``simple_layout`` in a measure→adjust→retry loop. Reach
for ``simple_layout`` directly when (a) you have a custom GridSpec
(spans, nested grids, attached colorbars) or (b) you want the cheaper
non-iterative call for many small figures.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# 0.4 API: plt.subplots(figsize=dm.figsize(...)). 9 cm × standard is the
# academic single-column default (also available as dm.col1).
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x) * 10000, color="tw.blue500", lw=dm.lw(1))

ax.set_title(
    "A Very Long and Descriptive Title\nThat Spans Multiple Lines to Test\nMargin Calculations Thoroughly"
)
ax.set_xlabel("Time Axis Label (with unit)")
ax.set_ylabel("Extremely Large Amplitude (units)")

# simple_layout handles multi-line titles and wide labels; for uniform
# grids, prefer dm.simple_layout(fig) which iterates simple_layout.
dm.simple_layout(fig)
plt.show()
