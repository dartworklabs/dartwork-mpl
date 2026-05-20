"""
Small multiples
===============

Small multiples / faceted panels - 2x2 grid of line charts.

Source: ``dartwork_mpl/asset/prompt/05-templates/small_multiples.py`` ·
``dm.get_prompt("05-templates/small_multiples")`` · MCP
``dartwork-mpl://templates/small_multiples``.
"""

# ai-template-meta-start
# use_case: Repeat the same chart across a grid for comparison
# difficulty: intermediate
# data_shape: panels: list[dict] (one entry per panel)
# tags: grid, panels, facet, comparison, small-multiples
# ai-template-meta-end

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

fig, axes = plt.subplots(
    2, 2, figsize=dm.figsize("17cm", "standard"), sharex=True, sharey=True
)
for ax, (label, y) in zip(axes.flat, panels, strict=False):
    ax.plot(x, y, color="dc.ocean3", linewidth=dm.lw(0))
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
