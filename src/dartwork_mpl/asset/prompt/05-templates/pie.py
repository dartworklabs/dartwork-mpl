"""Pie chart with four slices."""

import dartwork_mpl as dm

labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]

fig, ax = dm.subplots(width="11cm", aspect="square")
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
ax.set_aspect("equal")
dm.auto_layout(fig)
dm.save_and_show(fig, "pie")
