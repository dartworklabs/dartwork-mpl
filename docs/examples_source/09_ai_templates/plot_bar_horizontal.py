"""
Bar (horizontal)
================

Horizontal bar chart - basic template.

Source: ``dartwork_mpl/asset/prompt/05-templates/bar_horizontal.py`` ·
``dm.get_prompt("05-templates/bar_horizontal")`` · MCP
``dartwork-mpl://templates/bar_horizontal``.
"""

# ai-template-meta-start
# use_case: Compare categories when labels are long or ranked
# difficulty: beginner
# data_shape: categories: list[str], values: list[float]
# tags: bar, horizontal, ranking
# ai-template-meta-end

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

categories = [
    "Category A",
    "Category B",
    "Category C",
    "Category D",
    "Category E",
]
values = [23, 45, 56, 78, 33]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.barh(
    categories, values, color="dc.corporate2", edgecolor="white", linewidth=0.3
)
ax.set_xlabel("Value")
ax.invert_yaxis()
ax.set_title("Horizontal bars", fontsize=dm.fs(1), fontweight=dm.fw(1))

dm.simple_layout(fig)
