"""
Panel Labels (a, b, c)
======================

``dm.label_axes`` automatically adds panel labels to multi-panel
figures — essential for academic papers and technical reports.
It auto-detects the presence of y-axis labels and adjusts the
x-position accordingly.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Default labels (a, b, c, d)
# ----------------------------
fig, axes = plt.subplots(
    2, 2, figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

x = np.linspace(0, 2 * np.pi, 100)
plots = [
    (np.sin(x), "sin(x)", "oc.blue5"),
    (np.cos(x), "cos(x)", "oc.red5"),
    (np.sin(2 * x), "sin(2x)", "oc.green5"),
    (np.cos(2 * x), "cos(2x)", "oc.purple5"),
]

for ax, (y, title, color) in zip(axes.flat, plots, strict=False):
    ax.plot(x, y, color=color, lw=1)
    ax.set_title(title, fontsize=dm.fs(0))
    ax.set_xlabel("x", fontsize=dm.fs(-0.5))
    ax.set_ylabel("y", fontsize=dm.fs(-0.5))

# Add panel labels — auto-detects ylabel and adjusts x-position
dm.label_axes(axes, fontsize=dm.fs(1))

dm.simple_layout(fig)
plt.show()

# %%
# Custom labels and positioning
# -----------------------------
# Use Roman numerals and explicit positioning.
fig, axes = plt.subplots(
    1, 3, figsize=(dm.cm2in(15), dm.cm2in(6)), dpi=300
)

data = [
    (np.random.randn(200), "oc.blue4", "Histogram"),
    (np.random.exponential(2, 200), "oc.green4", "Exponential"),
    (np.random.lognormal(0, 0.5, 200), "oc.red4", "Log-normal"),
]

for ax, (d, color, title) in zip(axes, data, strict=False):
    ax.hist(d, bins=20, color=color, edgecolor="white",
            linewidth=0.3, alpha=0.8)
    ax.set_title(title, fontsize=dm.fs(0))

# Custom Roman numeral labels at specific position
dm.label_axes(
    axes,
    labels=["(i)", "(ii)", "(iii)"],
    fontsize=dm.fs(0.5),
    fontweight="bold",
    x=-0.02,
    y=1.08,
)

dm.simple_layout(fig)
plt.show()

# %%
# Mixed panels with and without y-labels
# ----------------------------------------
# ``label_axes`` auto-adjusts: panels with a y-label get
# ``x = -0.18``; panels without get ``x = -0.02``.
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(dm.cm2in(15), dm.cm2in(7)), dpi=300
)

t = np.linspace(0, 5, 100)
ax1.plot(t, np.exp(-t) * np.sin(4 * t), color="oc.indigo5", lw=1)
ax1.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax1.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax1.set_title("With y-label", fontsize=dm.fs(0.5))

ax2.plot(t, np.exp(-0.5 * t), color="oc.orange5", lw=1)
ax2.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax2.set_title("Without y-label", fontsize=dm.fs(0.5))

# x='auto' (default) adapts per-axes
dm.label_axes([ax1, ax2], fontsize=dm.fs(1))

dm.simple_layout(fig)
plt.show()
