"""Monthly rain as bars and temperature as a line on a twin axis."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

x = np.arange(1, 13)
temp = [5, 7, 12, 18, 23, 27, 30, 29, 24, 18, 11, 6]
precip = [50, 40, 45, 55, 70, 80, 90, 85, 65, 60, 55, 50]

fig, ax1 = plt.subplots(
    figsize=dm.figsize_for(n_points=len(x), n_series=2, dual_axis=True)
)
ax2 = ax1.twinx()
ax1.bar(x, precip, color="dc.teal1", alpha=0.7, label="Precipitation")
ax2.plot(
    x, temp, color="dc.orange3", marker="o", markersize=3, label="Temperature"
)
ax1.set_xlabel("Month")
ax1.set_ylabel("Precipitation (mm)")
ax2.set_ylabel("Temperature (C)")
dm.place_legend(ax1)  # one legend for both twins

dm.simple_layout(fig)
dm.save_formats(fig, "output/twin_axis_basic", formats=("png",))
