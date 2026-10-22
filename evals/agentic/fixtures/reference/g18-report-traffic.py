# known-defect: text_outside=1 (dm simple_layout ignores loc="left" titles; #523 phase 2)
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/web_traffic.csv", parse_dates=["week_start"])
fig, (top, bot) = plt.subplots(
    2, 1, sharex=True, figsize=dm.figsize("15cm", "golden")
)
top.plot(df["week_start"], df["sessions"])
top.set_ylabel("Sessions / week")
bot.plot(df["week_start"], df["signups"], color="dc.orange5")
bot.set_ylabel("Signups / week")
top.set_title("Weekly sessions and signups, 2024", loc="left")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
