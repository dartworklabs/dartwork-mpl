"""
Auto Layout: Preventing Text Overflow
=====================================

``dm.auto_layout()`` measures the actual bounding boxes of every text
element and iteratively grows the figure margins only on the sides
where overflow is detected. This example exaggerates the problem with
multi-line titles and verbose y-axis labels so the corrective behaviour
is visible at a glance.

The function works by:

1. **Initial Layout**: Applies minimal margins as a starting point.
2. **Overflow Detection**: Measures bounding boxes of all text.
3. **Margin Adjustment**: Increases margins only where overflow exists.
4. **Iteration**: Repeats until no overflow remains or ``max_iter`` is hit.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

fig, (ax1, ax2) = dm.subplots(1, 2, width="16cm", aspect="cinema")

x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.cos(x) + 0.1 * np.random.randn(100)

ax1.plot(x, y1, color="oc.blue5", lw=dm.lw(1))
ax1.set_title(
    "Panel A: Demonstration of\nMulti-Line Title with Potential Overflow\nThird Line for Extra Challenge",
    fontsize=dm.fs(1),
)
ax1.set_ylabel(
    "Extremely Long Y-Axis Label\nThat Spans Multiple Lines\n(Units: km/h)",
    fontsize=dm.fs(0),
)
ax1.set_xlabel("Time [seconds]", fontsize=dm.fs(0))

ax2.plot(x, y2, color="oc.red5", lw=dm.lw(1))
ax2.set_title("Panel B: Normal Title", fontsize=dm.fs(1))
ax2.set_ylabel("Value", fontsize=dm.fs(0))
ax2.set_xlabel("Time [seconds]", fontsize=dm.fs(0))

dm.label_axes([ax1, ax2])

print("Applying auto_layout to prevent text overflow...")
dm.auto_layout(fig, padding=0.05, max_iter=5, verbose=True)

plt.show()
