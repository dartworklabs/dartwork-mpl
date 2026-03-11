"""
Phase Diagram with Semantic Arrow Axes
=======================================

Scientific phase diagrams often benefit from replacing standard spines
with directional indicators. ``dm.arrow_axis()`` draws a
``Low ◄── label ──► High`` annotation along any axis edge, boosting the
data-ink ratio by encoding meaning directly into the frame.

This example renders a stylized material-science phase diagram with
three regions separated by ``dm.pseudo_alpha()`` fills.
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

dm.style.use('minimal')

fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.85))

# Synthetic phase boundaries
x = np.linspace(0, 10, 200)
boundary1 = 2.0 + 0.8 * np.log1p(x)
boundary2 = 5.0 + 1.2 * np.sqrt(x)

# Phase regions with pseudo-alpha (vector-safe solid colors)
ax.fill_between(x, 0, boundary1,
                color=dm.pseudo_alpha('oc.blue6', 0.20, background='white'),
                label='Phase I  (Solid)')
ax.fill_between(x, boundary1, boundary2,
                color=dm.pseudo_alpha('oc.grape6', 0.20, background='white'),
                label='Phase II  (Liquid)')
ax.fill_between(x, boundary2, 14,
                color=dm.pseudo_alpha('oc.red6', 0.20, background='white'),
                label='Phase III  (Gas)')

# Phase boundary lines
ax.plot(x, boundary1, color='oc.blue7', lw=dm.lw(1))
ax.plot(x, boundary2, color='oc.grape7', lw=dm.lw(1))

# Critical point annotation
cp_x, cp_y = 6.5, boundary2[130]
ax.plot(cp_x, cp_y, 'o', color='oc.red7', markersize=8, zorder=5)
ax.annotate('Critical\nPoint', xy=(cp_x, cp_y),
            xytext=(cp_x + 1.5, cp_y - 1.8),
            fontsize=dm.fs(-0.5), ha='center',
            arrowprops=dict(arrowstyle='->', color='oc.gray6', lw=0.8))

ax.set_title("Theoretical Phase Diagram", fontsize=dm.fs(1), weight='bold', pad=15)
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.legend(loc='upper left', fontsize=dm.fs(-0.5), framealpha=0.9, edgecolor='white')

# Replace standard spines with semantic directional arrows
dm.arrow_axis(ax, 'x', "Temperature")
dm.arrow_axis(ax, 'y', "Pressure")

fig.tight_layout(pad=1.5)
