from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/energy_mix.csv")
cols = ["coal", "gas", "nuclear", "hydro", "wind_solar"]
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "golden"))
ax.stackplot(
    df["year"],
    *(df[c] for c in cols),
    labels=["Coal", "Gas", "Nuclear", "Hydro", "Wind + solar"],
)
ax.set_xlabel("Year")
ax.set_ylabel("Generation (TWh)")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
