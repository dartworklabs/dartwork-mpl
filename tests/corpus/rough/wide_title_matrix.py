"""A slide correlation matrix whose one-sentence title is wider than the square canvas."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

assets = ["Stocks", "Bonds", "REITs", "Gold", "Cash"]
rng = np.random.default_rng(3)
returns = rng.normal(size=(60, len(assets)))
returns[:, 2] += returns[:, 0]

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
ax.imshow(np.corrcoef(returns.T), cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(assets)), assets)
ax.set_yticks(range(len(assets)), assets)
ax.set_title("Stocks and REITs moved together most")

dm.simple_layout(fig)
dm.save_formats(fig, "output/wide_title_matrix", formats=("png",))
