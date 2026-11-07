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
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.text import Text
from matplotlib.transforms import ScaledTranslation

__all__ = [
    "BBOX_ERRORS",
    "OutsideSide",
    "anchor_outside",
    "axes_decoration_extents",
    "axes_text_artists",
    "axes_titles",
    "axes_with_secondaries",
    "backdrop_layers",
    "canvas_renderer",
    "drawn_tick_labels",
    "get_renderer",
    "iter_figure_level_extents",
    "outside_clearance_px",
    "outside_side",
    "reanchor_outside",
    "respread_line_end_labels",
    "same_position_axes",
    "secondary_axes",
    "shared_axes",
    "spread_line_end_labels",
    "with_insets",
]

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

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


def canvas_renderer(fig: Figure | SubFigure) -> RendererBase | None:
    """The canvas's own renderer at the Figure's current size and DPI.

    ``None`` when the canvas has no ``get_renderer`` (a plain Figure, or a
    vector canvas while matplotlib saves). Unlike :func:`get_renderer` it
    never draws, so an artist may call it while the figure is drawn.
    """
    canvas = fig.canvas
    if hasattr(canvas, "get_renderer"):
        return canvas.get_renderer()  # type: ignore[no-any-return]
    return None


class _PngCanvas(FigureCanvasAgg):
    """A temporary Agg canvas whose default output is PNG.

    ``Figure.draw_without_rendering`` draws with the renderer of the
    canvas's default file type, which an Agg canvas reads from
    ``rcParams["savefig.format"]``. A PDF, SVG or PS default would switch
    to that print canvas, which sets the Figure DPI to 72 and leaves it
    there. Fixing the default here keeps the measurement at the Figure DPI
    without writing to the process-wide rcParams.
    """

    @classmethod
    def get_default_filetype(cls) -> str:
        """Return ``"png"`` whatever ``savefig.format`` says."""
        return "png"


def get_renderer(fig: Figure | SubFigure) -> RendererBase:
    """Return a measurement renderer without replacing the caller's canvas.

    Live rendering canvases keep their native renderer, without a draw. A
    plain Figure, a vector canvas, or a Figure closed by matplotlib 3.11
    has no ``canvas.get_renderer``. Then a temporary Agg canvas at the
    Figure's current DPI draws the root Figure once without output
    (``Figure.draw_without_rendering``) so artist positions are current,
    and its renderer is returned. The caller's canvas is set back even
    when drawing fails; artist errors propagate unchanged. The temporary
    canvas prints PNG whatever ``savefig.format`` says, which avoids the
    DPI change made by the PDF/SVG/PS print renderers.

    Such a Figure is always measured with Agg, also when another canvas is
    registered for PNG (``backend_bases.register_backend("png", ...)``,
    cairo say), whose text metrics can differ by a few pixels; a live
    canvas of any backend measures with its own renderer. The temporary
    canvas does not take over the caller's saving state: called while the
    figure is saved, ``canvas.is_saving()`` reads ``False`` in the
    measuring draw, so animated artists are left out of it.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
        Figure or SubFigure to measure. Fallback drawing uses its root
        Figure so SubFigure transforms and sibling positions are current.

    Returns
    -------
    matplotlib.backend_bases.RendererBase
        Native canvas renderer, or a temporary renderer at the Figure DPI.
    """
    native = canvas_renderer(fig)
    if native is not None:
        return native
    root = fig.get_figure(root=True)
    original = root.canvas
    try:
        measuring = _PngCanvas(root)  # attaches itself as root.canvas
        root.draw_without_rendering()
        renderer: RendererBase = measuring.get_renderer()  # type: ignore[no-untyped-call]
    finally:
        root.set_canvas(original)
    return renderer


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


# Matplotlib's slack for a tick on the view's edge (Axis._update_ticks).
_EDGE_RTOL = 1e-10


