"""Twin axis — advanced template (price + volume with color-coded axes)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: twin_axis
# use_case: Two-y-scale chart (price + volume) with each axis color-coded to its data
# difficulty: advanced
# data_shape: x: list[float], y_price: list[float], y_volume: list[float]
# tags: twin-axis, price-volume, color-coded, narrative
# narrative: Daily price + volume; price target axhline on the left axis
# advanced_apis: ax.twinx (each axis takes its series colour from dartwork-mpl), axhline target, no chart-junk
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
n = 90
days = np.arange(n)
price = 100 + np.cumsum(rng.normal(0.18, 0.9, size=n))
volume = (
    rng.lognormal(mean=9.0, sigma=0.35, size=n) * (1 + 0.2 * np.sin(days / 8))
).astype(int)
target = 115.0

price_color = dm.color("dc.teal5").to_hex()
vol_color = dm.color("oc.gray5").to_hex()

fig, ax_price = plt.subplots(
    figsize=dm.figsize_for(n_points=n, n_series=2, dual_axis=True)
)
ax_vol = ax_price.twinx()

# Volume — drawn behind, lighter.
ax_vol.bar(
    days,
    volume,
    color=vol_color,
    edgecolor="white",
    linewidth=0.2,
    alpha=0.55,
    zorder=1,
)
# One unit for the axis, in its name: "Volume (k shares)" over plain ticks
# (0, 5, 10 …), not "Volume (shares)" over 5k, 10k.
dm.axis_unit(ax_vol, "y", label="Volume ({unit} shares)")
ax_vol.set_ylim(0, volume.max() * 2.0)  # squeeze bars into the bottom third

# Price — drawn on top.
ax_price.plot(days, price, color=price_color, linewidth=dm.lw(0), zorder=3)
ax_price.set_ylabel("Price ($)")
# Limits before the target label: dm.label_hline reads the line ends.
ax_price.set_xlim(0, n - 1)
ax_price.set_zorder(ax_vol.get_zorder() + 1)
ax_price.patch.set_visible(False)  # transparent so volume bars show

# Target axhline.
ax_price.axhline(
    target, color="dc.amber5", linewidth=0.5, linestyle="--", zorder=2
)
dm.label_hline(
    ax_price,
    target,
    f"Target = ${target:.0f}",
    x="left",
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast("dc.amber5", ax_price.get_facecolor()),  # 4.5:1
    fontstyle="italic",
)

ax_price.set_xlabel("Trading day")

dm.simple_layout(fig, margin=dm.inch(0.12))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "Missing" not in i]
if issues:
    print(f"[twin_axis-advanced] quality issues: {issues}")

dm.save_formats(fig, "twin_axis_advanced")
