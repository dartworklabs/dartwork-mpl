"""Stacked survey bars with the net value in a column at a guessed x."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

areas = ["Security", "Analytics", "Automation", "Training", "Travel", "Offices"]
less = [4, 7, 9, 14, 39, 52]
more = [58, 46, 39, 25, 13, 7]
same = [100 - a - b for a, b in zip(less, more, strict=True)]

fig, ax = plt.subplots(figsize=dm.figsize("16cm", 0.6))
ax.barh(areas, less, color="dc.red5", label="Spend less")
ax.barh(areas, same, left=less, color="dc.gray3", label="The same")
ax.barh(
    areas,
    more,
    left=[a + b for a, b in zip(less, same, strict=True)],
    color="dc.blue6",
    label="Spend more",
)
ax.invert_yaxis()
ax.set(xlim=(0, 100), xlabel="Share of respondents (%)")
for y, (a, b) in enumerate(zip(less, more, strict=True)):
    ax.text(
        1.18,
        y,
        f"{b - a:+d}",
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="center",
    )
dm.place_legend(ax, loc="above")

dm.simple_layout(fig)
dm.save_formats(fig, "output/net_column_far", formats=("png",))
