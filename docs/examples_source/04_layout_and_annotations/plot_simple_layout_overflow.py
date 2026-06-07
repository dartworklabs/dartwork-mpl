"""
Simple Layout: Preventing Text Overflow
=======================================

``dm.simple_layout()`` measures the actual bounding boxes of every text
element on every axes and arithmetically places the GridSpec so the
content union sits at the requested distance from each figure edge.
This example exaggerates the problem with multi-line titles and verbose
y-axis labels so the corrective behaviour is visible at a glance.

The function works by:

1. **Draw**: Forces ``fig.canvas.draw()`` to populate text metrics.
2. **Measure**: Walks every visible artist on each axes (texts, title,
   axis labels, view-limited tick labels, axis offset text, legend).
3. **Place**: Sets GridSpec edges arithmetically so the content
   union sits at the requested ``margin`` from each figure edge.
4. **Re-measure**: Repeats until consecutive iterations agree to
   within 0.5 px (typically 2 iterations).
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=dm.figsize("16cm", "cinema"))

x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.cos(x) + 0.1 * np.random.randn(100)

ax1.plot(x, y1, color="dc.ocean2", lw=dm.lw(1))
ax1.set_title(
    "Panel A: Demonstration of\nMulti-Line Title with Potential Overflow\nThird Line for Extra Challenge",
    fontsize=dm.fs(1),
)
ax1.set_ylabel(
    "Extremely Long Y-Axis Label\nThat Spans Multiple Lines\n(Units: km/h)",
    fontsize=dm.fs(0),
)
ax1.set_xlabel("Time [seconds]", fontsize=dm.fs(0))

ax2.plot(x, y2, color="dc.vivid2", lw=dm.lw(1))
ax2.set_title("Panel B: Normal Title", fontsize=dm.fs(1))
ax2.set_ylabel("Value", fontsize=dm.fs(0))
ax2.set_xlabel("Time [seconds]", fontsize=dm.fs(0))

dm.label_axes([ax1, ax2])

print("Applying simple_layout to prevent text overflow...")
dm.simple_layout(fig, margin=dm.inch(0.05), verbose=True)

plt.show()
