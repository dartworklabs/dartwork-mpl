"""Which panels and texts a figure draws, and where a text draws."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from ..geometry import PANEL_LABELS_ATTR, axes_titles, draws_axis, holders_shown

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure


def drawn_axes(fig: Figure) -> list[tuple[int, Axes]]:
    """Each Axes of ``fig.axes`` no hidden SubFigure hides, with its index.

    The index is into ``fig.axes`` (the ``axes_index`` the checks report),
    not into this list. Each Axes' own visibility is left to the caller, as
    it was: without SubFigures this is ``enumerate(fig.axes)``.
    """
    return [(i, ax) for i, ax in enumerate(fig.axes) if holders_shown(ax)]


def panel_labels(fig: Figure | SubFigure) -> list[tuple[Axes, Text]]:
    """The letters ``dm.label_axes`` placed on ``fig``, each with its panel.

    Only the automatic ones (``x="auto"``), which the figure keeps in
    groups; a letter at a position the caller gave is an ordinary text.
    """
    root = fig.get_figure(root=True)
    return [
        (ax, text)
        for group in getattr(root, PANEL_LABELS_ATTR, [])
        for ax, text in group.members
    ]


def secondary_axes(ax: Axes) -> list[Axes]:
    """Return the visible ``secondary_xaxis`` / ``secondary_yaxis`` children of ``ax``.

    Matplotlib keeps them in ``ax.child_axes``, not in ``fig.axes``, so a
    walk over ``fig.axes`` never sees their tick labels, offset text or axis
    label, which sit around ``ax``'s box like its own. Inset Axes, also
    children, are not included. Matplotlib's ``SecondaryAxis`` is not an
    ``Axes`` subclass, but it has what the measurements read (its x/y axes,
    texts, window extent; no titles), so the list is typed as ``Axes``.
    """
    # matplotlib.axes does not export SecondaryAxis (3.11).
    from matplotlib.axes._secondary_axes import SecondaryAxis

    children = [
        child
        for child in ax.child_axes
        if isinstance(child, SecondaryAxis) and child.get_visible()
    ]
    return cast("list[Axes]", children)


def drawn_axes_texts(ax: Axes) -> list[Text]:
    """``ax.texts``, the three titles and the axis labels matplotlib draws.

    An axis label draws with its axis (:func:`draws_axis`): not
    on a 2D Axes after ``ax.axis("off")`` or with that axis hidden, nor on a
    3D Axes after ``set_axis_off``; there it stays where it was never drawn,
    often past the canvas. The checks read these texts; the layout still
    measures every label.
    """
    labels = [
        axis.label for axis in (ax.xaxis, ax.yaxis) if draws_axis(ax, axis)
    ]
    return [*ax.texts, *axes_titles(ax).values(), *labels]


def text_window_extent(text: Text, renderer: RendererBase) -> Bbox:
    """The window extent of ``text`` where it draws.

    A 3D axes' ``ax.text(x, y, z, ...)`` (a ``Text3D``) is placed by
    projection only while it draws; outside a draw ``get_window_extent``
    reads the unprojected ``(x, y)`` through the axes' 2D transform,
    thousands of pixels off. Its extent here is a copy of it measured at the
    point and angle ``Text3D.draw`` gives it: the position and the position
    plus the text's direction (``zdir``) through the axis scales and the
    projection ``M`` of the axes' last draw, the angle of that direction on
    screen normalised to (-90, 90]. A text that draw would hide (a position
    its scale cannot take, or outside the limits with ``axlim_clip``) has
    an empty extent, as has one on an axes not drawn yet. Every other text:
    its ``get_window_extent``.
    """
    get_position_3d = getattr(text, "get_position_3d", None)
    if get_position_3d is None or getattr(text.axes, "name", None) != "3d":
        return text.get_window_extent(renderer)
    axes: Any = text.axes  # an Axes3D: get_zlim, M
    figure = text.get_figure(root=False)
    empty = Bbox.from_bounds(0, 0, 0, 0)
    projection = getattr(axes, "M", None)
    if projection is None or figure is None:
        return empty
    from mpl_toolkits.mplot3d.proj3d import proj_transform

    position = np.asarray(get_position_3d(), dtype=float)
    # matplotlib keeps the direction and the clip flag only privately
    # (Text3D.set_3d_properties); without them: no direction (level text,
    # the ``ax.text`` default) and no clip (the default).
    direction = np.asarray(getattr(text, "_dir_vec", (0, 0, 0)), dtype=float)
    if getattr(text, "_axlim_clip", False):
        limits = (axes.get_xlim(), axes.get_ylim(), axes.get_zlim())
        if any(
            not min(lim) <= value <= max(lim)
            for value, lim in zip(position, limits, strict=True)
        ):
            return empty
    ends = np.stack([position, position + direction])
    with np.errstate(all="ignore"):
        scaled = [
            axis.get_transform().transform(ends[:, i])
            for i, axis in enumerate((axes.xaxis, axes.yaxis, axes.zaxis))
        ]
        xs, ys, _zs = proj_transform(*scaled, projection)
    if not (np.isfinite(xs[0]) and np.isfinite(ys[0])):
        return empty
    angle = float(np.degrees(np.arctan2(ys[1] - ys[0], xs[1] - xs[0])))
    angle = (angle + 180) % 180
    if angle > 90:
        angle -= 180
    probe = Text(float(xs[0]), float(ys[0]), text.get_text())
    probe.update_from(text)
    probe.set_rotation(angle)
    probe.set_rotation_mode(text.get_rotation_mode())
    probe.set_wrap(text.get_wrap())
    probe.set_parse_math(text.get_parse_math())
    probe.set_transform(text.get_transform())
    probe.set_figure(figure)
    return probe.get_window_extent(renderer)
