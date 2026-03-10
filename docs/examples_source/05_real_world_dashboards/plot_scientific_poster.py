"""
Scientific Conference Poster
==============================

A 6-panel dashboard designed for conference poster presentations, combining
time series, correlation heatmap, grouped bars, radar-style polygon,
distribution violin, and summary annotations. Uses the ``presentation`` preset
for large, readable text at poster scale.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import dartwork_mpl as dm

dm.style.use('presentation')

np.random.seed(42)
fig = plt.figure(figsize=(dm.DW * 1.1, dm.DW * 0.95))
gs = gridspec.GridSpec(3, 2, height_ratios=[1, 1, 1], hspace=0.4, wspace=0.35,
                       figure=fig)

# ── (a) Time series with trend ──
ax_a = fig.add_subplot(gs[0, 0])
t = np.arange(60)
signal = np.sin(t * 0.15) * 8 + 0.3 * t + np.random.randn(60) * 2
trend = 0.3 * t + np.mean(signal[:5])
ax_a.plot(t, signal, color='oc.blue5', lw=dm.lw(0), alpha=0.6)
ax_a.plot(t, trend, color='oc.red7', lw=dm.lw(1.5), label='Trend')
fill = dm.pseudo_alpha('oc.blue5', 0.10, background='white')
ax_a.fill_between(t, signal, trend, color=fill)
ax_a.set_title("Temporal Drift Analysis")
ax_a.set_xlabel("Sample index")
ax_a.set_ylabel("Response")
ax_a.legend(fontsize=dm.fs(-1))

# ── (b) Correlation heatmap ──
ax_b = fig.add_subplot(gs[0, 1])
corr_data = np.random.randn(5, 5)
corr = np.corrcoef(corr_data)
im = ax_b.imshow(corr, cmap='dc.balance', vmin=-1, vmax=1, aspect='equal')
fig.colorbar(im, ax=ax_b, shrink=0.8)
labels = ['X\u2081', 'X\u2082', 'X\u2083', 'X\u2084', 'X\u2085']
ax_b.set_xticks(range(5))
ax_b.set_xticklabels(labels)
ax_b.set_yticks(range(5))
ax_b.set_yticklabels(labels)
ax_b.set_title("Correlation Matrix")

# ── (c) Grouped bar chart ──
ax_c = fig.add_subplot(gs[1, 0])
categories = ['Method A', 'Method B', 'Method C']
metrics = {'Accuracy': [92, 88, 95], 'Speed': [78, 91, 85]}
x_pos = np.arange(len(categories))
width = 0.3
colors_bar = ['oc.blue5', 'oc.grape5']
for i, (metric, vals) in enumerate(metrics.items()):
    ax_c.bar(x_pos + i * width, vals, width, label=metric,
             color=colors_bar[i])
ax_c.set_xticks(x_pos + width / 2)
ax_c.set_xticklabels(categories)
ax_c.set_ylabel("Score")
ax_c.set_title("Method Benchmarks")
ax_c.legend(fontsize=dm.fs(-1))
ax_c.set_ylim(0, 110)

# ── (d) Radar / Polygon chart ──
ax_d = fig.add_subplot(gs[1, 1], projection='polar')
dims = ['Precision', 'Recall', 'F1', 'Latency', 'Memory']
n_dims = len(dims)
angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
angles += angles[:1]

vals_a = [85, 90, 87, 70, 60]
vals_b = [75, 80, 77, 95, 90]
vals_a += vals_a[:1]
vals_b += vals_b[:1]

ax_d.plot(angles, vals_a, 'o-', color='oc.blue6', lw=dm.lw(1), label='Model A')
ax_d.fill(angles, vals_a,
          color=dm.pseudo_alpha('oc.blue5', 0.15, background='white'))
ax_d.plot(angles, vals_b, 's-', color='oc.grape6', lw=dm.lw(1), label='Model B')
ax_d.fill(angles, vals_b,
          color=dm.pseudo_alpha('oc.grape5', 0.15, background='white'))
ax_d.set_xticks(angles[:-1])
ax_d.set_xticklabels(dims, fontsize=dm.fs(-1))
ax_d.set_ylim(0, 100)
ax_d.set_title("Performance Radar", pad=20)
ax_d.legend(fontsize=dm.fs(-1), loc='upper right', bbox_to_anchor=(1.3, 1.1))

# ── (e) Violin / distribution ──
ax_e = fig.add_subplot(gs[2, 0])
data_groups = [np.random.normal(mu, 3, 200) for mu in [30, 42, 38, 50]]
vp = ax_e.violinplot(data_groups, positions=[1, 2, 3, 4], showmedians=True,
                     showextrema=False)
violin_colors = ['oc.blue3', 'oc.grape3', 'oc.teal3', 'oc.orange3']
for body, color in zip(vp['bodies'], violin_colors):
    body.set_facecolor(color)
    body.set_alpha(0.7)
vp['cmedians'].set_color('oc.gray8')
ax_e.set_xticks([1, 2, 3, 4])
ax_e.set_xticklabels(['Ctrl', 'Treat 1', 'Treat 2', 'Treat 3'])
ax_e.set_title("Response Distribution")
ax_e.set_ylabel("Value")

# ── (f) Summary text panel ──
ax_f = fig.add_subplot(gs[2, 1])
ax_f.axis('off')
summary_text = (
    "KEY FINDINGS\n"
    "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\u2022 Method C achieves 95% accuracy\n"
    "\u2022 Model A excels in precision\n"
    "\u2022 Treatment 3 shows highest effect\n"
    "\u2022 Temporal drift detected (slope = 0.30)\n"
    "\u2022 Strong X\u2081\u2013X\u2083 correlation (r = 0.89)\n"
    "\n"
    "CONCLUSION\n"
    "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "Combined approach recommended\n"
    "for production deployment."
)
ax_f.text(0.08, 0.92, summary_text, transform=ax_f.transAxes,
          fontsize=dm.fs(-0.5), va='top', family='monospace',
          color='oc.gray8', linespacing=1.6)

# Panel labels
non_polar = [ax_a, ax_b, ax_c]
dm.label_axes(non_polar + [ax_d, ax_e, ax_f])

dm.simple_layout(fig)
