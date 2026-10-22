"""2024년 월별 매출액 막대그래프 (report-kr)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")

df = pd.read_csv("data/korea_monthly_sales.csv", thousands=",")
months = [f"{int(m[-2:])}월" for m in df["월"]]

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ax.bar(months, df["매출액(억원)"], color="dc.teal3", label="매출액")
ax.set_xlabel("월")
ax.set_ylabel("매출액 (억원)")
ax.set_title("2024년 월별 매출액")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
