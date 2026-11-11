"""A colleague's figure for the report."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report-kr")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
fig, ax = plt.subplots(figsize=dm.figsize("10cm", "6cm"))
ax.bar([r["건물"] for r in rows], [float(r["연간전력_MWh"]) for r in rows])
ax.set(xlabel="건물", ylabel="연간 전력 사용량 (MWh)")
dm.simple_layout(fig)
plt.setp(ax.get_xticklabels(), rotation=15)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
