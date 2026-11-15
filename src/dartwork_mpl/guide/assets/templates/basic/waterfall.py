"""Waterfall (bridge) chart - start, deltas, end."""

# ai-template-meta-start
# use_case: Show successive additive contributions to a total
# difficulty: advanced
# data_shape: labels: list[str], deltas: list[float]
# tags: waterfall, bridge, finance, additive
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

labels = ["Start", "Gain A", "Loss B", "Gain C", "Loss D", "End"]
deltas = np.array([100, 30, -15, 25, -20, 0])
is_total = np.array([True, False, False, False, False, True])

# The level after each bar: the first total opens it, a step moves it by
# its signed delta, a later total shows it. A step is drawn from the level
# before it with its signed delta as the height, so the bar holds its
# delta and dm.label_bars prints -15 below a fall.
level = np.zeros(len(deltas))
running = 0.0
for i, (delta, total) in enumerate(zip(deltas, is_total, strict=True)):
    if not total or i == 0:
        running += delta
    level[i] = running
x = np.arange(len(labels))
step = ~is_total

# The names decide how wide the canvas is for them to stand flat.
fig, ax = plt.subplots(
    figsize=dm.figsize_for(n_points=len(labels), n_series=1, labels=labels)
)
totals = ax.bar(
    x[is_total],
    level[is_total],
    color="dc.indigo3",
    edgecolor="white",
    linewidth=0.3,
)
steps = ax.bar(
    x[step],
    deltas[step],
    bottom=(level - deltas)[step],
    color=["dc.green2" if d >= 0 else "dc.red2" for d in deltas[step]],
    edgecolor="white",
    linewidth=0.3,
)
# A fall starts at its top, which matplotlib would pin to the axes edge;
# clearing it keeps the usual margin above the highest level.
for bar in steps:
    bar.sticky_edges.y.clear()
ax.set_xticks(x, labels)
ax.axhline(0, color="dc.indigo3", linewidth=0.3)
ax.set_ylabel("Value")
# Values, when asked (before dm.simple_layout):
# dm.label_bars(ax, steps, sign="+")  # +30, -15 below its bar, ...
# dm.label_bars(ax, totals)  # 100, 120

dm.simple_layout(fig)
dm.save_formats(fig, "waterfall")
