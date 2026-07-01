"""
Pseudo-Alpha (Solid Opacity Simulation)
=======================================

Real alpha transparency causes issues when saving to vector formats (EPS, PDF),
often resulting in rasterization or overlapping artifacts.
``dm.pseudo_alpha()`` calculates solid colors that *simulate* transparency
against a given background, keeping SVGs and PDFs perfectly clean and vector.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("report")

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))

x = np.linspace(0, 10, 100)
base_color = "dc.bold3"

# Original color (full opacity equivalent)
ax.plot(x, np.sin(x), color=base_color, label="Base (100%)", lw=dm.lw(1))

# Pseudo alpha 50% — solid color, no actual alpha channel
# The `background` parameter specifies which background color to mix against
color_50 = dm.pseudo_alpha(base_color, 0.5, background="white")
ax.plot(
    x, np.sin(x) - 0.5, color=color_50, label="Pseudo Alpha (50%)", lw=dm.lw(1)
)

# Pseudo alpha 15% — even lighter solid color
color_15 = dm.pseudo_alpha(base_color, 0.15, background="white")
ax.plot(
    x, np.sin(x) - 1.0, color=color_15, label="Pseudo Alpha (15%)", lw=dm.lw(1)
)

# Fill with pseudo-alpha — note alpha=1.0, the color itself handles the lightness
ax.fill_between(x, np.sin(x) - 1.0, -2.5, color=color_15, alpha=1.0)

ax.legend(loc="upper right")
ax.set_title("Solid Colors Simulating Opacity")
ax.set_ylim(-2.5, 1.5)

dm.simple_layout(fig)
plt.show()
