"""A 2 x 3 grid of city temperature panels, each with its own title, rotated month names and a y label on every panel."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

months = ["January", "February", "March", "April", "May", "June"]
cities = ["Seoul", "Busan", "Daegu", "Incheon", "Gwangju", "Daejeon"]
rng = np.random.default_rng(10)

fig, axes = plt.subplots(2, 3, figsize=dm.figsize("17cm", "9cm"))
for ax, city in zip(axes.flat, cities, strict=True):
    ax.plot(months, -3 + 4.5 * np.arange(6) + rng.normal(0, 1, 6), marker="o")
    ax.set_title(city)
    ax.set_ylabel("Mean temperature (°C)")
    ax.tick_params(axis="x", rotation=45)

dm.simple_layout(fig)
dm.save_formats(fig, "output/rotated_ticks_grid", formats=("png",))
