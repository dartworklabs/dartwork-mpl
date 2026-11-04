"""Electricity generation: trend (left) and 2023 mix (right)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/energy_mix.csv")
sources = ["coal", "gas", "nuclear", "hydro", "wind_solar"]

fig = plt.figure(figsize=dm.figsize("17cm", "cinema"))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 2])
ax_trend = fig.add_subplot(gs[0, 0])
ax_mix = fig.add_subplot(gs[0, 1])

for s in sources:
    ax_trend.plot(df["year"], df[s], label=s.replace("_", " + "))
ax_trend.set_xlabel("Year")
ax_trend.set_ylabel("Generation (TWh)")
ax_trend.set_title("Generation by source")
ax_trend.legend(loc="upper right", fontsize=dm.fs(-1))

last = df.iloc[-1]
ax_mix.barh(
    [s.replace("_", " + ") for s in sources],
    [last[s] for s in sources],
    color="dc.teal3",
)
ax_mix.set_xlabel("Generation in 2023 (TWh)")
ax_mix.set_title("2023 mix")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
