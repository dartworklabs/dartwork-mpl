"""Rainfall bars with a source note added by fig.text after the layout, in the bottom-right corner."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
rain = [21, 28, 47, 64, 105, 133]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.bar(months, rain)
ax.set(xlabel="Month", ylabel="Rainfall (mm)")
dm.simple_layout(fig)
fig.text(
    0.995,
    0.005,
    "Source: Korea Meteorological Administration",
    ha="right",
    va="bottom",
)

dm.save_formats(fig, "output/note_after_layout", formats=("png",))
