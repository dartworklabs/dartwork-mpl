"""Box plot across four spreads."""

import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = [rng.normal(0, std, 100) for std in (1, 2, 3, 4)]
colors = ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]

fig, ax = dm.subplots(width="13cm", aspect="standard")
bp = ax.boxplot(data, patch_artist=True)
for patch, color in zip(bp["boxes"], colors, strict=False):
    patch.set_facecolor(color)
ax.set_xticklabels(["std=1", "std=2", "std=3", "std=4"])
ax.set_ylabel("Value")
dm.auto_layout(fig)
dm.save_and_show(fig, "boxplot")
