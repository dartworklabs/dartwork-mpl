"""Sensitivity of a model output to six inputs as a tornado with signed labels."""

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

# Signed value labels on the outer end of each bar, with a true minus sign
# (U+2212) like the axis ticks.
for bars in ax.containers:
    ax.bar_label(
        bars,
        fmt=lambda v: f"{v:+.1f}%".replace("-", "\u2212"),
        padding=2,
        fontsize=dm.fs(-1),
        fontweight=dm.fw(1),
    )

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

dm.simple_layout(fig)

dm.save_formats(fig, "output/tornado_advanced", formats=("png",))
