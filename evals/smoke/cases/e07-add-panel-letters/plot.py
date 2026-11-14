"""Existing four-panel report figure; edit only the requested target."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
seasons = list(dict.fromkeys(r["season"] for r in rows))
fig, axs = plt.subplots(
    2, 2, figsize=dm.figsize_for(nrows=2, ncols=2), sharex=True, sharey=True
)
for ax, season in zip(axs.flat, seasons, strict=True):
    part = [r for r in rows if r["season"] == season]
    hours = [float(r["hour"]) for r in part]
    ax.plot(hours, [float(r["office_kW"]) for r in part], label="Office")
    ax.plot(
        hours, [float(r["laboratory_kW"]) for r in part], label="Laboratory"
    )
    ax.set_title(season)
for ax in axs[:, 0]:
    ax.set_ylabel("Electric load (kW)")
for ax in axs[-1]:
    ax.set_xlabel("Hour of day")
dm.figure_legend(fig)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
