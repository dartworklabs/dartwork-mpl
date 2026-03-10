"""
Icon-Enhanced KPI Infographic
==============================

Material Design Icons (7,448+) ship with ``dartwork-mpl`` and can be placed
anywhere via ``dm.icon_font('mdi')``. This example builds a KPI dashboard
where each metric is paired with a vector icon, a large value, and a
contextual sparkline — all in a clean 2×2 grid.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

fig = plt.figure(figsize=(dm.DW, dm.DW * 0.55))
gs = gridspec.GridSpec(2, 2, hspace=0.45, wspace=0.35, figure=fig)

mdi = dm.icon_font('mdi')
np.random.seed(42)

# KPI definitions: (icon_codepoint, label, value, unit, color, trend_data)
kpis = [
    ('\U000F0238', 'Energy Output',   '847',  'GWh',  'oc.blue6',
     np.cumsum(np.random.randn(30)) + 50),
    ('\U000F058C', 'Water Saved',     '12.4', 'ML',   'oc.teal6',
     np.cumsum(np.random.randn(30) + 0.3) + 20),
    ('\U000F0127', 'CO\u2082 Reduced', '3.2',  'Mt',   'oc.grape6',
     np.cumsum(np.random.randn(30) - 0.1) + 40),
    ('\U000F0A79', 'Recycling Rate',  '94',   '%',    'tw.emerald600',
     np.cumsum(np.random.randn(30) + 0.5) + 60),
]

for idx, (icon, label, value, unit, color, trend) in enumerate(kpis):
    ax = fig.add_subplot(gs[idx // 2, idx % 2])

    # Icon (top-left)
    ax.text(0.05, 0.85, icon, fontproperties=mdi,
            fontsize=dm.fs(8), color=color,
            transform=ax.transAxes, va='top')

    # Value + unit (center-right)
    ax.text(0.95, 0.78, f"{value}", fontsize=dm.fs(6), weight='bold',
            color='oc.gray8', transform=ax.transAxes, ha='right', va='top')
    ax.text(0.95, 0.55, unit, fontsize=dm.fs(0), color='oc.gray5',
            transform=ax.transAxes, ha='right', va='top')

    # Label (bottom-left, above sparkline)
    ax.text(0.05, 0.38, label, fontsize=dm.fs(-0.5), weight='bold',
            color='oc.gray7', transform=ax.transAxes, va='top')

    # Sparkline (bottom portion)
    spark_x = np.linspace(0, 1, len(trend))
    t_min, t_max = trend.min(), trend.max()
    t_range = t_max - t_min if t_max != t_min else 1
    spark_y = 0.05 + 0.22 * (trend - t_min) / t_range

    ax.plot(spark_x, spark_y, color=color, lw=dm.lw(1), transform=ax.transAxes,
            clip_on=False)
    fill_color = dm.pseudo_alpha(color, 0.12, background='white')
    ax.fill_between(spark_x, 0.05, spark_y, color=fill_color,
                    transform=ax.transAxes, clip_on=False)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

fig.suptitle("Sustainability KPI Dashboard", fontsize=dm.fs(2),
             weight='bold', y=1.02)
dm.simple_layout(fig)
