"""Content extent of one Axes in display pixels, 2-D and 3-D (the measurement ``simple_layout`` fits to)."""

from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING, Any

from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

# ``BBOX_ERRORS`` is shared with the validation checks via ``_figure_geometry``
# — one source for the bbox-measurement exception set (the two modules
# used to carry identical private copies).
from .._figure_geometry import BBOX_ERRORS as _BBOX_ERRORS
from .._figure_geometry import (
    axes_text_artists,
    axes_titles,
    outside_side,
    secondary_axes,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


# ─────────────────────────────────────────────────────────────────────
# per-axes content extent measurement
# ─────────────────────────────────────────────────────────────────────


def _axes_content_extent_px(
    ax: Axes, renderer: RendererBase, fig: Figure
) -> tuple[float, float, float, float] | None:
    """Return ``(x0, x1, y0, y1)`` in display pixels enclosing every
    visible artist of ``ax``.

    Walks texts, title, axis labels, view-limited tick labels, axis
    offset text, and legend, plus the axes' own window extent so the
    result is never smaller than the plot area. The tick labels, offset
    text and axis label of its ``secondary_xaxis`` / ``secondary_yaxis``
    children count as its own (:func:`secondary_axes`). This is *almost* the
    artist set the layout tests' ``measure_overflow`` oracle walks, with three deliberate
    deltas: the offset text and the axes window extent are only
    measured here, and the ``_LEGEND_FRAME_PAD`` slack is only added
    there — so do not treat that oracle as an exact
    post-``simple_layout`` invariant.

    Returns ``None`` for invisible axes (a hidden panel must not
    constrain the layout — matplotlib keeps a valid window extent for
    it, which used to push the visible axes' margins) and for axes
    with no measurable extent.
    """
    # Hidden axes must not contribute margins; mirrors the visibility
    # rule in ``validate_fixes.check_agent_requirements``.
    if not ax.get_visible():
        return None
    if getattr(ax, "name", None) == "3d":
        return _axes3d_extent_px(ax, renderer, fig.bbox.width)

    pts: list[tuple[float, float]] = []

    # Plot area corners — guarantees the result is at least the axes
    # box, so an axes with all artists invisible still gets a valid
    # extent.
    try:
        apos = ax.get_window_extent(renderer)
    except _BBOX_ERRORS:
        apos = None
    if apos is not None and apos.width > 0 and apos.height > 0:
        pts.append((apos.x0, apos.y0))
        pts.append((apos.x1, apos.y1))

    # ``secondary_xaxis`` / ``secondary_yaxis`` children: their tick
    # labels, offset text and axis label sit around this axes' box like
    # its own, but matplotlib keeps them out of ``fig.axes``.
    owners = [ax, *secondary_axes(ax)]

    # Texts, centre/left/right titles, axis labels.
    for txt in (t for owner in owners for t in axes_text_artists(owner)):
        if txt is None or not txt.get_visible() or not txt.get_text().strip():
            continue
        try:
            ext = txt.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if not _measurable(ext):
            continue
        x0, x1 = _fixable_text_span(txt, ext, apos, fig.bbox.width)
        pts.append((x0, ext.y0))
        pts.append((x1, ext.y1))

    # Tick labels — only those whose tick position falls inside the
    # current view interval. Auto-generated ticks outside the data
    # range (e.g. ``10^16`` on a log axis with data up to ``10^9``)
    # are ignored, mirroring the layout tests' ``measure_overflow``.
    # A tick label also counts only when its extent is finite and its tick
    # sits across its own axis' box (as the OVERFLOW check asks): a reciprocal
    # secondary axis puts a tick at infinity (a NaN width) and others in
    # view but far off the canvas, which would squeeze the Axes to nothing.
    for owner, axis in ((o, a) for o in owners for a in (o.xaxis, o.yaxis)):
        # ``get_view_interval`` returns the pair *reversed* on an inverted
        # axis (e.g. ``[1.05, -0.05]`` after ``invert_yaxis()``); sort so
        # the in-view test below doesn't drop every tick on such axes.
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        along_x = axis is owner.xaxis
        try:
            box = owner.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        for tick in axis.get_ticklabels():
            if not tick.get_visible() or not tick.get_text().strip():
                continue
            try:
                ext = tick.get_window_extent(renderer)
                pos = tick.get_position()
            except _BBOX_ERRORS:
                continue
            val = pos[0] if along_x else pos[1]
            if val < vmin - tol or val > vmax + tol:
                continue
            if not _measurable(ext) or not _across(owner, val, box, along_x):
                continue
            pts.append((ext.x0, ext.y0))
            pts.append((ext.x1, ext.y1))

        # ScalarFormatter's "1e9" exponent. Lives on the axis itself,
        # not the tick list, and is invisible to ``ax.get_tightbbox``
        # in some matplotlib versions.
        ot = axis.get_offset_text()
        if ot.get_visible() and ot.get_text().strip():
            with contextlib.suppress(*_BBOX_ERRORS):
                ext = ot.get_window_extent(renderer)
                if _measurable(ext):
                    pts.append((ext.x0, ext.y0))
                    pts.append((ext.x1, ext.y1))

    # Legend. One anchored outside a side (``place_legend``) is moved back
    # onto the canvas along that side by its anchor, so its reach along the
    # side past the plot asks no margin: counted, it would widen the margin
    # of the figure's far edge for a legend that reaches into the gap
    # between panels, narrow every panel, and move the span the legend was
    # planned for. What lies off the canvas still counts.
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        with contextlib.suppress(*_BBOX_ERRORS):
            ext = legend.get_window_extent(renderer)
            if ext.width > 0 and ext.height > 0:
                if apos is not None:
                    ext = _within_canvas_along(ext, apos, legend, fig)
                pts.append((ext.x0, ext.y0))
                pts.append((ext.x1, ext.y1))

    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def _within_canvas_along(
    ext: Bbox, plot: Bbox, legend: Any, fig: Figure
) -> Bbox:
    """``ext`` of a legend outside a side, its reach along that side cut to the plot.

    Along the side, only what lies off the canvas is kept; a legend not
    anchored outside (inside, or placed by hand) is returned as it is.
    """
    side = outside_side(legend)
    if side is None:
        return ext
    canvas = fig.bbox
    x0, y0, x1, y1 = ext.x0, ext.y0, ext.x1, ext.y1
    if side in ("above", "below"):
        x0 = x0 if x0 < canvas.x0 else max(x0, plot.x0)
        x1 = x1 if x1 > canvas.x1 else min(x1, plot.x1)
    else:
        y0 = y0 if y0 < canvas.y0 else max(y0, plot.y0)
        y1 = y1 if y1 > canvas.y1 else min(y1, plot.y1)
    return Bbox.from_extents(x0, y0, x1, y1)


def _measurable(ext: Bbox) -> bool:
    """A finite, non-empty extent (text at infinity has a NaN width)."""
    finite = all(math.isfinite(v) for v in ext.extents)
    return finite and ext.width > 0 and ext.height > 0


def _across(owner: Axes, value: float, box: Bbox, along_x: bool) -> bool:
    """Whether the tick at ``value`` sits across ``box`` (0.5 px slack).

    The tick's own place, not its label's centre, so rotated labels whose
    text leans past the box still count.
    """
    if along_x:
        place = owner.get_xaxis_transform().transform([(value, 0.0)])[0][0]
        low, high = box.x0, box.x1
    else:
        place = owner.get_yaxis_transform().transform([(0.0, value)])[0][1]
        low, high = box.y0, box.y1
    return bool(low - 0.5 <= place <= high + 0.5)


def _fixable_text_span(
    txt: Text, ext: Bbox, apos: Bbox | None, canvas_w_px: float
) -> tuple[float, float]:
    """Return the horizontal span of ``txt`` that moving axes edges can fix.

    The solver treats an overhang as moving with the nearest axes edge.
    Text anchored at or left of the left edge (a ``loc="left"`` title, a
    subtitle at ``transAxes`` x=0) stays put when the right edge moves, so
    chasing its overhang past the right edge shrank the axes on every
    iteration, down to 0.001 of the canvas; the same holds mirrored on the
    right. Text wider than the canvas cannot fit at all. Those overhangs
    are dropped here; the visual checks still report the overflow.
    """
    x0, x1 = ext.x0, ext.x1
    if apos is None or apos.width <= 0:
        return x0, x1
    if ext.width > canvas_w_px:
        return max(x0, apos.x0), min(x1, apos.x1)
    try:
        anchor_x = txt.get_transform().transform(txt.get_unitless_position())[0]
    except _BBOX_ERRORS:
        return x0, x1
    if anchor_x <= apos.x0 + 0.5:
        x1 = min(x1, apos.x1)
    elif anchor_x >= apos.x1 - 0.5:
        x0 = max(x0, apos.x0)
    return x0, x1


def _axes3d_extent_px(
    ax: Axes, renderer: RendererBase, canvas_w_px: float
) -> tuple[float, float, float, float] | None:
    """Return the ``(x0, x1, y0, y1)`` content extent of an mplot3d axes.

    mplot3d places tick labels at projected positions and leaves stale
    ones on ticks outside the view, so the per-tick walk of
    ``_axes_content_extent_px`` reads extents thousands of px off the
    canvas and the layout shrinks the axes into a corner. Instead the
    axes window, each axis's full tight bbox (in-view tick labels and the
    axis label) and the legend are measured natively, while titles and
    2-D texts go through :func:`_fixable_text_span` as on a 2-D axes, so
    an oversized title is not chased. ``Text3D`` (``ax.text(x, y, z)``)
    returns no tight bbox, so matplotlib's layouts skip it, and so does
    this one.
    """
    try:
        window = ax.get_window_extent(renderer)
    except _BBOX_ERRORS:
        return None
    boxes: list[Bbox] = []
    if window.width > 0 and window.height > 0:
        boxes.append(window)
    zaxis = getattr(ax, "zaxis", None)
    for artist in (ax.xaxis, ax.yaxis, zaxis, ax.get_legend()):
        if artist is None or not artist.get_visible():
            continue
        with contextlib.suppress(*_BBOX_ERRORS):
            bb = artist.get_tightbbox(renderer)
            if bb is not None and bb.width > 0 and bb.height > 0:
                boxes.append(bb)
    for txt in (*axes_titles(ax).values(), *ax.texts):
        if not txt.get_visible() or not txt.get_text().strip():
            continue
        try:
            ext = txt.get_tightbbox(renderer)
        except _BBOX_ERRORS:
            continue
        if ext is None or ext.width <= 0 or ext.height <= 0:
            continue
        x0, x1 = _fixable_text_span(txt, ext, window, canvas_w_px)
        boxes.append(Bbox.from_extents(x0, ext.y0, x1, ext.y1))
    if not boxes:
        return None
    union = Bbox.union(boxes)
    return union.x0, union.x1, union.y0, union.y1
