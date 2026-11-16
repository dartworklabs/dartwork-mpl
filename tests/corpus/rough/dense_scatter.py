"""Five thousand customers in two segments filling the Axes edge to edge (margins 0), with a default legend."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(9)
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
for name, centre in [("Retail", (40, 300)), ("Wholesale", (60, 700))]:
    age = rng.normal(centre[0], 12, 2500)
    spend = rng.normal(centre[1], 180, 2500)
    ax.scatter(age, spend, s=4, alpha=0.5, label=name)
ax.margins(0)
ax.set(xlabel="Age (years)", ylabel="Annual spend (USD)")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/dense_scatter", formats=("png",))
