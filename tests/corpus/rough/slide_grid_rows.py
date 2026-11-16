"""A 2 x 2 slide grid with a title, ticks and an axis name on every panel: the rows need more than matplotlib's spacing between them."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("presentation")

months = range(1, 13)
fig, axes = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
for ax in axes.flat:
    ax.plot(months, range(12))
    ax.set_title("Returns")
    ax.set_xlabel("Month")
    ax.set_ylabel("Sales (units)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/slide_grid_rows", formats=("png",))
