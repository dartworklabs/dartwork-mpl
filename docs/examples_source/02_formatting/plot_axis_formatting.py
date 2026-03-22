"""
Axis Formatting Examples
=========================

This example demonstrates various axis formatting utilities in dartwork-mpl,
including percentage, currency, scientific notation, and custom number formats.
These utilities make it easy to create publication-ready figures with
properly formatted axis labels.
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# Set random seed for reproducibility
np.random.seed(42)

# %%
# Percentage Formatting
# ---------------------
#
# Format y-axis values as percentages with customizable decimal places.

dm.style.use('scientific')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(dm.cm2in(16), dm.cm2in(8)))

# Growth rates as decimals
quarters = ['Q1', 'Q2', 'Q3', 'Q4']
growth_rates = np.array([0.125, 0.183, 0.095, 0.214])
conversion_rates = np.array([0.0234, 0.0312, 0.0289, 0.0356])

# Left: Bar chart with percentages
ax1.bar(quarters, growth_rates, color='oc.green5')
dm.format_axis_percent(ax1, axis='y')
ax1.set_title('Quarterly Growth Rates', fontsize=dm.fs(1))
ax1.set_ylabel('Growth Rate', fontsize=dm.fs(0))
dm.minimal_axes(ax1)

# Right: Line chart with precise percentages
ax2.plot(quarters, conversion_rates, 'o-', color='oc.blue5', lw=dm.lw(1.5))
dm.format_axis_percent(ax2, axis='y', decimals=2)  # Show 2 decimal places
ax2.set_title('Conversion Rates', fontsize=dm.fs(1))
ax2.set_ylabel('Conversion Rate', fontsize=dm.fs(0))
dm.minimal_axes(ax2)
dm.add_grid(ax2, axis='y', alpha=0.2)

dm.simple_layout(fig)

# %%
# Financial Number Formatting
# ----------------------------
#
# Format large numbers with thousands separators, millions, and billions.

fig, axes = plt.subplots(2, 2, figsize=(dm.cm2in(16), dm.cm2in(12)))

# Generate financial data
years = np.arange(2019, 2024)
revenue = np.array([125000, 248000, 392000, 516000, 687000])
market_cap = np.array([1.2e6, 2.5e6, 4.8e6, 8.3e6, 12.1e6])
gdp = np.array([1.8e9, 2.1e9, 2.4e9, 2.7e9, 3.1e9])
expenses = np.array([95000, 180000, 290000, 380000, 495000])

# Top-left: Thousands with separator
ax1 = axes[0, 0]
ax1.plot(years, revenue, 's-', color='oc.teal5', lw=dm.lw(1.5), markersize=8)
dm.format_axis_thousands(ax1, axis='y', sep=',')
ax1.set_title('Annual Revenue', fontsize=dm.fs(1))
ax1.set_ylabel('Revenue ($)', fontsize=dm.fs(0))
ax1.set_xlabel('Year', fontsize=dm.fs(0))
dm.minimal_axes(ax1)

# Top-right: Millions notation
ax2 = axes[0, 1]
ax2.bar(years, market_cap, color='oc.purple5')
dm.format_axis_millions(ax2, axis='y', suffix='M', decimals=1)
ax2.set_title('Market Capitalization', fontsize=dm.fs(1))
ax2.set_ylabel('Market Cap ($)', fontsize=dm.fs(0))
ax2.set_xlabel('Year', fontsize=dm.fs(0))
dm.minimal_axes(ax2)

# Bottom-left: Billions notation
ax3 = axes[1, 0]
ax3.plot(years, gdp, 'o-', color='oc.orange5', lw=dm.lw(2), markersize=8)
dm.format_axis_billions(ax3, axis='y', suffix='B', decimals=1)
ax3.set_title('GDP Growth', fontsize=dm.fs(1))
ax3.set_ylabel('GDP ($)', fontsize=dm.fs(0))
ax3.set_xlabel('Year', fontsize=dm.fs(0))
dm.minimal_axes(ax3)
dm.add_grid(ax3, axis='y', alpha=0.2)

# Bottom-right: Mixed scales
ax4 = axes[1, 1]
ax4.bar(years, revenue, color='oc.green5', alpha=0.7, label='Revenue')
ax4.bar(years, expenses, color='oc.red5', alpha=0.7, label='Expenses')
dm.format_axis_thousands(ax4, axis='y', sep=',')
ax4.set_title('Revenue vs Expenses', fontsize=dm.fs(1))
ax4.set_ylabel('Amount ($)', fontsize=dm.fs(0))
ax4.set_xlabel('Year', fontsize=dm.fs(0))
ax4.legend(fontsize=dm.fs(-1))
dm.minimal_axes(ax4)

dm.label_axes(axes.flat)
dm.simple_layout(fig)

# %%
# Currency Formatting
# -------------------
#
# Format axes with different currency symbols and positions.

fig, axes = plt.subplots(2, 3, figsize=(dm.cm2in(18), dm.cm2in(12)))

# Product prices in different currencies
products = ['A', 'B', 'C', 'D', 'E']
prices_usd = np.array([19.99, 34.50, 78.25, 124.00, 259.99])
prices_eur = prices_usd * 0.85  # EUR conversion
prices_gbp = prices_usd * 0.73  # GBP conversion
prices_jpy = prices_usd * 110   # JPY conversion
prices_krw = prices_usd * 1200  # KRW conversion
prices_chf = prices_usd * 0.92  # CHF conversion

# Different currency formats
currencies = [
    (axes[0, 0], prices_usd, '$', 'prefix', 'USD Prices'),
    (axes[0, 1], prices_eur, '€', 'suffix', 'EUR Prices'),
    (axes[0, 2], prices_gbp, '£', 'prefix', 'GBP Prices'),
    (axes[1, 0], prices_jpy, '¥', 'prefix', 'JPY Prices'),
    (axes[1, 1], prices_krw, '₩', 'prefix', 'KRW Prices'),
    (axes[1, 2], prices_chf, 'CHF ', 'prefix', 'Swiss Franc'),
]

for ax, prices, symbol, position, title in currencies:
    bars = ax.bar(products, prices, color='oc.indigo5')

    # Format based on currency scale
    if symbol in ['¥', '₩']:
        dm.format_axis_thousands(ax, axis='y', sep=',')
    else:
        dm.format_axis_currency(ax, axis='y', symbol=symbol, position=position)

    ax.set_title(title, fontsize=dm.fs(0))
    dm.minimal_axes(ax)

dm.simple_layout(fig)

# %%
# Scientific Notation with SI Prefixes
# -------------------------------------
#
# Use SI prefixes for scientific and engineering data.

fig, axes = plt.subplots(2, 2, figsize=(dm.cm2in(16), dm.cm2in(12)))

# Frequency response
freqs = np.logspace(3, 9, 50)  # 1kHz to 1GHz
response = -20 * np.log10(freqs / 1e6)

ax1 = axes[0, 0]
ax1.semilogx(freqs, response, color='oc.blue6', lw=dm.lw(1.5))
dm.format_axis_si(ax1, axis='x')
ax1.set_xlabel('Frequency (Hz)', fontsize=dm.fs(0))
ax1.set_ylabel('Response (dB)', fontsize=dm.fs(0))
ax1.set_title('Frequency Response', fontsize=dm.fs(1))
dm.minimal_axes(ax1)
dm.add_grid(ax1, alpha=0.2, which='both')

# Power measurements
power_values = np.array([1e-9, 1e-6, 1e-3, 1, 1e3, 1e6])
power_labels = ['nW', 'μW', 'mW', 'W', 'kW', 'MW']
measurements = np.random.rand(len(power_values)) * power_values

ax2 = axes[0, 1]
ax2.bar(range(len(power_values)), measurements, color='oc.orange5')
ax2.set_yscale('log')
dm.format_axis_si(ax2, axis='y')
ax2.set_ylabel('Power (W)', fontsize=dm.fs(0))
ax2.set_title('Power Measurements', fontsize=dm.fs(1))
ax2.set_xticks(range(len(power_values)))
ax2.set_xticklabels(power_labels)
dm.minimal_axes(ax2)

# Data sizes
sizes_bytes = np.array([1e3, 1e6, 1e9, 1e12])  # KB to TB
transfer_rates = np.array([95, 850, 10, 0.1]) * sizes_bytes / 1e9  # GB/s

ax3 = axes[1, 0]
ax3.loglog(sizes_bytes, transfer_rates, 'o-', color='oc.green6',
           lw=dm.lw(1.5), markersize=8)
dm.format_axis_si(ax3, axis='x')
dm.format_axis_si(ax3, axis='y')
ax3.set_xlabel('File Size (B)', fontsize=dm.fs(0))
ax3.set_ylabel('Transfer Rate (B/s)', fontsize=dm.fs(0))
ax3.set_title('Data Transfer Rates', fontsize=dm.fs(1))
dm.minimal_axes(ax3)
dm.add_grid(ax3, alpha=0.2, which='both')

# Time scales
time_scales = np.array([1e-9, 1e-6, 1e-3, 1, 60, 3600])  # ns to hours
events = np.array([1000, 500, 100, 50, 10, 2])

ax4 = axes[1, 1]
ax4.scatter(time_scales, events, s=100, c=range(len(time_scales)),
           cmap='dc.deep_sea')
ax4.set_xscale('log')
dm.format_axis_si(ax4, axis='x')
ax4.set_xlabel('Time (s)', fontsize=dm.fs(0))
ax4.set_ylabel('Event Count', fontsize=dm.fs(0))
ax4.set_title('Time Scale Analysis', fontsize=dm.fs(1))
dm.minimal_axes(ax4)

dm.label_axes(axes.flat)
dm.simple_layout(fig)

# %%
# Rotating Tick Labels
# --------------------
#
# Rotate labels for better readability with long text.

fig, axes = plt.subplots(1, 3, figsize=(dm.cm2in(18), dm.cm2in(8)))

# Long category names
categories = [
    'Machine Learning',
    'Deep Neural Networks',
    'Natural Language Processing',
    'Computer Vision',
    'Reinforcement Learning',
    'Generative AI',
    'Quantum Computing'
]

values = np.random.rand(len(categories)) * 100 + 50

# Left: 45-degree rotation (default)
ax1 = axes[0]
ax1.bar(range(len(categories)), values, color='oc.cyan5')
ax1.set_xticks(range(len(categories)))
ax1.set_xticklabels(categories)
dm.rotate_tick_labels(ax1, axis='x')  # Default 45 degrees
ax1.set_title('45° Rotation (Default)', fontsize=dm.fs(1))
ax1.set_ylabel('Score', fontsize=dm.fs(0))
dm.minimal_axes(ax1)

# Middle: 90-degree rotation
ax2 = axes[1]
ax2.bar(range(len(categories)), values, color='oc.pink5')
ax2.set_xticks(range(len(categories)))
ax2.set_xticklabels(categories)
dm.rotate_tick_labels(ax2, axis='x', rotation=90, ha='right')
ax2.set_title('90° Rotation', fontsize=dm.fs(1))
ax2.set_ylabel('Score', fontsize=dm.fs(0))
dm.minimal_axes(ax2)

# Right: 30-degree rotation
ax3 = axes[2]
ax3.bar(range(len(categories)), values, color='oc.yellow5')
ax3.set_xticks(range(len(categories)))
ax3.set_xticklabels(categories)
dm.rotate_tick_labels(ax3, axis='x', rotation=30, ha='right')
ax3.set_title('30° Rotation', fontsize=dm.fs(1))
ax3.set_ylabel('Score', fontsize=dm.fs(0))
dm.minimal_axes(ax3)

dm.simple_layout(fig)

# %%
# Complete Financial Dashboard
# ----------------------------
#
# Combining multiple formatting styles in a comprehensive dashboard.

fig = plt.figure(figsize=(dm.cm2in(20), dm.cm2in(16)))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Quarterly data
quarters = ['Q1 2023', 'Q2 2023', 'Q3 2023', 'Q4 2023', 'Q1 2024']
revenue = np.array([1.2e6, 1.5e6, 1.8e6, 2.1e6, 2.4e6])
profit_margin = np.array([0.12, 0.15, 0.18, 0.14, 0.16])
stock_price = np.array([45.20, 52.30, 61.50, 58.40, 67.80])
market_cap = revenue * 50  # Simplified
volume = np.array([2.3e6, 3.1e6, 2.8e6, 3.5e6, 4.2e6])
expenses = revenue * (1 - profit_margin)

# Revenue trend (top-left, 2x1)
ax1 = fig.add_subplot(gs[0, :2])
ax1.bar(quarters, revenue, color='oc.green5', alpha=0.7, label='Revenue')
ax1.plot(quarters, revenue, 'o-', color='oc.green8', lw=dm.lw(2))
dm.format_axis_millions(ax1, axis='y', suffix='M')
ax1.set_title('Quarterly Revenue Trend', fontsize=dm.fs(2))
ax1.set_ylabel('Revenue ($)', fontsize=dm.fs(0))
dm.rotate_tick_labels(ax1, axis='x', rotation=45)
dm.minimal_axes(ax1)

# Profit margin (top-right)
ax2 = fig.add_subplot(gs[0, 2])
ax2.plot(quarters, profit_margin, 's-', color='oc.blue5', lw=dm.lw(1.5), markersize=8)
dm.format_axis_percent(ax2, axis='y', decimals=1)
ax2.set_title('Profit Margin', fontsize=dm.fs(1))
ax2.set_ylabel('Margin', fontsize=dm.fs(0))
ax2.set_ylim(0, 0.25)
dm.rotate_tick_labels(ax2, axis='x', rotation=45)
dm.minimal_axes(ax2)
dm.add_grid(ax2, axis='y', alpha=0.2)

# Stock price (middle-left)
ax3 = fig.add_subplot(gs[1, 0])
ax3.plot(quarters, stock_price, 'o-', color='oc.purple5', lw=dm.lw(2), markersize=8)
dm.format_axis_currency(ax3, axis='y', symbol='$')
ax3.set_title('Stock Price', fontsize=dm.fs(1))
ax3.set_ylabel('Price', fontsize=dm.fs(0))
dm.rotate_tick_labels(ax3, axis='x', rotation=45)
dm.minimal_axes(ax3)

# Market cap (middle-center)
ax4 = fig.add_subplot(gs[1, 1])
ax4.bar(quarters, market_cap, color='oc.orange5')
dm.format_axis_billions(ax4, axis='y', suffix='B', decimals=2)
ax4.set_title('Market Cap', fontsize=dm.fs(1))
ax4.set_ylabel('Value ($)', fontsize=dm.fs(0))
dm.rotate_tick_labels(ax4, axis='x', rotation=45)
dm.minimal_axes(ax4)

# Trading volume (middle-right)
ax5 = fig.add_subplot(gs[1, 2])
ax5.bar(quarters, volume, color='oc.cyan5')
dm.format_axis_si(ax5, axis='y')
ax5.set_title('Trading Volume', fontsize=dm.fs(1))
ax5.set_ylabel('Shares', fontsize=dm.fs(0))
dm.rotate_tick_labels(ax5, axis='x', rotation=45)
dm.minimal_axes(ax5)

# Expense breakdown (bottom, 1x3)
ax6 = fig.add_subplot(gs[2, :])
width = 0.35
x_pos = np.arange(len(quarters))
ax6.bar(x_pos - width/2, revenue, width, label='Revenue', color='oc.green5')
ax6.bar(x_pos + width/2, expenses, width, label='Expenses', color='oc.red5')
dm.format_axis_millions(ax6, axis='y', suffix='M')
ax6.set_title('Revenue vs Expenses', fontsize=dm.fs(1))
ax6.set_ylabel('Amount ($)', fontsize=dm.fs(0))
ax6.set_xticks(x_pos)
ax6.set_xticklabels(quarters)
dm.rotate_tick_labels(ax6, axis='x', rotation=45)
ax6.legend(fontsize=dm.fs(-1))
dm.minimal_axes(ax6)
dm.add_grid(ax6, axis='y', alpha=0.2)

plt.suptitle('Financial Performance Dashboard', fontsize=dm.fs(3), y=0.98)
dm.simple_layout(fig)

plt.show()