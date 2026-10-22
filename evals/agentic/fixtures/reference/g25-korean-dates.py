from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

import dartwork_mpl as dm

dm.style.use("report-kr")
df = pd.read_csv("data/visitors_daily.csv")
df["날짜"] = pd.to_datetime(df["날짜"], format="%Y.%m.%d")
fig, ax = plt.subplots(figsize=dm.figsize("15cm", "golden"))
ax.plot(df["날짜"], df["방문자수"])
ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 15]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%-m월 %-d일"))
ax.set_ylabel("방문자 수")
ax.set_title("일별 방문자 수")
dm.simple_layout(fig)
Path("out").mkdir(exist_ok=True)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
