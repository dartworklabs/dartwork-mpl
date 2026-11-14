"""Existing four-panel report figure; edit only the requested target."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
zones = list(dict.fromkeys(r["zone"] for r in rows))
fig, axs = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
for ax, zone in zip(axs.flat, zones, strict=True):
    part = [r for r in rows if r["zone"] == zone]
    hours = [float(r["hour"]) for r in part]
    ax.plot(hours, [float(r["supply_temp_C"]) for r in part], label="Supply")
    ax.plot(hours, [float(r["return_temp_C"]) for r in part], label="Return")
    ax.set(xlabel="Hour of day", ylabel="Temperature (°C)", title=zone)
dm.label_axes(axs)
dm.figure_legend(fig)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
