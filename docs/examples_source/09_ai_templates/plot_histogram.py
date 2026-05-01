"""
Histogram
=========

Histogram of standard normal samples.

Source: ``dartwork_mpl/asset/prompt/05-templates/histogram.py`` ·
``dm.get_prompt("05-templates/histogram")`` · MCP
``dartwork-mpl://templates/histogram``.
"""

import numpy as np

import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.standard_normal(1000)

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.hist(data, bins=30, color="oc.blue5", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value")
ax.set_ylabel("Frequency")
dm.auto_layout(fig)
