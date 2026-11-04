"""Population vs GDP per capita, labelled (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/country_stats.csv")

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.scatter(
    df["gdp_per_capita_kusd"], df["population_m"], s=18, color="dc.blue5"
)
for _, row in df.iterrows():
    ax.annotate(
        row["country"],
        (row["gdp_per_capita_kusd"], row["population_m"]),
        xytext=(3, 3),
        textcoords="offset points",
        fontsize=dm.fs(-1),
    )
ax.set_yscale("log")
ax.set_xlabel("GDP per capita (thousand USD)")
ax.set_ylabel("Population (millions)")
ax.set_title("Population and income")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
