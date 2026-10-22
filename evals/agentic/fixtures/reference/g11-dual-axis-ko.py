from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/climate_monthly.csv")
x = range(1, 13)
fig, ax = plt.subplots(figsize=dm.figsize("14cm", "golden"))
ax.bar(x, df["precip_mm"], color="dc.blue3", label="강수량")
ax2 = ax.twinx()
ax2.plot(
    x, df["temp_c"], color="dc.red5", marker="o", markersize=3, label="기온"
)
ax.set_xticks(list(x), [f"{m}월" for m in x])
ax.set_ylabel("강수량 (mm)")
ax2.set_ylabel("기온 (°C)")
handles = ax.get_legend_handles_labels()
handles2 = ax2.get_legend_handles_labels()
ax.legend(handles[0] + handles2[0], handles[1] + handles2[1], loc="upper left")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
