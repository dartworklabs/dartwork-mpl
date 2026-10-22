from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = (
    pd.read_csv("data/survey_scores.csv")
    .dropna(subset=["score"])
    .sort_values("score")
)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "golden"))
bars = ax.barh(df["feature"], df["score"], color="dc.blue4")
ax.bar_label(bars, fmt="%.1f", padding=2)
ax.set_xlim(0, 100)
ax.set_xlabel("Satisfaction score")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
