"""
Grouped Bar Chart
=================

Lay out grouped bars with shared baselines, tuned spacing, and legends that scale to many categories.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply presentation style for web docs
# Default: font.size=7.5, lines.linewidth=0.5, axes.linewidth=0.3
dm.style.use("presentation")

# Sample data
categories = ["Q1", "Q2", "Q3", "Q4"]
group1 = np.array([20, 25, 30, 25])
group2 = np.array([15, 20, 25, 20])
group3 = np.array([10, 15, 20, 15])

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
    wspace=0.4,
    hspace=0.5,
)

# Panel A: Basic grouped bars
ax1 = fig.add_subplot(gs[0, 0])
x_pos = np.arange(len(categories))
width = 0.25
# Explicit parameters: width=0.25, alpha=0.7, edgecolor, linewidth=0.3
bars1a = ax1.bar(
    x_pos - width,
    group1,
    width,
    color="oc.blue5",
    alpha=0.7,
    edgecolor="oc.blue7",
    linewidth=0.3,
    label="Group A",
)
bars1b = ax1.bar(
    x_pos,
    group2,
    width,
    color="oc.red5",
    alpha=0.7,
    edgecolor="oc.red7",
    linewidth=0.3,
    label="Group B",
)
bars1c = ax1.bar(
    x_pos + width,
    group3,
    width,
    color="oc.green5",
    alpha=0.7,
    edgecolor="oc.green7",
    linewidth=0.3,
    label="Group C",
)
ax1.set_xlabel("Quarter", fontsize=dm.fs(0))
ax1.set_ylabel("Value", fontsize=dm.fs(0))
ax1.set_title("Basic Grouped Bars", fontsize=dm.fs(1))
ax1.set_xticks(x_pos)
ax1.set_xticklabels(categories, fontsize=dm.fs(-1))
ax1.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax1.set_yticks([0, 10, 20, 30])

# Panel B: Grouped bars with value labels
ax2 = fig.add_subplot(gs[0, 1])
# Explicit parameters: width=0.25, alpha=0.7
bars2a = ax2.bar(
    x_pos - width,
    group1,
    width,
    color="oc.blue5",
    alpha=0.7,
    edgecolor="oc.blue7",
    linewidth=0.3,
    label="Group A",
)
bars2b = ax2.bar(
    x_pos,
    group2,
    width,
    color="oc.red5",
    alpha=0.7,
    edgecolor="oc.red7",
    linewidth=0.3,
    label="Group B",
)
bars2c = ax2.bar(
    x_pos + width,
    group3,
    width,
    color="oc.green5",
    alpha=0.7,
    edgecolor="oc.green7",
    linewidth=0.3,
    label="Group C",
)
# Add value labels: fontsize=dm.fs(-2), padding=2
ax2.bar_label(bars2a, padding=2, fontsize=dm.fs(-2))
ax2.bar_label(bars2b, padding=2, fontsize=dm.fs(-2))
ax2.bar_label(bars2c, padding=2, fontsize=dm.fs(-2))
ax2.set_xlabel("Quarter", fontsize=dm.fs(0))
ax2.set_ylabel("Value", fontsize=dm.fs(0))
ax2.set_title("With Value Labels", fontsize=dm.fs(1))
ax2.set_xticks(x_pos)
ax2.set_xticklabels(categories, fontsize=dm.fs(-1))
ax2.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax2.set_yticks([0, 10, 20, 30])

# Panel C: Custom spacing
ax3 = fig.add_subplot(gs[1, 0])
# Custom spacing: width=0.2, spacing between groups
width_custom = 0.2
spacing = 0.1
x_pos_custom = np.arange(len(categories)) * (width_custom * 3 + spacing)
# Explicit parameters: width=0.2, alpha=0.7
bars3a = ax3.bar(
    x_pos_custom - width_custom,
    group1,
    width_custom,
    color="oc.blue5",
    alpha=0.7,
    edgecolor="oc.blue7",
    linewidth=0.3,
    label="Group A",
)
bars3b = ax3.bar(
    x_pos_custom,
    group2,
    width_custom,
    color="oc.red5",
    alpha=0.7,
    edgecolor="oc.red7",
    linewidth=0.3,
    label="Group B",
)
bars3c = ax3.bar(
    x_pos_custom + width_custom,
    group3,
    width_custom,
    color="oc.green5",
    alpha=0.7,
    edgecolor="oc.green7",
    linewidth=0.3,
    label="Group C",
)
ax3.set_xlabel("Quarter", fontsize=dm.fs(0))
ax3.set_ylabel("Value", fontsize=dm.fs(0))
ax3.set_title("Custom Spacing", fontsize=dm.fs(1))
ax3.set_xticks(x_pos_custom)
ax3.set_xticklabels(categories, fontsize=dm.fs(-1))
ax3.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax3.set_yticks([0, 10, 20, 30])

# Panel D: Grouped bars with error bars
ax4 = fig.add_subplot(gs[1, 1])
# Error values
errors1 = np.array([2, 1.5, 2.5, 2])
errors2 = np.array([1.5, 2, 1.5, 1.5])
errors3 = np.array([1, 1.5, 2, 1.5])
# Explicit parameters: width=0.25, alpha=0.7, capsize=2
bars4a = ax4.bar(
    x_pos - width,
    group1,
    width,
    color="oc.blue5",
    alpha=0.7,
    edgecolor="oc.blue7",
    linewidth=0.3,
    label="Group A",
    yerr=errors1,
    capsize=2,
    error_kw={"linewidth": 0.5},
)
bars4b = ax4.bar(
    x_pos,
    group2,
    width,
    color="oc.red5",
    alpha=0.7,
    edgecolor="oc.red7",
    linewidth=0.3,
    label="Group B",
    yerr=errors2,
    capsize=2,
    error_kw={"linewidth": 0.5},
)
bars4c = ax4.bar(
    x_pos + width,
    group3,
    width,
    color="oc.green5",
    alpha=0.7,
    edgecolor="oc.green7",
    linewidth=0.3,
    label="Group C",
    yerr=errors3,
    capsize=2,
    error_kw={"linewidth": 0.5},
)
ax4.set_xlabel("Quarter", fontsize=dm.fs(0))
ax4.set_ylabel("Value", fontsize=dm.fs(0))
ax4.set_title("With Error Bars", fontsize=dm.fs(1))
ax4.set_xticks(x_pos)
ax4.set_xticklabels(categories, fontsize=dm.fs(-1))
ax4.legend(loc="upper right", fontsize=dm.fs(-1), ncol=1)
ax4.set_yticks([0, 10, 20, 30, 40])

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Save and show plot
plt.show()
