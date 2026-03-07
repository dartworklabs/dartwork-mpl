"""
Line Styles
===========

Preview dashes, caps, and joins side by side to choose line styles that stay legible once printed or projected.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply scientific style preset
dm.style.use("presentation")

# Generate data
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 3
y2 = np.sin(x + 0.5) + 1.5
y3 = np.sin(x + 1.0)
y4 = np.sin(x + 1.5) - 1.5

# Create figure
# Double column figure: 17cm width, 2x2 layout
fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)

# Create GridSpec for 2x2 subplots
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.98,
    top=0.95,
    bottom=0.08,
    wspace=0.3,
    hspace=0.4,
)

# Panel A: Basic line styles
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(x, y1, "-", color="oc.red5", lw=0.7, label="Solid")
ax1.plot(x, y2, "--", color="oc.blue5", lw=0.7, label="Dashed")
ax1.plot(x, y3, "-.", color="oc.green5", lw=0.7, label="Dash-dot")
ax1.plot(x, y4, ":", color="oc.orange5", lw=0.7, label="Dotted")
ax1.set_xlabel("X value", fontsize=dm.fs(0))
ax1.set_ylabel("Y value", fontsize=dm.fs(0))
ax1.set_title("Basic Line Styles", fontsize=dm.fs(1))
ax1.legend(loc="best", fontsize=dm.fs(-1), ncol=2, frameon=False)
ax1.set_xticks([0, 2, 4, 6, 8, 10])
ax1.set_yticks([-3, -1, 1, 3, 5])

# Panel B: Custom dash patterns
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(x, y1, color="oc.red5", lw=0.7, linestyle=(0, (5, 1)), label="(5, 1)")
ax2.plot(x, y2, color="oc.blue5", lw=0.7, linestyle=(0, (5, 2)), label="(5, 2)")
ax2.plot(
    x,
    y3,
    color="oc.green5",
    lw=0.7,
    linestyle=(0, (5, 1, 1, 1)),
    label="(5, 1, 1, 1)",
)
ax2.plot(
    x, y4, color="oc.orange5", lw=0.7, linestyle=(0, (1, 1)), label="(1, 1)"
)
ax2.set_xlabel("X value", fontsize=dm.fs(0))
ax2.set_ylabel("Y value", fontsize=dm.fs(0))
ax2.set_title("Custom Dash Patterns", fontsize=dm.fs(1))
ax2.legend(loc="best", fontsize=dm.fs(-1), ncol=2, frameon=False)
ax2.set_xticks([0, 2, 4, 6, 8, 10])
ax2.set_yticks([-3, -1, 1, 3, 5])

# Panel C: Line styles with markers
ax3 = fig.add_subplot(gs[1, 0])
x_sparse = np.linspace(0, 10, 20)
y1_sparse = np.sin(x_sparse) + 3
y2_sparse = np.sin(x_sparse + 0.5) + 1.5
y3_sparse = np.sin(x_sparse + 1.0)
y4_sparse = np.sin(x_sparse + 1.5) - 1.5
ax3.plot(
    x_sparse, y1_sparse, "o-", color="oc.red5", lw=0.5, ms=3, label="Solid"
)
ax3.plot(
    x_sparse, y2_sparse, "s--", color="oc.blue5", lw=0.5, ms=3, label="Dashed"
)
ax3.plot(
    x_sparse,
    y3_sparse,
    "^-.",
    color="oc.green5",
    lw=0.5,
    ms=3,
    label="Dash-dot",
)
ax3.plot(
    x_sparse,
    y4_sparse,
    "D:",
    color="oc.orange5",
    lw=0.5,
    ms=2.5,
    label="Dotted",
)
ax3.set_xlabel("X value", fontsize=dm.fs(0))
ax3.set_ylabel("Y value", fontsize=dm.fs(0))
ax3.set_title("Lines with Markers", fontsize=dm.fs(1))
ax3.legend(loc="best", fontsize=dm.fs(-1), ncol=2, frameon=False)
ax3.set_xticks([0, 2, 4, 6, 8, 10])
ax3.set_yticks([-3, -1, 1, 3, 5])

# Panel D: Same color, different styles
ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(x, y1, "-", color="oc.blue5", lw=0.7, label="Model 1")
ax4.plot(x, y2, "--", color="oc.blue5", lw=0.7, label="Model 2")
ax4.plot(x, y3, "-.", color="oc.blue5", lw=0.7, label="Model 3")
ax4.plot(x, y4, ":", color="oc.blue5", lw=0.7, label="Model 4")
ax4.set_xlabel("X value", fontsize=dm.fs(0))
ax4.set_ylabel("Y value", fontsize=dm.fs(0))
ax4.set_title("Same Color Variants", fontsize=dm.fs(1))
ax4.legend(loc="best", fontsize=dm.fs(-1), ncol=2, frameon=False)
ax4.set_xticks([0, 2, 4, 6, 8, 10])
ax4.set_yticks([-3, -1, 1, 3, 5])

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Save and show plot
plt.show()
