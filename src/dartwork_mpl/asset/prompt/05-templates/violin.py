"""Violin plot for three groups."""

# ai-template-meta-start
# use_case: Show the density of multiple numeric groups
# difficulty: intermediate
# data_shape: groups: dict[str, list[float]]
# tags: distribution, density, violin
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
data = [rng.normal(loc, 1, 100) for loc in (0, 2, 4)]
colors = ["oc.blue5", "oc.green5", "oc.orange5"]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
parts = ax.violinplot(data, showmeans=True, showmedians=True)
for body, color in zip(parts["bodies"], colors, strict=False):
    body.set_facecolor(color)
    body.set_edgecolor("oc.gray7")
    body.set_alpha(0.55)
    body.set_linewidth(0.3)
for key in ("cmeans", "cmedians", "cbars", "cmins", "cmaxes"):
    if key in parts:
        parts[key].set_color("oc.gray9")
        parts[key].set_linewidth(0.3)
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(["Group A", "Group B", "Group C"])
ax.set_ylabel("Value")
ax.set_title("Distribution by group", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
dm.save_formats(fig, "violin")
