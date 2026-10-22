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
for col, label in names.items():
    ax.plot(df["year"], df[col], label=label)
ax.set_xlabel("Year")
ax.set_ylabel("Generation (TWh)")
ax.set_title("Electricity generation by source")
ax.legend(loc="upper right")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
