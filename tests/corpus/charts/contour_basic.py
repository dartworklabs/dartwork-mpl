"""A filled contour map of sin(x) cos(y) with a colorbar."""

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
fig.colorbar(cs, ax=ax, label="sin(x) cos(y)")
ax.set_xlabel("x")
ax.set_ylabel("y")

dm.simple_layout(fig)
dm.save_formats(fig, "output/contour_basic", formats=("png",))
