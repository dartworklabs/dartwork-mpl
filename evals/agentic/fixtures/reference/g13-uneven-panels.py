from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/plant_output.csv", parse_dates=["date"])
fig, (top, bot) = plt.subplots(
    2,
    1,
    sharex=True,
    figsize=dm.figsize("15cm", "standard"),
    gridspec_kw={"height_ratios": [7, 3]},
)
top.plot(df["date"], df["output_units"])
top.set_ylabel("Output (units/day)")
bot.plot(df["date"], df["defect_rate_pct"], color="dc.red5")
bot.set_ylabel("Defects (%)")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
