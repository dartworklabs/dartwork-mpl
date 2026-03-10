"""
Generate SVG/PNG figures for usage guide code examples.

Each function produces one figure matching a code block in the usage guide docs.
Run standalone or via Sphinx build hooks.

    python docs/usage_guide/generate_assets.py
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


# ── quickstart.md ──────────────────────────────────────────────────────


def _save_quickstart_first_figure(images_dir: Path) -> Path:
    """Quickstart 'First figure': sine wave with oc.blue5."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    x = np.linspace(0, 10, 200)
    ax.plot(x, np.sin(x), color="oc.blue5", label="signal")
    ax.set_xlabel("Time [s]", fontsize=dm.fs(0))
    ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
    ax.legend(fontsize=dm.fs(-1))
    dm.simple_layout(fig)

    path = images_dir / "quickstart_first_figure.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_quickstart_multi_panel(images_dir: Path) -> Path:
    """Quickstart 'Multi-panel layout': 2-panel with label_axes."""
    np.random.seed(42)
    dm.style.use("presentation")

    x = np.linspace(0, 10, 200)
    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(8.5)), dpi=300)
    gs = fig.add_gridspec(1, 2, wspace=0.3)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    ax1.plot(x, np.sin(x), color="oc.red5")
    ax1.set_ylabel("Amplitude", fontsize=dm.fs(0))
    ax2.plot(x, np.cos(x), color="oc.blue5")
    ax2.set_ylabel("Amplitude", fontsize=dm.fs(0))

    for ax in [ax1, ax2]:
        ax.set_xlabel("Time [s]", fontsize=dm.fs(0))

    dm.label_axes([ax1, ax2])
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "quickstart_multi_panel.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── layout.md ──────────────────────────────────────────────────────────


def _make_challenging_figure(use_simple_layout: bool = True) -> plt.Figure:
    """Create a multi-panel figure that exposes tight_layout weaknesses.

    Left panel: line chart with long Y-axis label + title.
    Right panel: heatmap with colorbar.
    Both share an x-label to stress margin negotiation.
    """
    np.random.seed(42)
    dm.style.use("scientific")

    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(8.5)), dpi=300)
    gs = fig.add_gridspec(1, 2, wspace=0.45)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # Left: line chart with long labels
    x = np.linspace(0, 10, 200)
    ax1.plot(x, np.sin(x) * np.exp(-0.1 * x), color="oc.blue6", lw=0.8)
    ax1.set_ylabel("Thermal conductivity\n[W/(m·K)]", fontsize=dm.fs(0))
    ax1.set_xlabel("Time [s]", fontsize=dm.fs(0))
    ax1.set_title("Transient response", fontsize=dm.fs(1))

    # Right: heatmap with colorbar
    data = np.random.randn(8, 8).cumsum(axis=0)
    im = ax2.imshow(data, cmap="dc.Crest", aspect="auto")
    cb = plt.colorbar(im, ax=ax2, shrink=0.85, pad=0.03)
    cb.set_label("Δ Temperature [K]", fontsize=dm.fs(0))
    cb.outline.set_visible(False)
    ax2.set_xlabel("Sensor index", fontsize=dm.fs(0))
    ax2.set_ylabel("Layer", fontsize=dm.fs(0))
    ax2.set_title("Heat distribution", fontsize=dm.fs(1))

    dm.label_axes([ax1, ax2])

    if use_simple_layout:
        dm.simple_layout(fig, gs=gs)
    else:
        fig.tight_layout()

    return fig


def _save_layout_tight(images_dir: Path) -> Path:
    """Layout comparison: tight_layout version."""
    fig = _make_challenging_figure(use_simple_layout=False)
    path = images_dir / "layout_tight.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    return path


def _save_layout_simple(images_dir: Path) -> Path:
    """Layout comparison: simple_layout version."""
    fig = _make_challenging_figure(use_simple_layout=True)
    path = images_dir / "layout_simple.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    return path


