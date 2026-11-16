"""A report's 2 x 2 grid moved to a slide by switching only the preset: titles, axis names and panel letters leave each plot about 3.7 cm tall on the whole slide, still SMALL_PANEL."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

rng = np.random.default_rng(7)
months = np.arange(1, 13)
panels = [
    ("North", "Sales (units)"),
    ("South", "Sales (units)"),
    ("Returns", "Returned (%)"),
    ("Margin", "Margin (%)"),
]

fig, axes = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
for ax, (title, ylabel) in zip(axes.flat, panels, strict=True):
    ax.plot(months, 50 + np.cumsum(rng.normal(1, 3, months.size)))
    ax.set_title(title)
    ax.set_xlabel("Month")
    ax.set_ylabel(ylabel)
dm.label_axes(axes.flat)

dm.simple_layout(fig)
dm.save_formats(fig, "output/slide_grid", formats=("png",))
