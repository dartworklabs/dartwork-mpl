"""Pie / donut — advanced template (gradient + explode + leader callout)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: pie
# use_case: Composition share with leader explode + callout + OKLCH gradient + donut hole
# difficulty: intermediate
# data_shape: labels: list[str], sizes: list[float]
# tags: pie, donut, composition, callout, narrative
# narrative: GPU vendor market share; leader exploded and called out
# advanced_apis: dm.cspace gradient, wedge explode, donut hole (wedgeprops width), ax.annotate leader callout
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

labels = ["NVIDIA", "AMD", "Intel Arc", "Apple", "Others"]
sizes = np.array([62.0, 17.0, 8.0, 7.0, 6.0])  # %

# OKLCH gradient — deeper for the leader, lighter for trailing share.
gradient = dm.cspace("dc.teal5", "dc.teal1", n=len(labels))
colors = [c.to_hex() for c in gradient]

# Explode only the leader.
explode = np.zeros(len(labels))
explode[0] = 0.08

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "square"))

wedges, texts, autotexts = ax.pie(
    sizes,
    labels=labels,
    colors=colors,
    autopct="%1.0f%%",
    startangle=90,
    explode=explode,
    pctdistance=0.78,
    wedgeprops={"edgecolor": "white", "linewidth": 0.5, "width": 0.38},
    textprops={"fontsize": dm.fs(-1)},
)
for t in autotexts:
    t.set_color("white")
    t.set_fontweight("bold")

ax.set_aspect("equal")

# Leader callout — anchor at the leader wedge center.
leader = wedges[0]
theta = np.deg2rad((leader.theta1 + leader.theta2) / 2)
x, y = np.cos(theta) * 1.1, np.sin(theta) * 1.1
ax.annotate(
    f"{labels[0]}\nholds {sizes[0]:.0f}% — 3.6x #2",
    xy=(np.cos(theta) * 0.9, np.sin(theta) * 0.9),
    xytext=(x + 0.4, y + 0.2),
    fontsize=dm.fs(-1),
    color=colors[0],
    arrowprops={"arrowstyle": "-", "color": colors[0], "lw": 0.5},
)

ax.set_title(
    "NVIDIA still holds a 3.6x lead in discrete GPU share",
    fontsize=dm.fs(1),
    fontweight=dm.fw(1),
    loc="left",
    pad=18,
)
ax.text(
    0.0,
    1.02,
    "Synthetic 2025 snapshot — gradient depth mirrors share rank.",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=dm.fs(-1),
    color="oc.gray6",
)

fig.text(
    0.01,
    0.005,
    "Source: synthetic GPU share snapshot.",
    fontsize=dm.fs(-2),
    color="oc.gray5",
    ha="left",
    va="bottom",
)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
# Pie has no x/y axes; quality checker flags missing labels as a
# false positive — filter the structural ones for this geometry.
issues = [i for i in issues if "Missing" not in i and "No data" not in i]
if issues:
    print(f"[pie-advanced] quality issues: {issues}")

dm.save_formats(fig, "pie_advanced")