def drawn_tick_labels(
    ax: Axes, which: Literal["x", "y"], *, minor: bool = False
) -> list[Text]:
    """The major (or ``minor``) tick labels matplotlib draws on an axis.

    Matplotlib draws a tick only when the axes' axis is on
    (``ax.axis("off")`` turns it off) and the axis is visible, and when its
    location lies in the view interval, compared after the axis transform
    with a 1e-10 relative slack. Each drawn tick draws its visible
    ``label1`` (left / bottom) and ``label2`` (right / top, with
    ``labelright`` / ``labeltop``). Every other label stays on the artist
    tree, visible and positioned, but is never drawn: a colorbar tick a
    hair past its limit, the ticks of a title-only panel, the labels of a
    hidden axis.
    """
    axis = ax.xaxis if which == "x" else ax.yaxis
    if not getattr(ax, "axison", True) or not axis.get_visible():
        return []
    transform = axis.get_transform()
    raw = axis.get_minorticklocs() if minor else axis.get_majorticklocs()
    locs = np.asarray(raw, dtype=float)
    if not locs.size:
        return []
    with np.errstate(all="ignore"):
        view = transform.transform(np.asarray(axis.get_view_interval(), float))
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


def axes_with_secondaries(fig: Figure | SubFigure) -> list[Axes]:
    """Return ``fig.axes``, each followed by its :func:`secondary_axes`."""
    return [owner for ax in fig.axes for owner in (ax, *secondary_axes(ax))]


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


def with_insets(axes: Sequence[Axes]) -> list[Axes]:
    """Return ``axes``, each followed by its inset Axes, nested ones too.

    ``ax.inset_axes`` keeps an inset in ``ax.child_axes``, not in
    ``fig.axes``, while a ``twinx`` of that inset lands in ``fig.axes``.
    ``secondary_xaxis`` / ``secondary_yaxis`` children are not Axes and are
    left out (see :func:`secondary_axes`).
    """
    from matplotlib.axes import Axes as _Axes

    out: list[Axes] = []
    for ax in axes:
        out.append(ax)
        out.extend(
            with_insets([c for c in ax.child_axes if isinstance(c, _Axes)])
        )
    return out


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


def backdrop_layers(
    axes: Sequence[Axes],
) -> list[tuple[float, float, float, float]]:
    """The patch colours that show behind ``axes``' data, lowest first.

    The figure's patch, then its subfigure's (when the Axes sit in one),
    then each Axes' own patch in zorder (stable on the order given); a patch
    that is not drawn adds nothing. Fold them over white with
    ``composite_layers``. The ``axes`` share one figure.
    """
    first = axes[0]
    root = first.get_figure(root=True)
    parent = first.get_figure(root=False)
    containers = (root, parent if parent is not root else None)
    layers = [
        to_rgba(container.get_facecolor())
        for container in containers
        if container is not None and container.patch.get_visible()
    ]
    layers.extend(
        to_rgba(member.get_facecolor())
        for member in sorted(axes, key=lambda m: m.get_zorder())
        if member.get_frame_on() and member.patch.get_visible()
    )
    return layers


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
            reach = max(reach, _reach_past(box, ext, side))
    return float(reach)


def _reach_past(box: Bbox, ext: Bbox, side: OutsideSide) -> float:
    """How far ``ext`` reaches past ``side`` of ``box`` (0: its centre is not beyond)."""
    cx, cy = (ext.x0 + ext.x1) / 2, (ext.y0 + ext.y1) / 2
    match side:
        case "above" if cy > box.y1 + 0.5:
            return float(ext.y1 - box.y1)
        case "below" if cy < box.y0 - 0.5:
            return float(box.y0 - ext.y0)
        case "right" if cx > box.x1 + 0.5:
            return float(ext.x1 - box.x1)
        case "left" if cx < box.x0 - 0.5:
            return float(box.x0 - ext.x0)
    return 0.0


