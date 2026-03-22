"""
Custom Colormaps on Scientific Data
====================================

``dartwork-mpl`` ships with **16 curated colormaps** registered under the
``dc.*`` namespace. They are immediately available for any matplotlib function
that accepts a ``cmap`` argument — no extra imports needed.

This example applies four curated colormaps to a 2D Gaussian mixture terrain,
demonstrating how each colormap reveals different features of the same data.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('presentation')

# Generate 2D Gaussian mixture terrain
x = np.linspace(-3, 3, 200)
y = np.linspace(-3, 3, 200)
X, Y = np.meshgrid(x, y)

Z = (1.5 * np.exp(-((X - 1)**2 + (Y - 1)**2) / 0.8)
     - 0.8 * np.exp(-((X + 1)**2 + (Y + 0.5)**2) / 1.2)
     + 0.6 * np.exp(-((X - 0.5)**2 + (Y + 1.5)**2) / 0.5)
     + 0.3 * np.sin(X * 2) * np.cos(Y * 2))

# Four scientifically useful colormaps
colormaps = [
    ('dc.deep_sea',   'dc.deep_sea \u2014 sequential cool'),
    ('dc.sunset_glow',  'dc.sunset_glow \u2014 sequential warm'),
    ('dc.cool_warm', 'dc.cool_warm \u2014 diverging'),
    ('dc.neon_pulse', 'dc.neon_pulse \u2014 perceptual multi-hue'),
]

fig = plt.figure(figsize=(dm.DW, dm.DW * 0.90))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.45)

for idx, (cmap_name, title) in enumerate(colormaps):
    ax = fig.add_subplot(gs[idx // 2, idx % 2])
    cf = ax.contourf(X, Y, Z, levels=20, cmap=cmap_name)
    ax.contour(X, Y, Z, levels=10, colors='white', linewidths=0.3, alpha=0.5)
    fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.04)
    ax.set_title(title, fontsize=dm.fs(0), weight='bold', pad=12)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect('equal')

fig.tight_layout(pad=1.5, h_pad=2.0, w_pad=2.0)
plt.show()
