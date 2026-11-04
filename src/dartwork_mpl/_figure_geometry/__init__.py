"""Figure measurement mechanism shared by layout, annotation and validation.

Platform code (ADR 0005): it knows matplotlib's renderer and artist extents
and nothing about any capability, and it imports no slice. Not part of the
public API. Besides measuring, it anchors an artist outside one side of an
Axes past that side's labels (:func:`anchor_outside`), so the annotation
slice that places such an artist and the layout that re-anchors it after
the Axes changed share one rule without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from matplotlib.text import Text
from matplotlib.transforms import ScaledTranslation

__all__ = [
    "BBOX_ERRORS",
    "OutsideSide",
    "anchor_outside",
    "axes_decoration_extents",
    "axes_text_artists",
    "axes_titles",
    "get_renderer",
    "iter_figure_level_extents",
    "outside_clearance_px",
    "reanchor_outside",
    "same_position_axes",
]

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.transforms import Bbox

OutsideSide: TypeAlias = Literal["above", "below", "right", "left"]
"""A side of an Axes that an artist can be anchored outside of."""

#: Exceptions matplotlib may raise from ``get_window_extent`` /
#: ``get_tightbbox`` on artists in degenerate states (NaN-only data,
#: zero-area fonts, renderers that refuse the call). Single source for
#: both the layout engine and the validation checks — the two used to
#: carry identical private copies.
BBOX_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    AttributeError,
)


def get_renderer(fig: Figure | SubFigure) -> RendererBase:
    """Return ``fig.canvas.get_renderer()`` with the type-ignore centralised.

    Matplotlib's ``FigureCanvasBase`` does not declare ``get_renderer`` —
    only the backend subclasses (``FigureCanvasAgg`` etc.) do. mypy
    flags every call site with ``attr-defined``. Routing through this
    helper keeps the suppression in one place.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
        Figure (or SubFigure) whose canvas exposes a renderer (true
        for every backend dartwork-mpl supports). SubFigure delegates
        its canvas to the parent Figure, so the same call works.

    Returns
    -------
    matplotlib.backend_bases.RendererBase
        The renderer used by ``fig``'s canvas.
    """
    return fig.canvas.get_renderer()  # type: ignore[attr-defined,no-any-return]


def iter_figure_level_extents(
    fig: Figure, renderer: RendererBase, *, legends: bool = True
) -> Iterator[tuple[Any, Bbox]]:
    """Yield ``(artist, window_extent)`` for each figure-level artist.

    Figure-level artists — ``fig.suptitle`` / ``fig.supxlabel`` /
    ``fig.supylabel`` (the private ``_sup*`` attributes), ``fig.text``
    entries, and ``fig.legend`` legends — live on the Figure, not on any
    Axes, so per-axes extent walks never see them. Three sites previously
    re-derived this candidate list plus the identical guard triplet:
    ``layout._figure_artist_reservations``, ``layout.tight_crop``, and the
    ``OVERFLOW`` visual check. This is their single source.

    matplotlib stores the sup-title / sup-labels in ``fig.texts`` *as well
    as* the ``_sup*`` attributes, so candidates are de-duplicated by
    identity — a bbox counted twice is harmless for the callers'
    ``min`` / ``max`` / ``Bbox.union`` math, but yielding each artist once
    keeps the contract clear.

    The guard, applied to every candidate:

    * skip invisible artists;
    * skip text artists whose text is empty or whitespace-only — a blank
      suptitle / footnote reserves no space and must not extend a
      bounding box (this unifies a prior inconsistency: reservations and
      OVERFLOW already skipped blank text, ``tight_crop`` did not);
    * swallow :data:`BBOX_ERRORS` from ``get_window_extent``;
    * drop zero-area extents — uninformative, and they poison the
      downstream ``min`` / ``max`` / ``Bbox.union`` math.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure whose figure-level artists to walk.
    renderer : matplotlib.backend_bases.RendererBase
        Renderer used to measure extents (from :func:`get_renderer`).
    legends : bool, optional
        Include ``fig.legends``. The OVERFLOW check passes ``False`` —
        figure legends are the LEGEND_OVERFLOW check's responsibility.
        Default ``True``.

    Yields
    ------
    tuple[matplotlib.artist.Artist, matplotlib.transforms.Bbox]
        Each qualifying artist and its display-space window extent.
    """
    seen: set[int] = set()
    candidates: list[Any] = []
    for art in (
        getattr(fig, "_suptitle", None),
        getattr(fig, "_supxlabel", None),
        getattr(fig, "_supylabel", None),
        *fig.texts,
        *(fig.legends if legends else ()),
    ):
        if art is None or id(art) in seen:
            continue
        seen.add(id(art))
        candidates.append(art)

    for art in candidates:
        if not art.get_visible():
            continue
        # Only text artists carry ``get_text``; legends don't, so they are
        # never dropped for "empty text".
        get_text = getattr(art, "get_text", None)
        if get_text is not None and not get_text().strip():
            continue
        try:
            ext = art.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        yield art, ext


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


def axes_text_artists(ax: Axes) -> list[Text]:
    """Return ``ax.texts``, the three titles and the x/y axis labels."""
    titles = axes_titles(ax).values()
    return [*ax.texts, *titles, ax.xaxis.label, ax.yaxis.label]


def same_position_axes(ax: Axes) -> list[Axes]:
    """Return ``ax`` and the visible Axes drawn in the same box as it.

    Those are its ``twinx`` / ``twiny`` partners: their tick labels, axis
    labels and legends sit around the same plot area as ``ax``'s own.
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


