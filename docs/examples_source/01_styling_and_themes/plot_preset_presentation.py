"""
Style Preset: ``presentation``
==============================

The ``presentation`` preset uses bold typography, thick lines, and high
contrast tuned for projected slides. Choose this preset when figures
need to read clearly from the back of a room.

Use ``dm.style.use("presentation")`` and let ``dm.fs()``/``dm.lw()``
keep fonts and line widths proportional to the preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + np.random.normal(0, 0.1, 100)
y2 = np.cos(x) * 0.8 + np.random.normal(0, 0.1, 100)

# 0.4 API: dm.style.use(...) + plt.subplots(figsize=dm.figsize(...)).
# Slide-friendly column width with the default standard aspect.
dm.style.use("presentation")
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

ax.plot(x, y1, label="Signal A", color="oc.blue5", lw=dm.lw(0))
ax.plot(x, y2, label="Signal B", color="oc.grape5", lw=dm.lw(0))

ax.set_title("Style Preset: 'presentation'")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")
ax.legend(loc="upper right")

dm.auto_layout(fig)
plt.show()
