"""Reference solution for agent-eval case c05-legend-top-en."""

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
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncols=5)
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
