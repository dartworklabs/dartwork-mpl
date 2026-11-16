"""Two curves, sin and cos, with a legend."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

x = np.linspace(0, 10, 100)
y1, y2 = np.sin(x), np.cos(x)

fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=len(x), n_series=2))
ax.plot(x, y1, color="dc.teal3", linewidth=dm.lw(0), label="sin(x)")
ax.plot(x, y2, color="dc.orange3", linewidth=dm.lw(0), label="cos(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend()

dm.simple_layout(fig)
dm.save_formats(fig, "output/line_basic", formats=("png",))
