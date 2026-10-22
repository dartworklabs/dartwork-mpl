"""GDP growth by country, 2012-2023 (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/gdp_growth.csv")
countries = ["Korea", "Japan", "United States", "Germany", "France"]

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ends = []
for name in countries:
    (line,) = ax.plot(
        df["year"], df[name], marker="o", markersize=3, label=name
    )
    ends.append([float(df[name].iloc[-1]), name, line.get_color()])
ax.axhline(0, color="0.5", linewidth=0.5, linestyle="--")
ax.set_xlabel("Year")
ax.set_ylabel("Real GDP growth (%)")
ax.set_title("Real GDP growth, 2012-2023")

# Spread the end labels so neighbours never touch (minimum gap in data units).
ends.sort()
gap = 0.9
for k in range(1, len(ends)):
    ends[k][0] = max(ends[k][0], ends[k - 1][0] + gap)
for y, name, color in ends:
    ax.text(df["year"].iloc[-1] + 0.3, y, name, color=color, va="center")
ax.set_xlim(right=df["year"].iloc[-1] + 2.6)

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
