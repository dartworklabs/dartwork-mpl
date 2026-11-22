"""Quarterly sales with the legend placed above, the title raised over it, then nudged higher by hand and laid out again."""

import matplotlib.pyplot as plt
from matplotlib.transforms import ScaledTranslation

import dartwork_mpl as dm

dm.style.use("report")

quarters = ["Q1", "Q2", "Q3", "Q4"]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.plot(quarters, [12, 15, 14, 18], marker="o", label="Laptops")
ax.plot(quarters, [8, 9, 11, 10], marker="o", label="Tablets")
ax.plot(quarters, [20, 19, 22, 25], marker="o", label="Phones")
ax.set_ylabel("Units sold (k)")
ax.set_title("Phones lead every quarter")
dm.place_legend(ax, loc="above")
dm.simple_layout(fig)

ax.title.set_transform(
    ax.transAxes + ScaledTranslation(0, 0.3, fig.dpi_scale_trans)
)
dm.simple_layout(fig)
dm.save_formats(fig, "output/title_moved_over_legend", formats=("png",))
