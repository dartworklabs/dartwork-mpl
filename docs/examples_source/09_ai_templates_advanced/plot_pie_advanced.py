"""
Pie (Advanced)
==============

Pie / donut — advanced template (gradient + explode + leader callout).

Source: ``dartwork_mpl/asset/prompt/05-templates/advanced/pie.py`` ·
MCP ``dartwork-mpl://template/advanced/pie``.
"""

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

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))

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
# Each share in white or black, whichever reads on its wedge.
for t, wedge in zip(autotexts, wedges, strict=True):
    t.set_color(dm.readable_text_color(wedge.get_facecolor()))
    t.set_fontweight(dm.fw(1))

ax.set_aspect("equal")

# Leader callout — anchor at the leader wedge center.
leader = wedges[0]
theta = np.deg2rad((leader.theta1 + leader.theta2) / 2)
x, y = np.cos(theta) * 1.1, np.sin(theta) * 1.1
ax.annotate(
    f"{labels[0]}\nholds {sizes[0]:.0f}%\n3.6x #2",
    xy=(np.cos(theta) * 0.9, np.sin(theta) * 0.9),
    xytext=(x + 0.4, y + 0.2),
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast(colors[0], ax.get_facecolor()),  # 4.5:1 text
    arrowprops={"arrowstyle": "-", "color": colors[0], "lw": 0.5},
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
