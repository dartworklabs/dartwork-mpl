"""
Bar (stacked)
=============

Stacked bar chart with three series.

Source: ``dartwork_mpl/asset/prompt/05-templates/stacked_bar.py`` ·
``dm.get_prompt("05-templates/stacked_bar")`` · MCP
``dartwork-mpl://templates/stacked_bar``.
"""

# ai-template-meta-start
# use_case: Show parts-of-whole composition across categories
# difficulty: intermediate
# data_shape: categories: list[str], series: dict[str, list[float]]
# tags: bar, stacked, composition, share
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["Q1", "Q2", "Q3", "Q4"]
a = [20, 35, 30, 35]
b = [25, 32, 34, 20]
c = [15, 18, 22, 28]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
x = np.arange(len(categories))
ax.bar(x, a, label="A", color="dc.teal2")
ax.bar(x, b, bottom=a, label="B", color="dc.green2")
bottom_c = [ai + bi for ai, bi in zip(a, b, strict=False)]
ax.bar(x, c, bottom=bottom_c, label="C", color="dc.orange2")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Value")
ax.legend()
ax.set_title("Stacked bars", fontsize=dm.fs(1), fontweight=dm.fw(1))

dm.simple_layout(fig)