def _obstacle_reach_px(
    artist: Any,
    ax: Axes,
    side: OutsideSide,
    renderer: RendererBase,
    obstacles: Sequence[Bbox],
) -> float:
    """How far past ``side`` of ``ax`` the obstacles in ``artist``'s way reach.

    An obstacle counts when its centre lies beyond that side (as for the
    decorations) and it overlaps ``artist`` along the side (in x above and
    below, in y right and left), so moving the artist outward clears it;
    one beside the artist leaves it where it is. In pixels, ``0.0`` when
    none counts.
    """
    if not obstacles:
        return 0.0
    try:
        box = ax.get_window_extent(renderer)
        own = artist.get_window_extent(renderer)
    except BBOX_ERRORS:
        return 0.0
    along_x = side in ("above", "below")
    reach = 0.0
    for ext in obstacles:
        low, high = (ext.x0, ext.x1) if along_x else (ext.y0, ext.y1)
        own_low, own_high = (own.x0, own.x1) if along_x else (own.y0, own.y1)
        if min(high, own_high) - max(low, own_low) > 0.5:
            reach = max(reach, _reach_past(box, ext, side))
    return reach


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
    artist: Any,
    ax: Axes,
    side: OutsideSide,
    renderer: RendererBase,
    obstacles: Sequence[Bbox] = (),
) -> bool:
    """Anchor ``artist`` at the middle of ``side`` of ``ax``, past its decorations.

    ``artist`` is anything with ``set_bbox_to_anchor`` (a ``Legend``, an
    ``AnchoredOffsetbox``); its ``loc`` decides which of its own edges
    touches the anchor. The anchor is the middle of that side in axes
    fraction, moved outward by :func:`outside_clearance_px` as a physical
    offset, so the artist keeps its distance when the Axes is resized.
    ``obstacles`` are further display boxes beyond that side the artist
    must clear where it would meet them (bar values past a limit, say): the
    anchor also moves past the ones the artist overlaps along the side. The
    side is recorded on the artist for :func:`reanchor_outside`. Returns
    whether the anchor moved by more than 0.01 pt.
    """
    root = ax.get_figure(root=True)
    if root is None:
        return False
    clearance_px = max(
        outside_clearance_px(ax, side, renderer),
        _obstacle_reach_px(artist, ax, side, renderer, obstacles),
    )
    clearance_pt = clearance_px * 72.0 / root.dpi
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


def reanchor_outside(
    artist: Any,
    ax: Axes,
    renderer: RendererBase,
    obstacles: Sequence[Bbox] = (),
) -> bool:
    """Re-anchor an artist :func:`anchor_outside` placed, after ``ax`` changed.

    Tick labels and axis labels added, removed or re-measured since the
    first anchoring move the anchor with them, and so do ``obstacles`` (as
    in :func:`anchor_outside`). Returns ``False`` without touching the
    artist when it was not anchored by :func:`anchor_outside`.
    """
    side = outside_side(artist)
    if side is None:
        return False
    return anchor_outside(artist, ax, side, renderer, obstacles)


def outside_side(artist: Any) -> OutsideSide | None:
    """The side :func:`anchor_outside` anchored ``artist`` on, or ``None``."""
    previous = getattr(artist, _OUTSIDE_ATTR, None)
    if not isinstance(previous, _OutsideAnchor):
        return None
    return previous.side


_LINE_ENDS_ATTR = "_dm_line_end_labels"


@dataclass
class _LineEnds:
    """Labels :func:`spread_line_end_labels` placed on an Axes, with their ends.

    ``placed`` is the offset this code last gave each label (``None`` before
    the first spacing); a label whose offset or coordinates changed since was
    moved by someone else and keeps its place.
    """

    labels: list[Any]
    ends: list[tuple[float, float]]
    gap_pt: float
    placed: list[tuple[float, float] | None]


def _moved_since(label: Any, placed: tuple[float, float] | None) -> bool:
    """Whether ``label`` left the offset this code last gave it."""
    if placed is None:
        return False
    if getattr(label, "anncoords", "offset points") != "offset points":
        return True
    x, y = (float(v) for v in label.xyann)
    return abs(x - placed[0]) > 0.01 or abs(y - placed[1]) > 0.01


