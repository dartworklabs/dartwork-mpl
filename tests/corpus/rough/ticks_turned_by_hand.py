"""Sales by region with the month names turned by hand to 45 degrees, ends at their ticks, then laid out twice."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = ["January", "February", "March", "April", "May", "June"]
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.bar(months, [12, 15, 14, 18, 21, 19])
ax.set_ylabel("Units sold (k)")
ax.tick_params(axis="x", rotation=45, rotation_mode="xtick")
dm.simple_layout(fig)
dm.simple_layout(fig)
dm.save_formats(fig, "output/ticks_turned_by_hand", formats=("png",))
