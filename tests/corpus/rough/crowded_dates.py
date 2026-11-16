"""Two years of daily web traffic with a full date on every weekly tick."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(3)
days = np.arange("2024-01-01", "2026-01-01", dtype="datetime64[D]")
visits = 1000 + np.cumsum(rng.normal(1, 20, days.size))

fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
ax.plot(days, visits, linewidth=0.8)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
ax.set_ylabel("Visits per day")

dm.simple_layout(fig)
dm.save_formats(fig, "output/crowded_dates", formats=("png",))
