"""A report chart whose one-sentence title is longer than the 9 cm canvas is wide."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

years = [2019, 2020, 2021, 2022, 2023, 2024]
exports = [542, 512, 644, 684, 632, 701]

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.plot(years, exports, marker="o")
ax.set(xlabel="Year", ylabel="Exports (USD bn)")
ax.set_title(
    "Exports recovered past their 2019 level in 2021 and kept climbing"
)

dm.simple_layout(fig)
dm.save_formats(fig, "output/long_title", formats=("png",))
