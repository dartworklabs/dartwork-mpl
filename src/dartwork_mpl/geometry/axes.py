"""What an Axes draws around its box: titles, axis labels, tick labels; its twins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl
import numpy as np
from matplotlib.text import Text

from ..axis import AxisSide, Which, X, Y, parse_axis_side
from ..projection import (
    Curved,
    Projection,
    Rectilinear,
    ThreeD,
    parse_projection,
)
from .model import CentreTitle, LeftTitle, RightTitle, TitleLoc
from .renderer import opens_group

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Axis


def axes_titles(ax: Axes) -> dict[TitleLoc, Text]:
    """Return the title Text artists of ``ax``, each under its ``loc``.

    ``ax.title`` is only the centre title; ``set_title(..., loc="left")``
    and ``loc="right"`` write two more Text artists that ``ax.texts`` does
    not list. They are the Axes' other direct Text children
    (``ax.get_children()``), left before right. Each is kept only while its
    text matches the public ``ax.get_title(loc=...)``, so a matplotlib that
    reorders them yields fewer titles instead of wrong ones.
    """
    titles: dict[TitleLoc, Text] = {CentreTitle(): ax.title}
    own = {id(t) for t in ax.texts}
    loose = [
        child
        for child in ax.get_children()
        if isinstance(child, Text)
        and child is not ax.title
        and id(child) not in own
    ]
    if len(loose) != 2:
        return titles
    sides: tuple[LeftTitle | RightTitle, ...] = (LeftTitle(), RightTitle())
    titles.update(
        (loc, text)
        for loc, text in zip(sides, loose, strict=True)
        if text.get_text() == ax.get_title(loc=loc.loc)
    )
    return titles


def axis_of(ax: Axes, axis: Which) -> Axis:
    """``ax.xaxis`` or ``ax.yaxis``."""
    match axis:
        case X():
            return ax.xaxis
        case Y():
            return ax.yaxis


def projection(ax: Axes) -> Projection:
    """How ``ax`` projects its data: plain 2D, 3D or another projection."""
    return parse_projection(ax.name)


def label_side(axis: Axis) -> AxisSide:
    """The side of its Axes ``axis`` draws its label on."""
    return parse_axis_side(str(axis.get_label_position()))


# Matplotlib's slack for a tick on the view's edge (Axis._update_ticks).
_EDGE_RTOL = 1e-10


# The share of a 3D view Axis._update_ticks leaves out at each end when
# ``axes3d.automargin`` is on (1/48 * 23/24, matplotlib's own constant).
_AUTOMARGIN_3D = 0.019965277777777776


def draws_axis(ax: Axes, axis: Axis) -> bool:
    """Whether ``ax`` draws ``axis`` at all, as matplotlib decides.

    A 2D Axes draws an axis when it is visible, its axes are on
    (``ax.axis("off")`` turns them off) and the axis itself is visible. A
    3D Axes keeps ``axison`` off and draws its three axes until
    ``set_axis_off``, whatever each axis' own visibility (``Axes3D.draw``,
    ``axis3d.Axis.draw``). No public getter says which, so the Axes is drawn
    into a renderer that paints nothing and is asked whether it opened an
    ``"axis3d"`` group.
    """
    if not ax.get_visible():
        return False
    match projection(ax):
        case ThreeD():
            return opens_group(ax, ax.figure, "axis3d")
        case Rectilinear() | Curved():
            return ax.axison and axis.get_visible()


def drawn_tick_labels(
    ax: Axes, which: Which, *, minor: bool = False
) -> list[Text]:
    """The major (or ``minor``) tick labels matplotlib draws on an axis.

    Matplotlib draws a tick only when the Axes draws the axis
    (:func:`draws_axis`: ``ax.set_visible(False)`` hides all of
    it, the idiom for an empty grid slot; ``ax.axis("off")`` turns a 2D
    Axes' axes off, ``set_axis_off`` a 3D one's), and when its location lies
    in the view (:func:`in_view_tick_labels`; a 3D view less
    ``_AUTOMARGIN_3D`` at each end under ``axes3d.automargin``). Every other
    label stays on the artist tree, visible and positioned, but is never
    drawn: a colorbar tick a hair past its limit, the ticks of a title-only
    panel, the labels of a hidden axis or a hidden Axes.
    """
    axis = axis_of(ax, which)
    if not draws_axis(ax, axis):
        return []
    match projection(ax):
        case ThreeD() if mpl.rcParams["axes3d.automargin"]:
            trim = _AUTOMARGIN_3D
        case ThreeD() | Rectilinear() | Curved():
            trim = 0.0
    return in_view_tick_labels(axis, minor=minor, trim=trim)


def in_view_tick_labels(
    axis: Axis, *, minor: bool = False, trim: float = 0.0
) -> list[Text]:
    """The visible labels of the major (or ``minor``) ticks in ``axis``' view.

    ``Axis._update_ticks`` draws a tick when its location lies in the view
    interval (less ``trim``, a share of the view, at each end), compared
    after the axis' scale transform with a 1e-10 relative slack. Each drawn
    tick draws its visible ``label1`` (left / bottom) and ``label2`` (right
    / top, with ``labelright`` / ``labeltop``). Whether the axis is drawn at
    all is the caller's question (:func:`draws_axis` for an Axes).
    """
    transform = axis.get_transform()
    raw = axis.get_minorticklocs() if minor else axis.get_majorticklocs()
    locs = np.asarray(raw, dtype=float)
    if not locs.size:
        return []
    view_low, view_high = sorted(float(v) for v in axis.get_view_interval())
    if trim:
        delta = view_high - view_low
        view_low, view_high = view_low + delta * trim, view_high - delta * trim
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


def shared_axes(ax: Axes, which: Which) -> list[Axes]:
    """``ax`` and every Axes sharing its ``which`` axis, in figure order.

    These are the Axes made with ``sharex`` / ``sharey`` and the partners of
    ``twinx`` (shares x) and ``twiny`` (shares y): they read one scale, so
    their limits and tick formatters move together. An Axes the figure no
    longer holds sorts last.
    """
    match which:
        case X():
            group = ax.get_shared_x_axes()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        case Y():
            group = ax.get_shared_y_axes()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
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
