"""
Component mix over time (stacked area)
======================================

Stacked area chart showing how a total is composed of several parts across
a time axis. Useful for looking at both total magnitude and internal
composition in a single view.

The sample data is synthetic energy consumption for a small site, split
into four end uses whose proportions drift over the observation window.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

periods = [f"T+{i}h" for i in range(6)]
total = np.array([1.60, 1.72, 1.81, 1.90, 1.88, 1.95])

# Component shares sum to 1 per period.
shares = np.array(
    [
        [0.42, 0.28, 0.18, 0.12],
        [0.40, 0.30, 0.18, 0.12],
        [0.38, 0.31, 0.19, 0.12],
        [0.37, 0.31, 0.20, 0.12],
        [0.36, 0.32, 0.20, 0.12],
        [0.34, 0.33, 0.21, 0.12],
    ]
)
components = shares * total[:, None]
labels = ["HVAC", "Lighting", "Compute", "Other"]
palette = ["oc.blue4", "oc.teal5", "oc.cyan6", "oc.gray5"]

fig = plt.figure(figsize=dm.figsize("14.5cm", 0.55))
gs = fig.add_gridspec(1, 1, left=0.12, right=0.96, top=0.88, bottom=0.18)
ax = fig.add_subplot(gs[0, 0])

x = np.arange(len(periods))
bottom = np.zeros_like(total)
for i, label in enumerate(labels):
    ax.fill_between(
        x,
        bottom,
        bottom + components[:, i],
        alpha=0.7,
        color=palette[i],
        label=label,
    )
    bottom = bottom + components[:, i]

ax.set_xticks(x)
ax.set_xticklabels(periods)
ax.set_xlabel("Time", fontsize=dm.fs(0))
ax.set_ylabel("Energy use (kWh)", fontsize=dm.fs(0))
ax.set_title("Energy mix over time", fontsize=dm.fs(1), weight="bold")
ax.grid(axis="y", alpha=0.2)
ax.legend(loc="upper left", fontsize=dm.fs(-1), ncol=2)

dm.simple_layout(fig)
plt.show()
