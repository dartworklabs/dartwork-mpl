"""8x8 random heatmap with colorbar."""

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
dm.save_formats(fig, "heatmap")
