"""Revenue bars and margin line on a twin axis, each with its own legend in the same corner."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

years = ["2019", "2020", "2021", "2022", "2023", "2024"]
revenue = [120, 98, 135, 160, 172, 190]
margin = [12.5, 8.1, 14.2, 15.8, 15.1, 16.9]

fig, ax1 = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax2 = ax1.twinx()
ax1.bar(years, revenue, color="dc.blue3", label="Revenue")
ax2.plot(years, margin, color="dc.red5", marker="o", label="Operating margin")
ax1.set_ylabel("Revenue (USD m)")
ax2.set_ylabel("Operating margin (%)")
ax1.legend(loc="upper left")
ax2.legend(loc="upper left")

dm.simple_layout(fig)
dm.save_formats(fig, "output/twin_axis", formats=("png",))
