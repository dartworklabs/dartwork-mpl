"""Axis names: two-line wrapping and the Low-High arrow axis."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text

from .._figure_geometry import BBOX_ERRORS, get_renderer
from ..scale import fs
from ._placement_geometry import _renderer_for_axes

if TYPE_CHECKING:
    from matplotlib.figure import SubFigure


_Axis = Literal["x", "y"]


def _parse_axis(axis: str, message: str) -> _Axis:
    """Return ``"x"`` or ``"y"``; raise ``ValueError(message)`` for anything else."""
    match axis:
        case "x" | "y":
            return axis
        case _:
            raise ValueError(message)


_UNIT_SUFFIX_RE = re.compile(r"\s*([([][^)\]]{1,32}[)\]])\s*$")


def _split_label_two_lines(label: str) -> str | None:
    stripped = label.strip()
    if not stripped or "\n" in stripped:
        return None

    unit = ""
    body = stripped
    match = _UNIT_SUFFIX_RE.search(stripped)
    if match:
        unit = match.group(1)
        body = stripped[: match.start()].strip()

    words = body.split()
    if unit and len(words) == 1:
        return f"{body}\n{unit}"
    if len(words) < 2:
        return None

    target = len(body) / 2.0
    split_index = min(
        range(1, len(words)),
        key=lambda index: abs(len(" ".join(words[:index])) - target),
    )
    first = " ".join(words[:split_index])
    second = " ".join(words[split_index:])
    if unit:
        second = f"{second} {unit}" if second else unit
    if not first or not second:
        return None
    return f"{first}\n{second}"


def wrap_axis_label(ax: Axes, axis: str = "y", max_frac: float = 1.0) -> bool:
    """Wrap an overlong x/y-axis label to two lines at word boundaries.

    The rendered label length is compared with the corresponding axes spine
    length. Parenthesized or bracketed unit suffixes stay intact and are moved
    to the second line when wrapping is needed. Returns ``True`` only when the
    label text changed.
    """
    which = _parse_axis(axis, "axis must be 'x' or 'y'")
    if max_frac <= 0:
        raise ValueError("max_frac must be positive")

    label = ax.xaxis.label if which == "x" else ax.yaxis.label
    raw_text = label.get_text()
    wrapped = _split_label_two_lines(raw_text)
    if wrapped is None:
        return False

    _fig, renderer = _renderer_for_axes(ax)
    try:
        text_bbox = label.get_window_extent(renderer)
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    rendered_length = text_bbox.width if which == "x" else text_bbox.height
    axis_length = axes_bbox.width if which == "x" else axes_bbox.height
    if rendered_length <= axis_length * float(max_frac):
        return False

    label.set_text(wrapped)
    return True


def wrap_axis_labels(
    fig: Figure | SubFigure, axis: str = "both", max_frac: float = 1.0
) -> list[Text]:
    """Wrap overlong axis labels for every axes in a figure.

    ``axis`` may be ``"x"``, ``"y"``, or ``"both"``. The returned list
    contains the label Text objects that were changed.
    """
    axes_to_wrap: tuple[_Axis, ...] = (
        ("x", "y")
        if axis == "both"
        else (_parse_axis(axis, "axis must be 'x', 'y', or 'both'"),)
    )
    changed: list[Text] = []
    for ax in fig.axes:
        for axis_name in axes_to_wrap:
            if wrap_axis_label(ax, axis_name, max_frac=max_frac):
                label = ax.xaxis.label if axis_name == "x" else ax.yaxis.label
                changed.append(label)
    return changed


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
    along = _parse_axis(
        direction,
        f"direction must be 'x' or 'y', got {direction!r}. "
        "(Any other value would silently draw a y-axis arrow.)",
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
        {"rotation": 90, "rotation_mode": "anchor"} if along == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if along == "x":
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

    i = 0 if along == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip: float, tail: float) -> None:
        if along == "x":
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
