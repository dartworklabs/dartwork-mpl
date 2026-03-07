"""
Font & Line Scaling (fs, fw, lw)
================================

``dm.fs(n)``, ``dm.fw(n)``, and ``dm.lw(n)`` offset from the current
style's base sizes. This keeps your charts visually consistent
regardless of which style preset is active.

- ``fs(+2)`` → base font size + 2 pt
- ``fw(+1)`` → base font weight + 100 (e.g. 400 → 500)
- ``lw(-0.3)`` → base line width − 0.3 pt
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Font size scaling with ``fs()``
# --------------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), color="oc.blue5", lw=dm.lw(0))

# Demonstrate various fs() levels
sizes = [-2, -1, 0, 1, 2, 3]
for i, n in enumerate(sizes):
    y_pos = 0.88 - i * 0.14
    ax.text(
        0.05, y_pos, f"fs({n:+d}) = {dm.fs(n):.1f} pt",
        transform=ax.transAxes,
        fontsize=dm.fs(n),
        va="center",
        color="oc.gray8",
    )

ax.set_title("Font Size Scaling: dm.fs(n)", fontsize=dm.fs(1),
             fontweight="bold")
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("sin(x)", fontsize=dm.fs(0))

dm.simple_layout(fig)
plt.show()

# %%
# Font weight scaling with ``fw()``
# -----------------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

ax.plot(x, np.cos(x), color="oc.red5", lw=dm.lw(0))

# Show different font weights
weights = [-2, -1, 0, 1, 2, 3]
for i, n in enumerate(weights):
    y_pos = 0.88 - i * 0.14
    w = dm.fw(n)
    ax.text(
        0.05, y_pos, f"fw({n:+d}) = weight {w}",
        transform=ax.transAxes,
        fontsize=dm.fs(0),
        fontweight=w,
        va="center",
        color="oc.gray8",
    )

ax.set_title("Font Weight Scaling: dm.fw(n)", fontsize=dm.fs(1),
             fontweight="bold")

dm.simple_layout(fig)
plt.show()

# %%
# Line width scaling with ``lw()``
# ----------------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

line_offsets = [-0.3, 0, 0.5, 1.0, 1.5, 2.0]
colors = ["oc.blue3", "oc.blue4", "oc.blue5", "oc.blue6",
          "oc.blue7", "oc.blue8"]

for i, (n, c) in enumerate(zip(line_offsets, colors, strict=False)):
    y = np.sin(x + i * 0.3) + i * 0.5
    ax.plot(x, y, color=c, lw=dm.lw(n),
            label=f"lw({n:+.1f}) = {dm.lw(n):.2f}")

ax.set_title("Line Width Scaling: dm.lw(n)", fontsize=dm.fs(1),
             fontweight="bold")
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("y", fontsize=dm.fs(0))
ax.legend(fontsize=dm.fs(-0.5), loc="upper right", framealpha=0.9)

dm.simple_layout(fig)
plt.show()
