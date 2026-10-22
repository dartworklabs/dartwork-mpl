"""Layout utilities for Matplotlib figures.

Provides ``simple_layout`` — a deterministic, content-aware GridSpec
layout. It measures the union extent of every visible artist on each
axes (texts, title, axis labels, view-limited tick labels, axis
offset text, legend) and arithmetically computes GridSpec edges that
place that union extent at the requested distance from each figure
edge. No optimizer is involved.
"""

from __future__ import annotations

__all__ = [
    "adopt_axis_label_font",
    "get_bounding_box",
    "simple_layout",
    "tight_crop",
]

import contextlib
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from matplotlib.figure import Figure
from matplotlib.gridspec import (
    GridSpec,
    GridSpecBase,
    GridSpecFromSubplotSpec,
    SubplotSpec,
)
from matplotlib.transforms import Bbox

# ``BBOX_ERRORS`` is shared with the validation checks via ``_figure_geometry``
# — one source for the bbox-measurement exception set (the two modules
# used to carry identical private copies).
from .._figure_geometry import BBOX_ERRORS as _BBOX_ERRORS
from .._figure_geometry import (
    axes_text_artists,
    get_renderer,
    iter_figure_level_extents,
)
from ..units import Length

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


# Tolerance for the per-iteration GridSpec edge change (display px). A
# scenario is considered converged when every edge moved by less than
# this between consecutive iterations.
_CONVERGE_TOL_PX: float = 0.5

# Maximum direct-calc iterations. Most figures converge in 2; the
# corner cases (AutoLocator fixed-points on log scales, subfigures)
# need up to ~8.
_MAX_ITER: int = 10

# Minimum slack between opposing GridSpec edges, in figure-fraction.
# Keeps left < right and bottom < top so the GridSpec rectangle stays
# valid even when the requested margins consume the whole figure.
_EDGE_EPSILON: float = 1e-3


def get_bounding_box(boxes: list[Bbox]) -> tuple[float, float, float, float]:
    """Compute the minimum bounding box that encloses all given box regions.

    Parameters
    ----------
    boxes : list
        List of box objects, each having at minimum p0 (bottom-left
        coordinate), width, and height attributes.

    Returns
    -------
    tuple[float, float, float, float]
        Overall bounding box as ``(min_x, min_y, bbox_width, bbox_height)``.

    Raises
    ------
    ValueError
        If ``boxes`` is empty — returning the infinite sentinel tuple
        would silently poison downstream position math with inf/NaN.
    """
    if not boxes:
        raise ValueError("get_bounding_box() requires at least one box")

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for box in boxes:
        min_x = min(min_x, box.p0[0])
        min_y = min(min_y, box.p0[1])
        max_x = max(max_x, box.p0[0] + box.width)
        max_y = max(max_y, box.p0[1] + box.height)

    return (min_x, min_y, max_x - min_x, max_y - min_y)


# ─────────────────────────────────────────────────────────────────────
# margin parsing
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _PercentMargin:
    """A margin written as ``"<n>%"``: ``percent`` hundredths of the figure extent."""

    percent: float


@dataclass(frozen=True)
class _PhysicalMargin:
    """A margin given as a physical :class:`Length` (or a unit string)."""

    length: Length


@dataclass(frozen=True)
class _FractionMargin:
    """A margin given as a bare number: already a figure fraction."""

    fraction: float


_Margin: TypeAlias = _PercentMargin | _PhysicalMargin | _FractionMargin


def _parse_margin(value: Length | str | float | int) -> _Margin:
    """Parse one public margin spec into its :data:`_Margin` variant.

    Accepts a :class:`Length`; a ``"5%"`` percentage string; a unit string
    :class:`Length` parses (``"5mm"``, ``"0.5cm"``, ``"0.1in"``, ``"24pt"``);
    or a non-bool ``int`` / ``float`` figure fraction (``0.05`` = 5 %).
    Raises ``ValueError`` for an unparseable string and ``TypeError`` for
    any other type.
    """
    if isinstance(value, Length):
        return _PhysicalMargin(value)
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("%"):
            return _PercentMargin(float(s[:-1]))
        return _PhysicalMargin(Length(s))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _FractionMargin(float(value))
    raise TypeError(
        f"margin must be Length, str, or number; got {type(value).__name__}"
    )


