from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("presentation-kr")
df = pd.read_csv("data/market_share.csv")
fig, ax = plt.subplots(figsize=dm.figsize("24cm", "slide"))
bars = ax.bar(df["company"], df["share_pct"], color="dc.blue4")
ax.bar_label(bars, fmt="%.1f%%", padding=3)
ax.set_ylabel("시장점유율 (%)")
ax.set_title("2024년 회사별 시장점유율")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
