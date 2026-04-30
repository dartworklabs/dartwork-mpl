"""
Generate SVG/PNG figures for API reference code examples.

Each function produces one figure matching a code block in the API docs.
Run standalone or via Sphinx build hooks.

    python docs/api/generate_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import dartwork_mpl as dm  # noqa: E402


def _prepare_images_dir(base_dir: Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else Path(__file__).parent
    images_dir = base / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


# ── layout.rst ─────────────────────────────────────────────────────────


def _save_layout_example(images_dir: Path) -> Path:
    """API layout: 2×2-panel with label_axes, arrow_axis, set_decimal."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig = plt.figure(figsize=(dm.cm(15), dm.cm(12)), dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])

    for ax in [ax1, ax2, ax3]:
        ax.plot(
            np.linspace(0, 1, 40), np.random.rand(40), color="oc.blue6", lw=0.8
        )

    # Hide the 4th subplot (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")

    dm.label_axes([ax1, ax2, ax3])
    dm.simple_layout(fig, gs=gs)
    dm.set_decimal(ax1, xn=2, yn=1)
    dm.arrow_axis(ax2, "x", "Installation cost")
    dm.arrow_axis(ax3, "y", "Information richness")

    path = images_dir / "layout_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── color.rst ──────────────────────────────────────────────────────────


