"""Dartwork UI — Complex Example.

A multi-subplot signal analysis dashboard demonstrating all
supported parameter types with up to 3 subplots.

Run with:

    uv run --extra ui python app.py
"""

from typing import Literal, Any

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
    """Parameters for the signal analysis dashboard."""

    # int slider (bounded with ge / le)
    n_points: int = Field(
        default=500, ge=50, le=3000, description="Number of sample points"
    )
    harmonics: int = Field(
        default=3, ge=1, le=10, description="Number of harmonics to sum"
    )
    n_bins: int = Field(
        default=40, ge=10, le=100, description="Histogram bin count"
    )

    # int number input (no bounds)
    random_seed: int = Field(default=42, description="Random seed for noise")

    # float slider (bounded with ge / le / step)
    frequency: float = Field(
        default=2.0,
        ge=0.1,
        le=20.0,
        json_schema_extra={"step": 0.1},
        description="Base frequency (Hz)",
    )
    amplitude: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        json_schema_extra={"step": 0.1},
        description="Amplitude",
    )
    noise_level: float = Field(
        default=0.15,
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
    phase: float = Field(default=0.0, description="Phase offset (rad)")

    # str — plain text input
    title: str = Field(default="Signal Analysis", description="Chart title")
    x_label: str = Field(default="Time (s)", description="X-axis label")
    y_label: str = Field(default="Amplitude", description="Y-axis label")

    # str — color picker (explicit widget hint)
    signal_color: str = Field(
        default="#0969da",
        json_schema_extra={"widget": "color"},
        description="Signal line color",
    )
    accent_color: str = Field(
        default="#cf222e",
        json_schema_extra={"widget": "color"},
        description="Accent color",
    )

    # str — color picker (auto-detected from field name)
    bg_color: str = Field(default="#ffffff", description="Background color")
    grid_color: str = Field(default="#e1e4e8", description="Grid color")

    # bool — checkbox
    show_grid: bool = Field(default=True, description="Show grid lines")
    show_noise: bool = Field(default=True, description="Add noise")
    fill_under: bool = Field(default=False, description="Fill area under curve")
    show_fft: bool = Field(default=True, description="Show FFT subplot")
    show_histogram: bool = Field(
        default=True, description="Show histogram subplot"
    )

    # Literal — dropdown select
    waveform: Literal["sine", "cosine", "square", "sawtooth"] = Field(
        default="sine", description="Waveform shape"
    )
    line_style: Literal["-", "--", "-.", ":"] = Field(
        default="-", description="Line style"
    )
    window_fn: Literal["none", "hanning", "hamming", "blackman"] = Field(
        default="none", description="Window function"
    )

    # list[float] — comma-separated text input
    custom_yticks: list[float] = Field(
        default=[], description="Custom Y-axis ticks (e.g. -1, 0, 1)"
    )
    harmonic_weights: list[float] = Field(
        default=[1.0, 0.5, 0.25],
        description=("Harmonic weights (e.g. 1.0, 0.5, 0.25)"),
    )

    # list[int] — comma-separated text input
    highlight_indices: list[int] = Field(
        default=[],
        description=("Sample indices to highlight (e.g. 100, 250, 400)"),
    )

    # list[str] — comma-separated text input
    annotations: list[str] = Field(
        default=[], description="Labels for highlighted points"
    )

    # tuple[float, ...] — comma-separated text input
    y_range: tuple[float, ...] = Field(
        default=(), description="Y-axis range (min, max)"
    )


# ================================================================
# Figure function — receives a Params instance, returns Figure
# ================================================================


def _build_waveform(p: Params, t: np.ndarray) -> np.ndarray:
    """Build a composite waveform from parameters.

    Parameters
    ----------
    p : Params
        Dashboard parameters.
    t : np.ndarray
        Time array.

    Returns
    -------
    np.ndarray
        Composite waveform signal.
    """

    def _wave(freq: float, phase: float) -> np.ndarray:
        """Generate a single waveform component.

        Parameters
        ----------
        freq : float
            Frequency multiplier.
        phase : float
            Phase offset.

        Returns
        -------
        np.ndarray
            Waveform values.
        """
        raw: np.ndarray = freq * t + phase
        if p.waveform == "cosine":
            return np.cos(raw)  # type: ignore[no-any-return]
        if p.waveform == "square":
            return np.sign(np.sin(raw))  # type: ignore[no-any-return]
        if p.waveform == "sawtooth":
            return 2 * (raw / (2 * np.pi) % 1) - 1  # type: ignore[no-any-return]
        return np.sin(raw)  # type: ignore[no-any-return]

    weights: list[float] = p.harmonic_weights or [
        1.0 / (k + 1) for k in range(p.harmonics)
    ]
    y: np.ndarray = np.zeros_like(t)
    for k in range(min(p.harmonics, len(weights))):
        w: float = weights[k] if k < len(weights) else 1.0 / (k + 1)
        y += w * _wave(p.frequency * (k + 1), p.phase * (k + 1))
    y *= p.amplitude

    if p.window_fn != "none":
        win_map: dict[str, Any] = {
            "hanning": np.hanning,
            "hamming": np.hamming,
            "blackman": np.blackman,
        }
        y *= win_map[p.window_fn](len(y))

    if p.show_noise:
        rng = np.random.default_rng(p.random_seed)
        y += rng.normal(0, p.noise_level, size=len(t))

    return y


def _determine_layout(p: Params) -> tuple[float, int, list[int]]:
    """Determine figure width and subplot column count.

    Parameters
    ----------
    p : Params
        Dashboard parameters.

    Returns
    -------
    tuple[float, int, list[int]]
        Figure width in cm, number of columns,
        and width ratios.
    """
    n_extra: int = int(p.show_fft) + int(p.show_histogram)
    if n_extra == 0:
        return 17.0, 1, [1]
    if n_extra == 1:
        return 22.0, 2, [3, 1]
    return 26.0, 3, [3, 1, 1]


def my_figure(p: Params) -> Figure:
    """Generate a multi-subplot signal analysis figure.

    Parameters
    ----------
    p : Params
        Dashboard parameters.

    Returns
    -------
    Figure
        Matplotlib figure with signal, FFT, and histogram.
    """
    dm.style.use("scientific")
    t: np.ndarray = np.linspace(0, 2 * np.pi, p.n_points)
    y: np.ndarray = _build_waveform(p, t)

    # ── Determine layout ──────────────────────────────────
    fig_w, ncols, ratios = _determine_layout(p)
    fig: Figure = plt.figure(figsize=(dm.cm2in(fig_w), dm.cm2in(9)), dpi=200)

    # ── GridSpec: title row + plot row ─────────────────────
    gs = fig.add_gridspec(
        nrows=2,
        ncols=ncols,
        left=0.17,
        right=0.95,
        top=0.95,
        bottom=0.17,
        hspace=0,
        wspace=0.3,
        height_ratios=[0.1, 0.9],
        width_ratios=ratios,
    )

    # ── Title axes (spans all columns) ────────────────────
    ax_title = fig.add_subplot(gs[0, :])
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

    # ── Subplot 1: Signal ─────────────────────────────────
    ax_signal = fig.add_subplot(gs[1, 0])
    ax_signal.plot(
        t,
        y,
        color=p.signal_color,
        linewidth=p.line_width,
        linestyle=p.line_style,
        label="Signal",
    )

    if p.fill_under:
        ax_signal.fill_between(t, y, alpha=0.1, color=p.signal_color)

    for i, idx in enumerate(p.highlight_indices):
        if 0 <= idx < len(t):
            ax_signal.axvline(
                t[idx],
                color=p.accent_color,
                alpha=0.4,
                linewidth=1,
                linestyle=":",
            )
            ax_signal.plot(
                t[idx], y[idx], "o", color=p.accent_color, markersize=5
            )
            if p.annotations and i < len(p.annotations):
                ax_signal.annotate(
                    p.annotations[i],
                    (t[idx], y[idx]),
                    textcoords="offset points",
                    xytext=(8, 8),
                    fontsize=dm.fs(-1),
                )

    ax_signal.set_xlim(0, 2 * np.pi)
    if p.y_range and len(p.y_range) >= 2:
        ax_signal.set_ylim(p.y_range[0], p.y_range[1])
    if p.custom_yticks:
        ax_signal.set_yticks(p.custom_yticks)

    ax_signal.set_xlabel(p.x_label, fontsize=dm.fs(0))
    ax_signal.set_ylabel(p.y_label, fontsize=dm.fs(0))
    ax_signal.legend(loc="upper right", fontsize=dm.fs(-1), framealpha=0.5)
    if p.show_grid:
        ax_signal.grid(True, alpha=0.2, color=p.grid_color)

    # ── Subplot 2: FFT ────────────────────────────────────
    col_idx: int = 1
    if p.show_fft and ncols >= 2:
        ax_fft = fig.add_subplot(gs[1, col_idx])
        fft_vals: np.ndarray = np.abs(np.fft.rfft(y))
        freqs: np.ndarray = np.fft.rfftfreq(len(t), d=(t[1] - t[0]))
        max_i: int = min(len(freqs), 50)
        ax_fft.bar(
            freqs[1:max_i],
            fft_vals[1:max_i],
            width=freqs[1] - freqs[0],
            color=p.signal_color,
            alpha=0.8,
        )
        ax_fft.set_xlabel("Frequency", fontsize=dm.fs(-1))
        ax_fft.set_ylabel("Magnitude", fontsize=dm.fs(-1))
        ax_fft.set_title("Frequency Spectrum", fontsize=dm.fs(0))
        if p.show_grid:
            ax_fft.grid(True, alpha=0.2, color=p.grid_color)
        col_idx += 1

    # ── Subplot 3: Histogram ──────────────────────────────
    if p.show_histogram and col_idx <= ncols - 1:
        ax_hist = fig.add_subplot(gs[1, col_idx])
        ax_hist.hist(
            y,
            bins=p.n_bins,
            color=p.signal_color,
            alpha=0.7,
            linewidth=0.5,
            orientation="horizontal",
        )
        ax_hist.set_xlabel("Count", fontsize=dm.fs(-1))
        ax_hist.set_ylabel("Value", fontsize=dm.fs(-1))
        ax_hist.set_title("Distribution", fontsize=dm.fs(0))
        if p.show_grid:
            ax_hist.grid(True, alpha=0.2, color=p.grid_color)

    # ── Layout optimization ───────────────────────────────
    dm.simple_layout(fig, gs=gs)
    return fig


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    run(my_figure, title="Signal Analysis")  # type: ignore[arg-type]