def _spread(centres: list[float], height: float) -> list[float]:
    """Move sorted label centres apart to ``height`` spacing, as little as possible.

    Labels that would overlap are merged into a group centred on their mean;
    groups that then touch merge again (a 1-D pool-adjacent pass), so the
    result keeps the order and the average position of each crowded group.
    """
    groups: list[list[float]] = []  # [first centre, count, mean of wanted]
    for c in centres:
        groups.append([c, 1, c])
        while len(groups) > 1:
            first, n, mean = groups[-1]
            p_first, p_n, p_mean = groups[-2]
            if p_first + p_n * height <= first + 1e-9:
                break
            total = p_n + n
            merged_mean = (p_mean * p_n + mean * n) / total
            groups[-2:] = [
                [merged_mean - (total - 1) * height / 2, total, merged_mean]
            ]
    out: list[float] = []
    for first, n, _mean in groups:
        out.extend(first + k * height for k in range(int(n)))
    return out


def _apply_line_end_spread(
    ax: Axes, group: _LineEnds, renderer: RendererBase
) -> bool:
    """Offset the group's labels apart at ``ax``'s current size; whether one moved."""
    root = ax.get_figure(root=True)
    keep = [
        (k, label, end)
        for k, (label, end) in enumerate(
            zip(group.labels, group.ends, strict=True)
        )
        if label.axes is ax
        and label in ax.texts
        and not _moved_since(label, group.placed[k])
    ]
    if root is None or len(keep) < 2:
        return False
    to_pt = 72.0 / root.dpi
    # Vertical spacing in points: one text line plus a sliver.
    height = (
        max(label.get_window_extent(renderer).height for _, label, _ in keep)
        * to_pt
        * 1.1
    )
    wanted = [ax.transData.transform(end)[1] * to_pt for _, _, end in keep]
    order = sorted(range(len(keep)), key=lambda i: wanted[i])
    spread = _spread([wanted[i] for i in order], height)
    moved = False
    for i, y_pt in zip(order, spread, strict=True):
        k, label, _ = keep[i]
        offset = (group.gap_pt, y_pt - wanted[i])
        old = tuple(label.xyann)
        if abs(old[0] - offset[0]) > 0.01 or abs(old[1] - offset[1]) > 0.01:
            moved = True
        label.xyann = offset
        group.placed[k] = offset
    return moved


def spread_line_end_labels(
    ax: Axes,
    labels: list[Any],
    ends: list[tuple[float, float]],
    gap_pt: float,
    renderer: RendererBase,
) -> bool:
    """Move line-end labels apart vertically at ``ax``'s current size.

    ``labels`` are annotations ``gap_pt`` right of their line's last point
    ``ends`` (data coordinates). Labels that would overlap move apart and
    keep their order. The group is recorded on ``ax`` (next to any earlier
    group) so :func:`respread_line_end_labels` spaces them again after the
    Axes is resized (``dm.simple_layout`` shrinking it for a note, say).
    Returns whether a label moved.
    """
    group = _LineEnds(
        list(labels), list(ends), float(gap_pt), [None] * len(labels)
    )
    groups = [
        g for g in getattr(ax, _LINE_ENDS_ATTR, []) if isinstance(g, _LineEnds)
    ]
    setattr(ax, _LINE_ENDS_ATTR, [*groups, group])
    return _apply_line_end_spread(ax, group, renderer)


def respread_line_end_labels(ax: Axes, renderer: RendererBase) -> bool:
    """Space :func:`spread_line_end_labels` labels again at ``ax``'s size now.

    Every group recorded on ``ax`` is spaced on its own; a label someone moved
    since keeps its place. Returns ``False`` without touching anything when
    ``ax`` has none.
    """
    moved = False
    for group in getattr(ax, _LINE_ENDS_ATTR, []):
        if isinstance(group, _LineEnds) and _apply_line_end_spread(
            ax, group, renderer
        ):
            moved = True
    return moved
