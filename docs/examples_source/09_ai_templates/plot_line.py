"""
Line
====

Two-series line chart.

Source: ``dartwork_mpl/asset/prompt/05-templates/line.py`` ·
``dm.get_prompt("05-templates/line")`` · MCP ``dartwork-mpl://templates/line``.
"""

import numpy as np

import dartwork_mpl as dm

x = np.linspace(0, 10, 100)
y1, y2 = np.sin(x), np.cos(x)

fig, ax = dm.subplots(width="15cm", aspect="wide")
ax.plot(x, y1, color="oc.blue6", linewidth=0.8, label="sin(x)")
ax.plot(x, y2, color="oc.red6", linewidth=0.8, label="cos(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend()
dm.auto_layout(fig)
