"""
Perceptual Color Interpolation (OKLCH)
======================================

``dm.cspace()`` interpolates between two colors in the perceptually uniform OKLCH
color space, preventing sequential gradients from becoming muddy or inconsistent
in lightness. Use ``dm.named()`` to convert named palette colors to ``Color`` objects before interpolation.
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

fig, axs = plt.subplots(2, 1, figsize=(dm.SW, dm.SW * 1.2))

n_colors = 8
x = np.linspace(0, 10, 100)

# ── Panel 1: Sequential scale (light blue → dark blue) ──
# dm.named() converts palette strings to Color objects for cspace
colors_seq = dm.cspace(dm.named('oc.blue1'), dm.named('oc.blue9'),
                       n=n_colors, space='oklch')
axs[0].set_title("Sequential Scale via OKLCH")

for i, c in enumerate(colors_seq):
    y = np.sin(x + i * 0.3) + (i * 0.3)
    axs[0].plot(x, y, color=c.to_hex(), lw=dm.lw(1))

# ── Panel 2: Warm sequential scale (yellow → deep red) ──
colors_warm = dm.cspace(dm.named('oc.yellow3'), dm.named('oc.red9'),
                        n=n_colors, space='oklch')
axs[1].set_title("Warm Sequential Scale via OKLCH")

for i, c in enumerate(colors_warm):
    y = np.cos(x + i * 0.3) + (i * 0.3)
    axs[1].plot(x, y, color=c.to_hex(), lw=dm.lw(1))

for ax in axs:
    dm.set_decimal(ax, yn=1)
    ax.set_xlabel("Time")
    ax.set_ylabel("Intensity")

dm.simple_layout(fig)
plt.show()
