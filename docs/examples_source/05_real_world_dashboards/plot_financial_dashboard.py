"""
Financial Reporting Dashboard
=============================

Combining multiple streams of data into a cohesive, publication-ready financial
dashboard using ``dartwork-mpl``. This example uses the ``report`` preset,
Tailwind and Open Color palettes, GridSpec for asymmetric layouts,
``dm.pseudo_alpha`` for vector-safe fills, ``dm.label_axes`` for panel indexing,
``dm.set_decimal`` for tick formatting, and ``dm.simple_layout`` to tie it all together.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

fig = plt.figure(figsize=(dm.DW, dm.DW * 0.65))
gs = gridspec.GridSpec(2, 2, height_ratios=[1.5, 1], figure=fig)

# Mock financial data
quarters = ['Q1', 'Q2', 'Q3', 'Q4']
revenue = [120, 135, 128, 150]
margins = [15.2, 16.5, 14.8, 18.1]

np.random.seed(42)
dates = np.arange(100)
stock_price = np.cumsum(np.random.randn(100)) + 150
volume = np.random.randint(50, 200, 100)

# ── Top: Revenue & Margins (Dual Axis) ──
ax_top = fig.add_subplot(gs[0, :])
ax_top.bar(quarters, revenue, color='tw.slate200', width=0.5, label='Revenue ($M)')

ax_twin = ax_top.twinx()
ax_twin.plot(quarters, margins, color='tw.emerald600', marker='o',
             lw=dm.lw(2), label='Net Margin (%)')

ax_top.set_title("Quarterly Financial Performance")
ax_top.set_ylabel("Revenue ($M)")
ax_twin.set_ylabel("Margin (%)")
ax_top.set_ylim(0, 180)
ax_twin.set_ylim(10, 25)

lines, labels = ax_top.get_legend_handles_labels()
lines2, labels2 = ax_twin.get_legend_handles_labels()
ax_top.legend(lines + lines2, labels + labels2, loc='upper left')

# ── Bottom Left: Stock Price ──
ax_bl = fig.add_subplot(gs[1, 0])
ax_bl.plot(dates, stock_price, color='oc.indigo6', lw=dm.lw(1))

# pseudo_alpha uses `background=` parameter
fill_color = dm.pseudo_alpha('oc.indigo6', 0.1, background='white')
ax_bl.fill_between(dates, stock_price, 130, color=fill_color, alpha=1.0)

ax_bl.set_title("Stock Price YTD")
ax_bl.set_xlabel("Trading Days")
ax_bl.set_ylabel("Price ($)")
ax_bl.set_ylim(130, 170)

# ── Bottom Right: Trading Volume ──
ax_br = fig.add_subplot(gs[1, 1])
colors = ['tw.rose400' if v < 100 else 'tw.emerald400' for v in volume]
ax_br.bar(dates, volume, color=colors, width=1.0)

ax_br.set_title("Daily Trading Volume")
ax_br.set_xlabel("Trading Days")
ax_br.set_ylabel("Volume (k)")

# Panel labels and formatting
dm.label_axes([ax_top, ax_bl, ax_br])
dm.set_decimal(ax_top, yn=0)
dm.set_decimal(ax_bl, yn=0)

fig.tight_layout(pad=1.5, h_pad=2.0, w_pad=2.0)
