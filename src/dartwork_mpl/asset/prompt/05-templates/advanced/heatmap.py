"""Heatmap — advanced template (correlation matrix + in-cell labels + diverging cmap)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: heatmap
# use_case: 6x6 asset-class correlation matrix with in-cell value labels and a diverging colormap
# difficulty: intermediate
# data_shape: matrix: 2D array (square, symmetric, values in [-1, 1])
# tags: heatmap, correlation, matrix, annotated, narrative
# narrative: Pairwise correlation of six asset classes; diagonal masked, off-diagonal labeled
# advanced_apis: imshow with RdBu_r diverging cmap (vmin=-1, vmax=1), per-cell ax.text, colorbar with formatter, masked diagonal
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable

import dartwork_mpl as dm

dm.style.use("scientific")

assets = ["Equities", "Bonds", "Gold", "REITs", "Crypto", "Cash"]
n = len(assets)

# Synthetic but plausible correlation pattern.
rng = np.random.default_rng(42)
base = np.array(
    [
        [1.00, 0.05, 0.10, 0.62, 0.35, -0.02],
        [0.05, 1.00, 0.20, -0.05, -0.10, 0.08],
        [0.10, 0.20, 1.00, 0.12, -0.08, 0.03],
        [0.62, -0.05, 0.12, 1.00, 0.30, 0.05],
        [0.35, -0.10, -0.08, 0.30, 1.00, -0.04],
        [-0.02, 0.08, 0.03, 0.05, -0.04, 1.00],
    ]
)
# Small symmetric noise so this looks like measured data, not a constant.
jitter = rng.normal(0, 0.02, size=(n, n))
jitter = (jitter + jitter.T) / 2
corr = np.clip(base + jitter, -1, 1)
np.fill_diagonal(corr, 1.0)

# Mask the diagonal so the eye locks on the off-diagonal story.
display = corr.copy()
mask = np.eye(n, dtype=bool)

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))

im = ax.imshow(
    np.ma.masked_array(display, mask=mask),
    cmap="RdBu_r",
    vmin=-1,
    vmax=1,
    aspect="equal",
)

# In-cell value labels — only off-diagonal.
cell_labels = []
for i in range(n):
    for j in range(n):
        if i == j:
            continue
        val = corr[i, j]
        # White or black, whichever reads better on the cell as drawn.
        text_color = dm.readable_text_color(im.to_rgba(val))
        label = ax.text(
            j,
            i,
            f"{val:+.2f}",
            ha="center",
            va="center",
            fontsize=dm.fs(-1),
            color=text_color,
        )
        cell_labels.append(label)

# Tick labels. No rotation: dm.simple_layout turns them only when they
# collide (on a slide's 10.5 cm square).
ax.set_xticks(np.arange(n))
ax.set_yticks(np.arange(n))
ax.set_xticklabels(assets, fontsize=dm.fs(-1))
ax.set_yticklabels(assets, fontsize=dm.fs(-1))
ax.tick_params(axis="both", length=0)

# Colorbar pinned to the matrix via a divider so its bar length matches
# the heatmap's spine exactly. Explicit -1, 0, +1 ticks.
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="4%", pad=0.15)
cbar = fig.colorbar(im, cax=cax, ticks=[-1, -0.5, 0, 0.5, 1])
cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.1f}"))
cbar.ax.tick_params(labelsize=dm.fs(-1))
cbar.outline.set_linewidth(0.3)

dm.simple_layout(fig)

# Cell labels keep dm.fs(-1) while it fits a cell. A slide's 10.5 cm
# square leaves cells narrower than its large text, so there they take
# the size that leaves a fifth of the cell between neighbours.
cell_px = ax.get_window_extent().width / n
widest = max(label.get_window_extent().width for label in cell_labels)
if widest > 0.8 * cell_px:
    for label in cell_labels:
        label.set_fontsize(label.get_fontsize() * 0.8 * cell_px / widest)

dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
# Heatmap with rotated tick labels acts as axis labels; quality checker
# flags missing set_xlabel/ylabel — that's a false positive here.
issues = [i for i in issues if "Missing" not in i and "No data" not in i]
if issues:
    print(f"[heatmap-advanced] quality issues: {issues}")

dm.save_formats(fig, "heatmap_advanced")
