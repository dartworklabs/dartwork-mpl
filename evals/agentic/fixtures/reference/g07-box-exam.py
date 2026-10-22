from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/exam_scores.csv").dropna()
groups = [g["score"].to_numpy() for _, g in df.groupby("section")]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "golden"))
ax.boxplot(groups, tick_labels=sorted(df["section"].unique()))
ax.set_xlabel("Section")
ax.set_ylabel("Score")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
