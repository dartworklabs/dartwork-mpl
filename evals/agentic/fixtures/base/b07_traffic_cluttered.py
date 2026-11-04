"""Weekly sessions and signups, 2024 (a quick, unpolished draft)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/web_traffic.csv")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "golden"))
ax.plot(df["week_start"], df["sessions"], label="sessions")
ax.plot(df["week_start"], df["signups"] * 30, label="signups x 30")
ax.set_xticks(range(len(df)))
ax.set_xticklabels(df["week_start"])
ax.set_ylabel("count")
ax.set_title("traffic")
ax.legend(loc="center")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
