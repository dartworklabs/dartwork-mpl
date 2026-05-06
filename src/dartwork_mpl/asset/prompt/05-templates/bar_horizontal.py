"""Horizontal bar chart - basic template."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

categories = [
    "Category A",
    "Category B",
    "Category C",
    "Category D",
    "Category E",
]
values = [23, 45, 56, 78, 33]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.barh(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.invert_yaxis()
dm.auto_layout(fig)
dm.save_formats(fig, "bar_horizontal")
