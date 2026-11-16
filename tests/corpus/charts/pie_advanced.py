"""GPU market share as a donut, the leader exploded and named in the hole."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

labels = ["NVIDIA", "AMD", "Intel Arc", "Apple", "Others"]
sizes = np.array([62.0, 17.0, 8.0, 7.0, 6.0])  # %, leader first

# OKLCH gradient — deeper for the leader, lighter for trailing share.
colors = ["dc.teal5", "dc.teal4", "dc.teal3", "dc.teal2", "dc.teal1"]

# Explode only the leader.
explode = np.zeros(len(labels))
explode[0] = 0.08

# The leader is named by the callout in the hole; every other wedge by its
# name and share outside the ring (a small wedge cannot hold its number).
# Turn the pie so those others centre on 3 o'clock, where their labels
# stack instead of crowding the top.
startangle = -360 * (sizes.sum() - sizes[1:].sum() / 2) / sizes.sum()
names = [
    "",
    *(f"{n} {s:.0f}%" for n, s in zip(labels[1:], sizes[1:], strict=True)),
]

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))

wedges, texts = ax.pie(
    sizes,
    labels=names,
    colors=colors,
    startangle=startangle,
    explode=explode,
    wedgeprops={"edgecolor": "white", "linewidth": 0.5, "width": 0.38},
    textprops={"fontsize": dm.fs(-1), "fontweight": dm.fw(1)},  # value labels
)
ax.set_aspect("equal")

# Leader callout in the donut's hole, which the leader's ring wraps: in its
# colour (darkened to 4.5:1), it needs no line to say whose share it is.
ax.annotate(
    f"{labels[0]}\nholds {sizes[0]:.0f}%\n3.6x #2",
    xy=(0, 0),
    ha="center",
    va="center",
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast(colors[0], ax.get_facecolor()),
)

dm.simple_layout(fig)

dm.save_formats(fig, "output/pie_advanced", formats=("png",))
