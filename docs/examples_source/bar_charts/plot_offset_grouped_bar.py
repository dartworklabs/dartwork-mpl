"""
Offset Grouped Bar Chart
========================

``dm.make_offset`` creates translation transforms for fine-grained
control of label and annotation positioning. This example uses it
to offset data labels on grouped bar charts so they don't overlap.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Grouped bar with offset labels
# --------------------------------
categories = ["Q1", "Q2", "Q3", "Q4"]
revenue = [120, 145, 138, 162]
profit = [24, 32, 28, 41]

x = np.arange(len(categories))
width = 0.35

fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

bars1 = ax.bar(x - width / 2, revenue, width, label="Revenue",
               color="oc.blue5", edgecolor="white", linewidth=0.3)
bars2 = ax.bar(x + width / 2, profit, width, label="Profit",
               color="oc.green5", edgecolor="white", linewidth=0.3)

# Use make_offset for precise label positioning
# Shift revenue labels slightly left, profit labels slightly right
offset_left = dm.make_offset(-3, 4, fig)
offset_right = dm.make_offset(3, 4, fig)

for bar in bars1:
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2, h,
        f"${h:,}M",
        ha="center", va="bottom",
        fontsize=dm.fs(-1),
        transform=ax.transData + offset_left,
    )

for bar in bars2:
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2, h,
        f"${h:,}M",
        ha="center", va="bottom",
        fontsize=dm.fs(-1),
        transform=ax.transData + offset_right,
    )

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=dm.fs(0))
ax.set_ylabel("Amount ($M)", fontsize=dm.fs(0))
ax.set_title("Revenue vs Profit by Quarter", fontsize=dm.fs(1))
ax.legend(fontsize=dm.fs(-0.5), loc="upper left", framealpha=0.9)
ax.set_ylim(0, 200)

dm.simple_layout(fig)
plt.show()

# %%
# Triple-group comparison
# ------------------------
# Three series with offset labels for clarity.
regions = ["Americas", "EMEA", "APAC"]
fy23 = [340, 280, 190]
fy24 = [385, 310, 225]
fy25 = [420, 350, 265]

x = np.arange(len(regions))
w = 0.25

fig, ax = plt.subplots(
    figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300
)

ax.bar(x - w, fy23, w, label="FY2023", color="oc.blue3",
       edgecolor="white", linewidth=0.3)
ax.bar(x, fy24, w, label="FY2024", color="oc.blue5",
       edgecolor="white", linewidth=0.3)
ax.bar(x + w, fy25, w, label="FY2025 E", color="oc.blue7",
       edgecolor="white", linewidth=0.3)

ax.set_xticks(x)
ax.set_xticklabels(regions, fontsize=dm.fs(0))
ax.set_ylabel("Revenue ($M)", fontsize=dm.fs(0))
ax.set_title("Regional Revenue Comparison", fontsize=dm.fs(1))
ax.legend(fontsize=dm.fs(-0.5), loc="upper right", framealpha=0.9)
ax.set_ylim(0, 500)

# Add growth annotations with make_offset
for i in range(len(regions)):
    growth = (fy25[i] / fy23[i] - 1) * 100
    offset = dm.make_offset(0, 8, fig)
    ax.text(
        x[i] + w, fy25[i], f"+{growth:.0f}%",
        ha="center", va="bottom",
        fontsize=dm.fs(-1), color="oc.green7",
        fontweight="bold",
        transform=ax.transData + offset,
    )

dm.simple_layout(fig)
plt.show()
