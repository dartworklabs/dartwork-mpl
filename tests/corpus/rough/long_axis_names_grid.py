"""Four plant KPIs over a year in a 2 x 2 grid, each panel with its full measure name on the y axis."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(2)
months = np.arange(1, 13)
names = [
    "Average energy use per unit (kWh)",
    "Scrap rate of finished parts (%)",
    "Mean time between failures (h)",
    "On-time delivery to customers (%)",
]
fig, axes = plt.subplots(2, 2, figsize=dm.figsize("12cm", "7cm"), sharex=True)
for ax, name in zip(axes.flat, names, strict=True):
    ax.plot(months, 50 + np.cumsum(rng.normal(0, 2, months.size)))
    ax.set_ylabel(name)
for ax in axes[1]:
    ax.set_xlabel("Month")

dm.simple_layout(fig)
dm.save_formats(fig, "output/long_axis_names_grid", formats=("png",))
