from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("presentation")
df = pd.read_csv("data/energy_mix.csv")
total = df[["coal", "gas", "nuclear", "hydro", "wind_solar"]].sum(axis=1)
share = (df["hydro"] + df["wind_solar"]) / total * 100
fig, ax = plt.subplots(figsize=dm.figsize("25.4cm", "slide"))
ax.plot(df["year"], share, marker="o")
ax.set_xlabel("Year")
ax.set_ylabel("Renewables share (%)")
ax.set_title("Hydro, wind and solar share of generation")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
