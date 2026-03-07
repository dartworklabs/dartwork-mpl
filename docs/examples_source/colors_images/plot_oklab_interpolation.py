"""
OKLab / OKLCH Color Interpolation
===================================

Dartwork-mpl provides the ``Color`` class with native OKLab and OKLCH
support. OKLCH interpolation produces perceptually uniform gradients —
unlike naive RGB mixing, which creates muddy mid-tones.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# OKLCH hue wheel
# ----------------
# Sweep the OKLCH hue from 0° to 360° at fixed lightness
# and chroma. Each hue step is perceptually equidistant.
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

n_hues = 72
hues = np.linspace(0, 360, n_hues, endpoint=False)
bar_width = 360 / n_hues

for h in hues:
    c = dm.oklch(0.72, 0.15, h)
    ax.bar(h, 1, width=bar_width, color=c.to_rgb(),
           edgecolor="none")

ax.set_xlim(0, 360)
ax.set_ylim(0, 1)
ax.set_xticks([0, 60, 120, 180, 240, 300, 360])
ax.set_xticklabels(["0°", "60°", "120°", "180°", "240°", "300°",
                     "360°"], fontsize=dm.fs(-0.5))
ax.set_yticks([])
ax.set_xlabel("Hue (h)", fontsize=dm.fs(0))
ax.set_title("OKLCH Hue Wheel (L=0.72, C=0.15)", fontsize=dm.fs(1))

dm.simple_layout(fig)
plt.show()

# %%
# RGB vs OKLCH interpolation
# ---------------------------
# Interpolating between blue and yellow reveals how RGB creates
# a muddy grey middle, while OKLCH maintains vivid colours.
fig, axes = plt.subplots(
    2, 1, figsize=(dm.cm2in(15), dm.cm2in(8)), dpi=300
)

start = dm.hex("#2563eb")  # Blue
end = dm.hex("#eab308")    # Yellow
n_steps = 50

# Top: RGB interpolation
ax_rgb = axes[0]
for i in range(n_steps):
    t = i / (n_steps - 1)
    r = start.rgb.r * (1 - t) + end.rgb.r * t
    g = start.rgb.g * (1 - t) + end.rgb.g * t
    b = start.rgb.b * (1 - t) + end.rgb.b * t
    ax_rgb.bar(i, 1, width=1.0, color=(r, g, b), edgecolor="none")

ax_rgb.set_xlim(-0.5, n_steps - 0.5)
ax_rgb.set_ylim(0, 1)
ax_rgb.set_xticks([])
ax_rgb.set_yticks([])
ax_rgb.set_title("RGB Interpolation (blue to yellow)",
                 fontsize=dm.fs(0.5))

# Bottom: OKLCH interpolation via dm.cspace
ax_oklch = axes[1]
colors_oklch = dm.cspace(start, end, n=n_steps, space="oklch")
for i, c in enumerate(colors_oklch):
    ax_oklch.bar(i, 1, width=1.0, color=c.to_rgb(), edgecolor="none")

ax_oklch.set_xlim(-0.5, n_steps - 0.5)
ax_oklch.set_ylim(0, 1)
ax_oklch.set_xticks([])
ax_oklch.set_yticks([])
ax_oklch.set_title("OKLCH Interpolation (blue to yellow)",
                   fontsize=dm.fs(0.5))

dm.simple_layout(fig)
plt.show()

# %%
# Building a custom gradient from named colors
# -----------------------------------------------
# Use ``dm.cspace()`` to interpolate between any two dartwork
# named colors in perceptual space.
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(6)), dpi=300
)

pairs = [
    ("oc.red5", "oc.blue5", "Red to Blue"),
    ("oc.green5", "oc.purple5", "Green to Purple"),
    ("oc.cyan5", "oc.orange5", "Cyan to Orange"),
]

for row, (c1, c2, label) in enumerate(pairs):
    start_c = dm.Color.from_name(c1)
    end_c = dm.Color.from_name(c2)
    gradient = dm.cspace(start_c, end_c, n=40, space="oklch")
    for i, c in enumerate(gradient):
        ax.bar(i, 1, bottom=row * 1.3, width=1.0,
               color=c.to_rgb(), edgecolor="none")
    ax.text(-2, row * 1.3 + 0.5, label, fontsize=dm.fs(-0.5),
            ha="right", va="center")

ax.set_xlim(-8, 40)
ax.set_ylim(-0.2, len(pairs) * 1.3)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Custom OKLCH Gradients", fontsize=dm.fs(1))

dm.simple_layout(fig)
plt.show()
