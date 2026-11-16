"""A share price over 90 trading days on top of its volume bars, with a target line."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.ticker import FuncFormatter

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
ax_vol.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:g}"))
ax_vol.set_ylabel("Volume (k shares)")
ax_vol.set_ylim(0, volume.max() * 2.0)  # squeeze bars into the bottom third

# Price — drawn on top.
ax_price.plot(days, price, color=price_color, linewidth=dm.lw(0), zorder=3)
ax_price.set_ylabel("Price ($)")
ax_price.set_xlim(0, n - 1)
ax_price.set_zorder(ax_vol.get_zorder() + 1)
ax_price.patch.set_visible(False)  # transparent so volume bars show

# Target axhline.
ax_price.axhline(
    target, color="dc.amber5", linewidth=0.5, linestyle="--", zorder=2
)
ax_price.annotate(
    f"Target = ${target:.0f}",
    xy=(0, target),
    xycoords=("axes fraction", "data"),
    xytext=(0, 2),
    textcoords="offset points",
    ha="left",
    va="bottom",
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast("dc.amber5", ax_price.get_facecolor()),  # 4.5:1
    fontstyle="italic",
)

ax_price.set_xlabel("Trading day")

# Each y scale in its series' colour, against the axes background: spine and
# ticks at 3:1, tick labels and name at 4.5:1. The volume bars show at 55 %.
background = ax_price.get_facecolor()
for ax, side, shown in (
    (ax_price, "left", price_color),
    (ax_vol, "right", tuple(0.55 * c + 0.45 for c in to_rgb(vol_color))),
):
    line = dm.ensure_contrast(shown, background, min_ratio=3.0)
    text = dm.ensure_contrast(shown, background)
    ax.spines[side].set_color(line)
    ax.tick_params(axis="y", color=line, labelcolor=text)
    ax.yaxis.label.set_color(text)
# The twin draws its own copy of the left spine over the price axis's.
ax_vol.spines["left"].set_color(ax_price.spines["left"].get_edgecolor())

dm.simple_layout(fig)

dm.save_formats(fig, "output/twin_axis_advanced", formats=("png",))
