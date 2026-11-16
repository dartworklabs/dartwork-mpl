"""Quarterly revenue by region as pandas grouped bars: a number on every bar, a boxed legend title, a title that repeats the axes."""

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.DataFrame(
    {
        "quarter": ["Q1", "Q2", "Q3", "Q4"],
        "North": [120, 135, 128, 150],
        "South": [95, 102, 110, 118],
        "East": [70, 88, 93, 101],
    }
).set_index("quarter")

fig, ax = plt.subplots(figsize=(9, 5.5))
df.plot(kind="bar", ax=ax, width=0.8, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
for c in ax.containers:
    ax.bar_label(c, fontsize=8, padding=2)
ax.set_title("Quarterly Revenue by Region")
ax.set_xlabel("Quarter")
ax.set_ylabel("Revenue")
ax.set_xticklabels(df.index, rotation=0)
ax.legend(title="Region", frameon=False)

dm.simple_layout(fig)
dm.save_formats(fig, "output/grouped_bar", formats=("png",))
