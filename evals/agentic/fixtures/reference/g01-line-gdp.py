from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/gdp_growth.csv")
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
for name in df.columns[1:]:
    ax.plot(df["year"], df[name], marker="o", markersize=3, label=name)
ax.set_xlabel("Year")
ax.set_ylabel("Real GDP growth (%)")
ax.legend(loc="lower left", ncols=2)
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
