"""Landing-page hero PoCs: vanilla matplotlib ↔ dartwork-mpl pairs.

Generates a deliberately varied set of "ugly default → publication-ready"
comparisons so the maintainer can pick the one (or two) that should
headline the landing page. Each PoC plots **the same data** twice:

1. ``*_before.svg`` — bare ``matplotlib.pyplot`` defaults, with the
   little user habits that make most quick-script charts look rough
   (saturated C0/C1, default font, no margin discipline, raw tick text,
   stock legend, etc.).
2. ``*_after.svg`` — the exact same plotting code wrapped with
   ``dm.style.use("report")``, ``dm.figsize(...)``, ``dm.lw``,
   ``dc.*`` colors, and ``dm.simple_layout(fig, margin="2mm")`` at the end.

The pairs span a deliberate complexity ladder so the user can see what
the package looks like across a representative slice of real workflows.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

OUT = (
    Path(__file__).resolve().parent.parent / "docs" / "_static" / "landing_pocs"
)
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Vanilla and dartwork widths are *deliberately different*.
#
# Vanilla preset font size is matplotlib's default 10 pt; dartwork
# `report` preset is 8 pt. When both SVGs are stretched to the same
# container width in the browser, the smaller font would make the
# dartwork side look optically smaller even though both figures
# share the exact same axes contents.
#
# Saving the dartwork figure at 75% of the vanilla width means the
# browser then upscales the dartwork SVG ~33% more than the vanilla
# one, which restores font-size parity (8pt x 1.33 ≈ 10pt x 1.0)
# and lets the slider compare the two on equal optical footing.
LANDING_W = "15cm"  # vanilla
LANDING_W_DM = "11.25cm"  # dartwork (15 * 0.75)
LANDING_W_IN = dm.figsize(LANDING_W, "wide")[0]  # inches — vanilla only


# ---------------------------------------------------------------------------
# Palette variants for the dartwork side
# ---------------------------------------------------------------------------
#
# The `report` preset ships with prop_cycle = dc.0..dc.9 (a vivid mood).
# Each entry below overrides that cycle so the same plotting code yields
# the same chart in a different mood. Six families x 6 shades; the order
# inside each list is deliberately scrambled to put the most saturated
# shade first so the dominant series gets the focal color.

PALETTES: dict[str, list[str] | None] = {
    "default": None,  # report preset's built-in dc.0..9 (vivid mood)
    "ocean": [
        "dc.teal3",
        "dc.teal1",
        "dc.teal5",
        "dc.teal0",
        "dc.teal2",
        "dc.teal4",
    ],
    "forest": [
        "dc.forest3",
        "dc.forest1",
        "dc.forest5",
        "dc.forest0",
        "dc.forest2",
        "dc.forest4",
    ],
    "sunset": [
        "dc.earth2",
        "dc.earth4",
        "dc.earth0",
        "dc.earth5",
        "dc.earth1",
        "dc.earth3",
    ],
    "autumn": [
        "dc.dusty3",
        "dc.dusty1",
        "dc.dusty5",
        "dc.dusty0",
        "dc.dusty2",
        "dc.dusty4",
    ],
    "cyber": [
        "dc.jewel3",
        "dc.jewel1",
        "dc.jewel5",
        "dc.jewel0",
        "dc.jewel2",
        "dc.jewel4",
    ],
    "pop": [
        "dc.vivid3",
        "dc.vivid1",
        "dc.vivid5",
        "dc.vivid0",
        "dc.vivid2",
        "dc.vivid4",
    ],
}


def _apply_palette(name: str) -> None:
    """Override prop_cycle on top of the active style preset."""
    colors = PALETTES.get(name)
    if colors is None:
        return  # keep preset's default cycle
    from cycler import cycler

    matplotlib.rcParams["axes.prop_cycle"] = cycler(color=colors)


@contextmanager
def vanilla():
    """Yield with a *truly* unstyled matplotlib state, then restore."""
    saved = matplotlib.rcParams.copy()
    matplotlib.rcdefaults()
    try:
        yield
    finally:
        matplotlib.rcParams.update(saved)


def save(fig: plt.Figure, name: str) -> Path:
    # Critical: do NOT use bbox_inches="tight". It crops each figure
    # to its own visible content, so the vanilla and dartwork SVGs
    # would end up with different natural sizes (different aspect
    # ratios, even). The slider stacks them; mismatched sizes mean
    # one is letterboxed inside the other, making it look smaller.
    # Saving at the raw figsize keeps both SVGs at exactly the same
    # canvas dimensions, so the wipe compares like-for-like.
    out_svg = OUT / f"{name}.svg"
    fig.savefig(out_svg, format="svg")
    out_png = OUT / f"{name}.png"
    fig.savefig(out_png, format="png", dpi=140)
    plt.close(fig)
    return out_svg


# ---------------------------------------------------------------------------
# Shared data — every PoC uses a deterministic dataset so re-runs are
# pixel-stable.
# ---------------------------------------------------------------------------

rng = np.random.default_rng(7)

t_fine = np.linspace(0, 12, 240)
signal_clean = np.sin(t_fine) * np.exp(-t_fine / 18) + 0.05 * t_fine
signal_noisy = signal_clean + rng.normal(scale=0.06, size=t_fine.size)

categories = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
values_a = np.array([54, 78, 63, 89, 71, 46])
values_b = np.array([42, 71, 80, 62, 88, 55])

scatter_x = rng.normal(size=120)
scatter_y = 1.4 * scatter_x + rng.normal(scale=0.55, size=120)

dual_x = np.arange(2018, 2027)
dual_revenue = np.array([42, 51, 49, 68, 88, 121, 158, 192, 240])
dual_margin = np.array([8.2, 9.1, 7.5, 11.4, 14.0, 16.8, 18.1, 19.6, 21.2])

heatmap = (
    np.abs(
        np.sin(np.linspace(0, 3 * np.pi, 8))[:, None]
        * np.cos(np.linspace(0, 2 * np.pi, 10))[None, :]
    )
    * 100
)
heat_row_labels = [f"Region {chr(65 + i)}" for i in range(8)]
heat_col_labels = [f"Q{q}'{y}" for y in (24, 25) for q in (1, 2, 3, 4, 5)][:10]


# Shared axis limits + tick positions per PoC. Both the vanilla and
# dartwork halves of each pair MUST call `_share_axes(ax, **AX_<N>)`
# so the slider compares identical grids — otherwise matplotlib's
# auto-locator picks different tick counts on the 25%-smaller
# dartwork canvas, and the user sees "different chart" rather than
# "same chart, different style".
def _share_axes(ax, *, xlim=None, ylim=None, xticks=None, yticks=None):
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if xticks is not None:
        ax.set_xticks(xticks)
    if yticks is not None:
        ax.set_yticks(yticks)


AX_L1 = {
    "xlim": (0, 12),
    "ylim": (-0.85, 1.25),
    "xticks": [0, 2, 4, 6, 8, 10, 12],
    "yticks": [-0.5, 0.0, 0.5, 1.0],
}
AX_L2 = {"ylim": (0, 110), "yticks": [0, 20, 40, 60, 80, 100]}
AX_L3 = {
    "xlim": (-3.6, 2.4),
    "ylim": (-5.5, 3.5),
    "xticks": [-3, -2, -1, 0, 1, 2],
    "yticks": [-5, -4, -3, -2, -1, 0, 1, 2, 3],
}
AX_L4 = {"ylim": (0, 270), "yticks": [0, 50, 100, 150, 200, 250]}
AX_L4_RIGHT = {  # twinx (operating margin %)
    "ylim": (6, 23),
    "yticks": [8, 12, 16, 20],
}
AX_L5 = {
    "xlim": (0, 10),
    "ylim": (-1.4, 1.4),
    "xticks": [0, 2, 4, 6, 8, 10],
    "yticks": [-1.0, -0.5, 0.0, 0.5, 1.0],
}
AX_L6 = {"ylim": (0, 150), "yticks": [0, 30, 60, 90, 120, 150]}
AX_L8 = {"ylim": (10, 95), "yticks": [20, 40, 60, 80]}


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------
#
# Each PoC ships a single `_draw_LN(ax)` (or `_draw_LN(fig, ax, ...)`) that
# is called *unchanged* by both the vanilla and the dartwork wrappers. The
# entire visual delta comes from what `dm.style.use("report")` sets in
# rcParams (font, line widths, spine top/right hidden, frameless legend,
# dc.* prop_cycle) and from the layout call (`tight_layout` vs
# `simple_layout`). The plot content — titles, labels, legend entries,
# tick positions, series colors via `C0`/`C1` — is byte-identical.
#
# Vanilla example uses `C0`/`C1` so prop_cycle resolves to matplotlib's
# default tab10 in vanilla and to dartwork-mpl's curated dc.* cycle when
# the `report` preset is active.


# ---------------------------------------------------------------------------
# PoC 1 — Single-line time series (lowest complexity)
# ---------------------------------------------------------------------------


def _draw_l1(ax):
    ax.plot(t_fine, signal_noisy, color="C0", label="signal")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Amplitude")
    ax.set_title("Sensor reading")
    ax.legend(loc="upper right")
    _share_axes(ax, **AX_L1)


def poc_01_line_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l1(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_01_line_before")


def poc_01_line_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l1(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_01_line_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 2 — Grouped bar with value labels
# ---------------------------------------------------------------------------


def _draw_l2(ax):
    idx = np.arange(len(categories))
    w = 0.38
    b1 = ax.bar(idx - w / 2, values_a, w, color="C0", label="2024")
    b2 = ax.bar(idx + w / 2, values_b, w, color="C1", label="2025")
    ax.set_xticks(idx, categories)
    ax.set_ylabel("Throughput")
    ax.set_title("Throughput by cohort")
    ax.legend(loc="upper right")
    ax.bar_label(b1)
    ax.bar_label(b2)
    _share_axes(ax, **AX_L2)


def poc_02_bar_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l2(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_02_bar_before")


def poc_02_bar_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l2(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_02_bar_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 3 — Scatter with regression
# ---------------------------------------------------------------------------


def _ols(x, y):
    n = x.size
    sx, sy = x.sum(), y.sum()
    sxx = (x * x).sum()
    sxy = (x * y).sum()
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _draw_l3(ax):
    slope, intercept = _ols(scatter_x, scatter_y)
    xs = np.linspace(scatter_x.min(), scatter_x.max(), 50)
    ax.scatter(scatter_x, scatter_y, s=10, color="C0", label="observations")
    ax.plot(
        xs,
        slope * xs + intercept,
        color="C1",
        label=f"y = {slope:.2f}x + {intercept:+.2f}",
    )
    ax.set_xlabel("Feature X")
    ax.set_ylabel("Response Y")
    ax.set_title("Bivariate regression")
    ax.legend(loc="upper left")
    _share_axes(ax, **AX_L3)


def poc_03_scatter_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.62))
        _draw_l3(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_03_scatter_before")


def poc_03_scatter_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.62))
    _draw_l3(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_03_scatter_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 4 — Dual-axis financial/operational dashboard
# ---------------------------------------------------------------------------


def _draw_l4(ax):
    ax.bar(dual_x, dual_revenue, color="C0", label="Revenue", zorder=2)
    ax.set_ylabel("Revenue")
    ax.set_xlabel("Fiscal year")
    ax2 = ax.twinx()
    ax2.plot(
        dual_x,
        dual_margin,
        marker="o",
        markersize=3.5,
        color="C1",
        label="Operating margin (%)",
        zorder=5,
    )
    ax2.set_ylabel("Operating margin (%)")
    ax.set_title("Revenue vs operating margin")
    # Combined legend so dual-axis chart shows one legend block.
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    _share_axes(ax, **AX_L4)
    _share_axes(ax2, **AX_L4_RIGHT)


def poc_04_dual_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l4(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_04_dual_before")


def poc_04_dual_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l4(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_04_dual_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 5 — 2x2 small multiples
# ---------------------------------------------------------------------------


def _draw_l5(axes):
    """4-panel mini-dashboard: line, bar, scatter, histogram."""
    rng_local = np.random.default_rng(11)
    ax_line, ax_bar, ax_scatter, ax_hist = axes.flat

    # (a) Line — time-series trend
    x = np.linspace(0, 10, 80)
    y = np.sin(x) + rng_local.normal(scale=0.15, size=x.size)
    ax_line.plot(x, y, color="C0")
    ax_line.set_title("Time series")
    ax_line.set_xlabel("Time")
    ax_line.set_ylabel("Signal")
    ax_line.set_xlim(0, 10)
    ax_line.set_xticks([0, 2, 4, 6, 8, 10])
    ax_line.set_ylim(-1.6, 1.6)
    ax_line.set_yticks([-1, 0, 1])

    # (b) Bar — category breakdown
    cats = ["A", "B", "C", "D", "E"]
    vals = [42, 67, 55, 78, 49]
    ax_bar.bar(cats, vals, color="C1")
    ax_bar.set_title("Category mix")
    ax_bar.set_xlabel("Group")
    ax_bar.set_ylabel("Count")
    ax_bar.set_ylim(0, 90)
    ax_bar.set_yticks([0, 30, 60, 90])

    # (c) Scatter — bivariate correlation
    sx = rng_local.normal(size=80)
    sy = 0.6 * sx + rng_local.normal(scale=0.5, size=80)
    ax_scatter.scatter(sx, sy, s=10, color="C2")
    ax_scatter.set_title("Correlation")
    ax_scatter.set_xlabel("X")
    ax_scatter.set_ylabel("Y")
    ax_scatter.set_xlim(-3, 3)
    ax_scatter.set_xticks([-2, 0, 2])
    ax_scatter.set_ylim(-3, 3)
    ax_scatter.set_yticks([-2, 0, 2])

    # (d) Histogram — distribution
    h = rng_local.normal(loc=50, scale=12, size=400)
    ax_hist.hist(h, bins=20, color="C3", edgecolor="white", linewidth=0.5)
    ax_hist.set_title("Distribution")
    ax_hist.set_xlabel("Value")
    ax_hist.set_ylabel("Count")
    ax_hist.set_xlim(10, 90)
    ax_hist.set_xticks([20, 40, 60, 80])
    ax_hist.set_ylim(0, 60)
    ax_hist.set_yticks([0, 20, 40, 60])


def poc_05_panels_before():
    with vanilla():
        fig, axes = plt.subplots(
            2, 2, figsize=(LANDING_W_IN, LANDING_W_IN * 0.75)
        )
        _draw_l5(axes)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_05_panels_before")


def poc_05_panels_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, axes = plt.subplots(
        2,
        2,
        figsize=dm.figsize(LANDING_W_DM, 0.75),
        gridspec_kw={"hspace": 0.75, "wspace": 0.35},
    )
    _draw_l5(axes)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_05_panels_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 6 — Stacked area / composition over time
# ---------------------------------------------------------------------------


def _draw_l6(ax):
    x = np.arange(2018, 2027)
    a = np.array([20, 24, 27, 30, 36, 41, 48, 52, 58])
    b = np.array([15, 18, 19, 22, 25, 28, 32, 36, 40])
    c = np.array([5, 7, 9, 12, 17, 22, 28, 34, 41])
    ax.stackplot(x, a, b, c, labels=["product A", "product B", "product C"])
    ax.set_title("Revenue mix by product")
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue")
    ax.legend(loc="upper left")
    _share_axes(ax, ylim=AX_L6["ylim"], yticks=AX_L6["yticks"])
    ax.set_xlim(x.min(), x.max())


def poc_06_stacked_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l6(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_06_stacked_before")


def poc_06_stacked_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l6(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_06_stacked_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 7 — Annotated heatmap
# ---------------------------------------------------------------------------


def _draw_l7(fig, ax):
    im = ax.imshow(heatmap, cmap="viridis", aspect="auto")
    ax.set_xticks(np.arange(len(heat_col_labels)), heat_col_labels, rotation=45)
    ax.set_yticks(np.arange(len(heat_row_labels)), heat_row_labels)
    ax.set_title("Sales heat by region & quarter")
    norm = plt.Normalize(vmin=heatmap.min(), vmax=heatmap.max())
    for i in range(heatmap.shape[0]):
        for j in range(heatmap.shape[1]):
            v = heatmap[i, j]
            text_color = "white" if norm(v) > 0.5 else "black"
            ax.text(
                j, i, f"{v:.0f}", ha="center", va="center", color=text_color
            )
    fig.colorbar(im, ax=ax)


def poc_07_heatmap_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l7(fig, ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_07_heatmap_before")


def poc_07_heatmap_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l7(fig, ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_07_heatmap_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# PoC 8 — Distribution comparison (violin)
# ---------------------------------------------------------------------------


def _draw_l8(ax):
    rng_local = np.random.default_rng(23)
    groups = [
        rng_local.normal(loc=45, scale=8, size=140),
        rng_local.normal(loc=58, scale=11, size=140),
        rng_local.normal(loc=53, scale=6, size=140),
        rng_local.normal(loc=66, scale=9, size=140),
    ]
    labels = ["Cohort A", "Cohort B", "Cohort C", "Cohort D"]
    ax.violinplot(groups, showmedians=True)
    ax.set_xticks(range(1, len(labels) + 1), labels)
    ax.set_ylabel("Measurement")
    ax.set_title("Group comparison")
    _share_axes(ax, **AX_L8)


def poc_08_distribution_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        _draw_l8(ax)
        fig.tight_layout(pad=1.3)
        save(fig, "poc_08_distribution_before")


def poc_08_distribution_after(palette: str = ""):
    dm.style.use("report")
    _apply_palette(palette)
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l8(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"poc_08_distribution_after{('_' + palette) if palette else ''}")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

POCS = [
    ("01_line", "L1 · Quick line chart", poc_01_line_before, poc_01_line_after),
    (
        "02_bar",
        "L2 · Grouped bar with labels",
        poc_02_bar_before,
        poc_02_bar_after,
    ),
    (
        "03_scatter",
        "L3 · Scatter + regression",
        poc_03_scatter_before,
        poc_03_scatter_after,
    ),
    (
        "04_dual",
        "L4 · Dual-axis dashboard",
        poc_04_dual_before,
        poc_04_dual_after,
    ),
    (
        "05_panels",
        "L5 · Small multiples (2x2)",
        poc_05_panels_before,
        poc_05_panels_after,
    ),
    (
        "06_stacked",
        "L6 · Stacked area composition",
        poc_06_stacked_before,
        poc_06_stacked_after,
    ),
    (
        "07_heatmap",
        "L7 · Annotated heatmap",
        poc_07_heatmap_before,
        poc_07_heatmap_after,
    ),
    (
        "08_distribution",
        "L8 · Distribution comparison",
        poc_08_distribution_before,
        poc_08_distribution_after,
    ),
]


def main():
    results = []
    palette_names = list(PALETTES.keys())
    for slug, label, fn_before, fn_after in POCS:
        print(f"\n=== {label} ===")
        fn_before()
        print(f"  ✓ {slug}_before.svg")
        for pname in palette_names:
            # `default` uses the preset's built-in cycle; everything else
            # gets the override + a "_<family>" suffix on the filename.
            palette_arg = "" if pname == "default" else pname
            fn_after(palette=palette_arg)
            suffix = "" if palette_arg == "" else f"_{palette_arg}"
            print(f"  ✓ {slug}_after{suffix}.svg")
        results.append({"slug": slug, "label": label})

    # Manifest the preview page can iterate over.
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(
        json.dumps({"pocs": results, "palettes": palette_names}, indent=2)
        + "\n"
    )
    print(f"\nWrote {manifest_path}")


if __name__ == "__main__":
    main()
