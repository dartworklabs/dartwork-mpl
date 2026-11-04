"""Reference solution for agent-eval case c07-dark-en."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("dark")
df = pd.read_csv("data/visitors_daily.csv")
df["date"] = pd.to_datetime(df["날짜"], format="%Y.%m.%d")
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ax.plot(df["date"], df["방문자수"])
ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 15]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %-d"))
ax.set_ylabel("Daily visitors")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