def _save_color_example(images_dir: Path) -> Path:
    """API color: mix_colors, pseudo_alpha, cspace, Color class."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig = plt.figure(figsize=(dm.cm(15), dm.cm(12)), dpi=300)
    gs = fig.add_gridspec(
        2, 1, hspace=0.4, left=0.08, right=0.98, top=0.92, bottom=0.08
    )

    # Top: named + mix + pseudo_alpha
    ax1 = fig.add_subplot(gs[0])
    x = np.linspace(0, 2 * np.pi, 100)
    ax1.plot(x, np.sin(x), color="oc.blue5", lw=1.5, label="oc.blue5")
    lighter = dm.mix_colors("oc.blue5", "white", alpha=0.35)
    ax1.fill_between(x, np.sin(x), alpha=0.9, color=lighter, label="mix_colors")
    muted = dm.pseudo_alpha("oc.blue7", alpha=0.6)
    ax1.plot(x, np.cos(x), color=muted, lw=1.5, label="pseudo_alpha")
    ax1.legend(fontsize=dm.fs(-1), ncol=3, frameon=False)
    ax1.set_title("Color Utilities", fontsize=dm.fs(1))

    # Bottom: cspace interpolation bars
    ax2 = fig.add_subplot(gs[1])
    palette = dm.cspace("#FF6B6B", "#4ECDC4", n=8, space="oklch")
    for i, c in enumerate(palette):
        ax2.bar(i, 1, color=c.to_hex(), edgecolor="white", lw=0.5)
    ax2.set_xlim(-0.6, 7.6)
    ax2.set_ylim(0, 1.05)
    ax2.set_yticks([])
    ax2.set_xticks(range(8))
    ax2.set_xticklabels([c.to_hex() for c in palette], fontsize=dm.fs(-2))
    ax2.set_title("cspace() — OKLCH interpolation", fontsize=dm.fs(1))
    for spine in ax2.spines.values():
        spine.set_visible(False)

    dm.simple_layout(fig, gs=gs)

    path = images_dir / "color_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── icon.rst ───────────────────────────────────────────────────────────


def _save_icon_example(images_dir: Path) -> Path:
    """API icon: MDI icon font rendering on matplotlib axes."""
    import warnings

    warnings.filterwarnings(
        "ignore", message=".*missing from font.*Material Design Icons.*"
    )

    dm.style.use("presentation")

    mdi = dm.icon_font("mdi")

    # A few recognizable MDI codepoints
    icons = [
        ("\U000f050f", "Thermometer"),
        ("\U000f0590", "Weather-sunny"),
        ("\U000f058e", "Weather-cloudy"),
        ("\U000f0599", "Weather-windy"),
        ("\U000f0597", "Weather-snowy"),
    ]

    fig, ax = plt.subplots(figsize=(dm.cm(15), dm.cm(6)), dpi=300)
    colors = [
        "tw.teal500",
        "tw.amber500",
        "tw.slate400",
        "tw.sky500",
        "tw.blue300",
    ]

    for i, (glyph, label) in enumerate(icons):
        ax.text(
            i,
            0.5,
            glyph,
            fontproperties=mdi,
            fontsize=28,
            ha="center",
            va="center",
            color=colors[i],
        )
        ax.text(
            i,
            -0.1,
            label,
            ha="center",
            va="top",
            fontsize=dm.fs(-1),
            color="#666",
        )

    ax.set_xlim(-0.7, len(icons) - 0.3)
    ax.set_ylim(-0.5, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(
        "Icon Font: Material Design Icons (MDI)",
        fontsize=dm.fs(1),
        fontweight="bold",
    )
    dm.simple_layout(fig)

    path = images_dir / "icon_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── font.rst ───────────────────────────────────────────────────────────


def _save_font_example(images_dir: Path) -> Path:
    """API font: fs(), fw(), lw() scaling demo."""
    dm.style.use("presentation")

    fig, ax = plt.subplots(figsize=(dm.cm(15), dm.cm(9)), dpi=300)

    # Show hierarchy levels
    levels = [
        (0.9, f"fs(6) = {dm.fs(6):.1f}pt — Title", dm.fs(6), dm.fw(4)),
        (0.72, f"fs(3) = {dm.fs(3):.1f}pt — Subtitle", dm.fs(3), dm.fw(2)),
        (0.54, f"fs(0) = {dm.fs(0):.1f}pt — Body / Labels", dm.fs(0), dm.fw(0)),
        (
            0.36,
            f"fs(-1) = {dm.fs(-1):.1f}pt — Annotations",
            dm.fs(-1),
            dm.fw(0),
        ),
        (
            0.18,
            f"fs(-2) = {dm.fs(-2):.1f}pt — Fine print",
            dm.fs(-2),
            dm.fw(-1),
        ),
    ]

    for y, text, fsize, fweight in levels:
        ax.text(
            0.05,
            y,
            text,
            fontsize=fsize,
            fontweight=fweight,
            transform=ax.transAxes,
            va="center",
            color="#333",
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(
        "Typography Scaling: fs(), fw()", fontsize=dm.fs(2), fontweight="bold"
    )
    dm.simple_layout(fig)

    path = images_dir / "font_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── xplot.rst ──────────────────────────────────────────────────────────


def _save_xplot_example(images_dir: Path) -> Path:
    """API xplot/templates: diverging bar chart."""
    dm.style.use("presentation")
    from dartwork_mpl.templates import plot_diverging_bar

    fig, ax = plot_diverging_bar(
        labels=["Category A", "Category B", "Category C"],
        neg_values=np.array([-30, -15, -25]),
        pos_values=np.array([40, 55, 35]),
        neg_label="Decrease",
        pos_label="Increase",
        add_total=False,
        figsize=(dm.cm(15), dm.cm(10)),
    )

    path = images_dir / "xplot_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── visualization.rst ──────────────────────────────────────────────────


def _save_viz_example(images_dir: Path) -> Path:
    """API visualization: compact plot_colors preview (SVG)."""
    dm.style.use("presentation")

    figs = dm.plot_colors(ncols=5, sort_colors=True)
    if figs:
        fig = figs[0]
        fig.set_size_inches(dm.cm(15), dm.cm(10))
        path = images_dir / "viz_example.svg"
        fig.savefig(path, format="svg", bbox_inches="tight")
        for f in figs:
            plt.close(f)
        return path
    return images_dir / "viz_example.svg"


# ── Entrypoint ─────────────────────────────────────────────────────────


def build_api_assets(base_dir: Path | None = None) -> list[Path]:
    """Generate all API reference figures.

    Parameters
    ----------
    base_dir : Path | None
        Override for the output base directory.
        Defaults to the directory containing this script.

    Returns
    -------
    list[Path]
        Paths to all generated files.
    """
    images_dir = _prepare_images_dir(base_dir)
    print(f"Generating API assets in {images_dir} ...")

    generators = [
        ("layout_example", _save_layout_example),
        ("color_example", _save_color_example),
        ("icon_example", _save_icon_example),
        ("font_example", _save_font_example),
        ("xplot_example", _save_xplot_example),
        ("viz_example", _save_viz_example),
    ]

    paths: list[Path] = []
    for name, func in generators:
        try:
            p = func(images_dir)
            paths.append(p)
            print(f"  ✓ {name} → {p.name}")
        except Exception as e:
            print(f"  ✗ {name} FAILED: {e}")

    print(f"Done. {len(paths)}/{len(generators)} assets generated.")
    return paths


if __name__ == "__main__":
    build_api_assets()
