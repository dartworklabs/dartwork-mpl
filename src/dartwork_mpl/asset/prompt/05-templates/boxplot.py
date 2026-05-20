"""Box plot across four spreads."""

# ai-template-meta-start
# use_case: Summarise the distribution of a few numeric groups
# difficulty: intermediate
# data_shape: groups: dict[str, list[float]]
# tags: distribution, boxplot, statistics, summary
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
data = [rng.normal(0, std, 100) for std in (1, 2, 3, 4)]
colors = ["oc.blue5", "oc.green5", "oc.orange5", "oc.red5"]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
bp = ax.boxplot(data, patch_artist=True, widths=0.55)
for patch, color in zip(bp["boxes"], colors, strict=False):
    patch.set_facecolor(color)
    patch.set_edgecolor("oc.gray7")
    patch.set_linewidth(0.3)
for line in bp["medians"]:
    line.set_color("oc.gray9")
    line.set_linewidth(dm.lw(0))
for line in bp["whiskers"] + bp["caps"]:
    line.set_color("oc.gray7")
    line.set_linewidth(0.3)
ax.set_xticklabels(["std=1", "std=2", "std=3", "std=4"])
ax.set_ylabel("Value")
ax.set_title("Box plot", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
dm.save_formats(fig, "boxplot")
