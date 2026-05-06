"""Two-series line chart."""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

x = np.linspace(0, 10, 100)
y1, y2 = np.sin(x), np.cos(x)

fig, ax = plt.subplots(figsize=dm.figsize("15cm", "wide"))
ax.plot(x, y1, color="oc.blue6", linewidth=0.8, label="sin(x)")
ax.plot(x, y2, color="oc.red6", linewidth=0.8, label="cos(x)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend()
dm.auto_layout(fig)
dm.save_formats(fig, "line")
