"""
Spine Colour and Thickness
===========================

Customise spine appearance with ``dm.style_spines`` to set colour and
linewidth on selected spines. The three panels compare: coloured
left/bottom spines, a thick coloured rectangular frame, and mixed
styling where top/right are thin and grey while left/bottom stay
bold black.

The three series are synthetic signals for illustration.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

np.random.seed(42)
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.exp(-x / 5) * np.cos(2 * x)
y3 = x + 0.5 * np.random.randn(100)

dm.style.use("scientific")
fig, axes = dm.subplots(1, 3, width="18cm", aspect=0.333)

# Coloured spines on left and bottom.
ax1 = axes[0]
ax1.plot(x, y1, color="oc.blue5", lw=dm.lw(1))
dm.style_spines(ax1, color="oc.blue8", linewidth=2, which=["left", "bottom"])
for s in ["top", "right"]:
    ax1.spines[s].set_visible(False)
ax1.set_title("Coloured Spines", fontsize=dm.fs(1))

# Thick coloured frame.
ax2 = axes[1]
ax2.plot(x, y2, color="oc.red5", lw=dm.lw(1))
dm.add_frame(ax2, color="oc.red8", linewidth=3)
ax2.set_title("Coloured Frame", fontsize=dm.fs(1))

# Mixed weighting: top/right faint grey, left/bottom bold black.
ax3 = axes[2]
ax3.plot(x, y3, color="oc.green5", lw=dm.lw(1))
dm.style_spines(ax3, color="gray", linewidth=0.5, which=["top", "right"])
dm.style_spines(ax3, color="black", linewidth=1.5, which=["left", "bottom"])
ax3.set_title("Mixed Styling", fontsize=dm.fs(1))

dm.simple_layout(fig)
plt.show()
