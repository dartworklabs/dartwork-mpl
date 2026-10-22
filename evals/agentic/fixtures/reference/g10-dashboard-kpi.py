from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/kpi_monthly.csv")
months = [m[-2:] for m in df["month"]]
panels = [
    ("revenue_musd", "Revenue (M USD)"),
    ("active_users", "Active users"),
    ("churn_pct", "Churn (%)"),
    ("nps", "NPS"),
]
fig, axes = plt.subplots(
    2, 2, sharex=True, figsize=dm.figsize("17cm", "golden")
)
for ax, (col, title) in zip(axes.flat, panels, strict=True):
    ax.plot(months, df[col], marker="o", markersize=3)
    ax.set_title(title)
for ax in axes[1]:
    ax.set_xlabel("Month (2024)")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
