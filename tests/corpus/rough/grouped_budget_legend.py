"""Four years of budget for three departments as grouped bars in a 9 cm square, the legend placed clear of the bars."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

departments = [
    "Research and Development",
    "Sales and Marketing",
    "Customer Success",
]
budget = {
    "2021": [6.4, 8.0, 7.4],
    "2022": [9.2, 8.7, 9.3],
    "2023": [1.2, 4.9, 5.4],
    "2024": [1.6, 1.1, 8.5],
}

x = np.arange(len(departments))
width = 0.2
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
for i, (year, values) in enumerate(budget.items()):
    ax.bar(x + (i - 1.5) * width, values, width, label=year)
ax.set_xticks(x, departments)
ax.set_ylabel("Budget (USD m)")
dm.place_legend(ax)

dm.simple_layout(fig)
dm.save_formats(fig, "output/grouped_budget_legend", formats=("png",))
