"""Respondents by age with an x tick forced on every single year from 18 to 80."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

rng = np.random.default_rng(13)
ages = np.arange(18, 81)
respondents = rng.poisson(40 + 20 * np.exp(-((ages - 40) ** 2) / 300))

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
ax.bar(ages, respondents)
ax.set_xticks(ages)
ax.set(xlabel="Age (years)", ylabel="Respondents")

dm.simple_layout(fig)
dm.save_formats(fig, "output/tick_every_year", formats=("png",))
