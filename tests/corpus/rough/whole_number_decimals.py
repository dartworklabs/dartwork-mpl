"""Survey answer counts as bars labelled with one decimal, so every whole count reads 12.0."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

answers = ["Never", "Rarely", "Sometimes", "Often", "Always"]
counts = [12, 31, 48, 26, 9]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bars = ax.bar(answers, counts)
ax.bar_label(bars, fmt="%.1f", padding=2)
ax.set_ylabel("Respondents")

dm.simple_layout(fig)
dm.save_formats(fig, "output/whole_number_decimals", formats=("png",))
