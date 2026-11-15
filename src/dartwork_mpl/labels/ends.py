"""Line names at the lines' ends instead of a legend."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from . import decide
from .measure import drawn_renderer, px_per_pt
from .model import Column

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

LINE_ENDS_ATTR = "_dm_line_end_labels"


@dataclass(eq=False)
class _LineEnds:
    labels: list[Annotation]
    ends: list[tuple[float, float]]
    gap_pt: float


def _space(ax: Axes, group: _LineEnds, renderer: RendererBase) -> bool:
    """Spread the group's labels one line apart at ``ax``'s size now."""
    keep = [
        (t, end)
        for t, end in zip(group.labels, group.ends, strict=True)
        if t.axes is ax and t in ax.texts
    ]
    if len(keep) < 2:
        return False
    to_pt = 1.0 / px_per_pt(ax)
    height = (
        max(t.get_window_extent(renderer).height for t, _ in keep) * to_pt * 1.1
    )
    wanted = [float(ax.transData.transform(end)[1]) * to_pt for _, end in keep]
    order = sorted(range(len(keep)), key=lambda i: wanted[i])
    spread = decide.spread(
        Column(tuple(wanted[i] for i in order), height)
    ).centres
    moved = False
    for i, y_pt in zip(order, spread, strict=True):
        label = keep[i][0]
        offset = (group.gap_pt, y_pt - wanted[i])
        old = tuple(label.xyann)
        if abs(old[0] - offset[0]) > 0.01 or abs(old[1] - offset[1]) > 0.01:
            moved = True
        label.xyann = offset
    return moved


def space_line_ends(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_line_ends`` names spaced again at each Axes' size now; whether one moved."""
    moved = False
    for ax in fig.axes:
        for group in getattr(ax, LINE_ENDS_ATTR, []):
            moved = _space(ax, group, renderer) or moved
    return moved


def _last_point(line: Line2D) -> tuple[float, float] | None:
    x = np.asarray(line.convert_xunits(line.get_xdata()), dtype=float)  # pyright: ignore[reportUnknownMemberType]
    y = np.asarray(line.convert_yunits(line.get_ydata()), dtype=float)  # pyright: ignore[reportUnknownMemberType]
    if x.size == 0 or x.shape != y.shape:
        return None
    finite = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
    return (
        None
        if finite.size == 0
        else (float(x[finite[-1]]), float(y[finite[-1]]))
    )


def label_line_ends(
    ax: Axes,
    lines: Iterable[Line2D] | None = None,
    *,
    gap_pt: float | None = None,
    **kw: Any,
) -> list[Text]:
    """Name each line at its last point instead of a legend.

    The line's label, ``gap_pt`` (default ``axes.labelpad``) right of its last
    finite point, in the line's colour made readable on the background;
    names that would overlap move apart and keep their order. The legend is
    removed; ``dm.simple_layout`` makes room. Keywords go to the texts.
    """
    from ..color import ensure_contrast

    if lines is None:
        lines = [
            ln
            for ln in ax.get_lines()
            if ln.get_visible() and not str(ln.get_label()).startswith("_")
        ]
    gap = float(mpl.rcParams["axes.labelpad"] if gap_pt is None else gap_pt)
    background = mcolors.to_rgba(ax.patch.get_facecolor())
    if not ax.patch.get_visible() or background[3] == 0:
        background = mcolors.to_rgba(ax.figure.get_facecolor())
    if (legend := ax.get_legend()) is not None:
        legend.remove()
    group = _LineEnds([], [], gap)
    for line in lines:
        end = _last_point(line)
        if end is None:
            continue
        style: dict[str, Any] = {
            "color": ensure_contrast(line.get_color(), background),
            "ha": "left",
            "va": "center",
            "annotation_clip": False,
            **kw,
        }
        group.labels.append(
            ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                str(line.get_label()),
                xy=end,
                xycoords="data",
                xytext=(gap, 0.0),
                textcoords="offset points",
                **style,
            )
        )
        group.ends.append(end)
    if len(group.labels) >= 2:
        if not hasattr(ax, LINE_ENDS_ATTR):
            setattr(ax, LINE_ENDS_ATTR, [])
        getattr(ax, LINE_ENDS_ATTR).append(group)
        _space(ax, group, drawn_renderer(ax))
    return list(group.labels)
