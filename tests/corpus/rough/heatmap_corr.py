"""A correlation matrix with every cell annotated: white text only past |0.6|, rotated column names, a title."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

names = ["price", "demand", "supply", "margin", "returns"]
corr = np.array(
    [
        [1.00, -0.62, 0.35, 0.71, -0.18],
        [-0.62, 1.00, -0.21, -0.44, 0.27],
        [0.35, -0.21, 1.00, 0.12, -0.05],
        [0.71, -0.44, 0.12, 1.00, -0.33],
        [-0.18, 0.27, -0.05, -0.33, 1.00],
    ]
)

fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
ax.set_yticks(range(len(names)), names)
for i in range(len(names)):
    for j in range(len(names)):
        v = corr[i, j]
        ax.text(
            j,
            i,
            f"{v:.2f}",
            ha="center",
            va="center",
            color="white" if abs(v) > 0.6 else "black",
        )
fig.colorbar(im, label="Correlation")
ax.set_title("Correlation matrix")

dm.simple_layout(fig)
dm.save_formats(fig, "output/heatmap_corr", formats=("png",))
