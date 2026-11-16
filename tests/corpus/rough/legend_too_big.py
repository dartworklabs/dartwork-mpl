"""Ten drug-trial arms with long names in a default legend on a 9 cm chart."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(12)
weeks = np.arange(0, 13)
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
for i in range(10):
    response = 100 - np.cumsum(rng.uniform(0, 3 + i * 0.3, weeks.size))
    ax.plot(
        weeks, response, label=f"Arm {i + 1}: {10 * (i + 1)} mg twice daily"
    )
ax.set(xlabel="Week", ylabel="Tumour volume (%)")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/legend_too_big", formats=("png",))
