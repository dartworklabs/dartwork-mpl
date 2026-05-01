"""
Grid Customization
===================

``dm.add_grid`` accepts all matplotlib grid kwargs and layers cleanly
over any spine preset. The 2×3 grid below compares six common grid
configurations on the same synthetic signal: default, y-only, x-only,
subtle, dotted, and major-plus-minor.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y = np.sin(x) + 0.1 * np.random.randn(100)

dm.style.use("scientific")
fig, axes = dm.subplots(2, 3, width="18cm", aspect="wide")

grid_configs = [
    {"title": "Default Grid", "kwargs": {}},
    {"title": "Y-axis Only", "kwargs": {"axis": "y"}},
    {"title": "X-axis Only", "kwargs": {"axis": "x"}},
    {
        "title": "Subtle Grid",
        "kwargs": {"alpha": 0.2, "linestyle": "-", "linewidth": 0.5},
    },
    {
        "title": "Dotted Grid",
        "kwargs": {"alpha": 0.4, "linestyle": ":", "linewidth": 1},
    },
    {"title": "Major & Minor", "kwargs": {"which": "both", "alpha": 0.3}},
]

for ax, config in zip(axes.flat, grid_configs, strict=False):
    ax.plot(x, y, color="oc.indigo5", lw=dm.lw(1))
    dm.minimal_axes(ax)
    dm.add_grid(ax, **config["kwargs"])
    ax.set_title(config["title"], fontsize=dm.fs(0))

    if config["title"] == "Major & Minor":
        ax.minorticks_on()

dm.simple_layout(fig)
plt.show()
