"""What an Axes draws around its box: titles, axis labels, tick labels; its twins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import matplotlib as mpl
import numpy as np
from matplotlib.text import Text

if TYPE_CHECKING:
    from matplotlib.axes import Axes

# ``ax.title`` is only the centre title. ``ax.set_title(..., loc="left")``
# and ``loc="right"`` write to these private attributes instead, so a walk
# over ``ax.title`` alone never sees a left-aligned headline.
_TITLE_ATTRS: dict[Literal["center", "left", "right"], str] = {
    "center": "title",
    "left": "_left_title",
    "right": "_right_title",
}


def axes_titles(ax: Axes) -> dict[str, Text]:
    """Return the title Text artists of ``ax`` keyed by ``set_title``'s ``loc``.

    This is the one place that reads matplotlib's private title
    attributes. Each is read with ``getattr`` and kept only while its text
    matches the public ``ax.get_title(loc=...)``, so a matplotlib that
    renames or repurposes them yields fewer titles instead of wrong ones.
    """
    titles: dict[str, Text] = {}
    for loc, attr in _TITLE_ATTRS.items():
        text = getattr(ax, attr, None)
        if not isinstance(text, Text):
            continue
        try:
            public = ax.get_title(loc=loc)
        except (TypeError, ValueError, AttributeError):
            continue
        if text.get_text() == public:
            titles[loc] = text
    return titles


# Matplotlib's slack for a tick on the view's edge (Axis._update_ticks).
_EDGE_RTOL = 1e-10


# The share of a 3D view Axis._update_ticks leaves out at each end when
# ``axes3d.automargin`` is on (1/48 * 23/24, matplotlib's own constant).
_AUTOMARGIN_3D = 0.019965277777777776


def draws_axis(ax: Axes, axis: Any) -> bool:
    """Whether ``ax`` draws ``axis`` at all, as matplotlib decides.

    A 2D Axes draws an axis when it is visible, its axes are on
    (``ax.axis("off")`` turns them off) and the axis itself is visible. A
    3D Axes keeps ``axison`` off and draws its three axes while its private
    ``_axis3don`` is set (``set_axis_off`` clears it), whatever each axis'
    own visibility (``Axes3D.draw``, ``axis3d.Axis.draw``); no public getter
    exists, so it is read as is, and a test fails if matplotlib renames it.
    """
    if not ax.get_visible():
        return False
    if getattr(ax, "name", None) == "3d":
        return bool(getattr(ax, "_axis3don", True))
    return bool(getattr(ax, "axison", True)) and bool(axis.get_visible())


def drawn_tick_labels(
    ax: Axes, which: Literal["x", "y"], *, minor: bool = False
) -> list[Text]:
    """The major (or ``minor``) tick labels matplotlib draws on an axis.

    Matplotlib draws a tick only when the Axes draws the axis
    (:func:`draws_axis`: ``ax.set_visible(False)`` hides all of
    it, the idiom for an empty grid slot; ``ax.axis("off")`` turns a 2D
    Axes' axes off, ``set_axis_off`` a 3D one's), and when its location lies
    in the view interval, compared after the axis' scale transform with a
    1e-10 relative slack (a 3D view less ``_AUTOMARGIN_3D`` at each end
    under ``axes3d.automargin``), as ``Axis._update_ticks`` picks them. Each
    drawn tick draws its visible ``label1`` (left / bottom) and ``label2``
    (right / top, with ``labelright`` / ``labeltop``). Every other label
    stays on the artist tree, visible and positioned, but is never drawn: a
    colorbar tick a hair past its limit, the ticks of a title-only panel,
    the labels of a hidden axis or a hidden Axes.
    """
    axis = ax.xaxis if which == "x" else ax.yaxis
    if not draws_axis(ax, axis):
        return []
    transform = axis.get_transform()
    raw = axis.get_minorticklocs() if minor else axis.get_majorticklocs()
    locs = np.asarray(raw, dtype=float)
    if not locs.size:
        return []
    view_low, view_high = sorted(float(v) for v in axis.get_view_interval())
    if getattr(ax, "name", None) == "3d" and mpl.rcParams["axes3d.automargin"]:
        delta = view_high - view_low
        view_low, view_high = (
            view_low + delta * _AUTOMARGIN_3D,
            view_high - delta * _AUTOMARGIN_3D,
        )
    with np.errstate(all="ignore"):
        view = transform.transform(np.asarray([view_low, view_high], float))
        placed = np.ravel(transform.transform(locs))
    low, high = sorted(float(v) for v in np.ravel(view))
    slack = _EDGE_RTOL * (high - low)
    ticks = (
        axis.get_minor_ticks(len(locs))
        if minor
        else axis.get_major_ticks(len(locs))
    )
    drawn: list[Text] = []
    # One Tick per location, as matplotlib pairs them when it draws.
    for place, tick in zip(placed, ticks, strict=True):
        if not (np.isfinite(place) and low - slack <= place <= high + slack):
            continue
        drawn += [
            lab for lab in (tick.label1, tick.label2) if lab.get_visible()
        ]
    return drawn


def shared_axes(ax: Axes, which: Literal["x", "y"]) -> list[Axes]:
    """``ax`` and every Axes sharing its ``which`` axis, in figure order.

    These are the Axes made with ``sharex`` / ``sharey`` and the partners of
    ``twinx`` (shares x) and ``twiny`` (shares y): they read one scale, so
    their limits and tick formatters move together. An Axes the figure no
    longer holds sorts last.
    """
    group = ax.get_shared_x_axes() if which == "x" else ax.get_shared_y_axes()
    members: list[Axes] = list(group.get_siblings(ax))
    fig = ax.get_figure(root=True)
    order = fig.axes if fig is not None else []
    members.sort(key=lambda m: order.index(m) if m in order else len(order))
    return members


def same_position_axes(ax: Axes) -> list[Axes]:
    """Return ``ax`` and the visible Axes drawn in the same box as it.

    Those are its ``twinx`` / ``twiny`` partners: their tick labels, axis
    labels and legends sit around the same plot area as ``ax``'s own. The
    candidates are the Axes of ``ax``'s figure (or subfigure); for an inset
    that includes its ``twinx``, which matplotlib adds to the figure.
    """
    parent = ax.get_figure(root=False)
    if parent is None:
        return [ax]
    bounds = ax.get_position().bounds
    partners = [
        other
        for other in parent.axes
        if other is not ax
        and other.get_visible()
        and all(
            abs(a - b) <= 1e-9
            for a, b in zip(other.get_position().bounds, bounds, strict=True)
        )
    ]
    return [ax, *partners]
