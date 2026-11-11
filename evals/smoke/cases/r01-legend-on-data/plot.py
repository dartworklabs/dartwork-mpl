"""A colleague's figure for the report."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
names = list(dict.fromkeys(r["control"] for r in rows))
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "7cm"))
for name in names:
    part = [r for r in rows if r["control"] == name]
    ax.plot(
        [float(r["week"]) for r in part],
        [float(r["load_MWh"]) for r in part],
        label=name,
    )
ax.set(xlabel="Week", ylabel="Load (MWh)")
ax.legend(loc="center")
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
