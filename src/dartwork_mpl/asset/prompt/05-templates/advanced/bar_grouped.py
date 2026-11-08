"""Grouped bar — advanced template (per-bar labels + per-category totals)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: bar_grouped
# use_case: Multi-series quarterly comparison with per-bar value labels and per-category totals
# difficulty: intermediate
# data_shape: categories: list[str], series: dict[str, list[float]]
# tags: bar, grouped, multi-series, annotated, narrative
# narrative: Throughput by zone across four periods (Plant / Lab / Field) — totals annotated
# advanced_apis: dm.label_bars per bar, total annotation above each group, format_axis_si, legend frameon=False
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["P1", "P2", "P3", "P4"]
series = {
    "Plant": [120, 135, 152, 178],
    "Lab": [88, 92, 101, 109],
    "Field": [54, 48, 52, 55],
}
series_names = list(series.keys())
gradient = dm.cspace("dc.teal5", "dc.teal2", n=len(series_names))
colors = [c.to_hex() for c in gradient]

x = np.arange(len(categories))
bar_width = 0.26

fig, ax = plt.subplots(
    figsize=dm.figsize_for(
        "grouped", n_points=len(categories), n_series=len(series_names)
    )
)

for i, name in enumerate(series_names):
    offset = (i - 1) * bar_width
    vals = series[name]
    ax.bar(
        x + offset,
        vals,
        bar_width,
        label=name,
        color=colors[i],
        edgecolor="white",
        linewidth=0.3,
    )

# Per-bar value labels. dm.label_bars has no per-group total, so the
# totals below stay hand-placed.
dm.label_bars(ax)

# Per-category total at its own height on the value axis: a total is
# at least its tallest bar plus the others, so it sits clear of the bar
# labels (turned upright on a narrow slide too). Two short lines keep
# neighbouring totals apart; the axis leaves room above the largest.
totals = [
    sum(series[n][q] for n in series_names) for q in range(len(categories))
]
for q, total in enumerate(totals):
    ax.text(
        x[q],
        total,
        f"Total\n{total}",
        ha="center",
        va="bottom",
        fontsize=dm.fs(-1),
        fontweight=dm.fw(1),
    )

ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Throughput (units)")
ax.set_xlabel("Period")
ax.set_ylim(0, max(totals) * 1.2)
dm.format_axis_si(ax, axis="y")

dm.place_legend(ax, fontsize=dm.fs(-1), frameon=False)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i]
if issues:
    print(f"[bar_grouped-advanced] quality issues: {issues}")

dm.save_formats(fig, "bar_grouped_advanced")
