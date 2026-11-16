"""Market share of nine brands as a pie, the four small slices' names and percentages piled on each other."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

brands = [
    "Alpha",
    "Bravo",
    "Charlie",
    "Delta",
    "Echo",
    "Foxtrot",
    "Golf",
    "Hotel",
    "India",
]
share = [38, 24, 15, 10, 7, 2.5, 1.5, 1.2, 0.8]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "square"))
ax.pie(share, labels=brands, autopct="%1.1f%%", startangle=90)
ax.set_title("Market share 2025")

dm.simple_layout(fig)
dm.save_formats(fig, "output/pie_small_slices", formats=("png",))
