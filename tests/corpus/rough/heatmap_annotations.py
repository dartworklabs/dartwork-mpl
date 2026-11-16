"""A 12 x 12 distance matrix with a two-decimal value in every cell at body text size."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(5)
points = rng.random((12, 2)) * 100
dist = np.linalg.norm(points[:, None] - points[None, :], axis=-1)
names = [f"Site {i + 1}" for i in range(12)]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "square"))
im = ax.imshow(dist, cmap="viridis")
ax.set_xticks(range(12), names, rotation=90)
ax.set_yticks(range(12), names)
for i in range(12):
    for j in range(12):
        ax.text(j, i, f"{dist[i, j]:.2f}", ha="center", va="center", color="w")
fig.colorbar(im, ax=ax, label="Distance (km)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/heatmap_annotations", formats=("png",))
