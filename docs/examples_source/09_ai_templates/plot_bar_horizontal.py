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

import dartwork_mpl as dm

categories = [
    "Category A",
    "Category B",
    "Category C",
    "Category D",
    "Category E",
]
values = [23, 45, 56, 78, 33]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.barh(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.invert_yaxis()
dm.auto_layout(fig)
