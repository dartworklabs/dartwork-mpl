"""Filled contour plot of sin(x) cos(y)."""

import numpy as np

import dartwork_mpl as dm

x = np.linspace(-3, 3, 100)
y = np.linspace(-3, 3, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

fig, ax = dm.subplots(width="11cm", aspect="square")
cs = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
fig.colorbar(cs, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")
dm.auto_layout(fig)
dm.save_formats(fig, "contour")