def _save_layout_gridspec(images_dir: Path) -> Path:
    """Layout 'Layout optimization': 2×2 GridSpec + panel labels."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(12)), dpi=300)
    gs = fig.add_gridspec(
        2,
        2,
        left=0.08,
        right=0.98,
        top=0.9,
        bottom=0.12,
        hspace=0.35,
        wspace=0.25,
    )
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    for ax in axes:
        ax.plot(
            np.linspace(0, 1, 40), np.random.rand(40), color="oc.blue6", lw=0.8
        )

    dm.label_axes(axes)
    dm.set_decimal(axes[0], xn=2, yn=1)
    dm.simple_layout(fig, gs=gs, margins=(0.05, 0.08, 0.06, 0.08))

    path = images_dir / "layout_gridspec.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_layout_typography(images_dir: Path) -> Path:
    """Layout 'Typography': fs(), fw(), lw() demo."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    x = np.array([0, 1, 2])
    y = np.array([0, 1, 0.4])
    ax.plot(x, y, color="oc.green6", lw=dm.lw(0.5))
    ax.set_title("Experiment result", fontsize=dm.fs(2), fontweight=dm.fw(1))
    ax.set_xlabel("Time", fontsize=dm.fs(0))
    ax.set_ylabel("Response", fontsize=dm.fs(0))
    dm.simple_layout(fig)

    path = images_dir / "layout_typography.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _make_label_axes_compare(use_dm: bool) -> plt.Figure:
    """Compare vanilla matplotlib text placement vs dm.label_axes()."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, axes = plt.subplots(
        3, 1, figsize=(dm.cm2in(10), dm.cm2in(12)), dpi=300
    )
    ylabels = ["y", "Velocity [m/s]", "A very long descriptive label"]

    for i, ax in enumerate(axes):
        ax.plot(np.random.randn(10), color=f"oc.blue{i + 4}")
        ax.set_ylabel(ylabels[i], fontsize=dm.fs(-1))
        if i < 2:
            ax.set_xticks([])

    if use_dm:
        dm.label_axes(axes)
    else:
        labels = ["(a)", "(b)", "(c)"]
        for ax, label in zip(axes, labels, strict=False):
            # Vanilla approach: manual generic positioning
            ax.text(
                -0.15,
                1.05,
                label,
                transform=ax.transAxes,
                fontsize=dm.fs(0),
                fontweight="bold",
                va="bottom",
                ha="left",
            )

    dm.simple_layout(fig)
    return fig


def _save_label_axes_vanilla(images_dir: Path) -> Path:
    """Save vanilla matplotlib version of label_axes comparison."""
    fig = _make_label_axes_compare(use_dm=False)
    path = images_dir / "label_axes_vanilla.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_label_axes_dm(images_dir: Path) -> Path:
    """Save dartwork-mpl version of label_axes comparison."""
    fig = _make_label_axes_compare(use_dm=True)
    path = images_dir / "label_axes_dm.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _make_set_decimal_compare(use_dm: bool) -> plt.Figure:
    """Compare vanilla unformatted ticks vs dm.set_decimal()."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, ax = plt.subplots(figsize=(dm.cm2in(12), dm.cm2in(6)), dpi=300)
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * 0.5 + 1.0

    ax.plot(x, y, color="oc.teal6")

    # Force some uneven ticks for vanilla
    ax.set_yticks([0.5, 0.75, 1, 1.25, 1.5])

    if use_dm:
        dm.set_decimal(ax, yn=1)

    dm.simple_layout(fig)
    return fig


