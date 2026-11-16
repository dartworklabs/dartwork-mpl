"""Four noisy series, one panel each, sharing both axes."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
x = np.linspace(0, 10, 100)
panels = [
    ("Group A", np.sin(x) + rng.normal(scale=0.1, size=x.size)),
    ("Group B", np.cos(x) + rng.normal(scale=0.1, size=x.size)),
    ("Group C", 0.5 * x + rng.normal(scale=0.4, size=x.size)),
    ("Group D", np.sin(2 * x) * 0.5 + rng.normal(scale=0.1, size=x.size)),
]

nrows, ncols = 2, 2
fig, axes = plt.subplots(
    nrows,
    ncols,
    figsize=dm.figsize_for(nrows=nrows, ncols=ncols),
    sharex=True,
    sharey=True,
)
for ax, (label, y) in zip(axes.flat, panels, strict=False):
    ax.plot(x, y, color="dc.teal3", linewidth=dm.lw(0))
    ax.set_xlabel("x")
    ax.set_ylabel(label)
    ax.text(
        0.02,
        0.95,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=dm.fs(0),
        fontweight=dm.fw(1),
    )
dm.simple_layout(fig)
dm.save_formats(fig, "output/small_multiples_basic", formats=("png",))
