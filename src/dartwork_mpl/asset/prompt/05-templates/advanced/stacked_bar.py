"""Stacked bar — advanced template (segment labels + totals above stack)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: stacked_bar
# use_case: Composition over 4 periods x 3 components with segment + total labels
# difficulty: intermediate
# data_shape: categories: list[str], components: dict[str, list[float]]
# tags: stacked-bar, composition, components, annotated, narrative
# narrative: Energy mix by period (Solar / Wind / Gas); totals annotated
# advanced_apis: cumulative bottom calc, per-segment label only if >= 8%, total label above each stack, dm.cspace
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

categories = ["P1", "P2", "P3", "P4"]
components = {
    "Solar": [82, 90, 101, 118],
    "Wind": [40, 45, 47, 55],
    "Gas": [28, 26, 22, 19],
}
component_names = list(components.keys())
totals = [
    sum(components[n][q] for n in component_names)
    for q in range(len(categories))
]

gradient = dm.cspace("dc.teal5", "dc.teal2", n=len(component_names))
colors = [c.to_hex() for c in gradient]

fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "standard"))

x = np.arange(len(categories))
bottom = np.zeros(len(categories))

for name, color in zip(component_names, colors, strict=False):
    vals = np.array(components[name])
    bars = ax.bar(
        x,
        vals,
        bottom=bottom,
        width=0.55,
        label=name,
        color=color,
        edgecolor="white",
        linewidth=0.3,
    )
    # In-segment label only if the segment is at least 8% of its stack.
    for q, (b, v) in enumerate(zip(bars, vals, strict=False)):
        share = v / totals[q]
        if share >= 0.08:
            ax.text(
                b.get_x() + b.get_width() / 2,
                bottom[q] + v / 2,
                f"{v:.0f}",
                ha="center",
                va="center",
                fontsize=dm.fs(-1),
                color="white",
                fontweight=dm.fw(1),
            )
    bottom += vals

# Total label above each stack.
for q, t in enumerate(totals):
    ax.text(
        x[q],
        t + 6,
        f"{t} MWh",
        ha="center",
        va="bottom",
        fontsize=dm.fs(-1),
        fontweight=dm.fw(1),
        color="oc.gray8",
    )

ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Generation (MWh)")
ax.set_xlabel("Period")
ax.set_ylim(0, max(totals) * 1.12)
dm.format_axis_si(ax, axis="y")

ax.legend(loc="upper left", fontsize=dm.fs(-1), frameon=False, ncol=3)

ax.set_title(
    "Solar share climbs to 60% of generation by P4",
    fontsize=dm.fs(1),
    fontweight=dm.fw(1),
    loc="left",
    pad=18,
)
ax.text(
    0.0,
    1.02,
    "Total annotated above each period; segment labels shown when ≥ 8% of stack.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=dm.fs(-1),
    color="oc.gray6",
)

fig.text(
    0.01,
    0.005,
    "Source: synthetic generation-mix model.",
    fontsize=dm.fs(-2),
    color="oc.gray5",
    ha="left",
    va="bottom",
)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i]
if issues:
    print(f"[stacked_bar-advanced] quality issues: {issues}")

dm.save_formats(fig, "stacked_bar_advanced")
