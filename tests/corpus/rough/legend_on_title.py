"""Quarterly sales of three products with the legend pushed just above the plot, onto the title."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

quarters = ["Q1", "Q2", "Q3", "Q4"]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.plot(quarters, [12, 15, 14, 18], marker="o", label="Laptops")
ax.plot(quarters, [8, 9, 11, 10], marker="o", label="Tablets")
ax.plot(quarters, [20, 19, 22, 25], marker="o", label="Phones")
ax.set_ylabel("Units sold (k)")
ax.set_title("Phones lead every quarter")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=3)

dm.simple_layout(fig)
dm.save_formats(fig, "output/legend_on_title", formats=("png",))
