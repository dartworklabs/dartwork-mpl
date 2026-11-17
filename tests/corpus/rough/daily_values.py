"""Visitors per day for one month as bars in an 8.5 cm report column, the count written on every bar."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(4)
days = np.arange(1, 31)
visitors = rng.integers(1800, 2600, days.size)

fig, ax = plt.subplots(figsize=dm.figsize("8.5cm", "wide"))
ax.bar(days, visitors)
dm.label_bars(ax)
ax.set(xlabel="Day of June", ylabel="Visitors")

dm.simple_layout(fig)
dm.save_formats(fig, "output/daily_values", formats=("png",))
