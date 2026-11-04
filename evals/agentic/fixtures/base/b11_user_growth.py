"""Monthly active users of two apps (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/user_growth.csv", parse_dates=["month"])

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "golden"))
ax.plot(df["month"], df["app_alpha_users"], label="Alpha")
ax.plot(df["month"], df["app_beta_users"], label="Beta")
ax.set_xlabel("Month")
ax.set_ylabel("Monthly active users")
ax.set_title("User growth, 2023-2024")
ax.legend(loc="upper left")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
