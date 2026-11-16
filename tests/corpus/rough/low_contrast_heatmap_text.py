"""Hourly occupancy as a heatmap whose cell values are all printed in white, unreadable on the pale cells."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(4)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
hours = [f"{h}h" for h in range(8, 20, 2)]
occupancy = rng.integers(5, 95, size=(len(days), len(hours)))

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
im = ax.imshow(occupancy, cmap="YlGnBu")
ax.set_xticks(range(len(hours)), hours)
ax.set_yticks(range(len(days)), days)
for i in range(len(days)):
    for j in range(len(hours)):
        ax.text(j, i, occupancy[i, j], ha="center", va="center", color="white")
fig.colorbar(im, ax=ax, label="Occupancy (%)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/low_contrast_heatmap_text", formats=("png",))
