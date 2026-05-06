"""Small multiples / faceted panels - 2x2 grid of line charts."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
x = np.linspace(0, 10, 100)
panels = [
    ("Group A", np.sin(x) + rng.normal(scale=0.1, size=x.size)),
    ("Group B", np.cos(x) + rng.normal(scale=0.1, size=x.size)),
    ("Group C", 0.5 * x + rng.normal(scale=0.4, size=x.size)),
    ("Group D", np.sin(2 * x) * 0.5 + rng.normal(scale=0.1, size=x.size)),
]

fig, axes = plt.subplots(
    2, 2, figsize=dm.figsize("17cm", "standard"), sharex=True, sharey=True
)
for ax, (label, y) in zip(axes.flat, panels, strict=False):
    ax.plot(x, y, color="oc.blue6", linewidth=0.8)
    ax.set_xlabel("x")
    ax.set_ylabel(label)
dm.auto_layout(fig)
dm.save_formats(fig, "small_multiples")