def _margin_fraction(margin: _Margin, fig_extent_inch: float) -> float:
    """Return ``margin`` as a fraction of a figure extent of ``fig_extent_inch`` inches."""
    match margin:
        case _PercentMargin(percent=percent):
            return percent / 100.0
        case _PhysicalMargin(length=length):
            return length.inch / fig_extent_inch
        case _FractionMargin(fraction=fraction):
            return fraction


@dataclass(frozen=True)
class _Sides:
    """One value per figure edge (figure fractions for margins and reservations)."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class _MarginSpec:
    """The margin of every edge, each side parsed once from ``simple_layout``'s arguments."""

    left: _Margin
    right: _Margin
    bottom: _Margin
    top: _Margin

    def fractions(self, fig_w_in: float, fig_h_in: float) -> _Sides:
        """Return the margins as figure fractions: left/right of the width, bottom/top of the height."""
        return _Sides(
            left=_margin_fraction(self.left, fig_w_in),
            right=_margin_fraction(self.right, fig_w_in),
            bottom=_margin_fraction(self.bottom, fig_h_in),
            top=_margin_fraction(self.top, fig_h_in),
        )


def _parse_margins(
    margin: Length | str | float | None,
    ml: Length | str | float | None,
    mr: Length | str | float | None,
    mt: Length | str | float | None,
    mb: Length | str | float | None,
) -> _MarginSpec:
    """Parse ``simple_layout``'s margins: each per-side value, else ``margin``.

    ``margin=None`` means no margin. Parses ``margin`` first, then ``ml``,
    ``mr``, ``mt``, ``mb``, so the first bad value in that order raises (see
    :func:`_parse_margin`).
    """
    base = _FractionMargin(0.0) if margin is None else _parse_margin(margin)

    def side(value: Length | str | float | None) -> _Margin:
        """Return the parsed per-side ``value``, or ``margin``'s when it is ``None``."""
        return base if value is None else _parse_margin(value)

    left, right, top, bottom = side(ml), side(mr), side(mt), side(mb)
    return _MarginSpec(left=left, right=right, bottom=bottom, top=top)


