"""Exports by year with a source line from dm.add_note under the x-axis name."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

years = [2019, 2020, 2021, 2022, 2023]
exports = [542, 512, 644, 684, 632]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.plot(years, exports)
ax.set_xticks(years)
ax.set(xlabel="Year", ylabel="Exports (USD bn)")
dm.add_note(fig, "Source: Statistics agency, typical gyp descenders")
dm.simple_layout(fig)
dm.save_formats(fig, "output/source_note", formats=("png",))
