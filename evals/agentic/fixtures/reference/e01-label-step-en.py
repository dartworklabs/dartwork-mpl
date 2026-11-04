"""GDP growth by country, 2012-2023 (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/gdp_growth.csv")
countries = ["Korea", "Japan", "United States", "Germany", "France"]

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
for name in countries:
    ax.plot(df["year"], df[name], marker="o", markersize=3, label=name)
ax.axhline(0, color="0.5", linewidth=0.5, linestyle="--")
ax.set_xlabel("Year")
ax.set_ylabel("Real GDP growth (%)")
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)
ax.set_title("Real GDP growth, 2012-2023")
ax.legend(loc="lower left", ncols=2)

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
