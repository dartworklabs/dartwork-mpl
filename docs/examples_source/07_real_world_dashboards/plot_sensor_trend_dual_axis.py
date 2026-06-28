"""
Dual-axis sensor trend (bar + line)
===================================

Bar series for an absolute measurement on the primary y-axis paired with a
line series for a derived rate-of-change on the secondary y-axis. A common
layout whenever the magnitude and the change-per-period answer different
questions about the same signal.

The sample data is synthetic hourly mean temperature for a single site.

In 0.4, ``ax.twinx()`` is monkey-patched to make the right spine
visible automatically with the active style's linewidth — no need for
``ax2.spines["right"].set_visible(True)``.
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

# 0.4 API: plt.subplots(figsize=dm.figsize(...)). Wide aspect (2:3) gives
# both y-axes room without crowding tick labels.
fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))

x = np.arange(len(periods))
ax.bar(x, temperature, color="dc.corporate2", alpha=0.85, width=0.55)
ax.set_xticks(x)
ax.set_xticklabels(periods)
ax.set_xlabel("Time", fontsize=dm.fs(0))
ax.set_ylabel("Temperature (°C)", fontsize=dm.fs(0))
ax.grid(axis="y", alpha=0.2)

# twinx: 0.4 auto-shows the right spine via the dartwork-mpl monkey-patch.
ax2 = ax.twinx()
ax2.plot(
    x, change_pct, "o-", color="dc.earth3", linewidth=dm.lw(1), markersize=5
)
ax2.set_ylabel("Change (%)", fontsize=dm.fs(0), color="dc.earth3")
ax2.tick_params(axis="y", labelcolor="dc.earth3")

ax.set_title(
    "Hourly temperature and rate of change", fontsize=dm.fs(1), weight="bold"
)

dm.simple_layout(fig)
plt.show()
