"""Three series per quarter as grouped bars."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["Q1", "Q2", "Q3", "Q4"]
series_a = [20, 35, 30, 35]
series_b = [25, 32, 34, 20]
series_c = [15, 18, 22, 28]

fig, ax = plt.subplots(
    figsize=dm.figsize_for("grouped", n_points=len(categories), n_series=3)
)
x = np.arange(len(categories))
bar_width = 0.27
ax.bar(x - bar_width, series_a, bar_width, label="Series A", color="dc.teal2")
ax.bar(x, series_b, bar_width, label="Series B", color="dc.green2")
ax.bar(x + bar_width, series_c, bar_width, label="Series C", color="dc.orange2")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Value")
dm.place_legend(ax)

dm.simple_layout(fig)
dm.save_formats(fig, "output/bar_grouped_basic", formats=("png",))
