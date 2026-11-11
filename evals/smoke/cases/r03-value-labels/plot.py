"""A colleague's figure for the report."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
x = [float(r["time_h"]) for r in rows]
measured = [float(r["measured_C"]) for r in rows]
model = [float(r["model_C"]) for r in rows]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "7cm"))
ax.plot(x, measured, marker="o", label="Measured")
ax.plot(x, model, marker="s", label="Model")
for i in range(0, len(x), 2):
    ax.text(
        x[i],
        measured[i],
        f"{measured[i]:.2f}",
        fontsize=4,
        ha="center",
        va="center",
    )
ax.set(xlabel="Time (h)", ylabel="Temperature (°C)")
dm.place_legend(ax)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
