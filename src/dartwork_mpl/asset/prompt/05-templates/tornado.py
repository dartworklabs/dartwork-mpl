"""Tornado chart - symmetric horizontal bars."""

# ai-template-meta-start
# use_case: Show signed deviations from a baseline (sensitivity)
# difficulty: intermediate
# data_shape: labels: list[str], lows: list[float], highs: list[float]
# tags: tornado, sensitivity, deviation, horizontal
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["Cat A", "Cat B", "Cat C", "Cat D"]
positive = [10, 25, 15, 30]
negative = [-8, -20, -12, -28]

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
y_pos = np.arange(len(categories))
ax.barh(
    y_pos,
    positive,
    color="oc.blue5",
    label="Positive",
    edgecolor="white",
    linewidth=0.3,
)
ax.barh(
    y_pos,
    negative,
    color="oc.red5",
    label="Negative",
    edgecolor="white",
    linewidth=0.3,
)
ax.set_yticks(y_pos)
ax.set_yticklabels(categories)
ax.axvline(0, color="oc.gray7", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_title("Tornado", fontsize=dm.fs(1), fontweight=dm.fw(1))
ax.legend(fontsize=dm.fs(-1))
dm.simple_layout(fig)
dm.save_formats(fig, "tornado")
