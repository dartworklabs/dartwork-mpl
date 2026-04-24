"""
Dual-axis sensor trend (bar + line)
===================================

Bar series for an absolute measurement on the primary y-axis paired with a
line series for a derived rate-of-change on the secondary y-axis. A common
layout whenever the magnitude and the change-per-period answer different
questions about the same signal.

The sample data is synthetic hourly mean temperature for a single site.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

periods = [f"T+{i}h" for i in range(6)]
temperature = np.array([18.5, 19.8, 21.2, 22.7, 23.1, 22.4])
change_pct = np.concatenate(
    [[0.0], np.diff(temperature) / temperature[:-1] * 100]
)

fig = plt.figure(figsize=(dm.TW, dm.TW * 0.55))
gs = fig.add_gridspec(1, 1, left=0.12, right=0.88, top=0.88, bottom=0.18)
ax = fig.add_subplot(gs[0, 0])

x = np.arange(len(periods))
ax.bar(x, temperature, color="oc.blue5", alpha=0.85, width=0.55)
ax.set_xticks(x)
ax.set_xticklabels(periods)
ax.set_xlabel("Time", fontsize=dm.fs(0))
ax.set_ylabel("Temperature (°C)", fontsize=dm.fs(0))
ax.grid(axis="y", alpha=0.2)

ax2 = ax.twinx()
ax2.plot(
    x, change_pct, "o-", color="oc.orange6", linewidth=dm.lw(1), markersize=5
)
ax2.set_ylabel("Change (%)", fontsize=dm.fs(0), color="oc.orange7")
ax2.tick_params(axis="y", labelcolor="oc.orange7")

ax.set_title(
    "Hourly temperature and rate of change", fontsize=dm.fs(1), weight="bold"
)

dm.auto_layout(fig)
plt.show()
