"""Horizontal bar — advanced template (top-1 highlight + median reference)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: bar_horizontal
# use_case: Ranked categories with #1 highlighted in accent color and a median reference axvline
# difficulty: intermediate
# data_shape: categories: list[str], values: list[float]
# tags: bar, horizontal, ranking, reference-line, highlight, narrative
# narrative: Top-8 metro housing-price indices; SF leads, axvline at median
# advanced_apis: per-bar value labels at end of bar, axvline at median, top-1 accent color, sorted descending, format_axis_si
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# Synthetic top-8 metro indices, sorted descending.
data = [
    ("SF", 412),
    ("SEA", 348),
    ("BOS", 301),
    ("DEN", 287),
    ("AUS", 265),
    ("CHI", 198),
    ("PHX", 182),
    ("DET", 128),
]
data.sort(key=lambda r: r[1], reverse=True)
categories = [r[0] for r in data]
values = np.array([r[1] for r in data])
median = float(np.median(values))

# Color rule — top-1 gets the accent, the rest a uniform muted blue.
accent = dm.color("dc.earth5").to_hex()
default = dm.color("dc.corporate3").to_hex()
colors = [accent if v == values.max() else default for v in values]

fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "standard"))

bars = ax.barh(
    categories, values, color=colors, edgecolor="white", linewidth=0.3
)
ax.invert_yaxis()  # rank 1 at top

# End-of-bar value labels.
for b, v in zip(bars, values, strict=False):
    ax.text(
        v + 6,
        b.get_y() + b.get_height() / 2,
        f"{v}",
        va="center",
        ha="left",
        fontsize=dm.fs(-1),
        fontweight=dm.fw(1),
        color="oc.gray8",
    )

# Median axvline reference.
ax.axvline(median, color="oc.gray5", linewidth=0.5, linestyle="--", zorder=1)
ax.text(
    median + 4,
    -0.4,
    f"Median = {median:.0f}",
    fontsize=dm.fs(-1),
    color="oc.gray6",
    fontstyle="italic",
    ha="left",
    va="bottom",
)

ax.set_xlim(0, values.max() * 1.12)
ax.set_xlabel("Index value")
dm.format_axis_si(ax, axis="x")

ax.set_title(
    "SF leads the index — 3.2x over Detroit",
    fontsize=dm.fs(1),
    fontweight=dm.fw(1),
    loc="left",
    pad=18,
)
ax.text(
    0.0,
    1.02,
    "Top-8 metros (3-letter codes); dashed line marks the cohort median.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=dm.fs(-1),
    color="oc.gray6",
)

fig.text(
    0.01,
    0.005,
    "Source: synthetic metro index panel.",
    fontsize=dm.fs(-2),
    color="oc.gray5",
    ha="left",
    va="bottom",
)

dm.simple_layout(fig, margin=dm.inch(0.35))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
if issues:
    print(f"[bar_horizontal-advanced] quality issues: {issues}")

dm.save_formats(fig, "bar_horizontal_advanced")
