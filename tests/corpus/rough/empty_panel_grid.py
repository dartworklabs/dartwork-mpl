"""Five regions' monthly sales in a 2 x 3 grid, the sixth panel left as an empty frame."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(11)
months = np.arange(1, 13)
regions = ["North", "South", "East", "West", "Central"]

fig, axes = plt.subplots(2, 3, figsize=dm.figsize("17cm", "10cm"), sharex=True)
for ax, region in zip(axes.flat, regions, strict=False):
    ax.plot(months, 100 + np.cumsum(rng.normal(1, 4, months.size)))
    ax.set_title(region)
for ax in axes[:, 0]:
    ax.set_ylabel("Sales (units)")
for ax in axes[-1]:
    ax.set_xlabel("Month")

dm.simple_layout(fig)
dm.save_formats(fig, "output/empty_panel_grid", formats=("png",))
