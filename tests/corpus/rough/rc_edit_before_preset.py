"""A notebook that sets a larger font and thicker lines by hand, then turns on the report preset and plots."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

plt.rcParams["font.size"] = 12
plt.rcParams["lines.linewidth"] = 2.5
dm.style.use("report")

years, exports = [2019, 2020, 2021, 2022, 2023], [542, 512, 644, 684, 632]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.plot(years, exports)
ax.set(xlabel="Year", ylabel="Exports (USD bn)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/rc_edit_before_preset", formats=("png",))
