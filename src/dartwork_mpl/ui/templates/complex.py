"""Dartwork UI — Complex Example.

A multi-subplot signal analysis dashboard demonstrating all
supported parameter types with 3 subplots.

Run with:

    uv run --extra ui python app.py
"""

from __future__ import annotations

from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from pydantic import Field

import dartwork_mpl as dm
from dartwork_mpl.ui import ParamModel, run


# ============================================================================
# Parameters — every supported widget type is shown here
# ============================================================================


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
    title: str = Field(
        default="Signal Analysis", description="Chart title"
    )
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
        description="Harmonic weights (e.g. 1.0, 0.5, 0.25)",
    )

    # list[int] — comma-separated text input
    highlight_indices: list[int] = Field(
        default=[],
        description="Sample indices to highlight (e.g. 100, 250, 400)",
    )

    # list[str] — comma-separated text input
    annotations: list[str] = Field(
        default=[], description="Labels for highlighted points"
    )

    # tuple[float, ...] — comma-separated text input
    y_range: tuple[float, ...] = Field(
        default=(), description="Y-axis range (min, max)"
    )


# ============================================================================
# Figure function — receives a Params instance, returns a Figure
# ============================================================================


def my_figure(p: Params) -> Figure:
    """Generate a multi-subplot signal analysis figure."""
    dm.style.use("scientific")
    rng = np.random.default_rng(p.random_seed)
    t = np.linspace(0, 2 * np.pi, p.n_points)

    # ── Build composite waveform ──────────────────────────────────

    def wave(freq: float, phase: float) -> np.ndarray:
        raw = freq * t + phase
        if p.waveform == "cosine":
            return np.cos(raw)
        elif p.waveform == "square":
            return np.sign(np.sin(raw))
        elif p.waveform == "sawtooth":
            return 2 * (raw / (2 * np.pi) % 1) - 1
        return np.sin(raw)

    weights = p.harmonic_weights or [
        1.0 / (k + 1) for k in range(p.harmonics)
    ]
    y = np.zeros_like(t)
    for k in range(min(p.harmonics, len(weights))):
        w = weights[k] if k < len(weights) else 1.0 / (k + 1)
        y += w * wave(p.frequency * (k + 1), p.phase * (k + 1))
    y *= p.amplitude

    if p.window_fn != "none":
        win_fn = {
            "hanning": np.hanning,
            "hamming": np.hamming,
            "blackman": np.blackman,
        }[p.window_fn]
        y *= win_fn(len(y))

    if p.show_noise:
        y += rng.normal(0, p.noise_level, size=len(t))

    # ── Subplot layout (adapts to checkboxes) ─────────────────────
    n_extra = int(p.show_fft) + int(p.show_histogram)
    if n_extra == 0:
        fig, axes_raw = plt.subplots(1, 1, figsize=(11, 5))
        ax_signal = axes_raw
        ax_fft = None
        ax_hist = None
    elif n_extra == 1:
        fig, axes_raw = plt.subplots(
            1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [3, 1]}
        )
        ax_signal = axes_raw[0]
        ax_fft = axes_raw[1] if p.show_fft else None
        ax_hist = axes_raw[1] if p.show_histogram and not p.show_fft else None
    else:
        fig, axes_raw = plt.subplots(
            1, 3, figsize=(16, 5), gridspec_kw={"width_ratios": [3, 1, 1]}
        )
        ax_signal = axes_raw[0]
        ax_fft = axes_raw[1]
        ax_hist = axes_raw[2]

    # ── Colors ────────────────────────────────────────────────────
    is_dark = p.bg_color < "#888888"
    text_c = "#e6edf3" if is_dark else "#1f2328"
    spine_c = "#30363d" if is_dark else "#d0d4d9"
    fig.patch.set_facecolor(p.bg_color)

    def style_ax(ax, title: str = "") -> None:
        ax.set_facecolor(p.bg_color)
        for spine in ax.spines.values():
            spine.set_color(spine_c)
        ax.tick_params(colors=text_c, labelsize=8)
        if title:
            ax.set_title(title, color=text_c, fontsize=10, pad=8)
        if p.show_grid:
            ax.grid(True, alpha=0.2, color=p.grid_color)

    # ── Subplot 1: Signal ─────────────────────────────────────────
    style_ax(ax_signal)
    ax_signal.plot(t, y, color=p.signal_color, linewidth=p.line_width,
                   linestyle=p.line_style, label="Signal")

    if p.fill_under:
        ax_signal.fill_between(t, y, alpha=0.1, color=p.signal_color)

    for i, idx in enumerate(p.highlight_indices):
        if 0 <= idx < len(t):
            ax_signal.axvline(t[idx], color=p.accent_color, alpha=0.4,
                              linewidth=1, linestyle=":")
            ax_signal.plot(t[idx], y[idx], "o", color=p.accent_color,
                           markersize=5)
            if p.annotations and i < len(p.annotations):
                ax_signal.annotate(
                    p.annotations[i], (t[idx], y[idx]),
                    textcoords="offset points", xytext=(8, 8),
                    fontsize=8, color=text_c,
                )

    ax_signal.set_xlim(0, 2 * np.pi)
    if p.y_range and len(p.y_range) >= 2:
        ax_signal.set_ylim(p.y_range[0], p.y_range[1])
    if p.custom_yticks:
        ax_signal.set_yticks(p.custom_yticks)

    ax_signal.set_xlabel(p.x_label, color=text_c, fontsize=9)
    ax_signal.set_ylabel(p.y_label, color=text_c, fontsize=9)
    ax_signal.legend(loc="upper right", fontsize=8, framealpha=0.5)

    # ── Subplot 2: FFT ────────────────────────────────────────────
    if ax_fft is not None:
        style_ax(ax_fft, "Frequency Spectrum")
        fft_vals = np.abs(np.fft.rfft(y))
        freqs = np.fft.rfftfreq(len(t), d=(t[1] - t[0]))
        max_i = min(len(freqs), 50)
        ax_fft.bar(freqs[1:max_i], fft_vals[1:max_i],
                   width=freqs[1] - freqs[0],
                   color=p.signal_color, alpha=0.8)
        ax_fft.set_xlabel("Frequency", color=text_c, fontsize=8)
        ax_fft.set_ylabel("Magnitude", color=text_c, fontsize=8)

    # ── Subplot 3: Histogram ──────────────────────────────────────
    if ax_hist is not None:
        style_ax(ax_hist, "Distribution")
        ax_hist.hist(y, bins=p.n_bins, color=p.signal_color, alpha=0.7,
                     edgecolor=spine_c, linewidth=0.5, orientation="horizontal")
        ax_hist.set_xlabel("Count", color=text_c, fontsize=8)
        ax_hist.set_ylabel("Value", color=text_c, fontsize=8)

    # ── Title ─────────────────────────────────────────────────────
    fig.suptitle(p.title, color=text_c, fontsize=13, fontweight=500, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return fig


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    run(my_figure, title="Signal Analysis")
