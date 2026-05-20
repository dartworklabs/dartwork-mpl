"""Pie chart with four slices."""

# ai-template-meta-start
# use_case: Show shares of a small whole
# difficulty: beginner
# data_shape: labels: list[str], sizes: list[float]
# tags: pie, share, composition, proportion
# ai-template-meta-end

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")

labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["oc.blue5", "oc.green5", "oc.orange5", "oc.red5"]

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
ax.pie(
    sizes,
    labels=labels,
    colors=colors,
    autopct="%1.1f%%",
    startangle=90,
    wedgeprops={"edgecolor": "white", "linewidth": 0.3},
    textprops={"fontsize": dm.fs(-1)},
)
ax.set_aspect("equal")
ax.set_title("Composition", fontsize=dm.fs(1), fontweight=dm.fw(1))
dm.simple_layout(fig)
dm.save_formats(fig, "pie")
