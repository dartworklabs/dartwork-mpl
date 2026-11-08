"""
Histogram (Advanced)
====================

Histogram — advanced template (mean/median + IQR band + SLA threshold).

Source: ``dartwork_mpl/asset/prompt/05-templates/advanced/histogram.py`` ·
MCP ``dartwork-mpl://template/advanced/histogram``.
"""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: histogram
# use_case: Response-time distribution with mean, median, IQR band, and SLA threshold reference
# difficulty: intermediate
# data_shape: values: list[float]
# tags: distribution, histogram, threshold, annotated, narrative
# narrative: API response-time distribution; SLA at p95 = 250ms; show how the tail breaches it
# advanced_apis: axvline (mean, median, SLA), axvspan (IQR band), np.percentile, legend
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# Synthetic response-time distribution: log-normal + small heavy tail.
rng = np.random.default_rng(42)
body = rng.lognormal(mean=4.6, sigma=0.45, size=4000)
tail = rng.lognormal(mean=5.4, sigma=0.35, size=300)
samples = np.concatenate([body, tail])
samples = samples[samples < 800]  # trim implausible spike

mean = samples.mean()
median = np.median(samples)
p25, p75 = np.percentile(samples, [25, 75])
sla_threshold = 250.0
breach_rate = (samples > sla_threshold).mean() * 100

fig, ax = plt.subplots(figsize=dm.figsize_for())

ax.hist(samples, bins=50, color="dc.teal3", edgecolor="white", linewidth=0.3)

# IQR band — the middle 50% as quiet context.
ax.axvspan(
    p25,
    p75,
    alpha=0.10,
    color="dc.teal5",
    zorder=0,
    label=f"IQR ({p25:.0f}-{p75:.0f} ms)",
)

# Mean + median verticals — distinct line styles.
ax.axvline(
    mean,
    color="dc.teal5",
    linewidth=dm.lw(0),
    linestyle="-",
    label=f"Mean = {mean:.0f} ms",
)
ax.axvline(
    median,
    color="dc.teal5",
    linewidth=dm.lw(0),
    linestyle=":",
    label=f"Median = {median:.0f} ms",
)

# SLA threshold — the headline.
ax.axvline(
    sla_threshold,
    color="dc.amber5",
    linewidth=0.5,
    linestyle="--",
    label=f"SLA = {sla_threshold:.0f} ms",
)
ax.text(
    sla_threshold + 8,
    ax.get_ylim()[1] * 0.9 if False else 320,
    f"{breach_rate:.1f}% breach SLA",
    fontsize=dm.fs(-1),
    color=dm.ensure_contrast("dc.amber5", ax.get_facecolor()),  # 4.5:1 text
    fontstyle="italic",
)

ax.set_xlim(0, samples.max() * 1.02)
ax.set_xlabel("Response time (ms)")
ax.set_ylabel("Frequency")

ax.legend(loc="upper right", fontsize=dm.fs(-1), frameon=False)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
if issues:
    print(f"[histogram-advanced] quality issues: {issues}")

dm.save_formats(fig, "histogram_advanced")
