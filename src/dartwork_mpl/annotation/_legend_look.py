"""The look of a legend ``place_legend`` built, to tell a legend its caller changed since.

``dm.simple_layout`` places ``place_legend``'s legends again at the size it
settles on. A legend the caller restyled or moved through the returned
``Legend`` (``Text.set_fontsize``, a title's text, ``set_frame_on``,
``set_loc``, ``set_bbox_to_anchor``, a frame alpha, a handle's colour,
line style, width or marker …) is the caller's from then on: rebuilding
it from the first call's keywords would undo the change. The look is read through matplotlib's public getters when the
legend is built and compared before it is placed again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.collections import Collection
from matplotlib.colors import to_rgba, to_rgba_array
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS
from ._legend_fit import anchored_box, legend_pad, points_px

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.legend import Legend
    from matplotlib.text import Text
    from matplotlib.typing import ColorType

#: A legend that sits within this many px of the spot its ``loc`` gives
#: is where the library put it.
SPOT_TOLERANCE_PX = 1.0


@dataclass(frozen=True)
class Look:
    """What the reader sees of a legend, and where the library meant it.

    ``loc`` is the matplotlib ``loc`` the legend was built with;
    ``own_anchor`` says the caller passed a ``bbox_to_anchor`` (an inside
    legend is otherwise anchored to its Axes). The other fields are read
    from the legend: its size in points, its frame, its texts' fonts and
    colours, its title's text (an entry's text is the entry check's,
    :func:`~._legend_entries._placed_as_built`), and what each entry's
    handle (``legend.legend_handles``) draws: colour, line style and
    width, marker and its size, face, edge and hatch.
    """

    loc: str
    own_anchor: bool
    size_pt: tuple[float, float]
    frame: tuple[Any, ...]
    texts: tuple[tuple[Any, ...], ...]
    title: str
    handles: tuple[tuple[Any, ...], ...]
    state: tuple[Any, ...]


def _rgba(color: ColorType) -> tuple[float, ...]:
    return tuple(round(float(v), 4) for v in to_rgba(color))


def _colours(colors: Any) -> tuple[float, ...]:
    """One colour or an RGBA array, flattened and rounded."""
    return tuple(round(float(v), 4) for v in to_rgba_array(colors).ravel())


def _numbers(values: Any) -> tuple[float, ...]:
    return tuple(
        round(float(v), 4) for v in np.asarray(values, dtype=float).ravel()
    )


def _artist(artist: Artist) -> tuple[Any, ...]:
    return (artist.get_visible(), artist.get_alpha(), artist.get_zorder())


def _handle(artist: Artist) -> tuple[Any, ...]:
    """What one handle artist draws, read by its type's public getters.

    Colours are compared as RGBA, so setting a value again is no edit.
    """
    seen = (type(artist).__name__, *_artist(artist))
    if isinstance(artist, Line2D):
        marker = artist.get_marker()
        return (
            *seen,
            _rgba(artist.get_color()),
            str(artist.get_linestyle()),
            round(float(artist.get_linewidth()), 3),
            marker if isinstance(marker, str) else repr(marker),
            round(float(artist.get_markersize()), 3),
            _rgba(artist.get_markerfacecolor()),
            _rgba(artist.get_markeredgecolor()),
            round(float(artist.get_markeredgewidth()), 3),
            str(artist.get_fillstyle()),
        )
    if isinstance(artist, Patch):
        return (
            *seen,
            _rgba(artist.get_facecolor()),
            _rgba(artist.get_edgecolor()),
            round(float(artist.get_linewidth()), 3),
            str(artist.get_linestyle()),
            artist.get_hatch(),
            _colours(artist.get_hatchcolor()),
            artist.get_fill(),
        )
    if isinstance(artist, Collection):
        sizes = getattr(artist, "get_sizes", lambda: None)()
        return (
            *seen,
            _colours(artist.get_facecolor()),
            _colours(artist.get_edgecolor()),
            _numbers(artist.get_linewidth()),
            () if sizes is None else _numbers(sizes),
            artist.get_hatch(),
        )
    return seen


def _text(text: Text) -> tuple[Any, ...]:
    return (
        *_artist(text),
        round(float(text.get_fontsize()), 3),
        str(text.get_fontweight()),
        str(text.get_fontstyle()),
        tuple(text.get_fontfamily()),
        _rgba(text.get_color()),
    )


def look(
    legend: Legend, renderer: RendererBase, loc: str, own_anchor: bool
) -> Look:
    """The look of ``legend`` now, for a legend built at ``loc``."""
    frame = legend.get_frame()
    try:
        box = legend.get_window_extent(renderer)
        pt = points_px(renderer, 1.0)
        size = (round(box.width / pt, 1), round(box.height / pt, 1))
    except BBOX_ERRORS:
        size = (float("nan"), float("nan"))
    return Look(
        loc=loc,
        own_anchor=own_anchor,
        size_pt=size,
        frame=(
            legend.get_frame_on(),
            *_artist(frame),
            _rgba(frame.get_facecolor()),
            _rgba(frame.get_edgecolor()),
            round(float(frame.get_linewidth()), 3),
        ),
        texts=tuple(
            _text(t) for t in [legend.get_title(), *legend.get_texts()]
        ),
        title=legend.get_title().get_text(),
        # The handles a caller reaches: Legend.legend_handles (get_lines,
        # get_patches), one per entry.
        handles=tuple(_handle(h) for h in legend.legend_handles if h),
        state=(*_artist(legend), legend.get_draggable()),
    )


def remember_look(
    legend: Legend, renderer: RendererBase, loc: str, kw: dict[str, Any]
) -> None:
    """Record the look of a legend the library just built at ``loc`` from ``kw``."""
    own_anchor = "bbox_to_anchor" in kw or "bbox_transform" in kw
    legend._dm_look = look(legend, renderer, loc, own_anchor)  # type: ignore[attr-defined]


def _at_its_spot(
    ax: Axes, legend: Legend, renderer: RendererBase, built: Look
) -> bool:
    """Whether ``legend`` sits where its ``loc`` puts it against its anchor.

    An inside legend the library anchored is anchored to its Axes; a
    ``set_loc`` or ``set_bbox_to_anchor`` since moves it off that spot.
    The layout re-anchors an outside legend's point itself, so there only
    the ``loc`` against that point is checked.
    """
    try:
        anchor = Bbox(legend.get_bbox_to_anchor().get_points())
        actual = legend.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    inside = anchor.width > 0 and anchor.height > 0
    if (
        inside
        and not built.own_anchor
        and _apart(anchor, axes_box) > SPOT_TOLERANCE_PX
    ):
        return False
    expected = anchored_box(
        built.loc,
        (actual.width, actual.height),
        anchor,
        legend_pad(legend, renderer),
    )
    return _apart(expected, actual) <= SPOT_TOLERANCE_PX


def _apart(a: Bbox, b: Bbox) -> float:
    """The largest distance between matching edges of ``a`` and ``b``, px."""
    return float(np.max(np.abs(np.asarray(a.extents) - np.asarray(b.extents))))


def untouched(ax: Axes, legend: Legend, renderer: RendererBase) -> bool:
    """Whether ``legend`` looks and sits as the library built it.

    A legend with no recorded look (one the library did not place) is
    taken as it is.
    """
    built = getattr(legend, "_dm_look", None)
    if not isinstance(built, Look):
        return True
    if look(legend, renderer, built.loc, built.own_anchor) != built:
        return False
    return _at_its_spot(ax, legend, renderer, built)


__all__ = ["Look", "look", "remember_look", "untouched"]
