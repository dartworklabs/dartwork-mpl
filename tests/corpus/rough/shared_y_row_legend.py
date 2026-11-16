"""Four regions in one report row sharing their y axis, one long y name and a figure legend: the name was taller than the room left under the legend, so the layout shrank the plots to slivers and never wrapped it."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(3)
months = np.arange(1, 13)
regions = ["North", "South", "East", "West"]

fig, axes = plt.subplots(1, 4, figsize=dm.figsize("17cm", "4.7cm"), sharey=True)
for ax, region in zip(axes, regions, strict=True):
    ax.plot(months, 50 + np.cumsum(rng.normal(1, 3, 12)), label="Online")
    ax.plot(months, 40 + np.cumsum(rng.normal(1, 3, 12)), label="Stores")
    ax.set_title(region)
    ax.set_xlabel("Month")
axes[0].set_ylabel("Monthly revenue in million KRW")
dm.figure_legend(fig)
dm.label_axes(axes)

dm.simple_layout(fig)
dm.save_formats(fig, "output/shared_y_row_legend", formats=("png",))
