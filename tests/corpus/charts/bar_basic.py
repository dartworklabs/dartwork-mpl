"""Five category values as vertical bars."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = plt.subplots(
    figsize=dm.figsize_for(n_points=len(categories), n_series=1)
)
ax.bar(categories, values, color="dc.teal2", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")

dm.simple_layout(fig)
dm.save_formats(fig, "output/bar_basic", formats=("png",))
