"""Layout utilities for Matplotlib figures.

Provides ``simple_layout`` — a deterministic, content-aware GridSpec
layout. It measures the union extent of every visible artist on each
axes (texts, title, axis labels, view-limited tick labels, axis
offset text, legend) and arithmetically computes GridSpec edges that
place that union extent at the requested distance from each figure
edge. No optimizer is involved.

The historical ``auto_layout`` name is preserved as a thin wrapper
for backwards compatibility.
"""

from __future__ import annotations

__all__ = [
    "adopt_axis_label_font",
    "auto_layout",
    "get_bounding_box",
    "simple_layout",
    "tight_crop",
]

import contextlib
import warnings
from typing import TYPE_CHECKING, Any

from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec
from matplotlib.transforms import Bbox

from .units import Length

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase


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
    """
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


def _parse_margin(
    value: Length | str | float | int | None, fig_extent_inch: float
) -> float | None:
    """Convert a margin spec to a figure-fraction (0-1) along one axis.

    Accepts:

    - ``None`` → returns ``None`` (caller substitutes the default).
    - :class:`Length` → ``length.inch / fig_extent_inch``.
    - ``str`` ``"5%"`` → ``0.05``.
    - ``str`` parseable by :class:`Length` (``"5mm"``, ``"0.5cm"``,
      ``"0.1in"``, ``"24pt"``) → as Length.
    - ``int`` / ``float`` → already a fraction (``0.05`` = 5 %).

    Returns
    -------
    float | None
        Margin in figure-fraction, or ``None`` if the input was
        ``None``.
    """
    if value is None:
        return None
    if isinstance(value, Length):
        return value.inch / fig_extent_inch
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("%"):
            return float(s[:-1]) / 100.0
        return Length(s).inch / fig_extent_inch
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise TypeError(
        f"margin must be Length, str, or number; got {type(value).__name__}"
    )


# ─────────────────────────────────────────────────────────────────────
# per-axes content extent measurement
# ─────────────────────────────────────────────────────────────────────


_BBOX_ERRORS = (RuntimeError, ValueError, AttributeError)


def _axes_content_extent_px(
    ax: Axes, renderer: RendererBase, fig: Figure
) -> tuple[float, float, float, float] | None:
    """Return ``(x0, x1, y0, y1)`` in display pixels enclosing every
    visible artist of ``ax``.

    Walks the same artist set as ``_measure_overflow`` (texts, title,
    axis labels, view-limited tick labels, axis offset text, legend)
    plus the axes' own window extent so the result is never smaller
    than the plot area.

    Returns ``None`` if the axes has no measurable extent (rare —
    only for fully invisible axes).
    """
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

    # Texts, title, axis labels.
    text_artists = [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]
    for txt in text_artists:
        if txt is None or not txt.get_visible() or not txt.get_text().strip():
            continue
        try:
            ext = txt.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        pts.append((ext.x0, ext.y0))
        pts.append((ext.x1, ext.y1))

    # Tick labels — only those whose tick position falls inside the
    # current view interval. Auto-generated ticks outside the data
    # range (e.g. ``10^16`` on a log axis with data up to ``10^9``)
    # are ignored, mirroring ``_measure_overflow``.
    for axis in (ax.xaxis, ax.yaxis):
        vmin, vmax = axis.get_view_interval()
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


def _resolve_gridspec(
    fig: Figure, gs: GridSpec | SubplotSpec | None
) -> GridSpec | None:
    """Pick the GridSpec to update. Walks past ``GridSpecFromSubplotSpec``
    to its root so ``.update`` is callable.
    """
    actual: Any
    if gs is not None:
        actual = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        actual = fig.axes[0].get_gridspec()
    if actual is None:
        return None
    while isinstance(actual, GridSpecFromSubplotSpec):
        actual = actual._subplot_spec.get_gridspec()  # type: ignore[attr-defined]
    return actual  # type: ignore[no-any-return]


# ─────────────────────────────────────────────────────────────────────
# orphan tick-label font adoption
# ─────────────────────────────────────────────────────────────────────

# When an axis carries tick labels but no axis label, the tick labels
# become that axis's most prominent textual descriptor. Under every
# preset they are styled lighter/smaller than the axis label, so a
# self-describing axis renders its descriptor in the subordinate tick
# style. These helpers copy the axis-label font onto such "orphan" tick
# labels. Color is intentionally excluded so user-set tick colors stay.


def _copy_label_font(src: Any, dst: Any) -> None:
    """Copy fontsize/weight/family/style from ``src`` Text onto ``dst``."""
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
            except (AttributeError, ValueError):
                # Non-standard axes (polar/3D) — skip defensively.
                continue


def adopt_axis_label_font(fig: Figure) -> None:
    """Draw ``fig`` then apply :func:`_adopt_axis_label_font_core`.

    Use this when you are not calling :func:`simple_layout` (which already
    applies the same adoption by default via ``adopt_orphan_tick_font``)
    but still want unlabeled axes' tick labels to take the axis-label
    font. A no-op on figures without axes.

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
    gs: GridSpec | SubplotSpec | None = None,
    *,
    margin: Length | str | float = 0,
    ml: Length | str | float | None = None,
    mr: Length | str | float | None = None,
    mt: Length | str | float | None = None,
    mb: Length | str | float | None = None,
    use_all_axes: bool = True,
    adopt_orphan_tick_font: bool = True,
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
    adopt_orphan_tick_font : bool, optional
        If ``True`` (default), tick labels (and offset text) on any axis
        that has no axis label adopt that axis's label font (size,
        weight, family, style; not color), via
        :func:`adopt_axis_label_font`. Applied each iteration *before*
        measurement so the computed margins fit the restyled ticks.
        Set to ``False`` to leave tick fonts untouched.
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

    actual_gs = _resolve_gridspec(fig, gs)
    if actual_gs is None:
        return

    fw_in, fh_in = fig.get_size_inches()

    # Resolve each side: per-side override else `margin`.
    base_h = _parse_margin(margin, fw_in) or 0.0
    base_v = _parse_margin(margin, fh_in) or 0.0
    ml_f = _parse_margin(ml, fw_in)
    mr_f = _parse_margin(mr, fw_in)
    mt_f = _parse_margin(mt, fh_in)
    mb_f = _parse_margin(mb, fh_in)
    if ml_f is None:
        ml_f = base_h
    if mr_f is None:
        mr_f = base_h
    if mt_f is None:
        mt_f = base_v
    if mb_f is None:
        mb_f = base_v

    last: tuple[float, float, float, float] | None = None
    gs_id = id(actual_gs)

    for it in range(_MAX_ITER):
        fig.canvas.draw()
        # Restyle orphan tick labels before measuring so the margins fit
        # the (possibly larger) adopted font. Re-applied each iteration to
        # survive locator-driven tick regeneration mid-loop.
        if adopt_orphan_tick_font:
            _adopt_axis_label_font_core(fig)
        renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
        fbox = fig.bbox
        fw_px, fh_px = fbox.width, fbox.height

        if use_all_axes:
            target_axes: Iterable[Axes] = fig.axes
        else:
            target_axes = [
                ax
                for ax in fig.axes
                if ax.get_gridspec() is not None
                and id(ax.get_gridspec()) == gs_id
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
            return

        new_l = ml_f + max(oh_l)
        new_r = 1.0 - mr_f - max(oh_r)
        new_b = mb_f + max(oh_b)
        new_t = 1.0 - mt_f - max(oh_t)

        # Sanity clamp: keep edges in [0, 1] and ensure at least
        # ``_EDGE_EPSILON`` slack between left/right and bottom/top.
        new_l = max(0.0, min(new_l, 1.0 - _EDGE_EPSILON))
        new_r = min(1.0, max(new_r, new_l + _EDGE_EPSILON))
        new_b = max(0.0, min(new_b, 1.0 - _EDGE_EPSILON))
        new_t = min(1.0, max(new_t, new_b + _EDGE_EPSILON))

        if last is not None:
            delta_px = max(
                abs(new_l - last[0]) * fw_px,
                abs(new_r - last[1]) * fw_px,
                abs(new_b - last[2]) * fh_px,
                abs(new_t - last[3]) * fh_px,
            )
        else:
            delta_px = float("inf")

        if verbose:
            print(
                f"[simple_layout] iter {it + 1}: "
                f"L={new_l:.3f} R={new_r:.3f} B={new_b:.3f} T={new_t:.3f}  "
                f"Δ={delta_px:.2f}px"
            )

        actual_gs.update(left=new_l, right=new_r, bottom=new_b, top=new_t)
        last = (new_l, new_r, new_b, new_t)

        if delta_px < _CONVERGE_TOL_PX:
            return


def auto_layout(
    fig: Figure,
    *,
    padding: float | tuple[float, float, float, float] = 0.08,
    max_iter: int = 5,
    tolerance: float = 2.0,
    verbose: bool = False,
) -> None:
    """Deprecated alias for :func:`simple_layout`.

    The previous ``auto_layout`` ran an outer loop over ``simple_layout``
    to compensate for an optimizer cap that no longer exists. Direct-calc
    ``simple_layout`` already handles the same cases in a single call,
    so ``auto_layout`` is now a thin wrapper that translates the legacy
    ``padding`` (inches) argument into ``margin`` and forwards the call.

    Will be removed in a future release; use :func:`simple_layout`
    directly. ``max_iter`` and ``tolerance`` are accepted for
    signature compatibility but no longer have an effect — convergence
    is governed by the deterministic loop inside ``simple_layout``.
    """
    warnings.warn(
        "dm.auto_layout is deprecated and will be removed in a future "
        "release; use dm.simple_layout(fig, ...) directly. The previous "
        "outer iteration is no longer needed.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not fig.axes:
        return
    if isinstance(padding, (int, float)):
        ml = mr = Length.from_inch(float(padding)) if padding else 0
        mt = mb = Length.from_inch(float(padding)) if padding else 0
    else:
        pl, pr, pb, pt_ = padding
        ml = Length.from_inch(float(pl)) if pl else 0
        mr = Length.from_inch(float(pr)) if pr else 0
        mb = Length.from_inch(float(pb)) if pb else 0
        mt = Length.from_inch(float(pt_)) if pt_ else 0
    simple_layout(fig, ml=ml, mr=mr, mt=mt, mb=mb, verbose=verbose)


# ─────────────────────────────────────────────────────────────────────
# diagnostic helpers (kept for backwards compatibility with tests
# that import them directly).
# ─────────────────────────────────────────────────────────────────────


def _measure_overflow(fig: Figure) -> dict[str, float]:
    """Measure per-side overflow of all visible artists beyond figure bounds.

    Returns a ``{"left", "right", "bottom", "top"}`` dict in display pixels.
    Used by the robustness suite as the post-layout invariant check;
    not called by :func:`simple_layout` itself.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]

    canvas_w, canvas_h = fig.canvas.get_width_height()
    bx0, by0 = 0.0, 0.0
    bx1, by1 = float(canvas_w), float(canvas_h)

    overflow: dict[str, float] = {
        "left": 0.0,
        "right": 0.0,
        "bottom": 0.0,
        "top": 0.0,
    }

    for ax in fig.axes:
        for txt in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except _BBOX_ERRORS:
                continue
            overflow["left"] = max(overflow["left"], bx0 - ext.x0)
            overflow["right"] = max(overflow["right"], ext.x1 - bx1)
            overflow["bottom"] = max(overflow["bottom"], by0 - ext.y0)
            overflow["top"] = max(overflow["top"], ext.y1 - by1)

        for axis in (ax.xaxis, ax.yaxis):
            vmin, vmax = axis.get_view_interval()
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
                overflow["left"] = max(overflow["left"], bx0 - ext.x0)
                overflow["right"] = max(overflow["right"], ext.x1 - bx1)
                overflow["bottom"] = max(overflow["bottom"], by0 - ext.y0)
                overflow["top"] = max(overflow["top"], ext.y1 - by1)

        legend = ax.get_legend()
        if legend is not None and legend.get_visible():
            leg_ext = None
            with contextlib.suppress(*_BBOX_ERRORS):
                leg_ext = legend.get_window_extent(renderer)
            if leg_ext is not None and leg_ext.width > 0 and leg_ext.height > 0:
                _LEGEND_FRAME_PAD = 2.0
                overflow["left"] = max(
                    overflow["left"], bx0 - (leg_ext.x0 - _LEGEND_FRAME_PAD)
                )
                overflow["right"] = max(
                    overflow["right"], (leg_ext.x1 + _LEGEND_FRAME_PAD) - bx1
                )
                overflow["bottom"] = max(
                    overflow["bottom"], by0 - (leg_ext.y0 - _LEGEND_FRAME_PAD)
                )
                overflow["top"] = max(
                    overflow["top"], (leg_ext.y1 + _LEGEND_FRAME_PAD) - by1
                )

    return overflow


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
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]

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

    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_visible():
        with contextlib.suppress(*_BBOX_ERRORS):
            bboxes_disp.append(suptitle.get_window_extent(renderer))
    for txt in fig.texts:
        if not txt.get_visible():
            continue
        try:
            bb = txt.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if bb.width > 0 and bb.height > 0:
            bboxes_disp.append(bb)
    for leg in getattr(fig, "legends", []):
        if not leg.get_visible():
            continue
        try:
            bb = leg.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if bb.width > 0 and bb.height > 0:
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
