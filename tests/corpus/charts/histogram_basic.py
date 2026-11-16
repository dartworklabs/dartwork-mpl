"""The distribution of 1000 normal samples as a histogram."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
data = rng.standard_normal(1000)

fig, ax = plt.subplots(figsize=dm.figsize_for())
ax.hist(data, bins=30, color="dc.teal2", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_ylabel("Frequency")

dm.simple_layout(fig)
dm.save_formats(fig, "output/histogram_basic", formats=("png",))
