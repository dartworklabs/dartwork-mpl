"""Stacked bar chart with three series."""

import numpy as np

import dartwork_mpl as dm

categories = ["Q1", "Q2", "Q3", "Q4"]
a = [20, 35, 30, 35]
b = [25, 32, 34, 20]
c = [15, 18, 22, 28]

fig, ax = dm.subplots(width="13cm", aspect="standard")
x = np.arange(len(categories))
ax.bar(x, a, label="A", color="dc.blue500")
ax.bar(x, b, bottom=a, label="B", color="dc.green500")
bottom_c = [ai + bi for ai, bi in zip(a, b, strict=False)]
ax.bar(x, c, bottom=bottom_c, label="C", color="dc.orange500")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Value")
ax.legend()
dm.auto_layout(fig)
dm.save_and_show(fig, "stacked_bar")
