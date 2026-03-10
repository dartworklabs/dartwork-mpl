"""
Climate Data Visualization Dashboard
======================================

A multi-panel dashboard for climate science communication, combining a
temperature anomaly heatmap (using the diverging ``dc.balance`` colormap),
a CO\u2082 concentration trend line, and a sea-level rise area chart.

This example showcases how ``dartwork-mpl``'s perceptual colormaps, layout
optimization, and annotation utilities produce publication-quality
scientific communication pieces.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('report')

np.random.seed(42)
fig = plt.figure(figsize=(dm.DW, dm.DW * 0.85))
gs = gridspec.GridSpec(2, 2, height_ratios=[1.4, 1], hspace=0.35, wspace=0.3,
                       figure=fig)

# ── (a) Temperature anomaly stripe (heatmap) ──
ax_a = fig.add_subplot(gs[0, :])

years = np.arange(1900, 2026)
n_years = len(years)
# Synthetic temperature anomaly: slow warming with natural variability
anomaly = (0.012 * (years - 1900) +
           0.3 * np.sin((years - 1900) * 0.1) +
           np.random.normal(0, 0.15, n_years))
anomaly -= np.mean(anomaly[:30])  # baseline to 1900–1930 mean

# Display as a horizontal strip (1 row × N columns)
anomaly_2d = anomaly.reshape(1, -1)
im = ax_a.imshow(anomaly_2d, cmap='dc.balance', aspect='auto',
                 vmin=-1.0, vmax=1.5,
                 extent=[years[0], years[-1], 0, 1])
ax_a.set_yticks([])
ax_a.set_xlabel("Year", fontsize=dm.fs(0))

# Year tick labels at 20-year intervals
tick_years = np.arange(1900, 2040, 20)
ax_a.set_xticks(tick_years)
ax_a.set_xticklabels([str(y) for y in tick_years], fontsize=dm.fs(-0.5))

cb = fig.colorbar(im, ax=ax_a, orientation='horizontal',
                  pad=0.15, shrink=0.6, aspect=30)
cb.set_label("Temperature Anomaly (\u00b0C)", fontsize=dm.fs(-0.5))

ax_a.set_title("Global Temperature Anomaly (1900\u20132025)",
               fontsize=dm.fs(1), weight='bold', pad=12)

# ── (b) CO₂ concentration ──
ax_b = fig.add_subplot(gs[1, 0])

co2_years = np.arange(1960, 2026)
# Keeling curve approximation
co2 = 315 + 1.5 * (co2_years - 1960) + 0.01 * (co2_years - 1960)**2
co2 += 3.0 * np.sin(2 * np.pi * co2_years)  # seasonal cycle
co2 += np.random.normal(0, 0.5, len(co2_years))

ax_b.plot(co2_years, co2, color='oc.red7', lw=dm.lw(1))
fill_co2 = dm.pseudo_alpha('oc.red5', 0.12, background='white')
ax_b.fill_between(co2_years, 310, co2, color=fill_co2)
ax_b.set_xlim(1960, 2025)
ax_b.set_ylim(310, 430)
ax_b.set_title("Atmospheric CO\u2082 Concentration", fontsize=dm.fs(0), weight='bold')
ax_b.set_xlabel("Year")
ax_b.set_ylabel("CO\u2082 (ppm)")
dm.set_decimal(ax_b, yn=0)

# Annotate milestone
idx_400 = np.argmax(co2 >= 400)
if idx_400 > 0:
    yr_400 = co2_years[idx_400]
    ax_b.axhline(400, color='oc.gray5', ls='--', lw=0.8, zorder=1)
    ax_b.annotate(f'400 ppm ({yr_400})', xy=(yr_400, 400),
                  xytext=(yr_400 - 20, 415),
                  fontsize=dm.fs(-1), color='oc.gray7',
                  arrowprops=dict(arrowstyle='->', color='oc.gray5', lw=0.7))

# ── (c) Sea level rise ──
ax_c = fig.add_subplot(gs[1, 1])

sl_years = np.arange(1900, 2026)
# Synthetic sea level: accelerating rise
sea_level = 0.001 * (sl_years - 1900)**2 + 0.5 * (sl_years - 1900) / 100
sea_level += np.cumsum(np.random.normal(0, 0.3, len(sl_years)))
sea_level -= sea_level[0]  # baseline at 0

# Gradient fill using cspace
n_bands = 30
gradient = dm.cspace(dm.named('oc.blue1'), dm.named('oc.blue8'),
                     n=n_bands, space='oklch')

sl_max = max(sea_level.max() * 1.1, 1)
band_edges = np.linspace(0, sl_max, n_bands + 1)
for i in range(n_bands):
    lo, hi = band_edges[i], band_edges[i + 1]
    clipped = np.clip(sea_level, lo, hi)
    ax_c.fill_between(sl_years, lo, clipped,
                      color=gradient[i].to_hex(), lw=0)

ax_c.plot(sl_years, sea_level, color='oc.blue9', lw=dm.lw(0.5), zorder=5)
ax_c.set_xlim(1900, 2025)
ax_c.set_ylim(0, sl_max)
ax_c.set_title("Sea Level Rise (relative)", fontsize=dm.fs(0), weight='bold')
ax_c.set_xlabel("Year")
ax_c.set_ylabel("Rise (cm)")
dm.set_decimal(ax_c, yn=0)

dm.label_axes([ax_a, ax_b, ax_c])
fig.tight_layout()
