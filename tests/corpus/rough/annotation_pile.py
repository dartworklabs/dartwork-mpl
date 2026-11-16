"""Quarterly profit with an annotation on every point, the callouts stacked over each other and the line."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

quarters = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
profit = [12.1, 12.8, 12.4, 13.0, 13.3, 12.9, 13.6, 14.1]
notes = [
    "Launch",
    "Price cut",
    "Recall",
    "New CEO",
    "Merger",
    "Strike",
    "Export deal",
    "Record",
]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.plot(quarters, profit, marker="o")
for q, p, note in zip(quarters, profit, notes, strict=True):
    ax.annotate(
        note, (q, p), xytext=(0, 6), textcoords="offset points", ha="center"
    )
ax.set_ylabel("Profit (USD m)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/annotation_pile", formats=("png",))
