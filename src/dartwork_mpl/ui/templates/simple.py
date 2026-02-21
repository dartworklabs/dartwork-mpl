"""Dartwork UI — Simple Example.

A single-subplot waveform viewer demonstrating all supported
parameter types.

Run with:

    uv run --extra ui python app.py
"""

from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from pydantic import Field

import dartwork_mpl as dm
from dartwork_mpl.ui import ParamModel, run

# ================================================================
# Parameters — every supported widget type is shown here
# ================================================================


class Params(ParamModel):
    """Parameters for the waveform viewer."""

    # int slider (bounded with ge / le)
    n_points: int = Field(
        default=500,
        ge=50,
        le=3000,
        description="Number of sample points",
    )

    # int number input (no bounds)
    random_seed: int = Field(
        default=42, description="Random seed for noise"
    )

    # float slider (bounded with ge / le / step)
    frequency: float = Field(
        default=2.0,
        ge=0.1,
        le=20.0,
        json_schema_extra={"step": 0.1},
        description="Frequency (Hz)",
    )
    amplitude: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        json_schema_extra={"step": 0.1},
        description="Amplitude",
    )
    noise_level: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        json_schema_extra={"step": 0.05},
        description="Noise level",
    )
    line_width: float = Field(
        default=1.5,
        ge=0.5,
        le=6.0,
        json_schema_extra={"step": 0.5},
        description="Line width",
    )

    # float number input (no bounds)
    phase: float = Field(
        default=0.0, description="Phase offset (rad)"
    )

    # str — plain text input
    title: str = Field(
        default="My Waveform", description="Chart title"
    )

    # str — color picker (explicit widget hint)
    line_color: str = Field(
        default="#0969da",
        json_schema_extra={"widget": "color"},
        description="Line color",
    )

    # str — color picker (auto-detected from field name)
    bg_color: str = Field(
        default="#ffffff", description="Background color"
    )

    # bool — checkbox
    show_grid: bool = Field(
        default=True, description="Show grid lines"
    )
    fill_under: bool = Field(
        default=False,
        description="Fill area under curve",
    )

    # Literal — dropdown select
    waveform: Literal[
        "sine", "cosine", "square", "sawtooth"
    ] = Field(default="sine", description="Waveform shape")
    line_style: Literal["-", "--", "-.", ":"] = Field(
        default="-", description="Line style"
    )

    # list[float] — comma-separated text input
    custom_yticks: list[float] = Field(
        default=[],
        description="Custom Y-axis ticks (e.g. -1, 0, 1)",
    )

    # list[int] — comma-separated text input
    highlight_indices: list[int] = Field(
        default=[],
        description=(
            "Sample indices to highlight (e.g. 100, 250)"
        ),
    )

    # list[str] — comma-separated text input
    annotations: list[str] = Field(
        default=[],
        description="Labels for highlighted points",
    )

    # tuple[float, ...] — comma-separated text input
    y_range: tuple[float, ...] = Field(
        default=(), description="Y-axis range (min, max)"
    )


# ================================================================
# Figure function — receives a Params instance, returns a Figure
# ================================================================


def my_figure(p: Params) -> Figure:
    """Generate a simple waveform figure.

    Parameters
    ----------
    p : Params
        Waveform viewer parameters.

    Returns
    -------
    Figure
        Matplotlib figure with the rendered waveform.
    """
    dm.style.use("scientific")
    rng = np.random.default_rng(p.random_seed)
    t: np.ndarray = np.linspace(0, 2 * np.pi, p.n_points)

    # ── Generate waveform ─────────────────────────────────
    raw: np.ndarray = p.frequency * t + p.phase
    if p.waveform == "cosine":
        y: np.ndarray = p.amplitude * np.cos(raw)
    elif p.waveform == "square":
        y = p.amplitude * np.sign(np.sin(raw))
    elif p.waveform == "sawtooth":
        y = p.amplitude * (
            2 * (raw / (2 * np.pi) % 1) - 1
        )
    else:
        y = p.amplitude * np.sin(raw)

    # Add noise
    y += rng.normal(0, p.noise_level, size=len(t))

    # ── Figure creation (guide pattern) ───────────────────
    fig: Figure = plt.figure(
        figsize=(dm.cm2in(17), dm.cm2in(9)),
        dpi=200,
    )

    # GridSpec: title row + plot row
    gs = fig.add_gridspec(
        nrows=2,
        ncols=1,
        left=0.17,
        right=0.95,
        top=0.95,
        bottom=0.17,
        hspace=0,
        height_ratios=[0.1, 0.9],
    )

    # ── Title axes ────────────────────────────────────────
    ax_title = fig.add_subplot(gs[0, 0])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        p.title,
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
        ha="center",
        va="center",
        transform=ax_title.transAxes,
    )

    # ── Plot axes ─────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 0])

    ax.plot(
        t,
        y,
        color=p.line_color,
        linewidth=p.line_width,
        linestyle=p.line_style,
    )

    if p.fill_under:
        ax.fill_between(
            t, y, alpha=0.12, color=p.line_color
        )

    # Highlights
    for i, idx in enumerate(p.highlight_indices):
        if 0 <= idx < len(t):
            ax.plot(
                t[idx],
                y[idx],
                "o",
                color="oc.red5",
                markersize=6,
            )
            if p.annotations and i < len(p.annotations):
                ax.annotate(
                    p.annotations[i],
                    (t[idx], y[idx]),
                    textcoords="offset points",
                    xytext=(8, 8),
                    fontsize=dm.fs(-1),
                )

    # Axes styling
    ax.set_xlim(0, 2 * np.pi)
    if p.y_range and len(p.y_range) >= 2:
        ax.set_ylim(p.y_range[0], p.y_range[1])
    if p.custom_yticks:
        ax.set_yticks(p.custom_yticks)

    ax.set_xlabel("Time", fontsize=dm.fs(0))
    ax.set_ylabel("Amplitude", fontsize=dm.fs(0))

    if p.show_grid:
        ax.grid(True, alpha=0.15)

    # ── Layout optimization ───────────────────────────────
    dm.simple_layout(fig, gs=gs)
    return fig


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    run(my_figure, title="Waveform Viewer")
