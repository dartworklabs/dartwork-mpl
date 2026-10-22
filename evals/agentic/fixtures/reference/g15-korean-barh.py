from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/sido_population.csv", thousands=",").sort_values(
    "인구(천명)"
)
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.barh(df["시도"], df["인구(천명)"], color="dc.blue4")
ax.set_xlabel("인구 (천 명)")
ax.set_title("시도별 인구")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
