"""Thirty days of orders as bars with a two-decimal value on every bar."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(8)
days = np.arange(1, 31)
orders = rng.normal(1250, 180, days.size)

fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
bars = ax.bar(days, orders)
ax.bar_label(bars, fmt="%.2f")
ax.set(xlabel="Day of month", ylabel="Orders")

dm.simple_layout(fig)
dm.save_formats(fig, "output/crowded_value_labels", formats=("png",))
