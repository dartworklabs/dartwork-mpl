# known-defect: text_outside=2 (dm simple_layout ignores loc="left" titles; #523 phase 2)
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("scientific")
df = pd.read_csv("data/gdp_growth.csv")
names = list(df.columns[1:])
fig, (a, b) = plt.subplots(
    1, 2, figsize=dm.figsize(dm.col2, "cinema"), width_ratios=[3, 2]
)
for name in names:
    a.plot(df["year"], df[name], label=name)
a.set_xlabel("Year")
a.set_ylabel("Real GDP growth (%)")
a.legend(loc="lower left", fontsize=dm.fs(-1))
means = df[names].mean()
b.barh(names, means, color="dc.blue4")
b.set_xlabel("Average growth (%)")
for ax, tag in ((a, "a"), (b, "b")):
    ax.set_title(tag, loc="left", fontweight="bold")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
