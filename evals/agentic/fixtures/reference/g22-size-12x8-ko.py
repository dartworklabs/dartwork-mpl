from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/gdp_growth.csv")
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "8cm"))
ax.plot(df["year"], df["Korea"], marker="o", markersize=3, label="한국")
ax.plot(df["year"], df["Japan"], marker="o", markersize=3, label="일본")
ax.set_xlabel("연도")
ax.set_ylabel("실질 GDP 성장률 (%)")
ax.legend(loc="lower left")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
