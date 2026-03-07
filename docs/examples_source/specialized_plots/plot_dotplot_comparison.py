"""
Dot-Plot Comparison
===================

Show a comparison between two cohorts using dot markers connected by horizontal
tracks.  Each row represents a category; the gap between dots highlights
which group scores higher.
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import dartwork_mpl as dm

dm.style.use("scientific")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
categories = [
    "Automated Customer Support",
    "Predictive Maintenance",
    "Supply Chain Optimization",
    "Fraud Detection",
    "Personalized Marketing",
    "Talent Acquisition",
    "Financial Forecasting",
    "Cybersecurity Threat Detection",
    "Legal Document Review",
]

success_values = np.array([64, 58, 57, 54, 51, 49, 45, 43, 42], dtype=float)
other_values = np.array([20, 23, 24, 25, 26, 28, 26, 25, 24], dtype=float)
multiples = [f"{s / o:.1f}×" for s, o in zip(success_values, other_values, strict=False)]


# ---------------------------------------------------------------------------
# Layout config
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Layout:
    left: float = 0.3
    right: float = 0.95
    top: float = 0.87
    bottom: float = 0.1
    fig_w: float = 13
    fig_h: float = 9


@dataclass(frozen=True)
class Palette:
    other: str = "oc.green7"
    success: str = "oc.green3"
    track_bg: str = "oc.gray4"
    track_fg: str = "oc.gray2"


lo = Layout()
pal = Palette()
track_lw = dm.lw(10)
y_pos = np.arange(len(categories))


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(dm.cm2in(lo.fig_w), dm.cm2in(lo.fig_h)), dpi=300)
gs = fig.add_gridspec(1, 1, left=lo.left, right=lo.right, top=lo.top, bottom=lo.bottom)
ax = fig.add_subplot(gs[0, 0])

# Background tracks
for i, (ov, sv) in enumerate(zip(other_values, success_values, strict=False)):
    ax.hlines(i, 0, ov, lw=track_lw, color=pal.track_bg, zorder=1)
    ax.hlines(i, ov, sv, lw=track_lw, color=pal.track_fg, zorder=1)

# Markers
ax.plot(other_values, y_pos, "o", ms=track_lw, ls="none", color=pal.other, zorder=2)
ax.plot(success_values, y_pos, "o", ms=track_lw, ls="none", color=pal.success, zorder=3)

# Multiples annotation
for i, (sv, m) in enumerate(zip(success_values, multiples, strict=False)):
    ax.text(sv + 3, i, m, va="center", ha="left", fontsize=dm.fs(-1))

# Axes
ax.set_yticks(y_pos)
ax.set_yticklabels(categories, fontsize=dm.fs(0))
ax.invert_yaxis()
ax.tick_params(axis="y", length=0, pad=4)
ax.set_xlabel("Result of transformation [%]", loc="center", fontsize=dm.fs(1))
ax.set_xlim(0, 80)
ax.set_ylim(len(categories) - 0.5, -0.5)
ax.xaxis.grid(True, ls=":", which="major", color="gray", alpha=0.3)
ax.set_axisbelow(True)
for sp in ax.spines.values():
    sp.set_edgecolor("oc.gray6")

# Title and legend
fig.text(0.02, 0.95, "AI Adoption Gap: AI-First vs. Traditional Companies",
         fontsize=dm.fs(2), fontweight=dm.fw(1), ha="left")

legend_elements = [
    Line2D([0], [0], marker="o", color="w", label="Other organizations",
           markerfacecolor=pal.other, ms=8),
    Line2D([0], [0], marker="o", color="w", label="Successfully transformed",
           markerfacecolor=pal.success, ms=8),
]
ax.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1, 1.13),
          ncol=2, frameon=False, fontsize=dm.fs(-1), columnspacing=1.5)

plt.show()
