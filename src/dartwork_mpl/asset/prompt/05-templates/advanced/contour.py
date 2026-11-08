"""Contour — advanced template (filled + line overlay + peak callouts)."""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: contour
# use_case: 2D scalar field with filled contour + line overlay + peak annotations
# difficulty: advanced
# data_shape: x: 1D array, y: 1D array, z: 2D array
# tags: contour, 2d-scalar, peaks, annotated, narrative
# narrative: gaussian-mixture landscape with two peaks; both annotated
# advanced_apis: contourf + contour overlay with clabel, ax.scatter on peak coords with annotate, colorbar
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# Two-gaussian energy landscape on a grid.
x = np.linspace(-3, 3, 200)
y = np.linspace(-3, 3, 200)
X, Y = np.meshgrid(x, y)

peaks = [(-1.0, -0.5, 1.0, 0.6), (1.2, 1.0, 0.7, 0.45)]  # cx, cy, amp, sigma
Z = np.zeros_like(X)
for cx, cy, amp, sigma in peaks:
    Z += amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma**2))

fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))

# Filled contour (background) + line contour (foreground) for layering.
# Round the top level up to a 0.1 step so levels, contour labels and
# colorbar ticks read 0.2, 0.4 … instead of 0.3999.
levels = np.linspace(0, np.ceil(Z.max() * 10) / 10, 11)
fill_alpha = 0.85
cf = ax.contourf(X, Y, Z, levels=levels, cmap="viridis", alpha=fill_alpha)
cs = ax.contour(X, Y, Z, levels=levels[::2], colors="white", linewidths=0.3)
# Label every other line (0.2, 0.6), each on the side of its hill away
# from the hill's callout so no arrow runs through a number. matplotlib
# puts a label on the line nearest each point; with other data, move the
# points (or drop ``manual=`` for matplotlib's own placement).
label_levels = levels[2::4]
# Each label in white or black, whichever reads on its band (the 0.85
# fill over the Axes, flattened with dm.pseudo_alpha).
inks = []
for z in label_levels:
    band = dm.pseudo_alpha(cf.to_rgba(z)[:3], fill_alpha, ax.get_facecolor())
    inks.append(dm.readable_text_color(band))
ax.clabel(
    cs,
    levels=label_levels,
    manual=[(-1.5, 0.4), (-1.4, -0.9), (1.9, 1.0)],
    inline=True,
    fontsize=dm.fs(-2),
    fmt="%.1f",
    colors=inks,
)

# Peak markers + callouts. Each callout sits in empty space past its
# hill's outer contour (data coordinates): it clears the contour labels at
# every preset's text size, where a fixed offset from the peak lands on
# them. (x, y, ha, va) of each callout's text.
callout_at = [(0.4, -1.2, "left", "top"), (-0.2, 1.2, "right", "bottom")]
for i, ((cx, cy, amp, _), (tx, ty, ha, va)) in enumerate(
    zip(peaks, callout_at, strict=True)
):
    ax.scatter(
        cx,
        cy,
        s=40,
        color="dc.amber5",
        edgecolor="white",
        linewidth=0.5,
        zorder=5,
        marker="*",
    )
    ax.annotate(
        f"Peak {i + 1}\nz = {amp:.1f}",
        xy=(cx, cy),
        xytext=(tx, ty),
        ha=ha,
        va=va,
        fontsize=dm.fs(-1),
        color="dc.amber5",
        arrowprops={"arrowstyle": "->", "color": "dc.amber5", "lw": 0.5},
    )

ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_aspect("equal")

cbar = fig.colorbar(cf, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("z", fontsize=dm.fs(-1))
cbar.ax.tick_params(labelsize=dm.fs(-1))
cbar.outline.set_linewidth(0.3)

dm.simple_layout(fig, margin=dm.inch(0.08))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
if issues:
    print(f"[contour-advanced] quality issues: {issues}")

dm.save_formats(fig, "contour_advanced")
