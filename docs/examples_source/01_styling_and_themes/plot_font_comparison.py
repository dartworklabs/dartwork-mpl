"""
Font Family Comparison
======================

dartwork-mpl bundles 9 professional font families.  This example renders the
**same chart** with six different typefaces so you can see at a glance how
typography shapes the personality of a figure.

Every text element uses ``FontProperties(fname=...)`` to guarantee the
correct bundled font file is resolved regardless of system font cache state.
"""

import os

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

# ── data ─────────────────────────────────────────────────────────────────────
quarters = ["Q1 '24", "Q2 '24", "Q3 '24", "Q4 '24", "Q1 '25", "Q2 '25"]
revenue = [4.2, 4.8, 5.1, 5.5, 5.9, 6.3]
margin = [38, 41, 39, 43, 45, 44]

# Resolve absolute path to bundled font directory
_FONT_DIR = os.path.join(
    os.path.dirname(dm.__file__), "asset", "font"
)

# (display name, font filename for weight-300 / Light variant)
fonts = [
    ("Roboto", "Roboto-Light.ttf"),
    ("Inter", "Inter-Light.ttf"),
    ("Noto Sans", "NotoSans-Light.ttf"),
    ("Noto Sans Condensed", "NotoSans_Condensed-Light.ttf"),
    ("Paperlogy", "Paperlogy-3Light.ttf"),
    ("Noto Sans SemiCondensed", "NotoSans_SemiCondensed-Light.ttf"),
]

for font_name, font_file in fonts:
    dm.style.use("report")

    fp = fm.FontProperties(fname=os.path.join(_FONT_DIR, font_file))

    fig, ax = plt.subplots(figsize=(dm.SW, dm.SW * 0.65))
    x = np.arange(len(quarters))

    # Bar chart (revenue)
    ax.bar(x, revenue, width=0.55, color="tw.sky500", zorder=3)
    ax.set_ylabel("Revenue ($B)")
    ax.set_ylim(0, 8.5)
    ax.set_yticks([0, 2, 4, 6, 8])

    # Line chart (margin) on twin axis
    ax2 = ax.twinx()
    ax2.plot(
        x,
        margin,
        color="oc.red6",
        marker="o",
        markersize=4,
        lw=dm.lw(1),
        zorder=4,
    )
    ax2.set_ylabel("Gross Margin (%)")
    ax2.set_ylim(20, 55)
    ax2.set_yticks([20, 30, 40, 50])

    ax.set_xticks(x)
    ax.set_xticklabels(quarters)
    ax.set_title(font_name)

    # Apply font to every text element
    for text in (
        [ax.title, ax.yaxis.label, ax2.yaxis.label]
        + ax.get_xticklabels()
        + ax.get_yticklabels()
        + ax2.get_yticklabels()
    ):
        text.set_fontproperties(fp)

    dm.simple_layout(fig)

plt.show()
