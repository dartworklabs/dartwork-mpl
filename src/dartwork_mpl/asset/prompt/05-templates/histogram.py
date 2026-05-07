"""Histogram of standard normal samples."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.standard_normal(1000)

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.hist(data, bins=30, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_ylabel("Frequency")
dm.simple_layout(fig)
dm.save_formats(fig, "histogram")
