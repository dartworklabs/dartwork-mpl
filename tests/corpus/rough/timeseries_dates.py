"""Daily temperature with a missing day marked by a rotated note, a tick every other day and autofmt_xdate's slanted dates."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

dates = np.arange("2026-03-01", "2026-03-22", dtype="datetime64[D]")
temps = np.array([
    4.1, 5.3, 6.0, 5.2, 7.8, 9.1, 8.4, 10.2, np.nan, 11.5, 12.0,
    10.9, 9.7, 11.8, 13.4, 14.1, 12.6, 13.9, 15.2, 16.0, 14.8,
])  # fmt: skip

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(dates, temps, marker="o", color="tab:red", label="Daily temperature")
for d in dates[np.isnan(temps)]:
    ax.axvline(d, color="gray", linestyle=":", alpha=0.7)
    ax.annotate(
        "No reading",
        (d, ax.get_ylim()[0]),
        xytext=(4, 8),
        textcoords="offset points",
        color="gray",
        rotation=90,
        va="bottom",
    )
ax.set_title("Daily Temperature, March 2026")
ax.set_xlabel("Date")
ax.set_ylabel("Temperature (°C)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
fig.autofmt_xdate()
ax.grid(alpha=0.3)

dm.simple_layout(fig)
dm.save_formats(fig, "output/timeseries_dates", formats=("png",))
