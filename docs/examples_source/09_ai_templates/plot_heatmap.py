"""
Heatmap
=======

8x8 random heatmap with colorbar.

Source: ``dartwork_mpl/asset/prompt/05-templates/heatmap.py`` ·
``dm.get_prompt("05-templates/heatmap")`` · MCP
``dartwork-mpl://templates/heatmap``.
"""

# ai-template-meta-start
# use_case: Show a 2D matrix with color-coded magnitude
# difficulty: beginner
# data_shape: matrix: 2D array
# tags: heatmap, matrix, correlation, image
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.random(size=(8, 8))

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
im = ax.imshow(data, cmap="viridis", aspect="auto")
fig.colorbar(im, ax=ax)
ax.set_xlabel("Column")
ax.set_ylabel("Row")
dm.simple_layout(fig)
