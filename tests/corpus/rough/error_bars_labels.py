"""Mean yield per fertiliser with standard-deviation error bars and a value label on each bar."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

treatments = ["Control", "Nitrogen", "Phosphate", "Compost", "Mixed"]
mean = [3.1, 4.6, 3.8, 4.1, 5.2]
sd = [0.4, 0.7, 0.5, 0.9, 0.6]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
bars = ax.bar(treatments, mean, yerr=sd, capsize=4)
ax.bar_label(bars, fmt="%.1f")
ax.set_ylabel("Yield (t/ha)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/error_bars_labels", formats=("png",))