@dataclass(frozen=True)
class _GridEdges:
    """GridSpec ``left/right/bottom/top`` in figure fraction."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class _LayoutStep:
    """One solver iteration: the new edges and the largest edge move in pixels."""

    edges: _GridEdges
    delta_px: float


def _solve_edges(
    overhang: _Sides,
    reserved: _Sides,
    margins: _Sides,
    last_edges: _GridEdges | None,
    fw_px: float,
    fh_px: float,
) -> _LayoutStep:
    """Compute GridSpec edges that put the axes content ``margins`` from each figure edge.

    Pure arithmetic, no measurement. ``overhang`` is how far the measured
    content sticks out of the axes boxes on each side and ``reserved`` the
    room figure-level artists claim, both in figure fraction. Edges are
    clamped into ``[0, 1]`` keeping ``_EDGE_EPSILON`` between opposite edges.
    ``delta_px`` is the largest edge move from ``last_edges`` in display
    pixels, or ``inf`` when there is no previous step.
    """
    new_l = reserved.left + margins.left + overhang.left
    new_r = (1.0 - reserved.right) - margins.right - overhang.right
    new_b = reserved.bottom + margins.bottom + overhang.bottom
    new_t = (1.0 - reserved.top) - margins.top - overhang.top

    # Sanity clamp: keep edges in [0, 1] and ensure at least
    # ``_EDGE_EPSILON`` slack between left/right and bottom/top.
    new_l = max(0.0, min(new_l, 1.0 - _EDGE_EPSILON))
    new_r = min(1.0, max(new_r, new_l + _EDGE_EPSILON))
    new_b = max(0.0, min(new_b, 1.0 - _EDGE_EPSILON))
    new_t = min(1.0, max(new_t, new_b + _EDGE_EPSILON))

    if last_edges is not None:
        delta_px = max(
            abs(new_l - last_edges.left) * fw_px,
            abs(new_r - last_edges.right) * fw_px,
            abs(new_b - last_edges.bottom) * fh_px,
            abs(new_t - last_edges.top) * fh_px,
        )
    else:
        delta_px = float("inf")

    return _LayoutStep(_GridEdges(new_l, new_r, new_b, new_t), delta_px)


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
    result is never smaller than the plot area. This is *almost* the
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

    # Texts, centre/left/right titles, axis labels.
    for txt in axes_text_artists(ax):
        if txt is None or not txt.get_visible() or not txt.get_text().strip():
            continue
        try:
            ext = txt.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        x0, x1 = _fixable_text_span(txt, ext, apos, fig.bbox.width)
        pts.append((x0, ext.y0))
        pts.append((x1, ext.y1))

    # Tick labels — only those whose tick position falls inside the
    # current view interval. Auto-generated ticks outside the data
    # range (e.g. ``10^16`` on a log axis with data up to ``10^9``)
    # are ignored, mirroring the layout tests' ``measure_overflow``.
    for axis in (ax.xaxis, ax.yaxis):
        # ``get_view_interval`` returns the pair *reversed* on an inverted
        # axis (e.g. ``[1.05, -0.05]`` after ``invert_yaxis()``); sort so
        # the in-view test below doesn't drop every tick on such axes.
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        for tick in axis.get_ticklabels():
            if not tick.get_visible() or not tick.get_text().strip():
                continue
            try:
                ext = tick.get_window_extent(renderer)
                pos = tick.get_position()
            except _BBOX_ERRORS:
                continue
            val = pos[0] if axis is ax.xaxis else pos[1]
            if val < vmin - tol or val > vmax + tol:
                continue
            if ext.width <= 0 or ext.height <= 0:
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
                if ext.width > 0 and ext.height > 0:
                    pts.append((ext.x0, ext.y0))
                    pts.append((ext.x1, ext.y1))

    # Legend.
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        with contextlib.suppress(*_BBOX_ERRORS):
            ext = legend.get_window_extent(renderer)
            if ext.width > 0 and ext.height > 0:
                pts.append((ext.x0, ext.y0))
                pts.append((ext.x1, ext.y1))

    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


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


def _resolve_gridspec(
    fig: Figure, gs: GridSpecBase | SubplotSpec | None
) -> GridSpec | None:
    """Pick the GridSpec to update. Walks past ``GridSpecFromSubplotSpec``
    to its root so ``.update`` is callable.

    The walker variable widens to ``GridSpecBase | SubplotSpec | None``
    because ``SubplotSpec.get_gridspec()`` returns the base class —
    matplotlib's stub doesn't narrow back to ``GridSpec``. We narrow
    again with an ``isinstance`` check before handing the result back,
    so callers see the precise ``GridSpec | None`` they expect.
    """
    actual: GridSpecBase | SubplotSpec | None
    if gs is not None:
        actual = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        actual = fig.axes[0].get_gridspec()
    if actual is None:
        return None
    while isinstance(actual, GridSpecFromSubplotSpec):
        actual = actual._subplot_spec.get_gridspec()  # type: ignore[attr-defined]
    if not isinstance(actual, GridSpec):
        # GridSpecBase has subclasses we don't recognise — bail rather
        # than handing back something whose ``.update`` may not exist.
        return None
    return actual


# ─────────────────────────────────────────────────────────────────────
# orphan tick-label font adoption
# ─────────────────────────────────────────────────────────────────────

# When an axis carries tick labels but no axis label, the tick labels
# become that axis's most prominent textual descriptor. Under every
# preset they are styled lighter/smaller than the axis label, so a
# self-describing axis renders its descriptor in the subordinate tick
# style. These helpers copy the axis-label font onto such "orphan" tick
# labels. Color is intentionally excluded so user-set tick colors stay.


def _copy_label_font(src: Text, dst: Text) -> None:
    """Copy fontsize/weight/family/style from ``src`` Text onto ``dst``.

    Both arguments are matplotlib :class:`~matplotlib.text.Text` artists
    (axis labels and tick labels alike). Typed as ``Text`` rather than
    ``Any`` so static analysis catches accidental calls with a
    non-Text artist.
    """
    dst.set_fontsize(src.get_fontsize())
    dst.set_fontweight(src.get_fontweight())
    dst.set_fontfamily(src.get_fontfamily())
    dst.set_fontstyle(src.get_fontstyle())


def _adopt_axis_label_font_core(fig: Figure) -> None:
    """Make unlabeled axes' tick labels adopt that axis's label font.

    For each axes and each axis direction (x, y) **independently**: if the
    axis has no axis label, copy the axis-label font (size, weight,
    family, style — *not* color) onto that axis's visible, non-empty tick
    labels (major and minor) and its offset text. Axes that *do* carry a
    label are left untouched, preserving any user tick-font customization.

    Assumes the figure has already been drawn so the tick label Text
    objects exist. The change persists across later redraws and locator
    regeneration because matplotlib copies the prototype tick's font onto
    any ticks it creates afterwards.
    """
    mutated_axes = (
        0  # debug-warning counter — see dm.config.warn_on_orphan_tick_adoption
    )
    for ax in fig.axes:
        for axis, get_label in (
            (getattr(ax, "xaxis", None), getattr(ax, "get_xlabel", None)),
            (getattr(ax, "yaxis", None), getattr(ax, "get_ylabel", None)),
        ):
            if axis is None or get_label is None:
                continue
            try:
                if get_label().strip():
                    continue  # labeled axis — leave ticks as-is
                label = axis.label
                targets: list[Any] = []
                for minor in (False, True):
                    targets.extend(
                        tick
                        for tick in axis.get_ticklabels(minor=minor)
                        if tick.get_visible() and tick.get_text().strip()
                    )
                offset = axis.get_offset_text()
                if offset.get_visible() and offset.get_text().strip():
                    targets.append(offset)
                for tick in targets:
                    _copy_label_font(label, tick)
                if targets:
                    mutated_axes += 1
            except (AttributeError, ValueError):
                # Non-standard axes (polar/3D) — skip defensively.
                continue

    if mutated_axes:
        from ..config import config

        if config.warn_on_orphan_tick_adoption:
            warnings.warn(
                f"Orphan tick-label font adoption applied to {mutated_axes} "
                f"axis(es) on this figure. Disable with "
                f"`adopt_orphan_tick_font=False` on the calling function "
                f"(simple_layout / save_formats / save_and_show) or set "
                f"`dm.config.adopt_orphan_tick_font = False` globally. "
                f"Silence this warning with "
                f"`dm.config.warn_on_orphan_tick_adoption = False`.",
                UserWarning,
                stacklevel=3,
            )


def adopt_axis_label_font(fig: Figure) -> None:
    """Draw ``fig`` then apply :func:`_adopt_axis_label_font_core`.

    Use this when you are not calling :func:`simple_layout` with
    ``adopt_orphan_tick_font=True`` but still want unlabeled axes' tick
    labels to take the axis-label font. A no-op on figures without axes.

    Note that the adoption reflects the figure state at call time: if you
    later add an axis label to a previously unlabeled axis, the ticks that
    already adopted the label font keep it. In the normal flow axis labels
    are set before layout, so this does not arise.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")
    >>> fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    >>> ax.bar(["A", "B", "C"], [3, 5, 4])
    >>> ax.set_ylabel("Count")         # x has no label
    >>> dm.adopt_axis_label_font(fig)  # x tick labels now use the label font
    """
    if not fig.axes:
        return
    fig.canvas.draw()
    _adopt_axis_label_font_core(fig)


# ─────────────────────────────────────────────────────────────────────
# main entry point
# ─────────────────────────────────────────────────────────────────────


def simple_layout(
    fig: Figure,
    gs: GridSpecBase | SubplotSpec | None = None,
    *,
    margin: Length | str | float = 0,
    ml: Length | str | float | None = None,
    mr: Length | str | float | None = None,
    mt: Length | str | float | None = None,
    mb: Length | str | float | None = None,
    use_all_axes: bool = True,
    adopt_orphan_tick_font: bool | None = None,
    verbose: bool = False,
) -> None:
    """Place axes content at the requested distance from each figure edge.

    Walks every visible artist on every axes (texts, title, axis labels,
    view-limited tick labels, axis offset text, legend) to find the
    union extent, then computes GridSpec edges so that union sits at
    ``ml/mr/mt/mb`` from the figure edge. Re-measures and re-applies
    until the GridSpec change between iterations falls below 0.5 px,
    handling cases where AutoLocator adjusts tick density when the
    axes is resized (e.g. log scales, large datetime ranges).

    Parameters
    ----------
    fig : Figure
        The figure to lay out.
    gs : GridSpec | SubplotSpec | None, optional
        GridSpec or SubplotSpec to update. If ``None``, the GridSpec of
        ``fig.axes[0]`` is used.
    margin : Length | str | float, optional
        Distance from every figure edge to the axes content. Accepts
        :class:`Length` (``dm.cm(0.5)`` / ``dm.mm(5)``), a unit string
        (``"5mm"``, ``"0.5cm"``, ``"0.1in"``, ``"24pt"``), a
        percentage string (``"5%"``), or a bare number interpreted as
        figure-fraction (``0.05`` = 5 %). Default is ``0`` —
        ``simple_layout`` then snaps axes content flush against the
        figure edges, which is the same as the historical
        ``auto_layout(fig)`` minimum-margin behaviour.
    ml, mr, mt, mb : Length | str | float | None, optional
        Per-side overrides for left / right / top / bottom margins.
        Each accepts the same forms as ``margin``. ``None`` falls
        back to ``margin``.
    use_all_axes : bool, optional
        If ``True`` (default), every axes in the figure contributes
        to the measurement. If ``False``, only axes belonging to
        ``gs`` are considered.
    adopt_orphan_tick_font : bool | None, optional
        If ``True``, tick labels (and offset text) on any axis that has
        no axis label adopt that axis's label font (size, weight, family,
        style; not color), via :func:`adopt_axis_label_font`. Applied
        each iteration *before* measurement so the computed margins fit
        the restyled ticks. Default is ``None`` — the value is read from
        :data:`dartwork_mpl.config.adopt_orphan_tick_font` (itself
        defaulting to ``False``), so set ``dm.config.adopt_orphan_tick_font
        = True`` once to opt in at every call site. Pass ``True`` /
        ``False`` explicitly to override per call.
    verbose : bool, optional
        If ``True``, prints per-iteration GridSpec edges and the
        change since the previous iteration.

    Notes
    -----
    The function returns ``None``. It is a no-op on figures with no
    axes.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")
    >>> fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    >>> ax.plot([1, 2, 3], [1, 4, 9])
    >>> ax.set_xlabel("x")
    >>> ax.set_ylabel("y")
    >>> dm.simple_layout(fig)                       # margin = 0 (flush)
    >>> dm.simple_layout(fig, margin="2%")          # 2% buffer
    >>> dm.simple_layout(fig, margin=dm.mm(2))      # 2 mm buffer
    >>> dm.simple_layout(fig, ml=dm.cm(1), mr="3%")  # mixed units
    """
    if not fig.axes:
        return

    if adopt_orphan_tick_font is None:
        from ..config import config

        adopt_orphan_tick_font = config.adopt_orphan_tick_font

    actual_gs = _resolve_gridspec(fig, gs)
    if actual_gs is None:
        # Figures built with fig.add_axes([...]) (or whose first axes is a
        # manually placed axes/colorbar) have no GridSpec to update, so
        # content-aware margins can't be applied. Warn rather than
        # silently no-op — otherwise clipped labels look like a layout bug.
        warnings.warn(
            "simple_layout: no GridSpec found (figure uses fig.add_axes or "
            "manually placed axes); layout unchanged. Build axes via "
            "plt.subplots / fig.add_gridspec to use content-aware margins.",
            stacklevel=2,
        )
        return

    fw_in, fh_in = fig.get_size_inches()
    margins = _parse_margins(margin, ml, mr, mt, mb).fractions(fw_in, fh_in)

    last: _GridEdges | None = None
    # Filter target axes by the gridspec the caller actually pointed at
    # (the *immediate* one), not the root that ``_resolve_gridspec``
    # walks to for ``.update()``. ``ax.get_gridspec()`` returns the
    # immediate ``GridSpecFromSubplotSpec`` for nested axes, so matching
    # on the root id made ``use_all_axes=False`` a silent no-op for any
    # nested gs (zero axes measured → early return). Matching the
    # immediate id keeps the documented "only this gridspec's axes"
    # semantics without over-matching sibling sub-gridspecs.
    requested_gs: GridSpecBase | None
    if gs is not None:
        requested_gs = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        requested_gs = fig.axes[0].get_gridspec()
    gs_id = id(requested_gs)

    for it in range(_MAX_ITER):
        step = _solve_layout_step(
            fig,
            margins=margins,
            use_all_axes=use_all_axes,
            gs_id=gs_id,
            last_edges=last,
            adopt_orphan_tick_font=adopt_orphan_tick_font,
        )
        if step is None:
            return
        new_edges = step.edges

        if verbose:
            print(
                f"[simple_layout] iter {it + 1}: "
                f"L={new_edges.left:.3f} R={new_edges.right:.3f} "
                f"B={new_edges.bottom:.3f} T={new_edges.top:.3f}  "
                f"Δ={step.delta_px:.2f}px"
            )

        actual_gs.update(
            left=new_edges.left,
            right=new_edges.right,
            bottom=new_edges.bottom,
            top=new_edges.top,
        )
        last = new_edges

        if step.delta_px < _CONVERGE_TOL_PX:
            return


def _figure_artist_reservations(
    fig: Figure, renderer: Any, fw_px: float, fh_px: float
) -> _Sides:
    """Space (in figure fraction) each edge must reserve for fig-level artists.

    ``simple_layout`` sizes the GridSpec from per-*axes* content, so
    figure-level artists — ``fig.suptitle``, ``fig.legend``, ``fig.text``
    — are otherwise invisible to it and end up overlapping the axes once
    the gridspec is pushed flush to the edge. Each such artist is assigned
    to one figure edge (see :func:`_reservation_edge`) and that edge
    reserves the artist's extent so the axes region is pulled in to clear
    it. Returns the reservation per edge in figure fraction; all zero
    when no figure-level artists are present (so the layout math is
    unchanged in the common case).
    """
    res_l = res_r = res_b = res_t = 0.0
    for art, ext in iter_figure_level_extents(fig, renderer):
        if not art.get_in_layout():
            continue
        x0f, x1f = ext.x0 / fw_px, ext.x1 / fw_px
        y0f, y1f = ext.y0 / fh_px, ext.y1 / fh_px
        edge = _reservation_edge(fig, art, x0f, x1f, y0f, y1f)
        if edge == "left":
            res_l = max(res_l, x1f)
        elif edge == "right":
            res_r = max(res_r, 1.0 - x0f)
        elif edge == "bottom":
            res_b = max(res_b, y1f)
        else:  # top
            res_t = max(res_t, 1.0 - y0f)
    return _Sides(left=res_l, right=res_r, bottom=res_b, top=res_t)


# Figure text whose centre lies in this outer band of the canvas height
# (horizontal text) or width (vertical text) reserves that band's edge.
_EDGE_BAND = 0.15

_Edge: TypeAlias = Literal["left", "right", "bottom", "top"]


def _reservation_edge(
    fig: Figure, art: Any, x0f: float, x1f: float, y0f: float, y1f: float
) -> _Edge:
    """Pick the figure edge a figure-level artist reserves space on.

    The nearest edge by distance put a left-aligned suptitle at the
    top-left corner on the *left* edge and pushed the whole grid right.
    So roles come first: the suptitle reserves the top, the sup x/y labels
    the bottom/left, each while it sits on that half of the canvas. Other
    text in an outer ``_EDGE_BAND`` reserves along its reading direction:
    horizontal text (a subtitle, a source note) the top or bottom band,
    vertical text the left or right band. Everything else, legends
    included, keeps the nearest edge.
    """
    xc, yc = (x0f + x1f) / 2, (y0f + y1f) / 2
    roles: tuple[tuple[str, _Edge, bool], ...] = (
        ("_suptitle", "top", yc >= 0.5),
        ("_supxlabel", "bottom", yc < 0.5),
        ("_supylabel", "left", xc < 0.5),
    )
    for attr, edge, on_side in roles:
        if on_side and art is getattr(fig, attr, None):
            return edge
    get_rotation = getattr(art, "get_rotation", None)
    if get_rotation is not None:
        vertical = 45.0 <= get_rotation() % 180.0 <= 135.0
        centre = xc if vertical else yc
        if centre <= _EDGE_BAND:
            return "left" if vertical else "bottom"
        if centre >= 1.0 - _EDGE_BAND:
            return "right" if vertical else "top"
    dists: dict[_Edge, float] = {
        "left": x0f,
        "right": 1.0 - x1f,
        "bottom": y0f,
        "top": 1.0 - y1f,
    }
    return min(dists, key=lambda k: dists[k])


def _solve_layout_step(
    fig: Figure,
    *,
    margins: _Sides,
    use_all_axes: bool,
    gs_id: int,
    last_edges: _GridEdges | None,
    adopt_orphan_tick_font: bool,
) -> _LayoutStep | None:
    """Measure the figure once and solve one iteration of ``simple_layout``.

    Returns the step, or ``None`` if the figure has no measurable axes (in
    which case the caller should bail out).

    Each step:

    1. Draws the canvas so artist bboxes are populated.
    2. Optionally adopts the axis-label font on orphan-label axes
       (so the measurement reflects the post-restyle ticks).
    3. Measures the content overhang of every target axes and the room
       figure-level artists reserve.
    4. Hands those measurements to the pure :func:`_solve_edges`.

    The caller writes the returned edges into the GridSpec and decides
    whether to stop iterating based on ``delta_px``.
    """
    fig.canvas.draw()
    # Restyle orphan tick labels before measuring so the margins fit
    # the (possibly larger) adopted font. Re-applied each iteration to
    # survive locator-driven tick regeneration mid-loop.
    if adopt_orphan_tick_font:
        _adopt_axis_label_font_core(fig)
    renderer = get_renderer(fig)
    fbox = fig.bbox
    fw_px, fh_px = fbox.width, fbox.height

    target_axes: Iterable[Axes]
    if use_all_axes:
        target_axes = fig.axes
    else:
        target_axes = [
            ax
            for ax in fig.axes
            if ax.get_gridspec() is not None and id(ax.get_gridspec()) == gs_id
        ]

    oh_l: list[float] = []
    oh_r: list[float] = []
    oh_b: list[float] = []
    oh_t: list[float] = []
    for ax in target_axes:
        ext = _axes_content_extent_px(ax, renderer, fig)
        if ext is None:
            continue
        x0, x1, y0, y1 = ext
        pos = ax.get_position()
        oh_l.append(pos.x0 - x0 / fw_px)
        oh_r.append(x1 / fw_px - pos.x1)
        oh_b.append(pos.y0 - y0 / fh_px)
        oh_t.append(y1 / fh_px - pos.y1)

    if not oh_l:  # no measurable axes
        return None

    # Reserve room for figure-level artists (suptitle / fig.legend /
    # fig.text) so the gridspec doesn't push axes content on top of them.
    reserved = _figure_artist_reservations(fig, renderer, fw_px, fh_px)
    overhang = _Sides(
        left=max(oh_l), right=max(oh_r), bottom=max(oh_b), top=max(oh_t)
    )
    return _solve_edges(overhang, reserved, margins, last_edges, fw_px, fh_px)


# ─────────────────────────────────────────────────────────────────────
# tight_crop — independent helper, unchanged
# ─────────────────────────────────────────────────────────────────────


def tight_crop(
    fig: Figure, *, padding: float = 0.05, verbose: bool = False
) -> tuple[float, float]:
    """Shrink figure to its content bounding box, eliminating outer whitespace.

    Unlike ``simple_layout`` which adjusts subplot margins inside a fixed
    figure size, ``tight_crop`` measures the union bounding box of all
    artists (axes spines, tick labels, axis labels, legends, suptitle,
    figure-level text/annotations) and resizes the figure itself to fit
    that bbox plus a uniform padding.

    Parameters
    ----------
    fig : Figure
        The Matplotlib Figure to crop.
    padding : float, optional
        Uniform padding in inches around the content bbox. Default is
        ``0.05`` (~1.3 mm). Set to ``0`` for absolute tight crop.
    verbose : bool, optional
        If ``True``, prints before/after dimensions.

    Returns
    -------
    tuple[float, float]
        New figure size in inches ``(width, height)``.
    """
    if not fig.axes:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    fig.canvas.draw()
    renderer = get_renderer(fig)

    bboxes_disp: list[Bbox] = []
    for ax in fig.axes:
        try:
            bb = ax.get_tightbbox(renderer)
        except _BBOX_ERRORS:
            bb = None
        if bb is not None and bb.width > 0 and bb.height > 0:
            bboxes_disp.append(bb)
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            try:
                bb = leg.get_window_extent(renderer)
            except _BBOX_ERRORS:
                continue
            if bb.width > 0 and bb.height > 0:
                bboxes_disp.append(bb)

    # Figure-level artists (suptitle, sup-labels, fig.text, fig.legend)
    # share the guarded walk with the layout engine.
    for _art, bb in iter_figure_level_extents(fig, renderer):
        bboxes_disp.append(bb)

    if not bboxes_disp:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    union_disp = Bbox.union(bboxes_disp)
    dpi = fig.get_dpi()
    cur_w_in, cur_h_in = fig.get_size_inches()
    cur_w_px = cur_w_in * dpi
    cur_h_px = cur_h_in * dpi
    pad_target_px = padding * dpi
    new_w_in = (union_disp.width + 2 * pad_target_px) / dpi
    new_h_in = (union_disp.height + 2 * pad_target_px) / dpi

    old_content_x0 = union_disp.x0 / cur_w_px
    old_content_y0 = union_disp.y0 / cur_h_px
    old_content_x1 = union_disp.x1 / cur_w_px
    old_content_y1 = union_disp.y1 / cur_h_px

    old_positions = [
        (ax, ax.get_position(original=False).bounds) for ax in fig.axes
    ]

    fig.set_size_inches(new_w_in, new_h_in)

    new_w_px = new_w_in * dpi
    new_h_px = new_h_in * dpi
    new_content_x0 = pad_target_px / new_w_px
    new_content_y0 = pad_target_px / new_h_px
    new_content_w = union_disp.width / new_w_px
    new_content_h = union_disp.height / new_h_px

    old_content_w = old_content_x1 - old_content_x0
    old_content_h = old_content_y1 - old_content_y0
    if old_content_w <= 0 or old_content_h <= 0:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    sx = new_content_w / old_content_w
    sy = new_content_h / old_content_h
    for ax, (x, y, w, h) in old_positions:
        new_x = new_content_x0 + (x - old_content_x0) * sx
        new_y = new_content_y0 + (y - old_content_y0) * sy
        new_w = w * sx
        new_h = h * sy
        ax.set_position((new_x, new_y, new_w, new_h))

    if verbose:
        pad_left_px = union_disp.x0
        pad_right_px = cur_w_px - union_disp.x1
        pad_bottom_px = union_disp.y0
        pad_top_px = cur_h_px - union_disp.y1
        print(
            f"[tight_crop] {cur_w_in:.2f}x{cur_h_in:.2f}in "
            f"→ {new_w_in:.2f}x{new_h_in:.2f}in  "
            f"(L:{pad_left_px / dpi:.2f} R:{pad_right_px / dpi:.2f} "
            f"B:{pad_bottom_px / dpi:.2f} T:{pad_top_px / dpi:.2f}in trimmed)"
        )

    return (new_w_in, new_h_in)
