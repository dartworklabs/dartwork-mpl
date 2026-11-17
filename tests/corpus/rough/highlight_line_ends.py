"""Five cities' rents with Seoul in colour and the rest in light grey, every line named at its end."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

years = np.arange(2015, 2025)
rents = {
    "Seoul": 1.0,
    "Busan": 0.55,
    "Incheon": 0.6,
    "Daegu": 0.45,
    "Daejeon": 0.4,
}
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
for city, scale in rents.items():
    color = "dc.red6" if city == "Seoul" else "dc.gray3"
    ax.plot(
        years, 100 * scale * 1.04 ** (years - 2015), color=color, label=city
    )
ax.set(xlabel="Year", ylabel="Monthly rent (USD)")
dm.label_line_ends(ax)

dm.simple_layout(fig)
dm.save_formats(fig, "output/highlight_line_ends", formats=("png",))
