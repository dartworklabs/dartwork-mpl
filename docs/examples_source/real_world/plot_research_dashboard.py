"""
Research Dashboard
==================

A realistic research dashboard combining a throughput bar chart with
an efficiency line overlay — the kind of figure commonly used
in engineering reports and academic publications.

This example showcases:

- Dual-axis layout (bars + line)
- ``dm.fs``, ``dm.lw`` for consistent scaling
- ``dm.set_decimal`` for percentage formatting
- ``dm.pseudo_alpha`` for subtle fill
- ``dm.simple_layout`` for production-ready spacing
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Throughput and efficiency chart
# --------------------------------
phases = [
    "P1", "P2", "P3", "P4",
    "P5", "P6", "P7", "P8",
    "P9", "P10",
]
throughput = [285, 310, 295, 340, 325, 365, 350, 395, 380, 420]
efficiency = [18.2, 19.5, 17.8, 21.3, 20.1, 22.4, 21.0, 23.8, 22.5, 24.6]

fig, ax1 = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

# Throughput bars
x = np.arange(len(phases))
fill_color = dm.pseudo_alpha("oc.blue5", alpha=0.75)
bars = ax1.bar(x, throughput, width=0.65, color=fill_color,
               edgecolor="oc.blue7", linewidth=0.3,
               label="Throughput", zorder=2)

ax1.set_ylabel("Throughput (samples/s)", fontsize=dm.fs(0), color="oc.blue7")
ax1.set_ylim(0, 500)
ax1.set_xticks(x)
ax1.set_xticklabels(phases, fontsize=dm.fs(-1), rotation=45,
                    ha="right")

# Efficiency line on secondary axis
ax2 = ax1.twinx()
ax2.plot(x, efficiency, color="oc.red6", lw=dm.lw(0.5),
         marker="o", markersize=4, markeredgecolor="white",
         markeredgewidth=0.5, label="Efficiency", zorder=3)
ax2.set_ylabel("Efficiency (%)", fontsize=dm.fs(0), color="oc.red6")
ax2.set_ylim(10, 30)

# Format efficiency axis to 1 decimal
dm.set_decimal(ax2, yn=1)

# Add value labels on bars
for bar, val in zip(bars, throughput, strict=False):
    ax1.text(bar.get_x() + bar.get_width() / 2, val + 5,
             f"{val}", ha="center", va="bottom",
             fontsize=dm.fs(-1.5), color="oc.gray7")

ax1.set_title("Throughput & Processing Efficiency",
              fontsize=dm.fs(1), fontweight="bold")

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2,
           loc="upper left", fontsize=dm.fs(-0.5), framealpha=0.9)

dm.simple_layout(fig)
plt.show()

# %%
# Results by method
# ------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

methods = ["CNN", "RNN", "Transformer", "MLP"]
run1 = [180, 120, 85, 45]
run2 = [250, 110, 95, 50]
run3 = [330, 100, 105, 55]

x = np.arange(len(methods))
w = 0.25

colors_run = ["oc.blue3", "oc.blue5", "oc.blue7"]
for i, (data, label, c) in enumerate(zip(
    [run1, run2, run3],
    ["Run 1", "Run 2", "Run 3"],
    colors_run, strict=False,
)):
    bars = ax.bar(x + (i - 1) * w, data, w, label=label, color=c,
                  edgecolor="white", linewidth=0.3)

ax.set_xticks(x)
ax.set_xticklabels(methods, fontsize=dm.fs(0))
ax.set_ylabel("Accuracy (%)", fontsize=dm.fs(0))
ax.set_title("Accuracy by Method", fontsize=dm.fs(1),
             fontweight="bold")
ax.legend(fontsize=dm.fs(-0.5), loc="upper right", framealpha=0.9)
ax.set_ylim(0, 400)
ax.set_xlim(-0.5, len(methods) - 0.5)

dm.simple_layout(fig)
plt.show()
