"""Histogram of standard normal samples."""

import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.standard_normal(1000)

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.hist(data, bins=30, color="dc.blue500", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_ylabel("Frequency")
dm.auto_layout(fig)
dm.save_and_show(fig, "histogram")
