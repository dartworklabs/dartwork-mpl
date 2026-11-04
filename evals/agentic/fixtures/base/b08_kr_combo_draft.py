"""2024년 매출액(막대)과 영업이익(선) 초안 (report-kr)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")

df = pd.read_csv("data/korea_monthly_sales.csv", thousands=",")
x = range(len(df))

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "golden"))
bars = ax.bar(x, df["매출액(억원)"], label="매출액")
ax.bar_label(bars, fmt="{:,.0f}", fontsize=dm.fs(1))
ax2 = ax.twinx()
ax2.plot(x, df["영업이익(억원)"], color="dc.red5", marker="o", label="영업이익")
ax.set_xticks(list(x))
ax.set_xticklabels(df["월"])
ax.set_ylabel("매출액 (억원)")
ax2.set_ylabel("영업이익 (억원)")
ax.set_title("2024년 월별 매출액과 영업이익")
ax.legend(loc="upper left")
ax2.legend(loc="upper left")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
