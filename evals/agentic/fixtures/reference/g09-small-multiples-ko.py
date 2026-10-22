from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/city_temps.csv", parse_dates=["month"])
names = {
    "Seoul": "서울",
    "Busan": "부산",
    "Daegu": "대구",
    "Gwangju": "광주",
    "Daejeon": "대전",
    "Incheon": "인천",
}
fig, axes = plt.subplots(
    2, 3, sharex=True, sharey=True, figsize=dm.figsize("17cm", "golden")
)
for ax, (city, label) in zip(axes.flat, names.items(), strict=True):
    g = df[df["city"] == city]
    ax.plot(g["month"], g["temp_c"])
    ax.set_title(label)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
for ax in axes[:, 0]:
    ax.set_ylabel("기온 (°C)")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
