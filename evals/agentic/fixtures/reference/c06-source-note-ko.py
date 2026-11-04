"""Reference solution for agent-eval case c06-source-note-ko."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/web_traffic.csv", parse_dates=["week_start"])
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ax.plot(df["week_start"], df["sessions"])
ax.set_ylabel("주간 세션 수")
fig.text(
    0.01, 0.01, "출처: 사내 웹 로그", ha="left", va="bottom", fontsize=dm.fs(-1)
)
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
