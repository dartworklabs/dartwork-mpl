"""A thumbnail-sized 5 x 4 cm chart that still carries a title, both axis names and a three-entry legend."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

x = np.arange(2015, 2025)
fig, ax = plt.subplots(figsize=dm.figsize("5cm", "4cm"))
ax.plot(x, 20 + 1.5 * (x - 2015), label="Solar")
ax.plot(x, 35 + 0.8 * (x - 2015), label="Wind")
ax.plot(x, 60 - 2.0 * (x - 2015), label="Coal")
ax.set(xlabel="Year", ylabel="Share of generation (%)")
ax.set_title("Generation mix")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/tiny_canvas", formats=("png",))
