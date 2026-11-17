"""Actual against plan in three plants, each panel given its legend, then one shared legend for the figure."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

months = np.arange(1, 13)
fig, axes = plt.subplots(1, 3, figsize=dm.figsize("17cm", "6cm"), sharey=True)
for i, (ax, plant) in enumerate(
    zip(axes, ["Ulsan", "Pohang", "Gumi"], strict=True)
):
    ax.plot(months, 60 + 3 * i + 1.5 * months, label="Actual")
    ax.plot(months, 62 + 3 * i + months, label="Plan", color="dc.gray4")
    ax.set(title=plant, xlabel="Month")
    ax.legend()
axes[0].set_ylabel("Output (kt)")
dm.figure_legend(fig)

dm.simple_layout(fig)
dm.save_formats(fig, "output/panel_legends_then_figure", formats=("png",))
