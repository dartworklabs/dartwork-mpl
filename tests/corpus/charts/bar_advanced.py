"""BEV share of new car sales in five markets against the EU 2030 target."""

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

import dartwork_mpl as dm

# 1. Style preset — switch to "report" / "presentation" / "*-kr" freely.
dm.style.use("scientific")

# 2. Real-world data with a story.
# Source (illustrative, near-2024 figures): IEA Global EV Outlook 2024
# https://www.iea.org/reports/global-ev-outlook-2024
countries = ["Norway", "Iceland", "Sweden", "China", "Germany"]
bev_share = [
    88.9,
    71.0,
    38.7,
    25.0,
    18.4,
]  # battery EV share of new car sales, %
eu_2030_target = 55.0  # EU CO2 fleet target implies ~55% BEV share by 2030

# 3. Steps of one family — colour encodes magnitude, the largest deepest.
bar_colors = ["dc.teal5", "dc.teal4", "dc.teal3", "dc.teal2", "dc.teal1"]

# 4. Figure — the preset's canvas for these bars; the names decide how
#    wide it is for them to stand flat.
fig, ax = plt.subplots(
    figsize=dm.figsize_for(
        n_points=len(countries), n_series=1, labels=countries
    )
)

# 5. Bars + per-bar value labels (annotation density carries the story).
#    dm.label_bars prints each value like the axis ticks (here "88.9%").
ax.bar(countries, bev_share, color=bar_colors, edgecolor="white", linewidth=0.3)
dm.label_bars(ax)

# 6. Reference threshold — EU 2030 mandate as a horizontal context line.
ax.axhline(
    eu_2030_target, linestyle="--", linewidth=0.5, color="dc.amber4", zorder=1
)
# Its label in the line's colour, darkened just enough to read (4.5:1).
ax.text(
    len(countries) - 0.5,
    eu_2030_target + 1.5,
    f"EU 2030 target ≈ {eu_2030_target:.0f}%",
    ha="right",
    va="bottom",
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast("dc.amber4", ax.get_facecolor()),
    fontstyle="italic",
)

# 7. Axes formatting — domain-aware (percent), no chart-junk.
ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
ax.set_ylim(0, 105)
ax.set_ylabel("BEV share of new car sales")
ax.set_xlabel("Market")

# No title, subtitle or source note: the caption or slide carries them.
# Add one only when the user asks for it.

# 8. Layout, after everything is drawn.
dm.simple_layout(fig)

dm.save_formats(fig, "output/bar_advanced", formats=("png",))
