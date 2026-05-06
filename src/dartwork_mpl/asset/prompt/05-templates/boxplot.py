"""Box plot across four spreads."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = [rng.normal(0, std, 100) for std in (1, 2, 3, 4)]
colors = ["oc.blue5", "oc.green5", "oc.orange5", "oc.red5"]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
bp = ax.boxplot(data, patch_artist=True)
for patch, color in zip(bp["boxes"], colors, strict=False):
    patch.set_facecolor(color)
ax.set_xticklabels(["std=1", "std=2", "std=3", "std=4"])
ax.set_ylabel("Value")
dm.auto_layout(fig)
dm.save_formats(fig, "boxplot")
