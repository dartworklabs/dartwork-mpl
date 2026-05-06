"""Pie chart with four slices."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["oc.blue5", "oc.green5", "oc.orange5", "oc.red5"]

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
ax.set_aspect("equal")
dm.auto_layout(fig)
dm.save_formats(fig, "pie")
