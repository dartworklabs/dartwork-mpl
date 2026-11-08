"""
3D Surface (Advanced)
=====================

3D surface — advanced template (gaussian-mixture surface + colorbar + viewing angle).

Source: ``dartwork_mpl/asset/prompt/05-templates/advanced/plot_3d.py`` ·
MCP ``dartwork-mpl://template/advanced/plot_3d``.
"""

# ai-template-meta-start
# tier: advanced
# basic_counterpart: plot_3d
# use_case: 3D surface of a gaussian-mixture landscape with colorbar and clean viewing angle
# difficulty: advanced
# data_shape: X: 2D array, Y: 2D array, Z: 2D array
# tags: 3d, surface, gaussian, colorbar, narrative
# narrative: Energy landscape with two minima; viewing angle chosen to show both
# advanced_apis: projection=3d, plot_surface with viridis cmap, view_init(elev=25, azim=-60), colorbar with formatter
# ai-template-meta-end

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("scientific")

# Two-gaussian "valley" landscape (Z = -sum of gaussians).
x = np.linspace(-3, 3, 80)
y = np.linspace(-3, 3, 80)
X, Y = np.meshgrid(x, y)
peaks = [(-1.0, -0.5, 1.0, 0.7), (1.2, 1.0, 0.8, 0.55)]
Z = np.zeros_like(X)
for cx, cy, amp, sigma in peaks:
    Z -= amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma**2))

fig = plt.figure(figsize=dm.figsize_for("matrix"))
ax = fig.add_subplot(111, projection="3d")

# Round the colour range out to a 0.1 step so the colorbar ticks read
# -1.0 … 0.0 like the z axis, not -0.75, -0.50 … crowded on a slide.
surf = ax.plot_surface(
    X,
    Y,
    Z,
    cmap="viridis",
    vmin=np.floor(Z.min() * 10) / 10,
    vmax=np.ceil(Z.max() * 10) / 10,
    edgecolor="none",
    alpha=0.95,
    rstride=2,
    cstride=2,
)
# Light wireframe overlay for depth cues.
ax.plot_wireframe(
    X, Y, Z, color="white", linewidth=0.2, rcount=10, ccount=10, alpha=0.4
)

ax.view_init(elev=25, azim=-60)
ax.set_xlabel("x", fontsize=dm.fs(-1))
ax.set_ylabel("y", fontsize=dm.fs(-1))
ax.set_zlabel("z (energy)", fontsize=dm.fs(-1))
ax.tick_params(labelsize=dm.fs(-2))

# Mark the two minima.
for i, (cx, cy, _, _) in enumerate(peaks):
    zmin = float(Z[(np.abs(y - cy)).argmin(), (np.abs(x - cx)).argmin()])
    ax.scatter(
        cx,
        cy,
        zmin,
        s=40,
        color="dc.amber5",
        edgecolor="white",
        linewidth=0.5,
        depthshade=False,
    )
    ax.text(
        cx,
        cy,
        zmin - 0.15,
        f"Min {i + 1}",
        fontsize=dm.fs(-1),
        color="dc.amber5",
        ha="center",
    )

# Colorbar on top, in the space the cube leaves above it: the z axis's
# ticks and name reach past the axes on the right, where a side colorbar
# would cover them at any preset's text size.
cbar = fig.colorbar(
    surf, ax=ax, location="top", fraction=0.04, pad=0.02, shrink=0.7
)
cbar.set_label("z", fontsize=dm.fs(-1))
cbar.ax.tick_params(labelsize=dm.fs(-1))
cbar.outline.set_linewidth(0.3)

dm.simple_layout(fig, margin=dm.inch(0.12))
dm.validate_with_fixes(fig)

issues = dm.check_figure_quality(fig)
# 3D axes report many "Missing/No data" false positives.
issues = [i for i in issues if "No data" not in i and "Missing" not in i]
if issues:
    print(f"[plot_3d-advanced] quality issues: {issues}")

dm.save_formats(fig, "plot_3d_advanced")
