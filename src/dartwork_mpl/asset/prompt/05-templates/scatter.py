"""Scatter with linear trend."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
x = rng.normal(size=50)
y = 2 * x + rng.normal(scale=0.5, size=50)

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.scatter(x, y, color="oc.blue5", edgecolor="white", linewidth=0.3, s=20)
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")
dm.simple_layout(fig)
dm.save_formats(fig, "scatter")
