"""
Automatic Panel Indexing
========================

For academic publications, subplots require (a), (b), (c) labels.
``dm.label_axes()`` automatically places indices at the top-left corner,
scaling its font size to match the active style preset.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

fig, axes = plt.subplots(2, 2, figsize=(dm.DW, dm.SW * 0.9))

np.random.seed(0)
for ax in axes.flat:
    x = np.cumsum(np.random.randn(100))
    ax.plot(x, color="oc.gray7", lw=dm.lw(0))
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)

# Automatically add (a), (b), (c), (d) using label_axes
dm.label_axes(axes.flat)

# Use simple_layout for consistent margins
dm.simple_layout(fig)
plt.show()
