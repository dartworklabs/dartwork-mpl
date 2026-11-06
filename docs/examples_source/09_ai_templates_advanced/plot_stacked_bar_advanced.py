"""
Stacked Bar (Advanced)
======================

Stacked bar — advanced template (segment labels + totals above stack).

Source: ``dartwork_mpl/asset/prompt/05-templates/advanced/stacked_bar.py`` ·
MCP ``dartwork-mpl://template/advanced/stacked_bar``.
"""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: stacked_bar
# use_case: Composition over 4 periods x 3 components with segment + total labels (dm.label_bars)
# difficulty: intermediate
# data_shape: categories: list[str], components: dict[str, list[float]]
# tags: stacked-bar, composition, components, annotated, narrative
# narrative: Energy mix by period (Solar / Wind / Gas); totals annotated
# advanced_apis: cumulative bottom calc, dm.label_bars (segment labels + stack totals), dm.cspace
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

gradient = dm.cspace("dc.teal5", "dc.teal2", n=len(component_names))
colors = [c.to_hex() for c in gradient]

fig, ax = plt.subplots(
    figsize=dm.figsize_for(
        n_points=len(categories), n_series=len(component_names)
    )
)

x = np.arange(len(categories))
bottom = np.zeros(len(categories))

for name, color in zip(component_names, colors, strict=False):
    vals = np.array(components[name])
    ax.bar(
        x,
        vals,
        bottom=bottom,
        width=0.55,
        label=name,
        color=color,
        edgecolor="white",
        linewidth=0.3,
    )
    bottom += vals

# Segment labels at each segment's middle and the stack total above each
# stack; the axis grows just enough to keep the totals inside.
dm.label_bars(ax)

ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Generation (MWh)")
ax.set_xlabel("Period")
dm.format_axis_si(ax, axis="y")

ax.legend(loc="upper left", fontsize=dm.fs(-1), frameon=False, ncol=3)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i]
if issues:
    print(f"[stacked_bar-advanced] quality issues: {issues}")

dm.save_formats(fig, "stacked_bar_advanced")
