"""Scatter — advanced template (regression line + R² + outlier highlight)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: scatter
# use_case: Two-variable relationship with regression fit, R-squared annotation, and outlier callout
# difficulty: intermediate
# data_shape: x: list[float], y: list[float]
# tags: scatter, correlation, regression, outlier, annotated, narrative
# narrative: Price vs. demand fit across 60 SKUs; one outlier flagged
# advanced_apis: np.polyfit, np.corrcoef, ax.annotate, axhline, dm.format_axis_currency, dm.validate_with_fixes
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# Synthetic price vs. demand with one obvious outlier (SKU #47).
rng = np.random.default_rng(42)
n = 60
price = rng.uniform(8, 42, size=n)
demand = 220 - 3.4 * price + rng.normal(0, 14, size=n)

# Plant an outlier well above the trend.
outlier_idx = 47
price[outlier_idx] = 32.0
demand[outlier_idx] = 240.0

# Linear fit + R-squared (excluding the outlier so the line tells the
# "normal" story; the outlier then becomes obviously off-trend).
mask = np.arange(n) != outlier_idx
slope, intercept = np.polyfit(price[mask], demand[mask], 1)
fit_line = slope * np.sort(price) + intercept
r = np.corrcoef(price[mask], demand[mask])[0, 1]
r_squared = r * r

# How far the outlier sits above the fitted line, in %, computed from the
# data so the subtitle can never drift from what is actually plotted.
_outlier_fit = slope * price[outlier_idx] + intercept
outlier_pct = (demand[outlier_idx] - _outlier_fit) / _outlier_fit * 100

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "square"))

# Cloud — semi-transparent so the line shows through.
ax.scatter(
    price[mask],
    demand[mask],
    s=18,
    color="dc.teal3",
    edgecolor="white",
    linewidth=0.3,
    alpha=0.85,
    label="SKU sample",
)

# Outlier — distinct color + marker.
ax.scatter(
    price[outlier_idx],
    demand[outlier_idx],
    s=70,
    color="dc.earth5",
    edgecolor="white",
    linewidth=0.5,
    marker="D",
    zorder=5,
    label="Outlier SKU",
)

# Regression line — drawn on top of the cloud, under the outlier.
ax.plot(
    np.sort(price), fit_line, color="dc.teal5", linewidth=dm.lw(0), zorder=4
)

# R-squared annotation in the upper-left, inside the axes.
ax.text(
    0.04,
    0.96,
    f"$R^2 = {r_squared:.2f}$\n$\\beta = {slope:.1f}$ units / \\$",
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=dm.fs(-1),
    color="oc.gray7",
    bbox={
        "boxstyle": "round,pad=0.3",
        "fc": "white",
        "ec": "oc.gray3",
        "lw": 0.3,
    },
)

# Outlier callout with arrow.
ax.annotate(
    "SKU #47:\nprice cut\nbut volume\ndidn't follow",
    xy=(price[outlier_idx], demand[outlier_idx]),
    xytext=(price[outlier_idx] + 5, demand[outlier_idx] + 25),
    fontsize=dm.fs(-1),
    color="dc.earth5",
    arrowprops={"arrowstyle": "->", "color": "dc.earth5", "lw": 0.5},
)

dm.format_axis_currency(ax, axis="x", symbol="$", decimals=0)
ax.set_xlabel("Unit price")
ax.set_ylabel("Weekly units sold")
ax.legend(loc="lower left", fontsize=dm.fs(-1), frameon=False)

ax.set_title(
    "Demand falls cleanly with price — except one SKU",
    fontsize=dm.fs(1),
    fontweight=dm.fw(1),
    loc="left",
    pad=18,
)
ax.text(
    0.0,
    1.02,
    f"60-SKU cross-section; the diamond marker sits "
    f"{outlier_pct:.0f}% above the fitted line.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=dm.fs(-1),
    color="oc.gray6",
)

fig.text(
    0.01,
    0.005,
    "Source: synthetic 60-SKU cross-section (rng seed 42).",
    fontsize=dm.fs(-2),
    color="oc.gray5",
    ha="left",
    va="bottom",
)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
if issues:
    print(f"[scatter-advanced] quality issues: {issues}")

dm.save_formats(fig, "scatter_advanced")
