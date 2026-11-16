"""Fifty points with a linear relationship as a scatter."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
x = rng.normal(size=50)
y = 2 * x + rng.normal(scale=0.5, size=50)

fig, ax = plt.subplots(figsize=dm.figsize_for())
ax.scatter(x, y, color="dc.teal2", edgecolor="white", linewidth=0.3, s=20)
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")

dm.simple_layout(fig)
dm.save_formats(fig, "output/scatter_basic", formats=("png",))
