"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, and ``arrow_axis`` for drawing bidirectional Low-High arrow axes.
"""

from __future__ import annotations

__all__ = ["arrow_axis", "label_axes"]

import string
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Text

from ._helpers import get_renderer
from .scale import fs


def _auto_panel_labels(n: int) -> list[str]:
    """Spreadsheet-style panel labels: a, b, ..., z, aa, ab, ....

    ``string.ascii_lowercase[:n]`` silently truncated at 26, dropping
    labels for any grid larger than 26 panels; this extends past z.
    """
    labels: list[str] = []
    for i in range(n):
        chars = ""
        k = i
        while True:
            chars = string.ascii_lowercase[k % 26] + chars
            k = k // 26 - 1
            if k < 0:
                break
        labels.append(chars)
    return labels


def label_axes(
    axes: list[Axes] | np.ndarray[Any, Any],
    labels: list[str] | None = None,
    fontsize: float | None = None,
    fontweight: str = "bold",
    x: float | str = "auto",
    y: float = 1.05,
    **kwargs: Any,
) -> list[Text]:
    """Add standardized identification labels (a, b, c, ...) to subplot panels.

    Commonly used in academic papers and reports to annotate multiple panels
    of a figure, placing labels at the left edge or top corner of each Axes.

    Parameters
    ----------
    axes : list[Axes] | np.ndarray
        List or array of Axes objects to label.
    labels : list[str] | None, optional
        Custom text labels. If None, lowercase letters (a, b, c, ...)
        are assigned automatically.
    fontsize : float | None, optional
        Font size for the labels. If ``None`` (default), resolves to
        ``fs(1)`` so panel labels track the active preset's base font
        size instead of a fixed point value.
    fontweight : str, optional
        Font weight for the labels. Default is "bold".
    x : float | str, optional
        Horizontal position in Axes-relative coordinates (may exceed 0.0-1.0).
        If "auto", the optimal x position is determined based on whether
        a y-axis label is present (-0.18 or -0.02).
    y : float, optional
        Vertical position in Axes-relative coordinates. Default is 1.05.
    **kwargs
        Additional text properties passed to ``ax.text()``.

    Returns
    -------
    list
        List of created Text objects.
    """
    if fontsize is None:
        fontsize = fs(1)

    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = _auto_panel_labels(len(axes))

    texts: list[Text] = []
    for ax, label in zip(axes, labels, strict=False):
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = float(x)

        t = ax.text(
            x_pos,
            y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
            **kwargs,
        )
        texts.append(t)

    return texts


def arrow_axis(
    ax: Axes,
    direction: str,
    label: str,
    *,
    offset: float = -0.10,
    low: str = "Low",
    high: str = "High",
    fontsize: float | None = None,
    fontsize_label: float | None = None,
    pad: float = -0.005,
    weight: str = "normal",
    color: str = "black",
    arrow_kw: dict[str, Any] | None = None,
) -> None:
    """Draw a bidirectional Low-High arrow axis along the edge of a plot.

    Produces a visual like ``Low ◄── label ──► High`` near the spine exterior.

    Parameters
    ----------
    ax : Axes
        Target Axes object for the annotation.
    direction : {'x', 'y'}
        "x": insert a horizontal arrow axis below the x-axis spine.
        "y": insert a vertical arrow axis to the left of the y-axis spine.
    label : str
        Center label text placed at the midpoint of the axis.
    offset : float, optional
        Offset from the spine in Axes-fraction units. Default is -0.10
        (sufficiently outside to avoid overlap with tick labels).
    low : str, optional
        Text for the low end (bottom/left) of the axis. Default is "Low".
    high : str, optional
        Text for the high end (top/right) of the axis. Default is "High".
    fontsize : float | None, optional
        Font size for the Low/High endpoint labels. Default is fs(-1).
    fontsize_label : float | None, optional
        Font size for the center label. Default is fs(0).
    pad : float, optional
        Fractional gap between text and arrowheads. Default is -0.005.
    weight : str, optional
        Font weight applied to all text elements.
    color : str, optional
        Color for both text and arrows. Default is "black".
    arrow_kw : dict | None, optional
        Override the arrowprops passed to the internal ``ax.annotate`` calls.
    """
    if fontsize is None:
        fontsize = fs(-1)
    if direction not in ("x", "y"):
        raise ValueError(
            f"direction must be 'x' or 'y', got {direction!r}. "
            "(Any other value would silently draw a y-axis arrow.)"
        )
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {
            "arrowstyle": "-|>,head_width=0.1",
            "color": color,
            "lw": 0.25,
        }

    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    renderer = get_renderer(fig)
    inv = ax.transAxes.inverted()
    rot_kw: dict[str, Any] = (
        {"rotation": 90, "rotation_mode": "anchor"} if direction == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if direction == "x":
        p_lo: tuple[float, float] = (0.0, float(offset))
        p_hi: tuple[float, float] = (1.0, float(offset))
        p_lb: tuple[float, float] = (0.5, float(offset))
    else:
        p_lo = (float(offset), 0.0)
        p_hi = (float(offset), 1.0)
        p_lb = (float(offset), 0.5)

    t_lo = ax.text(
        *p_lo,
        low,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="left",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_hi = ax.text(
        *p_hi,
        high,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="right",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_lb = ax.text(
        *p_lb,
        label,
        transform=ax.transAxes,
        fontsize=fontsize_label,
        fontweight=weight,
        color=color,
        ha="center",
        va="center",
        clip_on=False,
        **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    fig.canvas.draw()

    def _edges(t: Text) -> np.ndarray[Any, Any]:
        bb = t.get_window_extent(renderer)
        return inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])

    i = 0 if direction == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip: float, tail: float) -> None:
        if direction == "x":
            ax.annotate(
                "",
                xy=(tip, offset),
                xytext=(tail, offset),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "",
                xy=(offset, tip),
                xytext=(offset, tail),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)
    _arrow(hi_start - pad, lb_hi + pad)
