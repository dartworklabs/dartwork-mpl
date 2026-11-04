"""Electricity generation by source, 2000-2023 (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/energy_mix.csv")
names = {
    "coal": "Coal",
    "gas": "Gas",
    "nuclear": "Nuclear",
    "hydro": "Hydro",
    "wind_solar": "Wind + solar",
}

fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ends = []
for col, label in names.items():
    (line,) = ax.plot(df["year"], df[col], label=label)
    ends.append([float(df[col].iloc[-1]), label, line.get_color()])
ax.set_xlabel("Year")
ax.set_ylabel("Generation (TWh)")
ax.set_title("Electricity generation by source")

ends.sort()
gap = 22.0
for k in range(1, len(ends)):
    ends[k][0] = max(ends[k][0], ends[k - 1][0] + gap)
for y, label, color in ends:
    ax.text(df["year"].iloc[-1] + 0.5, y, label, color=color, va="center")
ax.set_xlim(right=df["year"].iloc[-1] + 5)

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
