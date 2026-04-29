"""
Style Preset: ``minimal``
=========================

The ``minimal`` preset removes most decorative chrome — light spines,
subtle ticks, and reduced label weights — to give the data maximum
visual prominence. Best for explanatory diagrams in slide decks or
landing pages.

Use ``dm.style.use("minimal")`` and let ``dm.fs()``/``dm.lw()`` keep
fonts and line widths proportional to the preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + np.random.normal(0, 0.1, 100)
y2 = np.cos(x) * 0.8 + np.random.normal(0, 0.1, 100)

dm.style.use("minimal")
fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.7))

ax.plot(x, y1, label="Signal A", color="oc.blue5", lw=dm.lw(0))
ax.plot(x, y2, label="Signal B", color="oc.grape5", lw=dm.lw(0))

ax.set_title("Style Preset: 'minimal'")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")
ax.legend(loc="upper right")

dm.simple_layout(fig)
plt.show()
