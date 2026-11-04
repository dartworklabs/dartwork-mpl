"""Average GDP growth by country, 2012-2023 (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/gdp_growth.csv")
means = df.drop(columns="year").mean().sort_values()

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "golden"))
ax.barh(means.index, means.values, color="dc.blue4")
ax.set_xlabel("Average real GDP growth, 2012-2023 (%)")
ax.set_title("Average growth by country")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
