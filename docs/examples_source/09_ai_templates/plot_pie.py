"""
Pie
===

Pie chart with four slices.

Source: ``dartwork_mpl/asset/prompt/05-templates/pie.py`` ·
``dm.get_prompt("05-templates/pie")`` · MCP ``dartwork-mpl://templates/pie``.
"""

# ai-template-meta-start
# use_case: Show shares of a small whole
# difficulty: beginner
# data_shape: labels: list[str], sizes: list[float]
# tags: pie, share, composition, proportion
# ai-template-meta-end

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["dc.ocean2", "dc.forest2", "dc.sunset2", "dc.vivid2"]

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
ax.set_aspect("equal")
ax.set_title("Composition", fontsize=dm.fs(1), fontweight=dm.fw(1))

dm.simple_layout(fig)
