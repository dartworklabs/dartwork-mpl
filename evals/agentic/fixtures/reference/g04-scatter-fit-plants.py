from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dartwork_mpl as dm

dm.style.use("scientific")
df = pd.read_csv("data/plants.csv").dropna()
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
for species, g in df.groupby("species"):
    pts = ax.scatter(
        g["leaf_length_cm"], g["leaf_width_cm"], s=10, label=species
    )
    k, b = np.polyfit(g["leaf_length_cm"], g["leaf_width_cm"], 1)
    xs = np.array([g["leaf_length_cm"].min(), g["leaf_length_cm"].max()])
    ax.plot(xs, k * xs + b, color=pts.get_facecolor()[0])
ax.set_xlabel("Leaf length (cm)")
ax.set_ylabel("Leaf width (cm)")
ax.legend(loc="upper left", title="Species")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
