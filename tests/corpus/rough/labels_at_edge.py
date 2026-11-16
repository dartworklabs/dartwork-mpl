"""Stock prices with each line's name typed past its last point, running off the right of the plot."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(7)
days = np.arange(60)
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
for name in ["Samsung Electronics", "SK Hynix", "LG Energy Solution"]:
    price = 100 + np.cumsum(rng.normal(0.2, 1.5, days.size))
    ax.plot(days, price)
    ax.text(days[-1] + 1, price[-1], name, va="center")
ax.set(xlabel="Trading day", ylabel="Price (indexed)")
ax.set_xlim(0, days[-1])

dm.simple_layout(fig)
dm.save_formats(fig, "output/labels_at_edge", formats=("png",))
