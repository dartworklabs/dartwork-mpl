from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/response_times.csv")
bins = np.linspace(df["response_ms"].min(), df["response_ms"].max(), 31)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "golden"))
for variant, g in df.groupby("variant"):
    ax.hist(g["response_ms"], bins=bins, alpha=0.6, label=f"Variant {variant}")
ax.set_xlabel("Response time (ms)")
ax.set_ylabel("Requests")
ax.legend(loc="upper right")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
