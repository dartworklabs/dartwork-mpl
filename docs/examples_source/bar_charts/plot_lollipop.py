"""
Lollipop Charts
===============

Swap solid bars for stems and dots to lighten dense comparisons while keeping precise positions.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# Apply presentation style for web docs
dm.style.use("presentation")

# Sample data
categories = ["A", "B", "C", "D", "E", "F", "G"]
values1 = np.array([23, 45, 56, 33, 41, 38, 29])
values2 = np.array([28, 38, 48, 35, 43, 32, 31])

# Create figure
# Double column figure: 17cm width, 2x2 layout
fig = plt.figure(figsize=(dm.cm2in(16), dm.cm2in(12)), dpi=300)

# Create GridSpec for 2x2 subplots
gs = fig.add_gridspec(
    nrows=2,
    ncols=2,
    left=0.12,
    right=0.98,
    top=0.95,
    bottom=0.08,
    wspace=0.4,
    hspace=0.5,
)

# Panel A: Basic lollipop chart (vertical)
ax1 = fig.add_subplot(gs[0, 0])
x_pos = np.arange(len(categories))
ax1.stem(x_pos, values1, linefmt="oc.blue5", markerfmt="o", basefmt=" ")
# Customize stem lines and markers
markerline, stemlines, baseline = ax1.stem(x_pos, values1, basefmt=" ")
plt.setp(stemlines, "color", "oc.blue5", "linewidth", 0.7)
plt.setp(
    markerline,
    "color",
    "oc.blue7",
    "markersize",
    5,
    "markerfacecolor",
    "oc.blue5",
    "markeredgewidth",
    0.5,
)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(categories, fontsize=dm.fs(-1))
ax1.set_ylabel("Value", fontsize=dm.fs(0))
ax1.set_title("Basic Lollipop", fontsize=dm.fs(1))
ax1.set_yticks([0, 20, 40, 60])

# Panel B: Horizontal lollipop chart
ax2 = fig.add_subplot(gs[0, 1])
y_pos = np.arange(len(categories))
ax2.hlines(y=y_pos, xmin=0, xmax=values1, color="oc.red5", linewidth=0.7)
ax2.plot(
    values1,
    y_pos,
    "o",
    color="oc.red7",
    markersize=5,
    markerfacecolor="oc.red5",
    markeredgewidth=0.5,
)
ax2.set_yticks(y_pos)
ax2.set_yticklabels(categories, fontsize=dm.fs(-1))
ax2.set_xlabel("Value", fontsize=dm.fs(0))
ax2.set_title("Horizontal Lollipop", fontsize=dm.fs(1))
ax2.set_xticks([0, 20, 40, 60])

# Panel C: Sorted lollipop chart
ax3 = fig.add_subplot(gs[1, 0])
sorted_idx = np.argsort(values1)
sorted_values = values1[sorted_idx]
sorted_cats = [categories[i] for i in sorted_idx]
y_pos_sorted = np.arange(len(sorted_cats))
ax3.hlines(
    y=y_pos_sorted, xmin=0, xmax=sorted_values, color="oc.green5", linewidth=0.7
)
ax3.plot(
    sorted_values,
    y_pos_sorted,
    "o",
    color="oc.green7",
    markersize=5,
    markerfacecolor="oc.green5",
    markeredgewidth=0.5,
)
ax3.set_yticks(y_pos_sorted)
ax3.set_yticklabels(sorted_cats, fontsize=dm.fs(-1))
ax3.set_xlabel("Value", fontsize=dm.fs(0))
ax3.set_title("Sorted Lollipop", fontsize=dm.fs(1))
ax3.set_xticks([0, 20, 40, 60])

# Panel D: Comparison lollipop chart
ax4 = fig.add_subplot(gs[1, 1])
y_pos_comp = np.arange(len(categories))
# Draw lines connecting the two values
for i, (v1, v2) in enumerate(zip(values1, values2, strict=False)):
    ax4.plot(
        [v1, v2], [i, i], "o-", color="oc.gray5", linewidth=0.5, markersize=0
    )
# Draw lollipops
ax4.plot(
    values1,
    y_pos_comp,
    "o",
    color="oc.blue7",
    markersize=5,
    markerfacecolor="oc.blue5",
    markeredgewidth=0.5,
    label="Group A",
)
ax4.plot(
    values2,
    y_pos_comp,
    "s",
    color="oc.red7",
    markersize=4,
    markerfacecolor="oc.red5",
    markeredgewidth=0.5,
    label="Group B",
)
ax4.set_yticks(y_pos_comp)
ax4.set_yticklabels(categories, fontsize=dm.fs(-1))
ax4.set_xlabel("Value", fontsize=dm.fs(0))
ax4.set_title("Comparison Lollipop", fontsize=dm.fs(1))
ax4.legend(loc="upper right", fontsize=dm.fs(-1))
ax4.set_xticks([0, 20, 40, 60])

for ax in (ax1, ax2, ax3, ax4):
    ax.margins(x=0.05, y=0.05)

# Optimize layout
dm.simple_layout(fig, gs=gs)

# Save and show plot
plt.show()
