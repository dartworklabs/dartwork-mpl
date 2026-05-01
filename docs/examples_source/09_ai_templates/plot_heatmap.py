"""
Heatmap
=======

8x8 random heatmap with colorbar.

Source: ``dartwork_mpl/asset/prompt/05-templates/heatmap.py`` ·
``dm.get_prompt("05-templates/heatmap")`` · MCP
``dartwork-mpl://templates/heatmap``.
"""

import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.random(size=(8, 8))

fig, ax = dm.subplots(width="11cm", aspect="square")
im = ax.imshow(data, cmap="viridis", aspect="auto")
fig.colorbar(im, ax=ax)
ax.set_xlabel("Column")
ax.set_ylabel("Row")
dm.auto_layout(fig)
