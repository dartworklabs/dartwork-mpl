"""An 8 x 8 matrix of values as a heatmap with a colorbar."""

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
data = rng.random(size=(8, 8))

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
im = ax.imshow(data, cmap="viridis", aspect="equal")
# Colorbar pinned to the heatmap so its bar length matches the spine.
cax = make_axes_locatable(ax).append_axes("right", size="4%", pad=0.15)
fig.colorbar(im, cax=cax, label="Value")
ax.set_xlabel("Column")
ax.set_ylabel("Row")

dm.simple_layout(fig)
dm.save_formats(fig, "output/heatmap_basic", formats=("png",))
