"""Stacked bar chart with three series."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

categories = ["Q1", "Q2", "Q3", "Q4"]
a = [20, 35, 30, 35]
b = [25, 32, 34, 20]
c = [15, 18, 22, 28]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
x = np.arange(len(categories))
ax.bar(x, a, label="A", color="oc.blue5")
ax.bar(x, b, bottom=a, label="B", color="oc.green5")
bottom_c = [ai + bi for ai, bi in zip(a, b, strict=False)]
ax.bar(x, c, bottom=bottom_c, label="C", color="oc.orange5")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Value")
ax.legend()
dm.auto_layout(fig)
dm.save_formats(fig, "stacked_bar")
