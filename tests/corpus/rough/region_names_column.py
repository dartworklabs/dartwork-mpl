"""Sales by region as bars, the two-word region names under a 9 cm column."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

regions = [
    "North America",
    "Western Europe",
    "Asia Pacific",
    "Latin America",
    "Middle East",
]
sales = [42.1, 35.4, 31.8, 12.6, 8.3]

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.bar(regions, sales)
ax.set_ylabel("Sales (USD m)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/region_names_column", formats=("png",))
