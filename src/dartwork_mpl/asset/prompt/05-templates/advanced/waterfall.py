"""Waterfall — advanced template (cumulative bridge with connectors)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: waterfall
# use_case: Cumulative bridge from one total to another via signed components, with connector lines
# difficulty: advanced
# data_shape: labels: list[str], values: list[float], is_total: list[bool]
# tags: waterfall, bridge, cumulative, annotated, narrative
# narrative: Energy bridge from generation to net delivery; positives green, negatives red, totals gray
# advanced_apis: signed step bars from the running level, sign-color, dashed connector lines, dm.label_bars(sign="+", color="series")
# ai-template-meta-end

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# (label, delta_value, is_total)
# Totals sit at fixed positions; deltas accumulate between them.
items = [
    ("Generated", 1200, True),
    ("Line loss", -280, False),
    ("Self-use", -240, False),
    ("Storage charge", -85, False),
    ("Net to grid", 595, True),
    ("Conversion", -45, False),
    ("Tariff", -110, False),
    ("Delivered", 440, True),
]
labels = [i[0] for i in items]
values = np.array([i[1] for i in items], dtype=float)
is_total = np.array([i[2] for i in items])

# The level after each bar: a total resets it; a step moves it by its
# signed delta. A step is drawn from the level before it with its signed
# delta as the height, so each bar holds its delta and dm.label_bars
# prints it, a fall below its bar.
level = np.zeros(len(items))
running = 0.0
for i, (value, total) in enumerate(zip(values, is_total, strict=True)):
    running = value if total else running + value
    level[i] = running
xs = np.arange(len(items))
step = ~is_total

pos_color = dm.color("dc.green5").to_hex()
neg_color = dm.color("dc.amber5").to_hex()
tot_color = dm.color("oc.gray6").to_hex()

fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=len(items), n_series=1))

totals = ax.bar(
    xs[is_total],
    level[is_total],
    color=tot_color,
    edgecolor="white",
    linewidth=0.3,
    width=0.7,
)
steps = ax.bar(
    xs[step],
    values[step],
    bottom=(level - values)[step],
    color=[pos_color if v >= 0 else neg_color for v in values[step]],
    edgecolor="white",
    linewidth=0.3,
    width=0.7,
)

# Dashed connector at each bar's closing level to the next bar.
for i in range(len(items) - 1):
    ax.plot(
        [xs[i] + 0.35, xs[i + 1] - 0.35],
        [level[i], level[i]],
        color="oc.gray5",
        linewidth=0.5,
        linestyle="--",
        zorder=1,
    )

# Value labels: steps signed in their bar's colour, totals plain.
dm.label_bars(ax, steps, sign="+", color="series")
dm.label_bars(ax, totals)

ax.set_xticks(xs)
ax.set_xticklabels(labels, rotation=30, ha="right")
ax.set_ylabel("Energy (MWh)")
ax.set_ylim(0, max(level) * 1.15)

# Legend via proxy patches.
handles = [
    mpatches.Patch(
        facecolor=pos_color, edgecolor="white", label="Positive delta"
    ),
    mpatches.Patch(
        facecolor=neg_color, edgecolor="white", label="Negative delta"
    ),
    mpatches.Patch(facecolor=tot_color, edgecolor="white", label="Subtotal"),
]
ax.legend(handles=handles, loc="upper right", fontsize=dm.fs(-1), frameon=False)

dm.simple_layout(fig, margin=dm.inch(0.12))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i]
if issues:
    print(f"[waterfall-advanced] quality issues: {issues}")

dm.save_formats(fig, "waterfall_advanced")
