"""
Dark Mode Rendering
===================

The ``dark`` preset is tuned for dashboards, presentations, and terminal UIs
with carefully softened grays and gridlines to prevent eye strain,
instead of naively inverting all colors.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("dark")

fig, ax = dm.subplots(width="9cm", aspect="wide")

np.random.seed(42)
x = np.random.randn(300)
y = x + np.random.randn(300) * 0.6

ax.scatter(x, y, color="oc.violet6", alpha=0.7, edgecolor="none", s=15)

ax.set_title("Latent Space Distribution")
ax.set_xlabel("Principal Component 1")
ax.set_ylabel("Principal Component 2")

dm.simple_layout(fig)
plt.show()
