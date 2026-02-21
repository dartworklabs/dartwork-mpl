"""Example: Dartwork Viewer — Signal Analysis Dashboard.

Demonstrates all supported widget types:
- int (slider with ge/le)
- int (number input, no bounds)
- float (slider with ge/le + step)
- float (number input, no bounds)
- str (text input)
- str (color picker via widget hint)
- str (color picker via name auto-detect)
- bool (checkbox)
- Literal[...] (select dropdown)
- list[float] (comma-separated)
- list[int] (comma-separated)
- list[str] (comma-separated)
- tuple[float, ...] (comma-separated)

Run with:

    uv run --extra ui python examples/example_ui.py
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
# Parameter model — every supported type
# ============================================================================


class SignalParams(ParamModel):
    """Full-featured parameter model for signal analysis."""

    # ── int slider (ge / le) ──────────────────────────────────────
    n_points: int = Field(
        default=500, ge=50, le=3000, description="Sample count"
    )
    harmonics: int = Field(
        default=3, ge=1, le=10, description="Number of harmonics"
    )

    # ── int number input (no bounds) ──────────────────────────────
    random_seed: int = Field(default=42, description="Random seed")

    # ── float slider (ge / le / step) ─────────────────────────────
    base_frequency: float = Field(
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

    # ── float number input (no bounds) ────────────────────────────
    phase_offset: float = Field(default=0.0, description="Phase offset (rad)")

    # ── str text input ────────────────────────────────────────────
    title_text: str = Field(
        default="Signal Analysis", description="Chart title"
    )
    x_label: str = Field(default="Time (s)", description="X-axis label")
    y_label: str = Field(default="Amplitude", description="Y-axis label")

    # ── str color picker (explicit widget hint) ───────────────────
    signal_color: str = Field(
        default="#0969da",
        json_schema_extra={"widget": "color"},
        description="Signal line color",
    )
    envelope_color: str = Field(
        default="#cf222e",
        json_schema_extra={"widget": "color"},
        description="Envelope color",
    )

    # ── str color picker (auto-detected from field name) ──────────
    bg_color: str = Field(default="#ffffff", description="Background color")
    grid_color: str = Field(default="#e1e4e8", description="Grid color")

    # ── bool checkbox ─────────────────────────────────────────────
    show_grid: bool = Field(default=True, description="Show grid")
    show_envelope: bool = Field(default=False, description="Show envelope")
    show_noise: bool = Field(default=True, description="Add noise")
    fill_under: bool = Field(default=False, description="Fill under curve")

    # ── Literal select dropdown ───────────────────────────────────
    waveform: Literal["sine", "cosine", "square", "sawtooth"] = Field(
        default="sine", description="Waveform type"
    )
    line_style: Literal["-", "--", "-.", ":"] = Field(
        default="-", description="Line style"
    )
    window_fn: Literal["none", "hanning", "hamming", "blackman"] = Field(
        default="none", description="Window function"
    )

    # ── list[float] comma-separated ───────────────────────────────
    custom_yticks: list[float] = Field(
        default=[], description="Custom Y-axis ticks (e.g. -1, 0, 1)"
    )
    harmonic_weights: list[float] = Field(
        default=[1.0, 0.5, 0.25],
        description="Harmonic weights (e.g. 1.0, 0.5, 0.25)",
    )

    # ── list[int] comma-separated ─────────────────────────────────
    highlight_samples: list[int] = Field(
        default=[],
        description="Highlight sample indices (e.g. 100, 200, 300)",
    )

    # ── list[str] comma-separated ─────────────────────────────────
    annotations: list[str] = Field(
        default=[], description="Annotation labels at highlights"
    )

    # ── tuple[float, ...] comma-separated ─────────────────────────
    y_limits: tuple[float, ...] = Field(
        default=(), description="Y-axis limits (min, max)"
    )


# ============================================================================
# Figure function
# ============================================================================


def signal_figure(p: SignalParams) -> Figure:
    dm.style.use("scientific")

    """Generate a multi-harmonic signal analysis figure."""
    rng = np.random.default_rng(p.random_seed)
    t = np.linspace(0, 2 * np.pi, p.n_points)

    # Build base waveform
    def wave(freq: float, phase: float) -> np.ndarray:
        raw = freq * t + phase
        if p.waveform == "cosine":
            return np.cos(raw)
        elif p.waveform == "square":
            return np.sign(np.sin(raw))
        elif p.waveform == "sawtooth":
            return 2 * (raw / (2 * np.pi) % 1) - 1
        return np.sin(raw)

    # Sum harmonics with weights
    weights = p.harmonic_weights or [1.0 / (k + 1) for k in range(p.harmonics)]
    y = np.zeros_like(t)
    for k in range(min(p.harmonics, len(weights))):
        w = weights[k] if k < len(weights) else 1.0 / (k + 1)
        y += w * wave(p.base_frequency * (k + 1), p.phase_offset * (k + 1))
    y *= p.amplitude

    # Optional window function
    if p.window_fn != "none":
        win_fn = {
            "hanning": np.hanning,
            "hamming": np.hamming,
            "blackman": np.blackman,
        }[p.window_fn]
        y *= win_fn(len(y))

    # Add noise
    if p.show_noise:
        y += rng.normal(0, p.noise_level, size=len(t))

    # ── Plot ──────────────────────────────────────────────────────
    is_dark = p.bg_color < "#888888"
    text_c = "#e6edf3" if is_dark else "#1f2328"
    spine_c = "#30363d" if is_dark else "#d0d4d9"

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(p.bg_color)
    ax.set_facecolor(p.bg_color)

    ax.plot(
        t,
        y,
        color=p.signal_color,
        linewidth=p.line_width,
        linestyle=p.line_style,
        label="Signal",
    )

    if p.fill_under:
        ax.fill_between(t, y, alpha=0.1, color=p.signal_color)

    # Envelope
    if p.show_envelope:
        from scipy.signal import hilbert

        analytic = hilbert(y)
        env = np.abs(analytic)
        ax.plot(
            t,
            env,
            color=p.envelope_color,
            linewidth=1.0,
            linestyle="--",
            alpha=0.8,
            label="Envelope",
        )
        ax.plot(t, -env, color=p.envelope_color, linewidth=1.0, linestyle="--", alpha=0.8)

    # Highlight samples
    if p.highlight_samples:
        for idx_i, sample_idx in enumerate(p.highlight_samples):
            if 0 <= sample_idx < len(t):
                ax.axvline(
                    t[sample_idx],
                    color=p.envelope_color,
                    alpha=0.4,
                    linewidth=1,
                    linestyle=":",
                )
                ax.plot(
                    t[sample_idx],
                    y[sample_idx],
                    "o",
                    color=p.envelope_color,
                    markersize=6,
                )
                # Add annotation label if available
                if p.annotations and idx_i < len(p.annotations):
                    ax.annotate(
                        p.annotations[idx_i],
                        (t[sample_idx], y[sample_idx]),
                        textcoords="offset points",
                        xytext=(8, 8),
                        fontsize=9,
                        color=text_c,
                    )

    # Styling
    ax.set_xlim(0, 2 * np.pi)
    if p.y_limits and len(p.y_limits) >= 2:
        ax.set_ylim(p.y_limits[0], p.y_limits[1])

    for spine in ax.spines.values():
        spine.set_color(spine_c)

    ax.tick_params(colors=text_c, labelsize=9)
    ax.set_xlabel(p.x_label, color=text_c, fontsize=10)
    ax.set_ylabel(p.y_label, color=text_c, fontsize=10)

    if p.custom_yticks:
        ax.set_yticks(p.custom_yticks)

    if p.show_grid:
        ax.grid(True, alpha=0.3, color=p.grid_color)
    else:
        ax.grid(False)

    ax.set_title(p.title_text, color=text_c, fontsize=13, pad=12, fontweight=500)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.5)
    fig.tight_layout()

    return fig


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    run(signal_figure, SignalParams, title="Signal Analysis")
