"""
Bar
===

Vertical bar chart - basic template.

Source: ``dartwork_mpl/asset/prompt/05-templates/bar.py`` ·
``dm.get_prompt("05-templates/bar")`` · MCP ``dartwork-mpl://templates/bar``.
"""

# ai-template-meta-start
# use_case: Compare a small set of categorical values
# difficulty: beginner
# data_shape: categories: list[str], values: list[float]
# tags: bar, categorical, comparison
# ai-template-meta-end

import matplotlib.pyplot as plt

import dartwork_mpl as dm

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.bar(categories, values, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
