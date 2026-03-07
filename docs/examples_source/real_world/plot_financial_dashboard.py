"""
Financial Dashboard
===================

A realistic financial dashboard combining a revenue bar chart with
an operating margin line overlay — the kind of figure commonly used
in equity research reports and investor presentations.

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
# Revenue and margin chart
# -------------------------
quarters = [
    "1Q23", "2Q23", "3Q23", "4Q23",
    "1Q24", "2Q24", "3Q24", "4Q24",
    "1Q25", "2Q25",
]
revenue = [285, 310, 295, 340, 325, 365, 350, 395, 380, 420]
op_margin = [18.2, 19.5, 17.8, 21.3, 20.1, 22.4, 21.0, 23.8, 22.5, 24.6]

fig, ax1 = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

# Revenue bars
x = np.arange(len(quarters))
fill_color = dm.pseudo_alpha("oc.blue5", alpha=0.75)
bars = ax1.bar(x, revenue, width=0.65, color=fill_color,
               edgecolor="oc.blue7", linewidth=0.3,
               label="Revenue", zorder=2)

ax1.set_ylabel("Revenue ($M)", fontsize=dm.fs(0), color="oc.blue7")
ax1.set_ylim(0, 500)
ax1.set_xticks(x)
ax1.set_xticklabels(quarters, fontsize=dm.fs(-1), rotation=45,
                    ha="right")

# Operating margin line on secondary axis
ax2 = ax1.twinx()
ax2.plot(x, op_margin, color="oc.red6", lw=dm.lw(0.5),
         marker="o", markersize=4, markeredgecolor="white",
         markeredgewidth=0.5, label="Op. Margin", zorder=3)
ax2.set_ylabel("Op. Margin (%)", fontsize=dm.fs(0), color="oc.red6")
ax2.set_ylim(10, 30)

# Format margin axis to 1 decimal
dm.set_decimal(ax2, yn=1)

# Add value labels on bars
for bar, val in zip(bars, revenue, strict=False):
    ax1.text(bar.get_x() + bar.get_width() / 2, val + 5,
             f"${val}", ha="center", va="bottom",
             fontsize=dm.fs(-1.5), color="oc.gray7")

ax1.set_title("Quarterly Revenue & Operating Margin",
              fontsize=dm.fs(1), fontweight="bold")

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2,
           loc="upper left", fontsize=dm.fs(-0.5), framealpha=0.9)

dm.simple_layout(fig)
plt.show()

# %%
# Segment revenue breakdown
# --------------------------
fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

segments = ["Cloud", "Hardware", "Services", "Licensing"]
fy23 = [180, 120, 85, 45]
fy24 = [250, 110, 95, 50]
fy25e = [330, 100, 105, 55]

x = np.arange(len(segments))
w = 0.25

colors_fy = ["oc.blue3", "oc.blue5", "oc.blue7"]
for i, (data, label, c) in enumerate(zip(
    [fy23, fy24, fy25e],
    ["FY2023", "FY2024", "FY2025E"],
    colors_fy, strict=False,
)):
    bars = ax.bar(x + (i - 1) * w, data, w, label=label, color=c,
                  edgecolor="white", linewidth=0.3)

ax.set_xticks(x)
ax.set_xticklabels(segments, fontsize=dm.fs(0))
ax.set_ylabel("Revenue ($M)", fontsize=dm.fs(0))
ax.set_title("Revenue by Segment", fontsize=dm.fs(1),
             fontweight="bold")
ax.legend(fontsize=dm.fs(-0.5), loc="upper right", framealpha=0.9)
ax.set_ylim(0, 400)
ax.set_xlim(-0.5, len(segments) - 0.5)

dm.simple_layout(fig)
plt.show()