def _save_set_decimal_vanilla(images_dir: Path) -> Path:
    """Save vanilla matplotlib version of set_decimal comparison."""
    fig = _make_set_decimal_compare(use_dm=False)
    path = images_dir / "set_decimal_vanilla.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_set_decimal_dm(images_dir: Path) -> Path:
    """Save dartwork-mpl version of set_decimal comparison."""
    fig = _make_set_decimal_compare(use_dm=True)
    path = images_dir / "set_decimal_dm.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_arrow_axis_example(images_dir: Path) -> Path:
    """Showcase dm.arrow_axis() conceptually."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, ax = plt.subplots(figsize=(dm.cm2in(10), dm.cm2in(10)), dpi=300)

    x = np.random.rand(20)
    y = x + np.random.randn(20) * 0.2
    ax.scatter(x, y, color="oc.indigo5", alpha=0.7, edgecolors="white", s=60)

    # Hide default spines and ticks
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    dm.arrow_axis(ax, direction="x", label="Risk", color="gray", offset=-0.02)
    dm.arrow_axis(
        ax, direction="y", label="Expected Return", color="gray", pad=0.03
    )

    dm.simple_layout(fig)
    path = images_dir / "arrow_axis_example.svg"
    try:
        fig.savefig(path, format="svg", bbox_inches="tight")
    except Exception as e:
        print(f"Warning: arrow_axis failed {e}")
    plt.close(fig)
    return path


# ── colors.md ──────────────────────────────────────────────────────────


def _save_colors_colormap(images_dir: Path) -> Path:
    """Colors 'Colormaps': dm.Crest imshow + colorbar."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig = plt.figure(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    gs = fig.add_gridspec(1, 1)
    ax = fig.add_subplot(gs[0, 0])

    data = np.random.randn(50, 50).cumsum(axis=0)
    cmap = plt.colormaps["dc.Crest"]
    im = ax.imshow(data, cmap=cmap, vmin=-8, vmax=8)
    cb = plt.colorbar(im, ax=ax, extend="both", shrink=0.9, pad=0.02)
    cb.set_label("normalized signal", fontsize=dm.fs(0))
    cb.outline.set_visible(False)
    ax.set_title(
        f"{cmap.name}  ({dm.classify_colormap(cmap)})",
        fontsize=dm.fs(1),
        fontweight="bold",
    )
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "colors_colormap.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_validation_example(images_dir: Path) -> Path:
    """Create a 'bad' figure and draw validation overlay."""
    dm.style.use("presentation")

    # Force a tight figsize
    fig, ax = plt.subplots(figsize=(dm.cm2in(10), dm.cm2in(6)), dpi=300)
    ax.plot([1, 2, 3], [1, 4, 9], color="oc.red6")
    ax.set_ylabel(
        "A very very long y-axis label that overflows bounds", fontsize=dm.fs(1)
    )
    ax.set_title("Validation Error", color="oc.red7")

    # Attempt to force cutoff
    fig.subplots_adjust(left=0.1)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = ax.yaxis.label.get_window_extent(renderer)

    inv = fig.transFigure.inverted()
    fig_bbox = bbox.transformed(inv)

    from matplotlib.patches import Rectangle

    rect = Rectangle(
        (fig_bbox.x0, fig_bbox.y0),
        fig_bbox.width,
        fig_bbox.height,
        transform=fig.transFigure,
        fill=True,
        facecolor="red",
        alpha=0.2,
        edgecolor="red",
        linestyle="--",
        linewidth=2,
        zorder=100,
        clip_on=False,
    )
    fig.patches.append(rect)

    fig.text(
        fig_bbox.x1 + 0.05,
        (fig_bbox.y0 + fig_bbox.y1) / 2,
        "[WARNING] OVERFLOW",
        color="#c92a2a",
        fontsize=dm.fs(0),
        fontweight="bold",
        transform=fig.transFigure,
        ha="left",
        va="center",
    )

    path = images_dir / "validation_example.svg"
    fig.savefig(
        path, format="svg"
    )  # don't use bbox_inches="tight" so it actually cuts off
    plt.close(fig)
    return path


# ── save_export.md ─────────────────────────────────────────────────────


