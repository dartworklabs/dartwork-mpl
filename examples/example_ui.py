"""Example: Dartwork Viewer — Signal Analysis Dashboard.

Demonstrates all supported widget types with a multi-subplot
figure:
- int (slider / number input)
- float (slider / number input)
- str (text / color picker)
- bool (checkbox)
- Literal[...] (select dropdown)
- list[float], list[int], list[str]
- tuple[float, ...]

Run with:

    uv run --extra ui python examples/example_ui.py
"""

from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from pydantic import Field

import dartwork_mpl as dm
from dartwork_mpl.ui import ParamModel, run

# ================================================================
# Parameter model — every supported type
# ================================================================


class SignalParams(ParamModel):
    """Full-featured parameter model for signal analysis."""

    # ── int slider (ge / le) ──────────────────────────────
    n_points: int = Field(
        default=500,
        ge=50,
        le=3000,
        description="Sample count",
        json_schema_extra={"group": "Signal"},
    )
    harmonics: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of harmonics",
        json_schema_extra={"group": "Signal"},
    )
    n_bins: int = Field(
        default=40,
        ge=10,
        le=100,
        description="Histogram bins",
        json_schema_extra={"group": "Display"},
    )

    # ── int number input (no bounds) ──────────────────────
    random_seed: int = Field(
        default=42, description="Random seed", json_schema_extra={"group": "Signal"}
    )

    # ── float slider (ge / le / step) ─────────────────────
    base_frequency: float = Field(
        default=2.0,
        ge=0.1,
        le=20.0,
        json_schema_extra={"step": 0.1, "group": "Signal"},
        description="Base frequency (Hz)",
    )
    amplitude: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        json_schema_extra={"step": 0.1, "group": "Signal"},
        description="Amplitude",
    )
    noise_level: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        json_schema_extra={"step": 0.05, "group": "Signal"},
        description="Noise level",
    )
    line_width: float = Field(
        default=1.5,
        ge=0.5,
        le=6.0,
        json_schema_extra={"step": 0.5, "group": "Display"},
        description="Line width",
    )

    # ── float number input (no bounds) ────────────────────
    phase_offset: float = Field(
        default=0.0,
        description="Phase offset (rad)",
        json_schema_extra={"group": "Signal"},
    )

    # ── str text input ────────────────────────────────────
    title_text: str = Field(
        default="Signal Analysis",
        description="Chart title",
        json_schema_extra={"group": "Display"},
    )
    x_label: str = Field(
        default="Time (s)",
        description="X-axis label",
        json_schema_extra={"group": "Display"},
    )
    y_label: str = Field(
        default="Amplitude",
        description="Y-axis label",
        json_schema_extra={"group": "Display"},
    )

    # ── str color picker (explicit widget hint) ───────────
    signal_color: str = Field(
        default="#0969da",
        json_schema_extra={"widget": "color", "group": "Colors"},
        description="Signal line color",
    )
    envelope_color: str = Field(
        default="#cf222e",
        json_schema_extra={"widget": "color", "group": "Colors"},
        description="Envelope / accent color",
    )

    # ── str color picker (auto-detected) ──────────────────
    bg_color: str = Field(
        default="#ffffff",
        description="Background color",
        json_schema_extra={"group": "Colors"},
    )
    grid_color: str = Field(
        default="#e1e4e8",
        description="Grid color",
        json_schema_extra={"group": "Colors"},
    )

    # ── bool checkbox ─────────────────────────────────────
    show_grid: bool = Field(
        default=True, description="Show grid", json_schema_extra={"group": "Toggles"}
    )
    show_noise: bool = Field(
        default=True, description="Add noise", json_schema_extra={"group": "Toggles"}
    )
    fill_under: bool = Field(
        default=False,
        description="Fill under curve",
        json_schema_extra={"group": "Toggles"},
    )
    show_fft: bool = Field(
        default=True,
        description="Show FFT subplot",
        json_schema_extra={"group": "Toggles"},
    )
    show_histogram: bool = Field(
        default=True,
        description="Show histogram subplot",
        json_schema_extra={"group": "Toggles"},
    )

    # ── Literal select dropdown ───────────────────────────
    waveform: Literal[
        "sine", "cosine", "square", "sawtooth"
    ] = Field(
        default="sine",
        description="Waveform type",
        json_schema_extra={"group": "Waveform"},
    )
    line_style: Literal["-", "--", "-.", ":"] = Field(
        default="-",
        description="Line style",
        json_schema_extra={"group": "Display"},
    )
    window_fn: Literal[
        "none", "hanning", "hamming", "blackman"
    ] = Field(
        default="none",
        description="Window function",
        json_schema_extra={"group": "Waveform"},
    )

    # ── list[float] comma-separated ───────────────────────
    custom_yticks: list[float] = Field(
        default=[],
        description="Custom Y ticks (e.g. -1, 0, 1)",
        json_schema_extra={"group": "Data"},
    )
    harmonic_weights: list[float] = Field(
        default=[1.0, 0.5, 0.25],
        description=("Harmonic weights (e.g. 1.0, 0.5, 0.25)"),
        json_schema_extra={"group": "Signal"},
    )

    # ── list[int] comma-separated ─────────────────────────
    highlight_samples: list[int] = Field(
        default=[],
        description=("Highlight sample indices " "(e.g. 100, 200, 300)"),
        json_schema_extra={"group": "Data"},
    )

    # ── list[str] comma-separated ─────────────────────────
    annotations: list[str] = Field(
        default=[],
        description="Annotation labels at highlights",
        json_schema_extra={"group": "Data"},
    )

    # ── tuple[float, ...] comma-separated ─────────────────
    y_limits: tuple[float, ...] = Field(
        default=(),
        description="Y-axis limits (min, max)",
        json_schema_extra={"group": "Display"},
    )


