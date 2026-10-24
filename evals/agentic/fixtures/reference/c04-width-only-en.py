from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/plants.csv").dropna()
fig, ax = plt.subplots(figsize=dm.figsize("20cm", "golden"))
for species, g in df.groupby("species"):
    ax.scatter(g["leaf_width_cm"], g["leaf_length_cm"], s=10, label=species)
ax.set_xlabel("Leaf width (cm)")
ax.set_ylabel("Leaf length (cm)")
ax.legend(loc="upper left", title="Species")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
