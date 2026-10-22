from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/korea_monthly_sales.csv", thousands=",")
x = range(1, 13)
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ax.bar(x, df["매출액(억원)"], color="dc.blue3", label="매출액")
ax2 = ax.twinx()
ax2.plot(
    x,
    df["영업이익(억원)"],
    color="dc.red5",
    marker="o",
    markersize=3,
    label="영업이익",
)
ax.set_xticks(list(x), [f"{m}월" for m in x])
ax.set_ylabel("매출액 (억원)")
ax2.set_ylabel("영업이익 (억원)")
ax.set_title("2024년 월별 매출액과 영업이익")
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", bbox_to_anchor=(1.12, 1))
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
