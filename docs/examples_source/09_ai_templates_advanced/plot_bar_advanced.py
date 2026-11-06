"""
Bar (Advanced)
==============

Vertical bar chart — advanced template (real data + narrative).

Source: ``dartwork_mpl/asset/prompt/05-templates/advanced/bar.py`` ·
MCP ``dartwork-mpl://template/advanced/bar``.
"""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: bar
# use_case: Rank a small categorical set with a reference threshold and per-bar value labels
# difficulty: intermediate
# data_shape: categories: list[str], values: list[float], threshold: float
# tags: bar, ranking, reference-line, annotated, narrative
# narrative: 2024 BEV market share, top-5 leaders vs. EU 2030 mandate (55%)
# advanced_apis: dm.cspace, dm.format_axis_si (for non-percent), PercentFormatter, axhline, dm.label_bars, dm.check_figure_quality
# ai-template-meta-end

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

# 3. OKLCH gradient — color encodes magnitude on a regular authoring path.
#    dm.cspace(start, end, n) returns Color objects across OKLCH space.
#    Higher value → deeper hue (sequential convention).
gradient = dm.cspace("dc.teal5", "dc.teal1", n=len(countries))
bar_colors = [c.to_hex() for c in gradient]

# 4. Figure — the preset's canvas for this many bars in one series.
fig, ax = plt.subplots(
    figsize=dm.figsize_for(n_points=len(countries), n_series=1)
)

# 5. Bars + per-bar value labels (annotation density carries the story).
#    dm.label_bars prints each value like the axis ticks (here "88.9%").
ax.bar(countries, bev_share, color=bar_colors, edgecolor="white", linewidth=0.3)
dm.label_bars(ax)

# 6. Reference threshold — EU 2030 mandate as a horizontal context line.
ax.axhline(
    eu_2030_target, linestyle="--", linewidth=0.5, color="dc.amber4", zorder=1
)
ax.text(
    len(countries) - 0.5,
    eu_2030_target + 1.5,
    f"EU 2030 target ≈ {eu_2030_target:.0f}%",
    ha="right",
    va="bottom",
    fontsize=dm.fs(-1),
    color="dc.amber4",
    fontstyle="italic",
)

# 7. Axes formatting — domain-aware (percent), no chart-junk.
ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
ax.set_ylim(0, 105)
ax.set_ylabel("BEV share of new car sales")
ax.set_xlabel("Market")

# No title, subtitle or source note: the caption or slide carries them.
# Add one only when the user asks for it.

# 8. Layout — simple_layout is flush (margin=0); a small inch margin
#    gives the value labels and x-label room to breathe.
#    Pair with validate_with_fixes to catch anything left.
dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

# 9. Self-check — surfaces remaining clipping / overlap / contrast
#     issues before the agent reports "done". Returns [] when clean.
issues = dm.check_figure_quality(fig)
if issues:
    print(f"[bar-advanced] quality issues: {issues}")

dm.save_formats(fig, "bar_advanced")
