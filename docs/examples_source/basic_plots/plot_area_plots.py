"""
Area Plots
==========

Layer filled regions and crisp lines to highlight ranges, uncertainty bands, and stacked totals without losing clarity.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply scientific style preset
dm.style.use("presentation")

# Generate data
x = np.linspace(0, 10, 100)
y1 = np.sin(x) + 2
y2 = np.cos(x) + 2
y_lower = np.zeros_like(x)
y_upper1 = np.sin(x) + 3
y_upper2 = np.sin(x) + 4

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

# Panel A: Basic fill_between
ax1 = fig.add_subplot(gs[0, 0])
ax1.fill_between(x, y_lower, y1, color="oc.blue5", alpha=0.3)
ax1.plot(x, y1, color="oc.blue7", lw=0.7, label="Upper bound")
ax1.set_xlabel("X value", fontsize=dm.fs(0))
ax1.set_ylabel("Y value", fontsize=dm.fs(0))
ax1.set_title("Basic Fill Between", fontsize=dm.fs(1))
ax1.legend(loc="best", fontsize=dm.fs(-1), frameon=False)
ax1.set_xticks([0, 2, 4, 6, 8, 10])
ax1.set_yticks([0, 1, 2, 3])
ax1.set_ylim(-0.1, 3.3)

# Panel B: Confidence interval style
ax2 = fig.add_subplot(gs[0, 1])
y_mean = np.sin(x) + 2
y_std = 0.3
ax2.fill_between(
    x, y_mean - y_std, y_mean + y_std, color="oc.red5", alpha=0.2, label="±1σ"
)
ax2.plot(x, y_mean, color="oc.red5", lw=0.7, label="Mean")
ax2.set_xlabel("X value", fontsize=dm.fs(0))
ax2.set_ylabel("Y value", fontsize=dm.fs(0))
ax2.set_title("Confidence Interval", fontsize=dm.fs(1))
ax2.legend(loc="best", fontsize=dm.fs(-1), frameon=False)
ax2.set_xticks([0, 2, 4, 6, 8, 10])
ax2.set_yticks([0, 1, 2, 3])
ax2.set_ylim(0, 3.4)

# Panel C: Multiple overlapping areas
ax3 = fig.add_subplot(gs[1, 0])
ax3.fill_between(x, 0, y1, color="oc.blue5", alpha=0.3, label="Sin")
ax3.fill_between(x, 0, y2, color="oc.red5", alpha=0.3, label="Cos")
ax3.plot(x, y1, color="oc.blue7", lw=0.5)
ax3.plot(x, y2, color="oc.red7", lw=0.5)
ax3.set_xlabel("X value", fontsize=dm.fs(0))
ax3.set_ylabel("Y value", fontsize=dm.fs(0))
ax3.set_title("Overlapping Areas", fontsize=dm.fs(1))
ax3.legend(loc="best", fontsize=dm.fs(-1), frameon=False)
ax3.set_xticks([0, 2, 4, 6, 8, 10])
ax3.set_yticks([0, 1, 2, 3])
ax3.set_ylim(-0.1, 3.3)

# Panel D: Stacked areas
ax4 = fig.add_subplot(gs[1, 1])
y_base = y1 - 2
y_stack1 = y_base + 0.5
y_stack2 = y_stack1 + 0.5
y_stack3 = y_stack2 + 0.5
ax4.fill_between(x, 0, y_base, color="oc.red5", alpha=0.6, label="Layer 1")
ax4.fill_between(
    x, y_base, y_stack1, color="oc.blue5", alpha=0.6, label="Layer 2"
)
ax4.fill_between(
    x, y_stack1, y_stack2, color="oc.green5", alpha=0.6, label="Layer 3"
)
ax4.fill_between(
    x, y_stack2, y_stack3, color="oc.orange5", alpha=0.6, label="Layer 4"
)
ax4.set_xlabel("X value", fontsize=dm.fs(0))
ax4.set_ylabel("Y value", fontsize=dm.fs(0))
ax4.set_title("Stacked Areas", fontsize=dm.fs(1))
ax4.legend(loc="best", fontsize=dm.fs(-2), ncol=2, frameon=False)
ax4.set_xticks([0, 2, 4, 6, 8, 10])
ax4.set_yticks([0, 0.5, 1, 1.5, 2, 2.5])
ax4.set_ylim(0, 2.7)

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Save and show plot
plt.show()
