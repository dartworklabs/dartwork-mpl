"""Filled contour plot of sin(x) cos(y)."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

x = np.linspace(-3, 3, 100)
y = np.linspace(-3, 3, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

fig, ax = plt.subplots(figsize=dm.figsize("11cm", "square"))
cs = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
fig.colorbar(cs, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")
dm.simple_layout(fig)
dm.save_formats(fig, "contour")
