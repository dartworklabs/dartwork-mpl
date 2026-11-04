"""서울·부산 월평균 기온, 발표용 (presentation-kr)."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("presentation-kr")

df = pd.read_csv("data/city_temps.csv", parse_dates=["month"])
names = {"Seoul": "서울", "Busan": "부산"}

fig, ax = plt.subplots(figsize=dm.figsize("25.4cm", "slide"))
for city, label in names.items():
    g = df[df["city"] == city]
    ax.plot(g["month"], g["temp_c"], label=label)
ax.set_xlabel("월")
ax.set_ylabel("월평균 기온 (°C)")
ax.set_title("서울과 부산의 월평균 기온, 2021-2023")
ax.legend(loc="upper left")

dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
