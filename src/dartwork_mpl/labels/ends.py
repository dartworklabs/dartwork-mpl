"""Line names at the lines' ends instead of a legend."""

from __future__ import annotations

import logging
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation, Text

from ..hidden import axes_name
from . import decide
from .measure import backdrop, drawn_renderer, px_per_pt, readable_on
from .model import Column

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D


LOG = logging.getLogger("dartwork_mpl.labels")


@dataclass(eq=False)
class _LineEnds:
    labels: list[Annotation]
    ends: list[tuple[float, float]]
    gap_pt: float


# The groups of names ``label_line_ends`` placed, by Axes.
GROUPS: weakref.WeakKeyDictionary[Axes, list[_LineEnds]] = (
    weakref.WeakKeyDictionary()
)


#: The offset (pt) the slice last gave each name; one that differs was
#: moved by the caller and stays where they put it.
OFFSETS: weakref.WeakKeyDictionary[Annotation, tuple[float, float]] = (
    weakref.WeakKeyDictionary()
)


def _moved(text: Annotation) -> bool:
    last = OFFSETS.get(text)
    return last is not None and tuple(text.xyann) != last


def _space(ax: Axes, group: _LineEnds, renderer: RendererBase) -> bool:
    """Spread the group's labels one line apart at ``ax``'s size now."""
    keep = [
        (t, end)
        for t, end in zip(group.labels, group.ends, strict=True)
        if t.axes is ax and t in ax.texts and not _moved(t)
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
        OFFSETS[label] = offset
    return moved


def space_line_ends(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_line_ends`` names spaced again at each Axes' size now; whether one moved."""
    moved = False
    for ax in fig.axes:
        for group in GROUPS.get(ax, []):
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


def label_line_ends(ax: Axes) -> list[Text]:
    """Name each labelled line at its last point instead of a legend.

    The line's label, ``axes.labelpad`` right of its last finite point, in
    the line's colour made readable on the background; names that would
    overlap move apart and keep their order. The legend is removed;
    ``dm.simple_layout`` makes room.
    """
    gap = float(mpl.rcParams["axes.labelpad"])
    background = backdrop(ax)
    if (legend := ax.get_legend()) is not None:
        legend.remove()
        LOG.info(
            "removed the legend of %s: dm.label_line_ends names its lines "
            "at their ends instead; call ax.legend() after it to have both",
            axes_name(ax),
        )
    group = _LineEnds([], [], gap)
    for line in ax.get_lines():
        end = _last_point(line)
        if (
            end is None
            or not line.get_visible()
            or str(line.get_label()).startswith("_")
        ):
            continue
        ink = readable_on(line.get_color(), background)
        if mcolors.to_hex(ink) != mcolors.to_hex(line.get_color()):
            LOG.info(
                'wrote the name "%s" on %s in %s, not its line\'s %s: the '
                "line's colour reads under 4.5:1 on the background; set the "
                "name's colour yourself afterwards (text.set_color) to keep "
                "the line's",
                line.get_label(),
                axes_name(ax),
                mcolors.to_hex(ink),
                mcolors.to_hex(line.get_color()),
            )
        group.labels.append(
            ax.annotate(  # pyright: ignore[reportUnknownMemberType]
                str(line.get_label()),
                xy=end,
                xycoords="data",
                xytext=(gap, 0.0),
                textcoords="offset points",
                color=ink,
                ha="left",
                va="center",
                annotation_clip=False,
            )
        )
        group.ends.append(end)
    if len(group.labels) >= 2:
        GROUPS.setdefault(ax, []).append(group)
        _space(ax, group, drawn_renderer(ax))
    return list(group.labels)
