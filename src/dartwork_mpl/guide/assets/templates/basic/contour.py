"""Filled contour plot of sin(x) cos(y)."""

# ai-template-meta-start
# use_case: Show a 2D scalar field as level curves
# difficulty: advanced
# data_shape: x: 1D array, y: 1D array, z: 2D array
# tags: contour, 2d-scalar, gridded, isolines
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# One full period (±π). The axes end between ticks, so the first x and y
# tick labels (-3) do not meet at the lower-left corner as they do on ±3.
x = np.linspace(-np.pi, np.pi, 100)
y = np.linspace(-np.pi, np.pi, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
cs = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
fig.colorbar(cs, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")

dm.simple_layout(fig)
dm.save_formats(fig, "contour")
