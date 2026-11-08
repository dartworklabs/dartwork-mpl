"""The iterative ``simple_layout`` solve and the other slices' steps it calls before measuring."""

from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING

from matplotlib.figure import Figure
from matplotlib.gridspec import (
    GridSpec,
    GridSpecBase,
    GridSpecFromSubplotSpec,
    SubplotSpec,
)

from .._figure_geometry import get_renderer
from ..units import Length
from ._content_extent import _axes_content_extent_px
from ._margins import (
    _GridEdges,
    _LayoutStep,
    _parse_margins,
    _Sides,
    _solve_edges,
)
from ._orphan_tick_font import _adopt_axis_label_font_core
from ._reservations import _figure_artist_reservations
from ._settle import _settle_outside_legends

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
    format_ticks: bool = True,
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
    format_ticks : bool, optional
        If ``True`` (default), an axis still on matplotlib's default number
        formatter whose visible ticks reach 1,000 gets the library's tick
        numbers before measuring: thousands separators (``1,750``;
        ``34,000``), and from one million the largest tick's SI unit
        (``0.5M … 2.5M``). Smaller axes, x axes of years (every tick in
        1000-2999), log, date and category axes, colorbars and any axis
        with a formatter you set are left alone. After fitting, a date axis
        matplotlib set up whose labels sit less than one em apart gets
        fewer ticks and the margins are fitted again. ``False`` keeps
        matplotlib's numbers and dates.
    verbose : bool, optional
        If ``True``, prints per-iteration GridSpec edges and the
        change since the previous iteration.

    Raises
    ------
    ValueError
        If any effective per-side margin resolves to a nonfinite figure
        fraction, after all margins have been parsed. Four finite side
        overrides can replace a nonfinite base margin. Existing parsing
        and GridSpec resolution errors take precedence.

    Notes
    -----
    The function returns ``None``. Figures with no axes, or without a
    supported GridSpec, return before parsing margins (the latter warn).
    Nonfinite effective margins are rejected before drawing, font
    adoption or layout mutation. Finite zero, negative and oversized
    margins retain the existing edge-clamping behavior.

    Before measuring, a legend placed with ``dm.place_legend(ax,
    loc="above" | "below" | "right" | "left")`` is re-anchored past the
    tick and axis labels present now (and past the ``dm.label_bars``
    values beyond that limit it would cover), and the titles of an axes whose
    legend sits above it (``place_legend(loc="above")`` or a raw
    ``ax.legend(..., bbox_to_anchor=(x, 1.0))``) get their offset raised
    so they sit ``axes.titlepad`` above that legend; their text, size and
    weight are kept.

    An Axes drawing its own y scale on the right of a shared plot area (y
    ticks and y label on the right, or one of them when its x axis is hidden
    as a twin's is: the Axes ``ax.twinx()`` returns, of an inset too) gets
    its right spine shown, which the presets hide; an Axes drawing its own
    x scale on the top (the same with x and y swapped: the Axes
    ``ax.twiny()`` returns) gets its top spine. Line width and colour stay,
    and a spine you hide after a layout stays hidden. The rule is in the
    docstring of ``dartwork_mpl.formatting._twin_spines``.

    On a ``twinx`` / ``twiny`` pair, a side whose series all draw one
    colour that no series on the other scale shares gets that colour on its
    spine and tick marks (at least 3:1 against the background) and the same
    hue darkened to 4.5:1 on its tick labels and axis label; single axes
    and colours set after a layout are left alone. The full rules are in
    the docstring of ``dartwork_mpl.formatting._twin_colors``;
    ``dm.config.twin_colors = "neutral"`` turns it off.

    Labels made by ``dm.label_bars`` settle at the size being fitted, in
    every step: a call whose labels are wider than the distance to the next
    bar less 1.5 pt follows its ``crowded`` rule, and a value axis whose
    limits matplotlib autoscales grows from matplotlib's own limits just
    enough to keep the outside labels and 3 pt inside the axes (``auto``
    stays on, so repeated calls give the same limits). Limits you set are
    kept, a view set with ``set_ybound`` included; a label that does not
    fit sits outside the axes and the margins make room for it. The rules
    are in the docstring of
    ``dartwork_mpl.annotation._bar_label_settle``.

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
    if not all(
        math.isfinite(side)
        for side in (margins.left, margins.right, margins.bottom, margins.top)
    ):
        raise ValueError("margin must resolve to finite figure fractions")

    # Tick formats change label widths, so they go before fitting, but
    # after every check that can still refuse the call. Twin spines and
    # colours follow the tick formats (the order bar labels rely on); they
    # are not number formats, so ``format_ticks=False`` keeps them. Their
    # order between themselves does not change the figure: the colours paint
    # a spine whether it shows or not.
    if format_ticks:
        _format_ticks(fig)
    _show_twin_spines(fig)
    _color_twins(fig)

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

    for _ in range(2):
        step: _LayoutStep | None = None
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
                break  # no measurable Axes: nothing to place
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
            # GridSpec.update only repositions pyplot-managed figures.
            # A retained closed Figure still needs its own axes updated;
            # reuse their SubplotSpecs to preserve SubFigure coordinates,
            # twin relationships and in_layout flags. Open figures whose
            # positions already match are left untouched.
            for ax in fig.axes:
                spec = ax.get_subplotspec()
                if (
                    spec is not None
                    and spec.get_topmost_subplotspec().get_gridspec()
                    is actual_gs
                ):
                    # Matplotlib accepts the local SubFigure here, though
                    # its SubplotSpec stub only declares Figure.
                    position = spec.get_position(ax.get_figure(root=False))  # type: ignore[arg-type]
                    if ax.get_position(original=True).bounds != position.bounds:
                        ax.set_subplotspec(spec)
            last = new_edges

            if step.delta_px < _CONVERGE_TOL_PX:
                break
        # Date ticks depend on the axis length only through their labels:
        # thin them at the fitted width, then fit once more if they moved.
        # The bar labels were settled in each step, so they are reported
        # below even when nothing could be measured.
        if step is None or not format_ticks:
            break
        from ..formatting import thin_crowded_date_ticks

        if not thin_crowded_date_ticks(fig):
            break
    _report_hidden_bar_labels(fig)


def _report_hidden_bar_labels(fig: Figure) -> None:
    """Warn about bar labels the fitted size left no room for.

    Once, after the fit: the warning speaks of the size laid out, not of a
    step on the way (:func:`~..annotation.warn_hidden_bar_labels`).
    """
    from ..annotation import warn_hidden_bar_labels

    # warn_hidden_bar_labels <- this <- simple_layout <- the caller.
    warn_hidden_bar_labels(fig, stacklevel=3)


def _format_ticks(fig: Figure) -> None:
    """The library's tick numbers and dates on axes nobody formatted."""
    from ..formatting import apply_default_tick_format

    apply_default_tick_format(fig)


def _show_twin_spines(fig: Figure) -> None:
    """The right / top spine of each twin scale drawn there."""
    from ..formatting import show_twin_spines

    show_twin_spines(fig)


def _color_twins(fig: Figure) -> None:
    """Series colours on twin pairs, unless ``dm.config.twin_colors`` is off."""
    from ..formatting import apply_twin_colors

    apply_twin_colors(fig)


def _settle_bar_labels(fig: Figure, renderer: RendererBase) -> bool:
    """Crowding and headroom of ``dm.label_bars`` labels at the size now.

    Returns whether a view limit moved: the caller redraws before measuring,
    since tick labels follow the limits only at draw (the bar labels
    themselves are measured afresh).
    """
    from ..annotation import settle_bar_labels

    before = [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    if not settle_bar_labels(fig, renderer):
        return False
    return before != [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]


def _clear_bar_labels(fig: Figure, renderer: RendererBase) -> None:
    """Hide the bar labels a legend or other text covers, where they are now."""
    from ..annotation import clear_bar_labels

    clear_bar_labels(fig, renderer)


# Most rounds of re-anchoring and title lifting per layout step. Matplotlib
# re-places an auto-positioned title on every draw (above top tick labels,
# say), so a lift can need a second round after the redraw; a third round
# would only confirm that nothing moves.
_SETTLE_ROUNDS: int = 3


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
    3. Settles ``dm.label_bars`` labels at the current Axes size
       (crowding, headroom on autoscaled value axes;
       :func:`_settle_bar_labels`), redrawing when a limit moved. Each
       step starts again from matplotlib's autoscaled limits, so the
       headroom follows the final size without compounding.
    4. Re-anchors outside legends (past the bar values beyond that limit
       they would cover too) and lifts titles over legends above their
       axes (:func:`_settle_outside_legends`), redrawing after a move.
    5. Hides the bar labels a legend or other text covers where those are
       drawn now (:func:`_clear_bar_labels`).
    6. Measures the content overhang of every target axes and the room
       figure-level artists reserve.
    7. Hands those measurements to the pure :func:`_solve_edges`.

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
    if _settle_bar_labels(fig, renderer):
        fig.canvas.draw()
        renderer = get_renderer(fig)
    for _round in range(_SETTLE_ROUNDS):
        if not _settle_outside_legends(fig, renderer):
            break
        fig.canvas.draw()
        renderer = get_renderer(fig)
    _clear_bar_labels(fig, renderer)
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
