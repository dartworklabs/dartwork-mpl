"""
Advanced Mega-Cap Valuation Dashboard
=====================================

This dashboard showcases the power of ``dartwork-mpl``'s layout engine and color system
in constructing a highly dense, professional equity research dashboard. It features a
10-year combo chart for revenue and margins, an EV/EBITDA valuation band chart, and a 
football field chart for intrinsic value ranges—all perfectly aligned without any manual spacing.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

# Generate Mock Data
years = np.arange(2015, 2026)
revenue = np.array([210, 230, 260, 250, 290, 310, 340, 380, 410, 450, 480]) # Billions
op_margin = np.array([21.2, 22.5, 23.1, 22.0, 24.5, 25.1, 26.8, 28.2, 29.5, 30.1, 31.0])

np.random.seed(42)
dates_band = np.arange(2015, 2026, 1/12)
price = 100 * np.exp(np.linspace(0, 1.5, len(dates_band))) + np.random.randn(len(dates_band))*10
# Calculate a mock smooth forward EBITDA
ebitda_fwd = price / (np.linspace(15, 25, len(dates_band)) + np.random.randn(len(dates_band))*2)
# Smooth it out
ebitda_fwd = np.convolve(ebitda_fwd, np.ones(12)/12, mode='same')
# Adjust ends to avoid nan
ebitda_fwd[:6] = ebitda_fwd[6]
ebitda_fwd[-6:] = ebitda_fwd[-7]

ff_labels = ["52-Week Range", "Analyst Tracker", "DCF (Base)", "DCF (Bull)", "EV/EBITDA"]
ff_low = np.array([310, 400, 380, 450, 390])
ff_high = np.array([480, 520, 460, 560, 430])
current_price = 425

fig = plt.figure(figsize=(dm.DW * 1.5, dm.DW * 0.9))
gs = gridspec.GridSpec(2, 2, width_ratios=[1.2, 1], height_ratios=[1, 1], figure=fig)

# ── 1. Left Panel: Revenue & Margin (Spanning 2 rows) ──
ax1 = fig.add_subplot(gs[:, 0])
ax1.bar(years, revenue, color='tw.slate800', alpha=0.9, width=0.6, label='Revenue ($B)')
ax1_twin = ax1.twinx()
ax1_twin.plot(years, op_margin, color='oc.teal5', marker='o', lw=dm.lw(2.5), label='OP Margin (%)')
ax1.set_title("10-Year Revenue & Operating Margin")
ax1.set_ylabel("Revenue (USD Billions)")
ax1_twin.set_ylabel("OP Margin (%)")
dm.set_decimal(ax1, yn=0)
dm.set_decimal(ax1_twin, yn=1)

# Combo legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# ── 2. Top Right: Valuation Bands ──
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(dates_band, price, color='oc.gray8', lw=dm.lw(1.5), label='Stock Price')
bands = [15, 20, 25]
colors = ['oc.indigo3', 'oc.indigo5', 'oc.indigo7']
for i, (band, color) in enumerate(zip(bands, colors)):
    band_price = ebitda_fwd * band
    ax2.plot(dates_band, band_price, color=color, lw=dm.lw(1.2), ls='--', alpha=0.8)
    # Add fill between bands
    if i > 0:
        prev_band_price = ebitda_fwd * bands[i-1]
        fill_c = dm.pseudo_alpha(color, 0.1, 'white')
        ax2.fill_between(dates_band, prev_band_price, band_price, color=fill_c)
        
    ax2.text(dates_band[-1]+0.2, band_price[-1], f"{band}x", color=color, va='center', fontsize=dm.fs(-1), fontweight='bold')
ax2.set_title("Forward EV/EBITDA Bands")
ax2.set_ylabel("Price ($)")
# Set specific limits
ax2.set_xlim(2015, 2027)
dm.set_decimal(ax2, yn=0)

# ── 3. Bottom Right: Football Field Valuation ──
ax3 = fig.add_subplot(gs[1, 1])
y_pos = np.arange(len(ff_labels))
# Create floating bars (barh with left offset)
ax3.barh(y_pos, ff_high - ff_low, left=ff_low, height=0.5, color='tw.slate300', edgecolor='tw.slate600', lw=1)
# Add value annotations on bars
for y, low, high in zip(y_pos, ff_low, ff_high):
    ax3.text(low - 5, y, f"${low}", ha='right', va='center', fontsize=dm.fs(-1), color='tw.slate600')
    ax3.text(high + 5, y, f"${high}", ha='left', va='center', fontsize=dm.fs(-1), color='tw.slate600')

# Current price line
ax3.axvline(current_price, color='oc.red6', ls='--', lw=dm.lw(1.5), zorder=5)
ax3.text(current_price, 4.4, f"Current: ${current_price}", color='oc.red7', ha='center', va='bottom', fontsize=dm.fs(-1), fontweight='bold')

ax3.set_yticks(y_pos)
ax3.set_yticklabels(ff_labels)
ax3.set_title("Football Field Valuation Range")
ax3.set_xlabel("Implied Share Price ($)")
# We hide the x-axis tick labels since we annotated the bars directly
ax3.set_xticks([])
# Hide top/right/bottom spines
ax3.spines['bottom'].set_visible(False)
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)

dm.label_axes([ax1, ax2, ax3])
dm.simple_layout(fig, gs=gs)

plt.show()
