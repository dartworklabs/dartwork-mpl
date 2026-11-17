"""Monthly revenue as bars with its value on every bar, in one 8.5 cm report column."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
revenue = [
    1284,
    1310,
    1452,
    1398,
    1520,
    1611,
    1702,
    1655,
    1590,
    1734,
    1820,
    1975,
]

fig, ax = plt.subplots(figsize=dm.figsize("8.5cm", "standard"))
ax.bar(months, revenue)
dm.label_bars(ax)
ax.set_ylabel("Revenue (USD k)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/monthly_values_column", formats=("png",))