def axes_decoration_extents(ax: Axes, renderer: RendererBase) -> list[Bbox]:
    """Return the window extents of ``ax``'s axis decorations.

    These are the in-view tick labels (major and minor), the x and y axis
    labels and the axis offset texts (``1e6``) of visible axes; titles,
    ``ax.texts`` and legends are not included. Out-of-view ticks stay on
    matplotlib's artist tree without being drawn, so they are skipped like
    in the layout engine. Blank, invisible, unmeasurable and zero-area
    artists are skipped.
    """
    texts: list[Text] = []
    for axis, index in ((ax.xaxis, 0), (ax.yaxis, 1)):
        if not axis.get_visible():
            continue
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        for tick in axis.get_ticklabels(which="both"):
            value = tick.get_position()[index]
            if vmin - tol <= value <= vmax + tol:
                texts.append(tick)
        texts.extend((axis.label, axis.get_offset_text()))
    extents: list[Bbox] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0:
            extents.append(ext)
    return extents


def outside_clearance_px(
    ax: Axes, side: OutsideSide, renderer: RendererBase
) -> float:
    """Return how far past ``side`` of ``ax`` its decorations reach, in pixels.

    The decorations are those of :func:`axes_decoration_extents` for ``ax``
    and its :func:`same_position_axes` partners, so a ``twinx`` partner's
    right tick labels and label count for the right side. A decoration
    belongs to a side when its centre lies beyond that spine: the x tick
    labels and the x label below the axes, the y tick labels and the y
    label left of it. The result is ``0.0`` when nothing lies beyond.
    """
    try:
        box = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return 0.0
    reach = 0.0
    for owner in same_position_axes(ax):
        for ext in axes_decoration_extents(owner, renderer):
            cx, cy = (ext.x0 + ext.x1) / 2, (ext.y0 + ext.y1) / 2
            match side:
                case "above" if cy > box.y1 + 0.5:
                    reach = max(reach, ext.y1 - box.y1)
                case "below" if cy < box.y0 - 0.5:
                    reach = max(reach, box.y0 - ext.y0)
                case "right" if cx > box.x1 + 0.5:
                    reach = max(reach, ext.x1 - box.x1)
                case "left" if cx < box.x0 - 0.5:
                    reach = max(reach, box.x0 - ext.x0)
    return float(reach)


# Each side's anchor point on the Axes (axes fraction) and the unit
# direction in which the anchor moves to clear that side's decorations.
_OUTSIDE_ANCHORS: dict[
    OutsideSide, tuple[tuple[float, float], tuple[float, float]]
] = {
    "above": ((0.5, 1.0), (0.0, 1.0)),
    "below": ((0.5, 0.0), (0.0, -1.0)),
    "right": ((1.0, 0.5), (1.0, 0.0)),
    "left": ((0.0, 0.5), (-1.0, 0.0)),
}

# Name of the attribute that records an outside anchoring on its artist.
_OUTSIDE_ATTR = "_dm_outside_anchor"


@dataclass(frozen=True)
class _OutsideAnchor:
    """An artist anchored outside ``side`` of an Axes, ``clearance_pt`` past it."""

    side: OutsideSide
    clearance_pt: float


def anchor_outside(
    artist: Any, ax: Axes, side: OutsideSide, renderer: RendererBase
) -> bool:
    """Anchor ``artist`` at the middle of ``side`` of ``ax``, past its decorations.

    ``artist`` is anything with ``set_bbox_to_anchor`` (a ``Legend``, an
    ``AnchoredOffsetbox``); its ``loc`` decides which of its own edges
    touches the anchor. The anchor is the middle of that side in axes
    fraction, moved outward by :func:`outside_clearance_px` as a physical
    offset, so the artist keeps its distance when the Axes is resized. The
    side is recorded on the artist for :func:`reanchor_outside`. Returns
    whether the anchor moved by more than 0.01 pt.
    """
    root = ax.get_figure(root=True)
    if root is None:
        return False
    clearance_pt = outside_clearance_px(ax, side, renderer) * 72.0 / root.dpi
    previous = getattr(artist, _OUTSIDE_ATTR, None)
    if (
        isinstance(previous, _OutsideAnchor)
        and previous.side == side
        and abs(previous.clearance_pt - clearance_pt) <= 0.01
    ):
        return False
    (anchor_x, anchor_y), (dx, dy) = _OUTSIDE_ANCHORS[side]
    shift_in = clearance_pt / 72.0
    offset = ScaledTranslation(
        dx * shift_in, dy * shift_in, root.dpi_scale_trans
    )
    artist.set_bbox_to_anchor((anchor_x, anchor_y), ax.transAxes + offset)
    setattr(artist, _OUTSIDE_ATTR, _OutsideAnchor(side, clearance_pt))
    return True


def reanchor_outside(artist: Any, ax: Axes, renderer: RendererBase) -> bool:
    """Re-anchor an artist :func:`anchor_outside` placed, after ``ax`` changed.

    Tick labels and axis labels added, removed or re-measured since the
    first anchoring move the anchor with them. Returns ``False`` without
    touching the artist when it was not anchored by :func:`anchor_outside`.
    """
    previous = getattr(artist, _OUTSIDE_ATTR, None)
    if not isinstance(previous, _OutsideAnchor):
        return False
    return anchor_outside(artist, ax, previous.side, renderer)
