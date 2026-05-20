"""Vertical bar chart - basic template."""

# ai-template-meta-start
# use_case: Compare a small set of categorical values
# difficulty: beginner
# data_shape: categories: list[str], values: list[float]
# tags: bar, categorical, comparison
# ai-template-meta-end

import matplotlib.pyplot as plt

import dartwork_mpl as dm

# Pick a style preset first — switch to "report", "presentation",
# "minimal", or any *-kr variant to retarget the figure.
dm.style.use("scientific")

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Category")
ax.set_ylabel("Value")
ax.set_title("Vertical bars", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
dm.save_formats(fig, "bar")
