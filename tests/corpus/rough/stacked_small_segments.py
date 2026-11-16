"""Household spending per year as stacked bars with a centred value in every segment, the thin ones included."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

years = ["2021", "2022", "2023", "2024"]
spending = {
    "Housing": [1450, 1520, 1610, 1690],
    "Food": [620, 660, 700, 720],
    "Transport": [310, 330, 345, 360],
    "Leisure": [45, 60, 52, 70],
    "Education": [25, 30, 28, 35],
}

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bottom = np.zeros(len(years))
for name, values in spending.items():
    bars = ax.bar(years, values, bottom=bottom, label=name)
    ax.bar_label(bars, label_type="center")
    bottom += values
ax.set_ylabel("Monthly spending (USD)")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/stacked_small_segments", formats=("png",))
