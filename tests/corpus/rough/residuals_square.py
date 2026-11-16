"""Standardised residuals of two models on a square -3..3 plot, the corner tick labels meeting."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(14)
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
ax.scatter(rng.normal(0, 1, 300), rng.normal(0, 1, 300), s=6)
ax.set_xlim(-3, 3)
ax.set_ylim(-3, 3)
ax.set(xlabel="Model A residual (sd)", ylabel="Model B residual (sd)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/residuals_square", formats=("png",))
