"""Landing-page hero PoCs: vanilla matplotlib ↔ dartwork-mpl pairs.

Generates a deliberately varied set of "ugly default → publication-ready"
comparisons so the maintainer can pick the one (or two) that should
headline the landing page. Each PoC plots **the same data** twice:

1. ``*_before.svg`` — bare ``matplotlib.pyplot`` defaults, with the
   little user habits that make most quick-script charts look rough
   (saturated C0/C1, default font, no margin discipline, raw tick text,
   stock legend, etc.).
2. ``*_after.svg`` — the exact same plotting code wrapped with
   ``dm.style.use("scientific")``, ``dm.figsize(...)``, ``dm.lw``,
   ``dc.*`` colors, and ``dm.simple_layout(fig)`` at the end.

The pairs span a deliberate complexity ladder so the user can see what
the package looks like across a representative slice of real workflows.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
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

# Vanilla figures are saved at the same physical width as the dartwork
# versions so the slider in the landing page can crossfade them
# pixel-for-pixel. We pick a single "natural" landing-page width.
LANDING_W = "15cm"
LANDING_W_IN = dm.figsize(LANDING_W, "wide")[0]  # inches


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
    out_svg = OUT / f"{name}.svg"
    fig.savefig(out_svg, format="svg", bbox_inches="tight")
    out_png = OUT / f"{name}.png"
    fig.savefig(out_png, format="png", dpi=140, bbox_inches="tight")
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


# ---------------------------------------------------------------------------
# PoC 1 — Single-line time series (lowest complexity)
# ---------------------------------------------------------------------------


def poc_01_line_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        ax.plot(t_fine, signal_noisy, label="signal")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Amplitude")
        ax.set_title("Sensor reading")
        ax.legend()
        fig.tight_layout()
        save(fig, "poc_01_line_before")


def poc_01_line_after():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    ax.plot(
        t_fine, signal_noisy, label="signal", color="dc.ocean3", lw=dm.lw(0.5)
    )
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Amplitude")
    ax.legend(frameon=False)
    dm.simple_layout(fig)
    save(fig, "poc_01_line_after")


# ---------------------------------------------------------------------------
# PoC 2 — Grouped bar with value labels
# ---------------------------------------------------------------------------


def poc_02_bar_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        idx = np.arange(len(categories))
        w = 0.38
        b1 = ax.bar(idx - w / 2, values_a, w, label="2024")
        b2 = ax.bar(idx + w / 2, values_b, w, label="2025")
        ax.set_xticks(idx, categories)
        ax.set_ylabel("Throughput")
        ax.set_title("Throughput by cohort")
        ax.legend()
        ax.bar_label(b1, fontsize=8)
        ax.bar_label(b2, fontsize=8)
        fig.tight_layout()
        save(fig, "poc_02_bar_before")


def poc_02_bar_after():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    idx = np.arange(len(categories))
    w = 0.38
    b1 = ax.bar(
        idx - w / 2,
        values_a,
        w,
        label="2024",
        color="dc.ocean1",
        edgecolor="none",
    )
    b2 = ax.bar(
        idx + w / 2,
        values_b,
        w,
        label="2025",
        color="dc.ocean3",
        edgecolor="none",
    )
    ax.set_xticks(idx, categories)
    ax.set_ylabel("Throughput")
    ax.legend(frameon=False, loc="upper right")
    for bars in (b1, b2):
        ax.bar_label(bars, fontsize=dm.fs(-2), padding=2, color="dc.nordic4")
    ax.set_ylim(0, max(values_a.max(), values_b.max()) * 1.18)
    ax.margins(x=0.04)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    dm.simple_layout(fig)
    save(fig, "poc_02_bar_after")


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


def poc_03_scatter_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.62))
        slope, intercept = _ols(scatter_x, scatter_y)
        xs = np.linspace(scatter_x.min(), scatter_x.max(), 50)
        ax.scatter(scatter_x, scatter_y, label="observations")
        ax.plot(
            xs,
            slope * xs + intercept,
            label=f"y = {slope:.2f}x + {intercept:+.2f}",
        )
        ax.set_xlabel("Feature X")
        ax.set_ylabel("Response Y")
        ax.set_title("Bivariate regression")
        ax.legend()
        fig.tight_layout()
        save(fig, "poc_03_scatter_before")


def poc_03_scatter_after():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.62))
    slope, intercept = _ols(scatter_x, scatter_y)
    xs = np.linspace(scatter_x.min(), scatter_x.max(), 50)
    ax.scatter(
        scatter_x,
        scatter_y,
        s=16,
        alpha=0.7,
        color="dc.ocean3",
        edgecolors="none",
        label="observations",
        zorder=3,
    )
    ax.plot(
        xs,
        slope * xs + intercept,
        color="dc.vivid1",
        lw=dm.lw(0.7),
        label=f"y = {slope:.2f}x + {intercept:+.2f}",
        zorder=5,
    )
    # Light residual lines hint at the fit quality.
    for xi, yi in zip(scatter_x, scatter_y, strict=True):
        yfit = slope * xi + intercept
        ax.plot(
            [xi, xi],
            [yi, yfit],
            color="dc.nordic1",
            lw=dm.lw(-0.3),
            alpha=0.45,
            zorder=2,
        )
    ax.set_xlabel("Feature X")
    ax.set_ylabel("Response Y")
    ax.legend(frameon=False, loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    dm.simple_layout(fig)
    save(fig, "poc_03_scatter_after")


# ---------------------------------------------------------------------------
# PoC 4 — Dual-axis financial/operational dashboard
# ---------------------------------------------------------------------------


def poc_04_dual_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        ax.bar(dual_x, dual_revenue, label="Revenue")
        ax.set_ylabel("Revenue")
        ax2 = ax.twinx()
        ax2.plot(
            dual_x,
            dual_margin,
            marker="o",
            color="orange",
            label="Operating margin (%)",
        )
        ax2.set_ylabel("Operating margin (%)")
        ax.set_xlabel("Fiscal year")
        ax.set_title("Revenue vs operating margin")
        ax.legend(loc="upper left")
        ax2.legend(loc="upper right")
        fig.tight_layout()
        save(fig, "poc_04_dual_before")


def poc_04_dual_after():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    ax.bar(
        dual_x,
        dual_revenue,
        color="dc.ocean1",
        edgecolor="none",
        label="Revenue",
        zorder=2,
    )
    ax.set_ylabel("Revenue [$M]")
    ax.set_xlabel("Fiscal year")
    ax.set_xticks(dual_x)
    ax.set_xticklabels([f"'{str(y)[-2:]}" for y in dual_x])
    ax.spines["top"].set_visible(False)

    ax2 = ax.twinx()
    ax2.plot(
        dual_x,
        dual_margin,
        marker="o",
        color="dc.autumn3",
        markersize=4,
        lw=dm.lw(0.5),
        label="Operating margin",
        zorder=5,
    )
    ax2.set_ylabel("Operating margin [%]", color="dc.autumn3")
    ax2.tick_params(axis="y", colors="dc.autumn3")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color("dc.autumn3")

    # Combined legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    dm.simple_layout(fig)
    save(fig, "poc_04_dual_after")


# ---------------------------------------------------------------------------
# PoC 5 — 2x2 small multiples (mid complexity)
# ---------------------------------------------------------------------------


def poc_05_panels_before():
    with vanilla():
        fig, axes = plt.subplots(
            2, 2, figsize=(LANDING_W_IN, LANDING_W_IN * 0.70)
        )
        x = np.linspace(0, 10, 80)
        rng_local = np.random.default_rng(11)
        for k, ax in enumerate(axes.flat):
            y = np.sin(x + k * 0.6) + rng_local.normal(scale=0.18, size=x.size)
            ax.plot(x, y, label=f"series {k + 1}")
            ax.set_title(f"Channel {k + 1}")
            ax.set_xlabel("Time")
            ax.set_ylabel("Value")
            ax.legend()
        fig.tight_layout()
        save(fig, "poc_05_panels_before")


def poc_05_panels_after():
    dm.style.use("scientific")
    fig, axes = plt.subplots(
        2,
        2,
        figsize=dm.figsize(LANDING_W, 0.70),
        gridspec_kw={"hspace": 0.55, "wspace": 0.3},
    )
    palette = ["dc.ocean3", "dc.forest2", "dc.sunset1", "dc.cyber3"]
    x = np.linspace(0, 10, 80)
    rng_local = np.random.default_rng(11)
    for k, (ax, color) in enumerate(zip(axes.flat, palette, strict=True)):
        y = np.sin(x + k * 0.6) + rng_local.normal(scale=0.18, size=x.size)
        ax.plot(x, y, color=color, lw=dm.lw(0.5))
        ax.set_xlabel("Time", fontsize=dm.fs(-1))
        ax.set_ylabel("Value", fontsize=dm.fs(-1))
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    dm.label_axes(axes.flat, fontsize=dm.fs(0), fontweight="bold")
    dm.simple_layout(fig)
    save(fig, "poc_05_panels_after")


# ---------------------------------------------------------------------------
# PoC 6 — Stacked area / composition over time
# ---------------------------------------------------------------------------


def poc_06_stacked_before():
    with vanilla():
        x = np.arange(2018, 2027)
        a = np.array([20, 24, 27, 30, 36, 41, 48, 52, 58])
        b = np.array([15, 18, 19, 22, 25, 28, 32, 36, 40])
        c = np.array([5, 7, 9, 12, 17, 22, 28, 34, 41])
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        ax.stackplot(x, a, b, c, labels=["product A", "product B", "product C"])
        ax.set_title("Revenue mix by product")
        ax.set_xlabel("Year")
        ax.set_ylabel("Revenue")
        ax.legend(loc="upper left")
        fig.tight_layout()
        save(fig, "poc_06_stacked_before")


def poc_06_stacked_after():
    dm.style.use("scientific")
    x = np.arange(2018, 2027)
    a = np.array([20, 24, 27, 30, 36, 41, 48, 52, 58])
    b = np.array([15, 18, 19, 22, 25, 28, 32, 36, 40])
    c = np.array([5, 7, 9, 12, 17, 22, 28, 34, 41])
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    ax.stackplot(
        x,
        a,
        b,
        c,
        labels=["product A", "product B", "product C"],
        colors=["dc.ocean2", "dc.forest2", "dc.sunset1"],
        edgecolor="white",
        lw=dm.lw(-0.5),
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue [$M]")
    ax.set_xticks(x)
    ax.set_xticklabels([f"'{str(y)[-2:]}" for y in x])
    ax.margins(x=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    dm.simple_layout(fig)
    save(fig, "poc_06_stacked_after")


# ---------------------------------------------------------------------------
# PoC 7 — Annotated heatmap
# ---------------------------------------------------------------------------


def poc_07_heatmap_before():
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        im = ax.imshow(heatmap, cmap="viridis", aspect="auto")
        ax.set_xticks(
            np.arange(len(heat_col_labels)), heat_col_labels, rotation=45
        )
        ax.set_yticks(np.arange(len(heat_row_labels)), heat_row_labels)
        ax.set_title("Sales heat by region & quarter")
        for i in range(heatmap.shape[0]):
            for j in range(heatmap.shape[1]):
                ax.text(
                    j,
                    i,
                    f"{heatmap[i, j]:.0f}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=7,
                )
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        save(fig, "poc_07_heatmap_before")


def poc_07_heatmap_after():
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    cmap = plt.colormaps["dc.deep_sea"]
    im = ax.imshow(heatmap, cmap=cmap, aspect="auto")
    ax.set_xticks(
        np.arange(len(heat_col_labels)),
        heat_col_labels,
        rotation=45,
        ha="right",
    )
    ax.set_yticks(np.arange(len(heat_row_labels)), heat_row_labels)
    norm = plt.Normalize(vmin=heatmap.min(), vmax=heatmap.max())
    for i in range(heatmap.shape[0]):
        for j in range(heatmap.shape[1]):
            v = heatmap[i, j]
            text_color = "white" if norm(v) > 0.45 else "#1a2a3a"
            ax.text(
                j,
                i,
                f"{v:.0f}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=dm.fs(-2),
                fontweight="bold",
            )
    ax.tick_params(axis="both", which="both", length=0)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0)
    dm.simple_layout(fig)
    save(fig, "poc_07_heatmap_after")


# ---------------------------------------------------------------------------
# PoC 8 — Distribution comparison (violin + strip + median markers)
# ---------------------------------------------------------------------------


def poc_08_distribution_before():
    rng_local = np.random.default_rng(23)
    groups = [
        rng_local.normal(loc=45, scale=8, size=140),
        rng_local.normal(loc=58, scale=11, size=140),
        rng_local.normal(loc=53, scale=6, size=140),
        rng_local.normal(loc=66, scale=9, size=140),
    ]
    labels = ["Cohort A", "Cohort B", "Cohort C", "Cohort D"]
    with vanilla():
        fig, ax = plt.subplots(figsize=(LANDING_W_IN, LANDING_W_IN * 0.55))
        ax.violinplot(groups, showmedians=True)
        ax.set_xticks(range(1, len(labels) + 1), labels)
        ax.set_ylabel("Measurement")
        ax.set_title("Group comparison")
        fig.tight_layout()
        save(fig, "poc_08_distribution_before")


def poc_08_distribution_after():
    dm.style.use("scientific")
    rng_local = np.random.default_rng(23)
    groups = [
        rng_local.normal(loc=45, scale=8, size=140),
        rng_local.normal(loc=58, scale=11, size=140),
        rng_local.normal(loc=53, scale=6, size=140),
        rng_local.normal(loc=66, scale=9, size=140),
    ]
    labels = ["Cohort A", "Cohort B", "Cohort C", "Cohort D"]
    palette = ["dc.ocean2", "dc.forest2", "dc.sunset1", "dc.vivid1"]
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W, 0.55))
    parts = ax.violinplot(
        groups, showmedians=False, showextrema=False, widths=0.7
    )
    for body, color in zip(parts["bodies"], palette, strict=True):
        body.set_facecolor(mcolors.to_rgba(color, 0.32))
        body.set_edgecolor(color)
        body.set_linewidth(dm.lw(-0.3))
    for i, (g, color) in enumerate(zip(groups, palette, strict=True), start=1):
        jitter = (rng_local.random(g.size) - 0.5) * 0.18
        ax.scatter(
            np.full(g.size, i) + jitter,
            g,
            s=4,
            alpha=0.55,
            color=color,
            edgecolors="none",
            zorder=4,
        )
        median = float(np.median(g))
        ax.hlines(
            median,
            i - 0.18,
            i + 0.18,
            color="dc.nordic5",
            lw=dm.lw(0.6),
            zorder=6,
        )
        ax.text(
            i + 0.22,
            median,
            f"{median:.1f}",
            fontsize=dm.fs(-2),
            color="dc.nordic4",
            va="center",
        )
    ax.set_xticks(range(1, len(labels) + 1), labels)
    ax.set_ylabel("Measurement")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    dm.simple_layout(fig)
    save(fig, "poc_08_distribution_after")


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
    for slug, label, fn_before, fn_after in POCS:
        print(f"\n=== {label} ===")
        fn_before()
        print(f"  ✓ {slug}_before.svg")
        fn_after()
        print(f"  ✓ {slug}_after.svg")
        results.append({"slug": slug, "label": label})

    # Manifest the preview page can iterate over.
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nWrote {manifest_path}")


if __name__ == "__main__":
    main()
