"""Vertical bar chart - basic template."""

import dartwork_mpl as dm

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
dm.save_formats(fig, "bar")
