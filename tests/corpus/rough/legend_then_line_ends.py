"""Three product lines over the year, first with a legend, then named at their ends instead."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

months = np.arange(1, 13)
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.plot(months, 20 + 2.0 * months, label="Laptops")
ax.plot(months, 35 + 0.5 * months, label="Phones")
ax.plot(months, 15 + 1.2 * months, label="Tablets")
ax.set(xlabel="Month", ylabel="Units sold (k)")
ax.legend()
dm.label_line_ends(ax)

dm.simple_layout(fig)
dm.save_formats(fig, "output/legend_then_line_ends", formats=("png",))
