"""Daily output and defect rate, two stacked panels (report)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")

df = pd.read_csv("data/plant_output.csv", parse_dates=["date"])

fig, (ax_top, ax_bot) = plt.subplots(
    2,
    1,
    sharex=True,
    figsize=dm.figsize("15cm", "standard"),
    gridspec_kw={"height_ratios": [1, 1]},
)
ax_top.plot(df["date"], df["output_units"], color="dc.blue5")
ax_top.set_ylabel("Output (units/day)")
ax_top.set_title("Plant output and quality, Apr-Jun 2024")
ax_bot.plot(df["date"], df["defect_rate_pct"], color="dc.red5")
ax_bot.set_ylabel("Defect rate (%)")
ax_bot.set_xlabel("Date")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
