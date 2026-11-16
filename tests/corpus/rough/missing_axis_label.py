"""Engine displacement against fuel economy as a scatter with neither axis named."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(6)
displacement = rng.uniform(1.0, 5.0, 80)
economy = 22 - 3 * displacement + rng.normal(0, 1.5, 80)

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.scatter(displacement, economy, s=14)
ax.set_title("Bigger engines burn more fuel")

dm.simple_layout(fig)
dm.save_formats(fig, "output/missing_axis_label", formats=("png",))