def _save_scientific_chart(images_dir: Path) -> Path:
    """Save & Export: scientific style line chart."""
    np.random.seed(42)
    dm.style.use("scientific")

    fig, ax = plt.subplots(figsize=(dm.cm2in(15), dm.cm2in(10)), dpi=300)
    ax.plot(
        np.arange(50),
        np.cumsum(np.random.randn(50)) + 20,
        color="oc.blue6",
        lw=1.2,
    )
    ax.set_xlabel("Sample Index", fontsize=dm.fs(0))
    ax.set_ylabel("Signal Amplitude", fontsize=dm.fs(0))
    ax.set_title("Scientific Style Preview", fontsize=dm.fs(1))
    dm.simple_layout(fig)

    path = images_dir / "save_scientific.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_diverging_bar(images_dir: Path) -> Path:
    """Save & Export: xplot diverging bar chart."""
    dm.style.use("presentation")
    from dartwork_mpl.xplot import plot_diverging_bar

    fig, ax = plot_diverging_bar(
        labels=["Accuracy", "Precision", "Recall", "F1-Score", "AUC"],
        neg_values=np.array([-30, -55, -10, -20, -15]),
        pos_values=np.array([60, 20, 45, 50, 35]),
        neg_label="Decrease",
        pos_label="Increase",
        add_total=False,
        figsize=(dm.cm2in(15), dm.cm2in(10)),
    )

    path = images_dir / "save_diverging_bar.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_diagnostics_preview(images_dir: Path) -> Path:
    """Save & Export: plot_colors excerpt (SVG)."""
    dm.style.use("presentation")

    # Generate an OpenColor sheet — keep natural figure size
    figs = dm.plot_colors(ncols=4, sort_colors=True, show_hex=False)
    if len(figs) >= 2:
        fig = figs[1]  # OpenColor (library order: dm, opencolor, ...)

        path = images_dir / "save_diagnostics.svg"
        fig.savefig(path, format="svg", bbox_inches="tight")
        for f in figs:
            plt.close(f)
        return path
    return images_dir / "save_diagnostics.svg"


# ── Entrypoint ─────────────────────────────────────────────────────────


def build_usage_guide_assets(base_dir: Path | None = None) -> list[Path]:
    """Generate all usage guide figures.

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
    print(f"Generating usage guide assets in {images_dir} ...")

    generators = [
        ("quickstart_first_figure", _save_quickstart_first_figure),
        ("quickstart_multi_panel", _save_quickstart_multi_panel),
        ("layout_tight", _save_layout_tight),
        ("layout_simple", _save_layout_simple),
        ("layout_gridspec", _save_layout_gridspec),
        ("layout_typography", _save_layout_typography),
        ("label_axes_vanilla", _save_label_axes_vanilla),
        ("label_axes_dm", _save_label_axes_dm),
        ("set_decimal_vanilla", _save_set_decimal_vanilla),
        ("set_decimal_dm", _save_set_decimal_dm),
        ("arrow_axis_example", _save_arrow_axis_example),
        ("validation_example", _save_validation_example),
        ("colors_colormap", _save_colors_colormap),
        ("save_scientific", _save_scientific_chart),
        ("save_diverging_bar", _save_diverging_bar),
        ("save_diagnostics", _save_diagnostics_preview),
    ]

    paths: list[Path] = []
    for name, func in generators:
        try:
            p = func(images_dir)
            paths.append(p)
            print(f"  ✓ {name} → {p.name}")
        except Exception as e:
            print(f"  ✗ {name} FAILED: {e}")

    # ── Preset comparison widget (separate generator) ──
    try:
        try:
            from usage_guide.generate_preset_compare import (
                build_preset_compare_html,
            )
        except ModuleNotFoundError:
            from generate_preset_compare import build_preset_compare_html

        p = build_preset_compare_html(images_dir / "preset_compare.html")
        paths.append(p)
        print(f"  ✓ preset_compare → {p.name}")
    except Exception as e:
        print(f"  ✗ preset_compare FAILED: {e}")

    print(f"Done. {len(paths)}/{len(generators) + 1} assets generated.")
    return paths


if __name__ == "__main__":
    build_usage_guide_assets()
