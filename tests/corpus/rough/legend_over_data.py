"""Monthly sales of four stores with the legend forced into the upper left, on top of the lines."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(1)
months = np.arange(1, 13)
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
for i, store in enumerate(["Mapo", "Gangnam", "Jongno", "Songpa"]):
    sales = 80 - 2 * months + 4 * i + rng.normal(0, 2, months.size)
    ax.plot(months, sales, label=store)
ax.set(xlabel="Month", ylabel="Sales (units)")
ax.legend(loc="upper left")

dm.simple_layout(fig)
dm.save_formats(fig, "output/legend_over_data", formats=("png",))
