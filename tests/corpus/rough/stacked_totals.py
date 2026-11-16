"""Generation by source as pandas stacked bars, totals typed above each stack and the legend pushed outside right."""

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.DataFrame(
    {
        "year": [2020, 2021, 2022, 2023, 2024],
        "Coal": [210, 198, 180, 165, 150],
        "Gas": [150, 158, 162, 160, 155],
        "Wind": [40, 48, 57, 66, 74],
        "Solar": [22, 30, 41, 55, 70],
    }
).set_index("year")

fig, ax = plt.subplots(figsize=(9, 6))
df.plot(kind="bar", stacked=True, ax=ax, width=0.7)
for i, total in enumerate(df.sum(axis=1)):
    ax.text(
        i, total + 3, f"{total:g}", ha="center", va="bottom", fontweight="bold"
    )
ax.set_ylim(0, df.sum(axis=1).max() * 1.1)
ax.set_xlabel("Year")
ax.set_ylabel("Generation (TWh)")
ax.set_title("Electricity generation by source")
ax.tick_params(axis="x", rotation=0)
ax.legend(title="Source", loc="upper left", bbox_to_anchor=(1, 1))

dm.simple_layout(fig)
dm.save_formats(fig, "output/stacked_totals", formats=("png",))
