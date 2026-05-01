"""
Style Preset: ``report``
========================

The ``report`` preset is calibrated for business and analytical reports:
slightly larger fonts than ``scientific`` and balanced spine weights so
that figures remain legible at A4 page sizes.

Use ``dm.style.use("report")`` and let ``dm.fs()``/``dm.lw()`` keep
fonts and line widths proportional to the preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + np.random.normal(0, 0.1, 100)
y2 = np.cos(x) * 0.8 + np.random.normal(0, 0.1, 100)

dm.style.use("report")
fig, ax = dm.subplots(width="9cm", aspect="wide")

ax.plot(x, y1, label="Signal A", color="oc.blue5", lw=dm.lw(0))
ax.plot(x, y2, label="Signal B", color="oc.grape5", lw=dm.lw(0))

ax.set_title("Style Preset: 'report'")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Amplitude")
ax.legend(loc="upper right")

dm.simple_layout(fig)
plt.show()
