"""Weekly sessions and signups, 2024."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/web_traffic.csv", parse_dates=["week_start"])

fig, (top, bot) = plt.subplots(
    2, 1, sharex=True, figsize=dm.figsize("13cm", "golden")
)
top.plot(df["week_start"], df["sessions"], color="dc.blue5")
top.set_ylabel("Sessions / week")
top.set_title("Weekly traffic, 2024")
bot.plot(df["week_start"], df["signups"], color="dc.orange5")
bot.set_ylabel("Signups / week")
bot.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
bot.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
