"""
Scatter
=======

Scatter with linear trend.

Source: ``dartwork_mpl/asset/prompt/05-templates/scatter.py`` ·
``dm.get_prompt("05-templates/scatter")`` · MCP
``dartwork-mpl://templates/scatter``.
"""

# ai-template-meta-start
# use_case: Show the relationship between two numeric variables
# difficulty: beginner
# data_shape: x: list[float], y: list[float]
# tags: scatter, correlation, 2d, relationship
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
x = rng.normal(size=50)
y = 2 * x + rng.normal(scale=0.5, size=50)

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.scatter(x, y, color="dc.corporate2", edgecolor="white", linewidth=0.3, s=20)
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")
ax.set_title("Scatter", fontsize=dm.fs(1), fontweight=dm.fw(1))

dm.simple_layout(fig)
