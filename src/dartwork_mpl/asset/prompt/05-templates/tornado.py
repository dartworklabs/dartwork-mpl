"""Tornado chart - symmetric horizontal bars."""

import numpy as np

import dartwork_mpl as dm

categories = ["Cat A", "Cat B", "Cat C", "Cat D"]
positive = [10, 25, 15, 30]
negative = [-8, -20, -12, -28]

fig, ax = dm.subplots(width="13cm", aspect="standard")
y_pos = np.arange(len(categories))
ax.barh(y_pos, positive, color="dc.blue500", label="Positive")
ax.barh(y_pos, negative, color="dc.red500", label="Negative")
ax.set_yticks(y_pos)
ax.set_yticklabels(categories)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Value")
ax.legend()
dm.auto_layout(fig)
dm.save_and_show(fig, "tornado")
