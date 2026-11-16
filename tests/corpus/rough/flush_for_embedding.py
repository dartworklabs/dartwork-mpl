"""A chart drawn to sit inside a slide's frame, so its content goes flush with the canvas edge (margin=0)."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

months = np.arange(1, 13)
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.plot(months, 40 + 8 * np.sin(months / 2), label="Visitors")
ax.set(xlabel="Month", ylabel="Visitors (thousands)")

dm.simple_layout(fig, margin=0)
dm.save_formats(fig, "output/flush_for_embedding", formats=("png",))
