"""Energy generation by source per period as stacked bars with segment and total labels."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["P1", "P2", "P3", "P4"]
components = {
    "Solar": [82, 90, 101, 118],
    "Wind": [40, 45, 47, 55],
    "Gas": [28, 26, 22, 19],
}
component_names = list(components.keys())

colors = ["dc.teal5", "dc.teal3", "dc.teal2"]

fig, ax = plt.subplots(
    figsize=dm.figsize_for(
        n_points=len(categories), n_series=len(component_names)
    )
)

x = np.arange(len(categories))
bottom = np.zeros(len(categories))

for name, color in zip(component_names, colors, strict=False):
    vals = np.array(components[name])
    ax.bar(
        x,
        vals,
        bottom=bottom,
        width=0.55,
        label=name,
        color=color,
        edgecolor="white",
        linewidth=0.3,
    )
    bottom += vals

# Segment labels at each segment's middle and the stack total above each
# stack; the axis grows just enough to keep the totals inside.
dm.label_bars(ax)

ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Generation (MWh)")
ax.set_xlabel("Period")

dm.place_legend(ax, fontsize=dm.fs(-1), frameon=False)

dm.simple_layout(fig)

dm.save_formats(fig, "output/stacked_bar_advanced", formats=("png",))
