"""
Color Cycles
============

Preview built-in color cycles and learn how to swap or extend them for multi-series plots.
"""

import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

import dartwork_mpl as dm

dm.style.use("presentation")

np.random.seed(42)
x = np.linspace(0, 10, 100)

fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.08,
    right=0.98,
    top=0.95,
    bottom=0.08,
    wspace=0.4,
    hspace=0.5,
)

# Panel A: Default dartwork-mpl cycle
ax1 = fig.add_subplot(gs[0, 0])
for i in range(6):
    y = np.sin(x + i * 0.5) + i * 0.3
    ax1.plot(x, y, lw=0.7, label=f"Line {i + 1}")
ax1.set_xlabel("X", fontsize=dm.fs(0))
ax1.set_ylabel("Y", fontsize=dm.fs(0))
ax1.set_title("Default Color Cycle", fontsize=dm.fs(1))
ax1.legend(loc="upper right", fontsize=dm.fs(-2), ncol=2)

# Panel B: Custom color cycle (blues)
ax2 = fig.add_subplot(gs[0, 1])
blue_cycle = cycler(
    color=["oc.blue2", "oc.blue4", "oc.blue5", "oc.blue6", "oc.blue8"]
)
ax2.set_prop_cycle(blue_cycle)
for i in range(5):
    y = np.sin(x + i * 0.6) + i * 0.4
    ax2.plot(x, y, lw=0.7, label=f"Blue {i + 1}")
ax2.set_xlabel("X", fontsize=dm.fs(0))
ax2.set_ylabel("Y", fontsize=dm.fs(0))
ax2.set_title("Blue Gradient Cycle", fontsize=dm.fs(1))
ax2.legend(loc="upper right", fontsize=dm.fs(-2), ncol=2)

# Panel C: Tailwind color cycle
ax3 = fig.add_subplot(gs[1, 0])
tw_cycle = cycler(
    color=[
        "tw.red500",
        "tw.orange500",
        "tw.yellow600",
        "tw.green500",
        "tw.blue500",
        "tw.purple500",
    ]
)
ax3.set_prop_cycle(tw_cycle)
for i in range(6):
    y = np.sin(x + i * 0.5) + i * 0.3
    ax3.plot(x, y, lw=0.7, label=f"TW {i + 1}")
ax3.set_xlabel("X", fontsize=dm.fs(0))
ax3.set_ylabel("Y", fontsize=dm.fs(0))
ax3.set_title("Tailwind Color Cycle", fontsize=dm.fs(1))
ax3.legend(loc="upper right", fontsize=dm.fs(-2), ncol=2)

# Panel D: Combined style cycle (color + linestyle)
ax4 = fig.add_subplot(gs[1, 1])
combined_cycle = cycler(color=["oc.red5", "oc.blue5", "oc.green5"]) * cycler(
    linestyle=["-", "--", "-."]
)
ax4.set_prop_cycle(combined_cycle)
for i in range(9):
    y = np.sin(x + i * 0.3) + (i // 3) * 0.5
    ax4.plot(x, y, lw=0.7)
ax4.set_xlabel("X", fontsize=dm.fs(0))
ax4.set_ylabel("Y", fontsize=dm.fs(0))
ax4.set_title("Combined Cycle (Color × Style)", fontsize=dm.fs(1))

dm.simple_layout(fig, gs=gs)
plt.show()
