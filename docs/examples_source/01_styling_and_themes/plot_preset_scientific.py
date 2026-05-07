"""
Style Preset: ``scientific``
============================

The ``scientific`` preset is tuned for publication-style plots:
moderate font sizes, thin spines, and crisp gridless axes. It pairs
well with figures destined for journal articles or LaTeX documents.

Use ``dm.style.use("scientific")`` and let ``dm.fs()``/``dm.lw()`` keep
fonts and line widths proportional to the preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + np.random.normal(0, 0.1, 100)
y2 = np.cos(x) * 0.8 + np.random.normal(0, 0.1, 100)

# 0.4 API: dm.style.use(...) + plt.subplots(figsize=dm.figsize(...)).
# 9 cm = academic single-column width (also available as dm.col1).
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

ax.plot(x, y1, label="Signal A", color="oc.blue5", lw=dm.lw(0))
ax.plot(x, y2, label="Signal B", color="oc.grape5", lw=dm.lw(0))

ax.set_title("Style Preset: 'scientific'")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")
ax.legend(loc="upper right")

dm.simple_layout(fig)
plt.show()
