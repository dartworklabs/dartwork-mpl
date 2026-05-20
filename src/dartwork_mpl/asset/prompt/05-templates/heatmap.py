"""8x8 random heatmap with colorbar."""

# ai-template-meta-start
# use_case: Show a 2D matrix with color-coded magnitude
# difficulty: beginner
# data_shape: matrix: 2D array
# tags: heatmap, matrix, correlation, image
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
data = rng.random(size=(8, 8))

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
im = ax.imshow(data, cmap="viridis", aspect="auto")
cbar = fig.colorbar(im, ax=ax)
cbar.ax.tick_params(labelsize=dm.fs(-1))
ax.set_xlabel("Column")
ax.set_ylabel("Row")
ax.set_title("Heatmap", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
dm.save_formats(fig, "heatmap")
