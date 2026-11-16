"""Positive and negative values per category as a tornado chart."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["Cat A", "Cat B", "Cat C", "Cat D"]
positive = [10, 25, 15, 30]
negative = [-8, -20, -12, -28]

fig, ax = plt.subplots(
    figsize=dm.figsize_for("barh", n_points=len(categories), n_series=2)
)
y_pos = np.arange(len(categories))
ax.barh(y_pos, positive, color="dc.teal2", label="Positive")
ax.barh(y_pos, negative, color="dc.red2", label="Negative")
ax.set_yticks(y_pos)
ax.set_yticklabels(categories)
ax.axvline(0, color="black", linewidth=0.3)
ax.set_xlabel("Value")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/tornado_basic", formats=("png",))
