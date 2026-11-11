"""Existing two-panel report figure; edit only the requested target."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
x = [float(r["time_s"]) for r in rows]
y = [float(r["measured_mV"]) for r in rows]
z = [float(r["model_mV"]) for r in rows]
fig, (left, right) = plt.subplots(
    1, 2, figsize=dm.figsize("14cm", "7cm"), gridspec_kw={"wspace": 0.5}
)
left.plot(x, y, label="Measured")
left.plot(x, z, label="Model")
left.set(xlabel="Time (s)", ylabel="Response (mV)", title="Response")
dm.place_legend(left)
right.plot(x, [a - b for a, b in zip(y, z, strict=True)])
right.set(xlabel="Time (s)", ylabel="Residual (mV)", title="Residual")
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
