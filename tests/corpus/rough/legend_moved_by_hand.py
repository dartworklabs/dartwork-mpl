"""Quarterly sales with the legend placed above, then moved by hand with set_loc and laid out again at a slide width."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

quarters = ["Q1", "Q2", "Q3", "Q4"]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.plot(quarters, [12, 15, 14, 18], marker="o", label="Laptops")
ax.plot(quarters, [8, 9, 11, 10], marker="o", label="Tablets")
ax.plot(quarters, [20, 19, 22, 25], marker="o", label="Phones")
ax.set_ylabel("Units sold (k)")
dm.place_legend(ax, loc="above")
dm.simple_layout(fig)

legend = ax.get_legend()
legend.set_loc("lower left")
fig.set_size_inches(dm.figsize("16cm", "wide"))
dm.simple_layout(fig)
dm.save_formats(fig, "output/legend_moved_by_hand", formats=("png",))
