"""A colleague's figure for the report."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report-kr")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
zones = list(dict.fromkeys(r["구역"] for r in rows))
fig, axs = plt.subplots(
    2,
    2,
    figsize=dm.figsize("14cm", "9cm"),
    gridspec_kw={"hspace": 0.05, "wspace": 0.05},
)
for ax, zone in zip(axs.flat, zones, strict=True):
    part = [r for r in rows if r["구역"] == zone]
    ax.plot(
        [float(r["경과시간_s"]) for r in part],
        [float(r["응답_mV"]) for r in part],
    )
    ax.set(xlabel="경과 시간 (s)", ylabel="응답 (mV)", title=zone)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