# ================================================================
# Figure function
# ================================================================


def _build_signal(
    p: SignalParams,
    t: np.ndarray,
) -> np.ndarray:
    """Build composite waveform signal.

    Parameters
    ----------
    p : SignalParams
        Signal analysis parameters.
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
            return np.cos(raw)
        if p.waveform == "square":
            return np.sign(np.sin(raw))
        if p.waveform == "sawtooth":
            return 2 * (raw / (2 * np.pi) % 1) - 1
        return np.sin(raw)

    weights: list[float] = p.harmonic_weights or [
        1.0 / (k + 1) for k in range(p.harmonics)
    ]
    y: np.ndarray = np.zeros_like(t)
    for k in range(min(p.harmonics, len(weights))):
        w: float = (
            weights[k]
            if k < len(weights)
            else 1.0 / (k + 1)
        )
        y += w * _wave(
            p.base_frequency * (k + 1),
            p.phase_offset * (k + 1),
        )
    y *= p.amplitude

    if p.window_fn != "none":
        win_map: dict[str, type] = {
            "hanning": np.hanning,
            "hamming": np.hamming,
            "blackman": np.blackman,
        }
        y *= win_map[p.window_fn](len(y))

    if p.show_noise:
        rng = np.random.default_rng(p.random_seed)
        y += rng.normal(0, p.noise_level, size=len(t))

    return y


def signal_figure(p: SignalParams) -> Figure:
    """Generate a multi-subplot signal analysis figure.

    Parameters
    ----------
    p : SignalParams
        Signal analysis parameters.

    Returns
    -------
    Figure
        Matplotlib figure with signal, FFT,
        and histogram subplots.
    """
    dm.style.use("scientific")
    t: np.ndarray = np.linspace(
        0, 2 * np.pi, p.n_points
    )
    y: np.ndarray = _build_signal(p, t)

    # ── Determine layout ──────────────────────────────────
    n_extra: int = (
        int(p.show_fft) + int(p.show_histogram)
    )
    if n_extra == 0:
        fig_w: float = 17.0
        ncols: int = 1
        ratios: list[int] = [1]
    elif n_extra == 1:
        fig_w = 22.0
        ncols = 2
        ratios = [3, 1]
    else:
        fig_w = 26.0
        ncols = 3
        ratios = [3, 1, 1]

    # ── Figure creation (guide pattern) ───────────────────
    fig: Figure = plt.figure(
        figsize=(dm.cm2in(fig_w), dm.cm2in(9)),
        dpi=200,
    )

    # GridSpec: title row + plot row
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
    label: str = p.title_text
    if not label:
        label = (
            f"{p.waveform}  f={p.base_frequency:.1f}  "
            f"A={p.amplitude:.1f}  "
            f"phase={p.phase_offset:.2f}"
        )

    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(
        0.5,
        0.5,
        label,
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
        ax_signal.fill_between(
            t, y, alpha=0.1, color=p.signal_color
        )

    # Highlight samples
    for idx_i, sample_idx in enumerate(
        p.highlight_samples
    ):
        if 0 <= sample_idx < len(t):
            ax_signal.axvline(
                t[sample_idx],
                color=p.envelope_color,
                alpha=0.4,
                linewidth=1,
                linestyle=":",
            )
            ax_signal.plot(
                t[sample_idx],
                y[sample_idx],
                "o",
                color=p.envelope_color,
                markersize=5,
            )
            if (
                p.annotations
                and idx_i < len(p.annotations)
            ):
                ax_signal.annotate(
                    p.annotations[idx_i],
                    (t[sample_idx], y[sample_idx]),
                    textcoords="offset points",
                    xytext=(8, 8),
                    fontsize=dm.fs(-1),
                )

    ax_signal.set_xlim(0, 2 * np.pi)
    if p.y_limits and len(p.y_limits) >= 2:
        ax_signal.set_ylim(
            p.y_limits[0], p.y_limits[1]
        )

    ax_signal.set_xlabel(
        p.x_label, fontsize=dm.fs(0)
    )
    ax_signal.set_ylabel(
        p.y_label, fontsize=dm.fs(0)
    )

    if p.custom_yticks:
        ax_signal.set_yticks(p.custom_yticks)

    ax_signal.legend(
        loc="upper right",
        fontsize=dm.fs(-1),
        framealpha=0.5,
    )

    if p.show_grid:
        ax_signal.grid(
            True, alpha=0.2, color=p.grid_color
        )

    # ── Subplot 2: FFT ────────────────────────────────────
    col_idx: int = 1
    if p.show_fft and ncols >= 2:
        ax_fft = fig.add_subplot(gs[1, col_idx])
        fft_vals: np.ndarray = np.abs(np.fft.rfft(y))
        freqs: np.ndarray = np.fft.rfftfreq(
            len(t), d=(t[1] - t[0])
        )
        max_freq_idx: int = min(len(freqs), 50)
        ax_fft.bar(
            freqs[1:max_freq_idx],
            fft_vals[1:max_freq_idx],
            width=freqs[1] - freqs[0],
            color=p.signal_color,
            alpha=0.8,
        )
        ax_fft.set_xlabel(
            "Frequency", fontsize=dm.fs(-1)
        )
        ax_fft.set_ylabel(
            "Magnitude", fontsize=dm.fs(-1)
        )
        ax_fft.set_title(
            "Frequency Spectrum", fontsize=dm.fs(0)
        )
        if p.show_grid:
            ax_fft.grid(
                True, alpha=0.2, color=p.grid_color
            )
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
        ax_hist.set_xlabel(
            "Count", fontsize=dm.fs(-1)
        )
        ax_hist.set_ylabel(
            "Value", fontsize=dm.fs(-1)
        )
        ax_hist.set_title(
            "Distribution", fontsize=dm.fs(0)
        )
        if p.show_grid:
            ax_hist.grid(
                True, alpha=0.2, color=p.grid_color
            )

    # ── Layout optimization ───────────────────────────────
    dm.simple_layout(fig, gs=gs)
    return fig


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    run(signal_figure, title="Signal Analysis")
