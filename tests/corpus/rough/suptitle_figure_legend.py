"""Six regional panels under one figure title, with one legend for every panel at its default place."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

months = np.arange(1, 13)
regions = ["North", "South", "East", "West", "Central", "Islands"]
fig, axes = plt.subplots(
    2, 3, figsize=dm.figsize("17cm", "8.5cm"), sharex=True, sharey=True
)
for i, (ax, name) in enumerate(zip(axes.flat, regions, strict=True)):
    ax.plot(months, 40 + 2 * i + months, label="Actual")
    ax.plot(months, 43 + 2 * i + months / 2, label="Plan", color="dc.gray4")
    ax.set_title(name)
fig.suptitle("Every region beat plan from July on")
dm.figure_legend(fig)

dm.simple_layout(fig)
dm.save_formats(fig, "output/suptitle_figure_legend", formats=("png",))
