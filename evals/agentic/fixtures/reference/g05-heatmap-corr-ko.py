from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
corr = pd.read_csv("data/sensors.csv").corr()
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "square"))
im = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
n = len(corr)
ax.set_xticks(range(n), corr.columns, rotation=45, ha="right")
ax.set_yticks(range(n), corr.columns)
for i in range(n):
    for j in range(n):
        v = corr.iloc[i, j]
        ax.text(
            j,
            i,
            f"{v:.2f}",
            ha="center",
            va="center",
            fontsize=dm.fs(-1),
            color="white" if abs(v) > 0.6 else "black",
        )
fig.colorbar(im, ax=ax, label="상관계수")
ax.set_title("센서 변수 간 상관계수")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
