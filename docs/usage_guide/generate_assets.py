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

import dartwork_mpl as dm


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

    fig, ax = plt.subplots(
        figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300
    )
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
    fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(5)), dpi=300)
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


def _make_challenging_figure(
    use_simple_layout: bool = True,
) -> plt.Figure:
    """Create a multi-panel figure that exposes tight_layout weaknesses.

    Left panel: line chart with long Y-axis label + title.
    Right panel: heatmap with colorbar.
    Both share an x-label to stress margin negotiation.
    """
    np.random.seed(42)
    dm.style.use("scientific")

    fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(5)), dpi=300)
    gs = fig.add_gridspec(1, 2, wspace=0.45)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # Left: line chart with long labels
    x = np.linspace(0, 10, 200)
    ax1.plot(x, np.sin(x) * np.exp(-0.1 * x), color="oc.blue6", lw=0.8)
    ax1.set_ylabel(
        "Thermal conductivity\n[W/(m·K)]",
        fontsize=dm.fs(0),
    )
    ax1.set_xlabel("Time [s]", fontsize=dm.fs(0))
    ax1.set_title("Transient response", fontsize=dm.fs(1))

    # Right: heatmap with colorbar
    data = np.random.randn(8, 8).cumsum(axis=0)
    im = ax2.imshow(data, cmap="dc.Crest", aspect="auto")
    cb = plt.colorbar(im, ax=ax2, shrink=0.85, pad=0.03)
    cb.set_label(
        "Δ Temperature [K]", fontsize=dm.fs(0),
    )
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

    fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=300)
    gs = fig.add_gridspec(
        2, 2,
        left=0.08, right=0.98, top=0.9, bottom=0.12,
        hspace=0.35, wspace=0.25,
    )
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    for ax in axes:
        ax.plot(
            np.linspace(0, 1, 40),
            np.random.rand(40),
            color="oc.blue6",
            lw=0.8,
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

    fig, ax = plt.subplots(
        figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300
    )
    x = np.array([0, 1, 2])
    y = np.array([0, 1, 0.4])
    ax.plot(x, y, color="oc.green6", lw=dm.lw(0.5))
    ax.set_title(
        "Experiment result",
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
    )
    ax.set_xlabel("Time", fontsize=dm.fs(0))
    ax.set_ylabel("Response", fontsize=dm.fs(0))
    dm.simple_layout(fig)

    path = images_dir / "layout_typography.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── colors.md ──────────────────────────────────────────────────────────


def _save_colors_named(images_dir: Path) -> Path:
    """Colors 'Named colors': 4 color systems + mix + pseudo_alpha."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig, ax = plt.subplots(
        figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300
    )
    x = np.array([0, 1, 2])

    ax.plot(
        x,
        [1, 2, 1.5],
        marker="o",
        color="oc.green5",
        label="OpenColor (oc.*)",
    )
    ax.plot(
        x,
        [1.2, 1.6, 2.1],
        marker="s",
        color="tw.blue500",
        label="Tailwind (tw.*)",
    )
    highlight = dm.mix_colors("md.orange600", "white", alpha=0.45)
    ax.fill_between(
        x, 0.9, 1.3, color=highlight, label="mix_colors()", alpha=0.9
    )
    muted_line = dm.pseudo_alpha("pr.blue5", alpha=0.65, background="white")
    ax.plot(
        x,
        [0.8, 1.1, 1.4],
        color=muted_line,
        lw=2,
        label="pseudo_alpha()",
    )
    ax.legend(fontsize=dm.fs(-1))
    ax.set_xlabel("Index", fontsize=dm.fs(0))
    ax.set_ylabel("Value", fontsize=dm.fs(0))
    dm.simple_layout(fig)

    path = images_dir / "colors_named.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


def _save_colors_colormap(images_dir: Path) -> Path:
    """Colors 'Colormaps': dm.Crest imshow + colorbar."""
    np.random.seed(42)
    dm.style.use("presentation")

    fig = plt.figure(figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300)
    gs = fig.add_gridspec(1, 1)
    ax = fig.add_subplot(gs[0, 0])

    data = np.random.randn(50, 50).cumsum(axis=0)
    cmap = plt.colormaps["dc.Crest"]
    im = ax.imshow(data, cmap=cmap, vmin=-8, vmax=8)
    cb = plt.colorbar(im, ax=ax, extend="both", shrink=0.9, pad=0.02)
    cb.set_label("normalized signal", fontsize=dm.fs(0))
    cb.outline.set_visible(False)
    ax.set_title(
        f'{cmap.name}  ({dm.classify_colormap(cmap)})',
        fontsize=dm.fs(1),
        fontweight="bold",
    )
    dm.simple_layout(fig, gs=gs)

    path = images_dir / "colors_colormap.svg"
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return path


# ── save_export.md ─────────────────────────────────────────────────────


def _save_scientific_chart(images_dir: Path) -> Path:
    """Save & Export: scientific style line chart."""
    np.random.seed(42)
    dm.style.use("scientific")

    fig, ax = plt.subplots(
        figsize=(dm.cm2in(9), dm.cm2in(6)), dpi=300
    )
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
        figsize=(dm.cm2in(9), dm.cm2in(6)),
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


def build_usage_guide_assets(
    base_dir: Path | None = None,
) -> list[Path]:
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
        ("colors_named", _save_colors_named),

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

    print(f"Done. {len(paths)}/{len(generators)} assets generated.")
    return paths


if __name__ == "__main__":
    build_usage_guide_assets()
