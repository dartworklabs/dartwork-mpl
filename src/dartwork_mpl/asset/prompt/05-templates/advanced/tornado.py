"""Tornado — advanced template (two-sided sensitivity with baseline)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: tornado
# use_case: Parameter sensitivity ranking with two-sided bars colored by direction of output impact
# difficulty: intermediate
# data_shape: variables: list[str], low_impact: list[float], high_impact: list[float]
# tags: tornado, sensitivity, two-sided, ranking, narrative
# narrative: Six model parameters ranked by absolute impact on output; output drops red, output rises green
# advanced_apis: horizontal bars at axvline x=0, color by sign of effect, dm.label_bars signed value labels
# ai-template-meta-end

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# (variable, low_scenario_impact, high_scenario_impact) — impact on model output.
# For parameters where higher input drives output down, the pair is flipped.
data = [
    ("Growth", -22.0, +28.0),
    ("Yield", -18.5, +21.0),
    ("Friction", +14.0, -16.5),
    ("Drift", -11.0, +13.0),
    ("Decay", +9.0, -10.5),
    ("Noise", +6.5, -7.5),
]
data.sort(key=lambda r: max(abs(r[1]), abs(r[2])), reverse=True)
variables = [r[0] for r in data]
low = np.array([r[1] for r in data])
high = np.array([r[2] for r in data])

pos_color = dm.color("dc.green5").to_hex()
neg_color = dm.color("dc.amber5").to_hex()

fig, ax = plt.subplots(
    figsize=dm.figsize_for("barh", n_points=len(variables), n_series=2)
)
ys = np.arange(len(variables))

# Color by sign of output impact — green = output rises, red = output drops.
for y_pos, lo, hi in zip(ys, low, high, strict=False):
    ax.barh(
        y_pos,
        lo,
        color=(pos_color if lo >= 0 else neg_color),
        edgecolor="white",
        linewidth=0.3,
    )
    ax.barh(
        y_pos,
        hi,
        color=(pos_color if hi >= 0 else neg_color),
        edgecolor="white",
        linewidth=0.3,
    )

ax.axvline(0, color="oc.gray7", linewidth=0.5, zorder=3)

# Signed value labels on the outer end of each bar. The low and high bar of
# a row stand together, so ask for plain labels (no per-row net total).
dm.label_bars(ax, where="outside", total=False, fmt=lambda v: f"{v:+.1f}%")

ax.set_yticks(ys)
ax.set_yticklabels(variables)
ax.invert_yaxis()
ax.set_xlabel("Impact on model output (%)")
# Symmetric limits around the zero line (a stated choice, so they stay),
# with room at both ends for the outer labels.
xmax = max(abs(low).max(), abs(high).max()) * 1.20
ax.set_xlim(-xmax, xmax)

handles = [
    mpatches.Patch(
        facecolor=pos_color, edgecolor="white", label="Output rises"
    ),
    mpatches.Patch(
        facecolor=neg_color, edgecolor="white", label="Output drops"
    ),
]
ax.legend(
    handles=handles,
    loc="lower right",
    bbox_to_anchor=(1.0, 1.0),
    ncol=2,
    fontsize=dm.fs(-1),
    frameon=False,
)

dm.simple_layout(fig, margin=dm.inch(0.45))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i]
if issues:
    print(f"[tornado-advanced] quality issues: {issues}")

dm.save_formats(fig, "tornado_advanced")
