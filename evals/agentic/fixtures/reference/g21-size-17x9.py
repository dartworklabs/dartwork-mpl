from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report")
df = pd.read_csv("data/quarterly_sales.csv", thousands=",")
wide = df.pivot(index="quarter", columns="region", values="revenue")
fig, ax = plt.subplots(figsize=dm.figsize("17cm", "9cm"))
bottom = np.zeros(len(wide))
for region in wide.columns:
    ax.bar(wide.index, wide[region], bottom=bottom, label=region)
    bottom += wide[region].to_numpy()
ax.set_ylabel("Revenue")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
