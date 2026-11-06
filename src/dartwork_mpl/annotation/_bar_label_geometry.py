"""Where a bar value label sits: anchor, side, view and host Axes.

The geometry behind :func:`~._bar_labels.label_bars`, kept apart from the
text, unit and option handling:

* **Anchor.** The bar end (the bar's middle for ``where="center"``) in the
  bar axes' data coordinates. An outside label moves past the bar's error
  bar, but never past the edge of the view.
* **View.** A label is shown while its anchor lies in the bar axes' view,
  within :data:`EDGE_TOL_PX` (one pixel, as matplotlib's own annotation
  clipping). A bar whose end sits on a limit keeps its label just outside
  the axes; a bar beyond the view, or whose end runs past a limit the
  caller set, has none.
* **Side.** Outside the end, 3 pt (:data:`OFFSET_PT`) away; a bar growing
  down or left on screen (a negative value, or an inverted value axis) has
  its label below or left of the end. ``"inside"`` mirrors that inwards,
  ``"center"`` centres the label on the bar.
* **Host.** On a ``twinx`` / ``twiny`` pair the labels live on the Axes
  drawn last, by zorder and then figure order, so no partner draws over
  them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.axes import Axes

from .._figure_geometry import same_position_axes

if TYPE_CHECKING:
    from ._bar_labels import BarLabel, Where

__all__ = [
    "EDGE_TOL_PX",
    "OFFSET_PT",
    "bar_point",
    "host_axes",
    "in_view",
    "place",
]

# Point offset between a bar end and its label (``dm.annotate_value``'s).
OFFSET_PT = 3.0
# How far (display pixels) an anchor may sit past the view and still show.
EDGE_TOL_PX = 1.0


def host_axes(bar_axes: Axes) -> Axes:
    """The Axes drawn last in ``bar_axes``' box: the top-most twin.

    Matplotlib draws Axes by zorder, then in figure order, so the
    ``ax.set_zorder(ax2.get_zorder() + 1)`` idiom puts ``ax`` on top.
    """
    owners = same_position_axes(bar_axes)
    parent = bar_axes.get_figure(root=False)
    order = parent.axes if parent is not None else owners
    return max(
        owners,
        key=lambda member: (
            member.get_zorder(),
            order.index(member) if member in order else -1,
        ),
    )


def bar_point(label: BarLabel, where: Where) -> tuple[float, float]:
    """The bar end (its middle for ``"center"``) in data coordinates."""
    bar = label.bar
    x, y = float(bar.get_x()), float(bar.get_y())
    width, height = float(bar.get_width()), float(bar.get_height())
    if where == "center":
        return (x + width / 2, y + height / 2)
    if label.orientation == "vertical":
        return (x + width / 2, y + height)
    return (x + width, y + height / 2)


def in_view(label: BarLabel, where: Where) -> bool:
    """Whether the label's anchor lies in the bar axes' view (1 px slack)."""
    axes = label.bar_axes
    shown = axes.transData.transform(bar_point(label, where))
    if not np.all(np.isfinite(shown)):
        return False
    box = axes.get_window_extent()
    return bool(
        box.x0 - EDGE_TOL_PX <= shown[0] <= box.x1 + EDGE_TOL_PX
        and box.y0 - EDGE_TOL_PX <= shown[1] <= box.y1 + EDGE_TOL_PX
    )


def _outward(label: BarLabel) -> int:
    """+1 when the bar grows towards higher display coordinates, else -1."""
    bar = label.bar
    length = (
        bar.get_height() if label.orientation == "vertical" else bar.get_width()
    )
    sign = -1 if length < 0 else 1
    return -sign if label.value_axis.get_inverted() else sign


def _error_extent(label: BarLabel) -> np.ndarray | None:
    """The bar's error bar along the value axis, as data values, if any.

    The segment at the bar's index that runs along the value axis
    (``yerr`` for ``bar``, ``xerr`` for ``barh``), as ``ax.bar_label``
    reads it.
    """
    errorbar = label.container.errorbar
    if errorbar is None:
        return None
    along = 1 if label.orientation == "vertical" else 0
    for collection in errorbar.lines[2]:
        segments = collection.get_segments()
        if label.index >= len(segments):
            continue
        segment = np.asarray(segments[label.index], dtype=float)
        if (
            segment.shape != (2, 2)
            or segment[0, 1 - along] != segment[1, 1 - along]
        ):
            continue  # the error bar across the value axis
        extent = segment[:, along][np.isfinite(segment[:, along])]
        return extent if extent.size else None
    return None


def _past_error_bar(label: BarLabel, end: float) -> float:
    """``end`` pushed past the error bar's cap, but not past the view."""
    extent = _error_extent(label)
    if extent is None:
        return end
    low, high = sorted(float(v) for v in label.value_axis.get_view_interval())
    if label.value >= 0:
        return max(end, min(float(extent.max()), high))
    return min(end, max(float(extent.min()), low))


def _setter(label: BarLabel, name: str) -> Callable[[Any], None]:
    def write(value: Any) -> None:
        setattr(label, name, value)
        label.stale = True

    return write


def place(label: BarLabel, where: Where) -> None:
    """Anchor and align ``label`` on its bar for ``where``.

    Writes only what ``label`` still owns (:meth:`BarLabel.own`).
    """
    if where == "center":
        # Fractions of the bar's own extent: its middle on any scale.
        xy: tuple[float, float] = (0.5, 0.5)
        xyann = (0.0, 0.0)
        ha, va = "center", "center"
    else:
        inside = where == "inside"
        x, y = bar_point(label, where)
        if label.orientation == "vertical":
            xy = (x, y if inside else _past_error_bar(label, y))
        else:
            xy = (x if inside else _past_error_bar(label, x), y)
        toward = _outward(label) * (-1 if inside else 1)
        offset = toward * OFFSET_PT
        if label.orientation == "vertical":
            ha, va = "center", ("bottom" if toward > 0 else "top")
            xyann = (0.0, offset)
        else:
            ha, va = ("left" if toward > 0 else "right"), "center"
            xyann = (offset, 0.0)
    label.own("xy", tuple(label.xy), xy, _setter(label, "xy"))
    label.own("offset", tuple(label.xyann), xyann, _setter(label, "xyann"))
    label.own(
        "ha", label.get_horizontalalignment(), ha, label.set_horizontalalignment
    )
    label.own(
        "va", label.get_verticalalignment(), va, label.set_verticalalignment
    )
