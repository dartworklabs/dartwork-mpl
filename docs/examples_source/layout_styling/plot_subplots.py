"""
Subplots Layout
===============

Starter recipes for common subplot grids (1x2, 2x2, and more) with balanced spacing.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply presentation style for web docs
# Default: font.size=7.5, lines.linewidth=0.5, axes.linewidth=0.3
dm.style.use("presentation")

# Generate sample data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)
y3 = np.sin(x) * np.cos(x)
y4 = np.sin(2 * x)

# Create figure
# Double column figure: 16cm width
fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)

# Create GridSpec for 2x2 subplots
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.98,
    top=0.95,
    bottom=0.08,
    hspace=0.5,
    wspace=0.3,
)

# Panel A: Top-left
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(x, y1, color="oc.blue5", lw=0.7, label="Sin")
ax1.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax1.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax1.set_title("Subplot 1", fontsize=dm.fs(1))
ax1.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax1.set_xticks([0, 2, 4, 6, 8, 10])
ax1.set_yticks([-1, -0.5, 0, 0.5, 1])

# Panel B: Top-right
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(x, y2, color="oc.red5", lw=0.7, label="Cos")
ax2.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax2.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax2.set_title("Subplot 2", fontsize=dm.fs(1))
ax2.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax2.set_xticks([0, 2, 4, 6, 8, 10])
ax2.set_yticks([-1, -0.5, 0, 0.5, 1])

# Panel C: Bottom-left
ax3 = fig.add_subplot(gs[1, 0])
ax3.plot(x, y3, color="oc.green5", lw=0.7, label="Sin×Cos")
ax3.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax3.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax3.set_title("Subplot 3", fontsize=dm.fs(1))
ax3.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax3.set_xticks([0, 2, 4, 6, 8, 10])
ax3.set_yticks([-0.5, 0, 0.5])

# Panel D: Bottom-right
ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(x, y4, color="oc.orange5", lw=0.7, label="Sin(2x)")
ax4.set_xlabel("Time [s]", fontsize=dm.fs(0))
ax4.set_ylabel("Amplitude", fontsize=dm.fs(0))
ax4.set_title("Subplot 4", fontsize=dm.fs(1))
ax4.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax4.set_xticks([0, 2, 4, 6, 8, 10])
ax4.set_yticks([-1, -0.5, 0, 0.5, 1])

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Show plot
plt.show()
