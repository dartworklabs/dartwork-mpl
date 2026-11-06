"""Where a bar value label sits: anchor, side, view and host Axes.

The geometry behind :func:`~._bar_labels.label_bars`, kept apart from the
text, unit and option handling:

* **Anchor.** The bar end in the bar axes' data coordinates; for
  ``where="center"`` the middle of the bar's box on screen (on a log axis
  its geometric middle, not the data mean). An outside label moves past
  the bar's error bar and past the far ends of the bars it must clear
  (``clear_of``: the neighbours a crowded label spans), but never past the
  edge of the view.
* **View.** A label is shown while its anchor, on screen where it is drawn,
  lies in the bar axes' view, within :data:`EDGE_TOL_PX` (one pixel, as
  matplotlib's own annotation clipping). A bar whose end sits on a limit
  keeps its label just outside the axes; a bar beyond the view has none.
* **Past a limit.** A plain bar (not a stack's segment or total) whose end
  runs more than :data:`EDGE_TOL_PX` past the view in the direction it
  grows, while it starts inside that edge and its middle across the bars
  is in view, is cut by a limit the caller set (an autoscaled view holds
  its bars): its end label (``"outside"`` or ``"inside"``) sits just inside
  that edge, 3 pt in, with its true value (:func:`clipped_edge`), and
  shows while the part of the bar in view holds it. Its ink is the one for
  a label on its bar (:mod:`._bar_label_ink`), set at each draw, so a
  wider view puts the label back outside in its own ink.
* **Side.** Outside the end, 3 pt (:data:`OFFSET_PT`) away; a bar growing
  down or left on screen (a negative value, or an inverted value axis) has
  its label below or left of the end. ``"inside"`` mirrors that inwards,
  ``"center"`` centres the label on the bar. A stack's total is anchored on
  the bar that ends the stack, so it sits beyond the stack's end, and
  beyond the label it must clear (``beyond``: the top segment's, labelled
  ``"outside"`` at the same end) by that label's length and 3 pt more.
* **Room.** A label on a stack segment fits when the segment is at least as
  long as the label along the value axis (:func:`fits_on_bar`); a label
  inside a limit, when the part of its bar in view is that long and 3 pt.
* **Host.** On a ``twinx`` / ``twiny`` pair the labels live on the Axes
  drawn last, by zorder and then figure order, so no partner draws over
  them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Text

from .._figure_geometry import same_position_axes

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase

    from ._bar_label_options import Where
    from ._bar_labels import BarLabel

__all__ = [
    "EDGE_TOL_PX",
    "OFFSET_PT",
    "bar_point",
    "clipped_edge",
    "fits_on_bar",
    "host_axes",
    "in_view",
    "outward",
    "place",
    "text_length",
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


def bar_point(label: BarLabel) -> tuple[float, float]:
    """The bar end in data coordinates (a centred label's anchor is the bar).

    The true end, also past the view: a label inside a limit is anchored on
    the edge instead (:func:`place`, :func:`clipped_edge`).
    """
    bar = label.bar
    x, y = float(bar.get_x()), float(bar.get_y())
    width, height = float(bar.get_width()), float(bar.get_height())
    if label.orientation == "vertical":
        return (x + width / 2, y + height)
    return (x + width, y + height / 2)


def _along(label: BarLabel) -> int:
    """The display coordinate the bar's value runs along (1: y, 0: x)."""
    return 1 if label.orientation == "vertical" else 0


def _on_screen(label: BarLabel) -> np.ndarray:
    """The bar's base and end, middle across, in display pixels (2 x 2)."""
    bar = label.bar
    x, y = float(bar.get_x()), float(bar.get_y())
    width, height = float(bar.get_width()), float(bar.get_height())
    if label.orientation == "vertical":
        points = [(x + width / 2, y), (x + width / 2, y + height)]
    else:
        points = [(x, y + height / 2), (x + width, y + height / 2)]
    return np.asarray(label.bar_axes.transData.transform(points), dtype=float)


def clipped_edge(label: BarLabel) -> float | None:
    """The view edge a plain bar runs past, in display pixels, if it does.

    For a plain bar's end label (``kind`` ``"edge"``, ``where``
    ``"outside"`` or ``"inside"``): its bar ends more than
    :data:`EDGE_TOL_PX` past the view in the direction it grows
    (:func:`outward`), starts inside that edge, and its middle across the
    bars lies in the view (the same slack). ``None`` otherwise: the end in
    view, a bar beyond the view, a stack's segment or total, a centred
    label. Read afresh at each call, as the view may move.
    """
    if label.kind != "edge" or label.where == "center":
        return None
    base, end = _on_screen(label)
    along = _along(label)
    view = label.bar_axes.get_window_extent()
    low, high = (view.y0, view.y1) if along else (view.x0, view.x1)
    across = (view.x0, view.x1) if along else (view.y0, view.y1)
    middle = float(end[1 - along])
    if not (
        across[0] - EDGE_TOL_PX <= middle <= across[1] + EDGE_TOL_PX
    ):  # NaN fails too
        return None
    start, stop = float(base[along]), float(end[along])
    if outward(label) > 0:
        cut, edge = stop - high > EDGE_TOL_PX and start < high, high
    else:
        cut, edge = low - stop > EDGE_TOL_PX and start > low, low
    return float(edge) if cut else None


def _at_edge(label: BarLabel, edge: float) -> tuple[float, float]:
    """The bar's end point moved along its value to the display ``edge``."""
    axes = label.bar_axes
    along = _along(label)
    point = np.array(bar_point(label), dtype=float)
    shown = axes.transData.transform(point)
    shown[along] = edge
    point[along] = axes.transData.inverted().transform(shown)[along]
    return (float(point[0]), float(point[1]))


def in_view(label: BarLabel, where: Where) -> bool:
    """Whether the label's anchor lies in the bar axes' view (1 px slack).

    The anchor on screen where :func:`place` puts it: the bar end mapped
    through the data transform, or for ``"center"`` the middle of the bar's
    box on screen (on a log axis the geometric middle, not the data mean).
    A bar cut by a limit (:func:`clipped_edge`) has its anchor on that
    edge, so in view.
    """
    axes = label.bar_axes
    if where == "center":
        box = label.bar.get_window_extent()
        shown = np.array([(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2])
    elif clipped_edge(label) is not None:
        return True
    else:
        shown = axes.transData.transform(bar_point(label))
    if not np.all(np.isfinite(shown)):
        return False
    box = axes.get_window_extent()
    return bool(
        box.x0 - EDGE_TOL_PX <= shown[0] <= box.x1 + EDGE_TOL_PX
        and box.y0 - EDGE_TOL_PX <= shown[1] <= box.y1 + EDGE_TOL_PX
    )


def text_length(label: BarLabel, renderer: RendererBase | None) -> float:
    """The label's text extent along the value axis, in display pixels.

    Its font, size and rotation as drawn, measured with ``renderer`` (the
    canvas's renderer at the figure's current dpi); with ``None``,
    matplotlib uses the renderer of the label's last draw.
    """
    text = Text.get_window_extent(label, renderer)  # the text, not the anchor
    return float(text.height if label.orientation == "vertical" else text.width)


def fits_on_bar(label: BarLabel, text_px: float) -> bool:
    """Whether ``label`` is no longer than its bar along the value axis.

    ``text_px`` (:func:`text_length`), plus the 3 pt inset for
    ``"inside"`` and for a label inside a limit, against the bar's length
    on screen, read afresh; for a bar cut by a limit
    (:func:`clipped_edge`), the length of the part in view.
    """
    edge = clipped_edge(label)
    need = text_px
    if label.where == "inside" or edge is not None:
        figure = label.get_figure(root=True)
        dpi = figure.dpi if figure is not None else 72.0
        need += OFFSET_PT * dpi / 72.0
    along = _along(label)
    base, end = _on_screen(label)
    if edge is None:
        length = abs(float(end[along] - base[along]))
    else:
        view = label.bar_axes.get_window_extent()
        low, high = (view.y0, view.y1) if along else (view.x0, view.x1)
        length = abs(edge - min(max(float(base[along]), low), high))
    return bool(np.isfinite(length) and length >= need)


def outward(label: BarLabel) -> int:
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


def _past_bars(label: BarLabel, end: float) -> float:
    """``end`` pushed past the far ends of ``label.clear_of``, within the view.

    The far end is the one on the label's side on screen; a bar that ends
    short of ``end`` (or that is gone) changes nothing.
    """
    bars = [bar for bar in label.clear_of if bar.axes is not None]
    if not bars:
        return end
    axes = label.bar_axes
    along = 1 if label.orientation == "vertical" else 0
    toward = outward(label)
    anchor = np.array(bar_point(label), dtype=float)
    anchor[along] = end
    shown = axes.transData.transform(anchor)
    reach = float(shown[along])
    for bar in bars:
        box = bar.get_window_extent()
        far = (box.y1, box.y0) if along else (box.x1, box.x0)
        reach = max(reach, far[0]) if toward > 0 else min(reach, far[1])
    view = axes.get_window_extent()
    edges = (view.y0, view.y1) if along else (view.x0, view.x1)
    reach = min(max(reach, edges[0]), edges[1])
    if (reach - float(shown[along])) * toward <= 0:
        return end
    shown[along] = reach
    return float(axes.transData.inverted().transform(shown)[along])


def _beyond_pt(label: BarLabel) -> float:
    """How far (points) ``label`` moves out to clear ``label.beyond``.

    The other label's length along the value axis plus 3 pt, while it is
    drawn (added to an Axes and visible); else nothing.
    """
    other = label.beyond
    if other is None or other.axes is None or not other.get_visible():
        return 0.0
    figure = label.get_figure(root=True)
    dpi = figure.dpi if figure is not None else 72.0
    return other.measured_length() * 72.0 / dpi + OFFSET_PT


def _setter(label: BarLabel, name: str) -> Callable[[Any], None]:
    def write(value: Any) -> None:
        setattr(label, name, value)
        label.stale = True

    return write


def place(label: BarLabel, where: Where) -> None:
    """Anchor and align ``label`` on its bar for ``where``.

    A bar cut by a limit (:func:`clipped_edge`) has its label inside that
    edge, as ``"inside"`` places it at the bar end. Writes only what
    ``label`` still owns (:meth:`BarLabel.own`).
    """
    if where == "center":
        # Fractions of the bar's own extent: its middle on any scale.
        xy: tuple[float, float] = (0.5, 0.5)
        xyann = (0.0, 0.0)
        ha, va = "center", "center"
    else:
        inside = where == "inside"
        x, y = bar_point(label)
        edge = clipped_edge(label)
        if edge is not None:  # inside the limit the bar runs past
            inside = True
            x, y = _at_edge(label, edge)
        elif label.orientation == "vertical":
            if not inside:
                y = _past_bars(label, _past_error_bar(label, y))
        elif not inside:
            x = _past_bars(label, _past_error_bar(label, x))
        xy = (x, y)
        toward = outward(label) * (-1 if inside else 1)
        offset = toward * (OFFSET_PT + (0.0 if inside else _beyond_pt(label)))
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
