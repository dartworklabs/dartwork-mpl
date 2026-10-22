from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/quarterly_sales.csv", thousands=",")
wide = df.pivot(index="quarter", columns="region", values="revenue")
x = np.arange(len(wide))
w = 0.8 / len(wide.columns)
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
for k, region in enumerate(wide.columns):
    ax.bar(x + (k - 1.5) * w, wide[region], width=w, label=region)
ax.set_xticks(x, wide.index)
ax.set_ylabel("매출")
ax.set_title("분기별 지역 매출")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
