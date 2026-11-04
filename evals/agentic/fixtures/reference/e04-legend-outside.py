"""Leaf length vs width by species (scientific)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("scientific")

df = pd.read_csv("data/plants.csv").dropna()

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
for species, g in df.groupby("species"):
    ax.scatter(g["leaf_length_cm"], g["leaf_width_cm"], s=12, label=species)
ax.set_xlabel("Leaf length (cm)")
ax.set_ylabel("Leaf width (cm)")
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), title="Species")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
