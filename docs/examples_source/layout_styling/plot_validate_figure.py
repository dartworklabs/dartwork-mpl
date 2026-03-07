"""
Visual Validation Engine
========================

The ``validate_figure`` function detects common rendering issues that
are invisible in stdout-only environments (e.g. AI agent pipelines).
Every check emits structured ``[VISUAL]`` log lines for automated
correction.

This example intentionally creates figures with defects so you can see
what the validator catches.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Clean figure (passes all checks)
# ---------------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)
x = np.linspace(0, 10, 100)
ax.plot(x, np.sin(x), label="sin(x)", color="oc.blue5")
ax.set_title("Clean Figure", fontsize=dm.fs(1))
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("y", fontsize=dm.fs(0))
ax.legend(fontsize=dm.fs(-0.5))

dm.simple_layout(fig)

# Run validation — should pass cleanly
warnings = dm.validate_figure(fig, quiet=False)
print(f"Warnings found: {len(warnings)}")
plt.show()

# %%
# Crowded ticks (too many labels)
# --------------------------------
# Here we deliberately set 50 tick marks on the x-axis,
# which ``validate_figure`` flags as tick crowding.
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)
ax.plot(x, np.cos(x), color="oc.red5")
ax.set_title("Crowded Ticks (50 ticks)", fontsize=dm.fs(1))
ax.set_xlabel("x", fontsize=dm.fs(0))
ax.set_ylabel("y", fontsize=dm.fs(0))

# Force 50 ticks to trigger the crowding check
ax.set_xticks(np.linspace(0, 10, 50))

dm.simple_layout(fig)

warnings = dm.validate_figure(fig, quiet=False)
print(f"Warnings found: {len(warnings)}")
for w in warnings:
    print(f"  {w}")
plt.show()

# %%
# Overlapping text labels
# -----------------------
# Two text annotations placed at the same position will overlap.
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)
ax.plot(x, np.sin(x), color="oc.green5")
ax.set_title("Overlapping Text", fontsize=dm.fs(1))

# Place two labels on top of each other
ax.text(5, 0.5, "Label A", fontsize=dm.fs(1), ha="center",
        bbox={"boxstyle": "round", "facecolor": "oc.green2",
              "edgecolor": "oc.green7", "linewidth": 0.3})
ax.text(5.2, 0.5, "Label B", fontsize=dm.fs(1), ha="center",
        bbox={"boxstyle": "round", "facecolor": "oc.yellow2",
              "edgecolor": "oc.yellow7", "linewidth": 0.3})

dm.simple_layout(fig)

warnings = dm.validate_figure(fig, quiet=False)
print(f"Warnings found: {len(warnings)}")
for w in warnings:
    print(f"  {w}")
plt.show()
