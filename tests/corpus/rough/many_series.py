"""Twelve product lines on one axis with the default legend, colours repeating after eight."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(2)
weeks = np.arange(1, 27)
fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
for i in range(12):
    ax.plot(
        weeks,
        50 + np.cumsum(rng.normal(0.3, 2, weeks.size)),
        label=f"Line {i + 1}",
    )
ax.set(xlabel="Week", ylabel="Orders")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/many_series", formats=("png",))
