from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/quarterly_sales.csv", thousands=",")
wide = df.pivot(index="quarter", columns="region", values="revenue")
regions = {"North": "북부", "South": "남부", "East": "동부", "West": "서부"}
x = np.arange(len(wide))
w = 0.8 / len(regions)
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
for k, (region, name) in enumerate(regions.items()):
    ax.bar(x + (k - 1.5) * w, wide[region], width=w, label=name)
ax.set_xticks(x, [f"{q[1]}분기" for q in wide.index])
ax.set_ylabel("매출")
ax.set_title("지역별 분기 매출")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
