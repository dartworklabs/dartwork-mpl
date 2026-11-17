"""Energy mix per year as stacked bars, every source's share written in its segment."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

years = ["2020", "2021", "2022", "2023", "2024"]
mix = {
    "Coal": [38, 35, 33, 30, 27],
    "Gas": [26, 27, 27, 28, 28],
    "Nuclear": [27, 28, 28, 29, 30],
    "Renewables": [7, 8, 10, 11, 13],
    "Other": [2, 2, 2, 2, 2],
}

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bottom = np.zeros(len(years))
for source, share in mix.items():
    ax.bar(years, share, bottom=bottom, label=source)
    bottom += share
dm.label_bars(ax)
ax.set_ylabel("Share of generation (%)")
dm.place_legend(ax, loc="right")

dm.simple_layout(fig)
dm.save_formats(fig, "output/stacked_labelled_segments", formats=("png",))
