"""
Waterfall
=========

Waterfall (bridge) chart - start, deltas, end.

Source: ``dartwork_mpl/asset/prompt/05-templates/waterfall.py`` ·
``dm.get_prompt("05-templates/waterfall")`` · MCP
``dartwork-mpl://templates/waterfall``.
"""

import numpy as np

import dartwork_mpl as dm

labels = ["Start", "Gain A", "Loss B", "Gain C", "Loss D", "End"]
deltas = [100, 30, -15, 25, -20, 0]
is_total = [True, False, False, False, False, True]

# Compute baselines and bar heights for each step.
baselines = np.zeros(len(deltas))
heights = np.zeros(len(deltas))
running = 0.0
for i, (delta, total) in enumerate(zip(deltas, is_total, strict=False)):
    if total:
        if i == 0:
            running = delta
        baselines[i] = 0
        heights[i] = running
    else:
        baselines[i] = running + min(delta, 0)
        heights[i] = abs(delta)
        running += delta

colors = [
    "oc.gray6" if total else ("oc.teal5" if d >= 0 else "oc.red5")
    for d, total in zip(deltas, is_total, strict=False)
]

fig, ax = dm.subplots(width="15cm", aspect="standard")
ax.bar(
    labels,
    heights,
    bottom=baselines,
    color=colors,
    edgecolor="white",
    linewidth=0.3,
)
ax.axhline(0, color="oc.gray7", linewidth=0.5)
ax.set_ylabel("Value")
dm.auto_layout(fig)
