from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/stock_prices.csv", parse_dates=["date"])
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "golden"))
ax.plot(df["date"], df["close"])
ax.axvspan(
    pd.Timestamp("2024-03-11"),
    pd.Timestamp("2024-03-22"),
    color="0.85",
    label="Product recall",
)
ax.set_ylabel("Closing price")
ax.legend(loc="upper left")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
