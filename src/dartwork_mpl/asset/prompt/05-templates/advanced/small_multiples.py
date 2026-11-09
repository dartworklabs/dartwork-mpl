"""Small multiples — advanced template (6 panels + label_axes + shared y)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: small_multiples
# use_case: Same KPI trend across 6 product lines with panel IDs (a)-(f) and a shared y-axis
# difficulty: advanced
# data_shape: groups: dict[str, list[float]], x: list[float]
# tags: small-multiples, panel-ids, shared-axes, narrative
# narrative: 24-month KPI trend across 6 product lines; sharey reveals the relative wins
# advanced_apis: dm.grid_shape + dm.figsize_for(nrows, ncols) for the 2 x 3 grid, plt.subplots(sharey=True), dm.label_axes for (a)-(f), per-panel sub-title, fig.supxlabel/supylabel
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

rng = np.random.default_rng(42)
months = np.arange(24)

# Six product lines with different growth profiles.
lines = {
    "Line A": 50 + 0.6 * months + rng.normal(0, 1.2, 24),
    "Line B": 50 + 1.4 * months + rng.normal(0, 1.5, 24),
    "Line C": 50 + 0.1 * months + rng.normal(0, 1.0, 24),
    "Line D": 60 - 0.4 * months + rng.normal(0, 1.6, 24),  # declining
    "Line E": 50 + 0.8 * months + rng.normal(0, 1.0, 24),
    "Line F": 50 + 2.1 * months + rng.normal(0, 2.0, 24),  # rocket
}

gradient = dm.cspace("dc.teal5", "dc.teal1", n=len(lines))
colors = [c.to_hex() for c in gradient]

nrows, ncols = dm.grid_shape(len(lines))
fig, axes = plt.subplots(
    nrows,
    ncols,
    figsize=dm.figsize_for(nrows=nrows, ncols=ncols),
    sharex=True,
    sharey=True,
)
axes_flat = axes.flatten()

for i, (name, vals) in enumerate(lines.items()):
    ax = axes_flat[i]
    ax.plot(months, vals, color=colors[i], linewidth=dm.lw(0))
    ax.fill_between(months, vals, vals.min(), color=colors[i], alpha=0.08)
    # The preset's title pad (6 pt, 15.6 pt on slides) keeps the title line,
    # and the panel letter dm.label_axes puts on it, above the top y tick.
    ax.set_title(name, loc="left", fontsize=dm.fs(0), fontweight=dm.fw(1))
    # Per-panel takeaway: total growth.
    delta = vals[-1] - vals[0]
    dm.annotate_corner(
        ax,
        f"Δ {delta:+.0f}",
        loc="upper left",
        fontsize=dm.fs(-1),
        fontweight=dm.fw(1),
        color=dm.ensure_contrast(colors[i], ax.get_facecolor()),  # 4.5:1 text
    )

# Panel IDs (a)-(f) via the dartwork helper (as the template advertises)
# rather than hand-formatted into each title.
dm.label_axes(axes_flat)

# Shared axis labels. dm.simple_layout places them past the tick labels
# and sets the margins and panel gaps for the preset's text size.
fig.supxlabel("Month after launch", fontsize=dm.fs(0))
fig.supylabel("KPI (indexed to 50)", fontsize=dm.fs(0))

dm.simple_layout(fig)
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
issues = [i for i in issues if "No data" not in i and "Missing" not in i]
if issues:
    print(f"[small_multiples-advanced] quality issues: {issues}")

dm.save_formats(fig, "small_multiples_advanced")
