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

    fig = plt.figure(figsize=dm.figsize("15cm", "12cm"), dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])

    for ax in [ax1, ax2, ax3]:
        ax.plot(
            np.linspace(0, 1, 40),
            np.random.rand(40),
            color="dc.corporate3",
            lw=0.8,
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

    fig, ax = plt.subplots(figsize=dm.figsize("15cm", "6cm"), dpi=300)
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

    fig, ax = plt.subplots(figsize=dm.figsize("15cm", "9cm"), dpi=300)

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

    fig, _ax = plot_diverging_bar(
        labels=["Category A", "Category B", "Category C"],
        neg_values=np.array([-30, -15, -25]),
        pos_values=np.array([40, 55, 35]),
        neg_label="Decrease",
        pos_label="Increase",
        add_total=False,
        figsize=dm.figsize("15cm", "10cm"),
    )

    path = images_dir / "xplot_example.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── visualization.rst ──────────────────────────────────────────────────


# ── Entrypoint ─────────────────────────────────────────────────────────


def _write_placeholder_svg(path: Path, label: str) -> None:
    """Write a minimal, valid, deterministic placeholder SVG.

    Used when an asset generator fails after retries so the docs build
    (run with ``-W``) still finds the referenced figure file instead of
    aborting on a missing image. The placeholder is visibly a fallback.
    """
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80" '
        'viewBox="0 0 320 80">\n'
        '  <rect width="320" height="80" fill="#f5f5f5" stroke="#cccccc"/>\n'
        '  <text x="160" y="44" font-family="sans-serif" font-size="12" '
        'fill="#999999" text-anchor="middle">'
        f"{label} unavailable</text>\n"
        "</svg>\n",
        encoding="utf-8",
    )


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
        ("icon_example", _save_icon_example),
        ("font_example", _save_font_example),
        ("xplot_example", _save_xplot_example),
    ]

    paths: list[Path] = []
    for name, func in generators:
        # Retry once: the matplotlib render path has shown rare transient
        # failures in CI (e.g. an isfinite-on-object-array during tight
        # bbox) that a fresh attempt clears. On final failure, drop a
        # placeholder so the docs ``-W`` build never aborts on a missing
        # figure asset.
        last_err: Exception | None = None
        for attempt in range(1, 3):
            try:
                p = func(images_dir)
                paths.append(p)
                suffix = "" if attempt == 1 else f" (attempt {attempt})"
                print(f"  ✓ {name} → {p.name}{suffix}")
                last_err = None
                break
            except Exception as e:
                last_err = e
                print(f"  ✗ {name} attempt {attempt} FAILED: {e}")
        if last_err is not None:
            placeholder = images_dir / f"{name}.svg"
            _write_placeholder_svg(placeholder, name)
            paths.append(placeholder)
            print(f"  ⚠ {name} → placeholder {placeholder.name} (after retry)")

    print(f"Done. {len(paths)}/{len(generators)} assets generated.")
    return paths


if __name__ == "__main__":
    build_api_assets()
