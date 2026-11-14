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

from .._figure_geometry import get_renderer, holders_shown, root_position
from ..units import Length
from ._content_extent import _axes_content_extent_px
from ._fit_labels import (
    _all_in,
    _on_grid,
    _root_gridspec,
    climb,
    grid_edges,
    put_back_edges,
    remember_layout,
    resolve_steps,
    restore_fitted,
)
from ._gutter import fit_gutter, parse_gutter
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
from ._subfigure_frames import (
    held_grids,
    place_subfigure_title,
    shown_subfigures,
    titles_above,
)
from ._subfigure_frames import holder_margins as _holder_margins
from ._subfigure_frames import holder_of as _holder_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import SubFigure

    from ._fit_labels import Edges


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
    fit_labels: bool | Iterable[str] | None = None,
    gutter: Length | str | float | None = None,
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
    fit_labels : bool | Iterable[str] | None, optional
        What the layout may do when text still collides once the margins
        fit, each step only where text overlaps by more than half a pixel:
        wrap an axis name that runs into another panel or past the figure
        edge, and with it the same name on the same axis of that grid
        (``"axis_labels"``), widen the space between panels nobody
        spaced (``"space"``), wrap crowded bottom tick labels at their
        spaces (``"wrap"``) and, when they cannot wrap, turn them 30, 45 or
        90 degrees (``"rotate"``). After each round the margins are fitted
        again, and a change that crushed a plot (left it under 30 % of its
        width or height) or gave any axis more overlapping neighbouring tick
        labels is taken back; the collision it tried to fix is left, and
        reported, and a figure whose every change was taken back draws
        exactly as without fitting. An axis whose ticks matplotlib picks and
        that a change made shorter keeps the ticks it had, while its labels
        stay half an em apart. Margins that do not settle (a legend wider
        than the canvas leaves) are not fitted further. Nothing is
        shortened, hidden or made smaller, and a figure without a collision
        draws exactly as without this. ``None`` (the default) reads
        :data:`dartwork_mpl.config.fit_labels` (itself ``True``: every
        step); ``False`` turns them off; step names (strings) allow only
        those. Only the Axes this call lays out are fitted
        (``use_all_axes=False`` keeps to ``gs``), and what they share with
        an Axes left out (a shared x formatter, their grid's spacing) is
        neither changed nor undone: they only turn their own labels. Tick
        labels you rotated or broke into
        lines (top labels included), axis names with line breaks or
        mathtext and spacing you set (``gridspec_kw``, ``add_gridspec``,
        ``fig.subplots_adjust``) are left alone, and each call first undoes
        what an earlier call fitted where it is still as set, and starts the
        margins where that call started them while they are as it left
        them: calling it again draws the same figure (a date axis whose
        ticks the first call thinned can still move on the second; the same
        from then on). The rules are in the docstring of
        ``dartwork_mpl.layout._fit_labels``.
    gutter : Length | str | float | None, optional
        The gap between the content of neighbouring panels: a
        :class:`Length` (``dm.pt(28)``, ``dm.mm(10)``), a unit string
        (``"28pt"``) or a number of points. The root GridSpec's ``wspace``
        and ``hspace`` are set, in every step, so that the narrowest gap
        between the content (tick labels, axis names, titles, colour bars,
        legends, ``dm.label_axes`` labels) of two panels facing each other
        across a column or row is this. Matplotlib gives every gap of a grid
        one width, so the closest pair sets it. It is fitted last, after the
        ``fit_labels`` steps (which may wrap an axis name that collides at
        the spacing the figure had), and replaces any spacing set before;
        the next call without it goes back to that spacing. Content that
        grows as the panels shrink (an axis name longer than its panel)
        stops the spacing at 1.5 cells, as ``space`` does. ``None``
        (default) leaves the spacing alone.
    verbose : bool, optional
        If ``True``, prints per-iteration GridSpec edges and the
        change since the previous iteration.

    Raises
    ------
    ValueError
        If any effective per-side margin resolves to a nonfinite figure
        fraction, after all margins have been parsed. Four finite side
        overrides can replace a nonfinite base margin. Existing parsing
        and GridSpec resolution errors take precedence. Also if
        ``fit_labels`` (or ``dm.config.fit_labels``) names an unknown
        step, before the figure is touched.
    TypeError
        If ``fit_labels`` is neither a bool, ``None`` nor step names, or
        names a step that is not a string (``bytes`` included).

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
    steps = resolve_steps(fit_labels)
    gutter_pt = parse_gutter(gutter)

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

    if gs is None and fig.subfigs:
        # Each grid is fitted in the box of the SubFigure that holds it.
        _fit_holders(
            fig,
            margins=margins,
            steps=steps,
            gutter_pt=gutter_pt,
            use_all_axes=use_all_axes,
            adopt_orphan_tick_font=adopt_orphan_tick_font,
            format_ticks=format_ticks,
            verbose=verbose,
        )
        return
    # A grid named by ``gs`` in a SubFigure is fitted in that SubFigure's box.
    holder = _holder_of(fig, actual_gs)
    if holder is not None:
        margins = _holder_margins(fig, holder, margins)

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
    # The Axes this call lays out, computed once: the margins measure them,
    # place_legend's legends are placed again on them, and the label ladder
    # fits and restores them. ``actual_gs`` (the root) is what the margins
    # are written into; for a nested ``gs`` that is not this set's GridSpec.
    # A SubFigure's grid is measured in its box, so "all Axes" are those it
    # holds itself: a sibling's, measured in this box's fractions, would
    # collapse the plot.
    scope = [
        ax
        for ax in fig.axes
        if (holder is None or ax.get_figure(root=False) is holder)
        and holders_shown(ax)  # a hidden SubFigure's Axes are not measured
        and (
            use_all_axes
            or (
                ax.get_gridspec() is not None and id(ax.get_gridspec()) == gs_id
            )
        )
    ]

    # Each call fits from the figure as the caller left it: what an earlier
    # layout fitted (wraps, rotations, spacing it set, the margins it left)
    # is undone first.
    restore_fitted(fig, scope)
    start = grid_edges(actual_gs)

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
    # The root's figure legends past its labels, then the titles the library
    # places above this grid, parents first, each SubFigure's figure legend
    # past its title.
    _place_title_and_legends(fig, fig)
    if holder is not None:
        for above in titles_above(holder):
            _place_title_and_legends(fig, above)

    _fit_grid(
        fig,
        actual_gs,
        scope=scope,
        margins=margins,
        steps=steps,
        gutter_pt=gutter_pt,
        start=start,
        adopt_orphan_tick_font=adopt_orphan_tick_font,
        format_ticks=format_ticks,
        verbose=verbose,
        holder=holder,
    )
    # The bar labels were settled in each step, so they are reported even
    # when nothing could be measured.
    _report_hidden_bar_labels(fig)


def _place_title_and_legends(fig: Figure, holder: Figure | SubFigure) -> None:
    """``holder``'s title under the text above it, then its figure legends past it.

    On one edge the title comes first, then the legend ``dm.figure_legend``
    placed there (:func:`dartwork_mpl.annotation.settle_figure_legends`),
    then the panels, which the reservations keep clear of both. The root
    figure's own title stays where it is; its legends move past it.
    """
    from ..annotation import settle_figure_legends

    place_subfigure_title(fig, holder)
    settle_figure_legends(fig, holder)


def _fit_holders(
    fig: Figure,
    *,
    margins: _Sides,
    steps: frozenset[str],
    gutter_pt: float | None,
    use_all_axes: bool,
    adopt_orphan_tick_font: bool,
    format_ticks: bool,
    verbose: bool,
) -> None:
    """Fit every grid of a figure with SubFigures in its holder's box.

    Each grid is fitted as :func:`simple_layout` fits a lone grid on the
    canvas (the margin fit, then the label ladder), in the box of the
    (Sub)Figure that holds it, parents first: a SubFigure title the library
    places goes under the figure-level text above it, and that text and the
    SubFigure's own reserve the box's edges. The scope of a grid is the
    Axes its holder holds (``use_all_axes``) or those on the grid.
    """
    grids = held_grids(fig)
    scopes = [
        [
            ax
            for ax in fig.axes
            if ax.get_figure(root=False) is holder
            and (use_all_axes or _root_gridspec(ax) is grid)
        ]
        for holder, grid in grids
    ]
    restore_fitted(fig, [ax for scope in scopes for ax in scope])
    starts = [grid_edges(grid) for _holder, grid in grids]
    if format_ticks:
        _format_ticks(fig)
    _show_twin_spines(fig)
    _color_twins(fig)
    # The root's figure legends past its labels, then every shown
    # SubFigure's title, parents before children, one that holds only nested
    # SubFigures too, each with its figure legends past it; then the grids.
    titled: list[Figure | SubFigure] = [fig, *shown_subfigures(fig)]
    for holder in titled:
        _place_title_and_legends(fig, holder)
    for (_holder, grid), scope, start in zip(
        grids, scopes, starts, strict=True
    ):
        sub = _holder_of(fig, grid)
        _fit_grid(
            fig,
            grid,
            scope=scope,
            margins=margins
            if sub is None
            else _holder_margins(fig, sub, margins),
            steps=steps,
            gutter_pt=gutter_pt,
            start=start,
            adopt_orphan_tick_font=adopt_orphan_tick_font,
            format_ticks=format_ticks,
            verbose=verbose,
            holder=sub,
        )
    _report_hidden_bar_labels(fig)


def _two_state_cycle(answers: Sequence[_GridEdges]) -> bool:
    """Whether the last four answers are A, B, A, B with A unlike B.

    The solver is deterministic, so a true cycle repeats its edges exactly;
    a slow approach (each answer a hair from the last) never does.
    """
    if len(answers) < 4:
        return False
    a, b, c, d = answers[-4:]
    return a == c and b == d and a != b


def _holds(wanted: _GridEdges, edges: _GridEdges) -> bool:
    """Whether a fit at ``edges`` asks for no more room than they give."""
    return (
        wanted.left <= edges.left
        and wanted.right >= edges.right
        and wanted.bottom <= edges.bottom
        and wanted.top >= edges.top
    )


def _apply_edges(fig: Figure, actual_gs: GridSpec, edges: _GridEdges) -> None:
    """Write ``edges`` into the grid and move its Axes there."""
    actual_gs.update(
        left=edges.left, right=edges.right, bottom=edges.bottom, top=edges.top
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
            and spec.get_topmost_subplotspec().get_gridspec() is actual_gs
        ):
            # Matplotlib accepts the local SubFigure here, though
            # its SubplotSpec stub only declares Figure.
            position = spec.get_position(ax.get_figure(root=False))  # type: ignore[arg-type]
            if ax.get_position(original=True).bounds != position.bounds:
                ax.set_subplotspec(spec)


def _inner_edges(a: _GridEdges, b: _GridEdges) -> _GridEdges:
    """The smaller of two grid boxes, edge by edge."""
    return _GridEdges(
        max(a.left, b.left),
        min(a.right, b.right),
        max(a.bottom, b.bottom),
        min(a.top, b.top),
    )


def _fit_grid(
    fig: Figure,
    actual_gs: GridSpec,
    *,
    scope: Sequence[Axes],
    margins: _Sides,
    steps: frozenset[str],
    gutter_pt: float | None,
    start: Edges,
    adopt_orphan_tick_font: bool,
    format_ticks: bool,
    verbose: bool,
    holder: SubFigure | None = None,
) -> None:
    """Fit one grid's margins, then climb the label ladder on ``scope``,
    then, with a ``gutter_pt``, fit the panel spacing and the margins again.

    ``margins`` are fractions of the box the grid is fitted in: the canvas,
    or the SubFigure ``holder`` that holds the grid (:func:`_fit_holders`).
    The gutter comes last: the ladder first wraps what collides at the
    spacing the figure has (an axis name longer than its panel), which a
    wider spacing would only make room for.
    """
    last: _GridEdges | None = None
    settled = False
    spacing: float | None = None

    def fit_margins() -> bool:
        """Fit the margins to the content now; ``False``: nothing to measure."""
        nonlocal last, settled
        step, last = _fit_margins(
            fig,
            actual_gs,
            margins=margins,
            scope=scope,
            gutter_pt=spacing,
            last_edges=last,
            adopt_orphan_tick_font=adopt_orphan_tick_font,
            format_ticks=format_ticks,
            verbose=verbose,
            holder=holder,
        )
        settled = step is not None and step.delta_px < _CONVERGE_TOL_PX
        return step is not None

    # Text that still collides at the fitted size climbs the ladder
    # (``_fit_labels.climb``): every change is followed by a fresh margin
    # fit and kept only if it crushed no plot and added no tick overlap.
    # Margins that did not settle (a legend wider than the canvas leaves
    # moves them on every fit) would move under each round, so no round
    # could be judged: such a figure is not fitted. When every change was
    # taken back, each after a margin fit that stopped a hair from where the
    # last one had, the margins are fitted once more from where this call
    # started, as without fitting.
    if (
        fit_margins()
        and settled
        and steps
        and climb(fig, steps, actual_gs, scope, fit_margins)
    ):
        put_back_edges(fig, actual_gs, start)
        last = None
        fit_margins()
    if gutter_pt is not None and _all_in(
        _on_grid(fig, actual_gs), {id(ax) for ax in scope}
    ):
        spacing = gutter_pt
        fit_margins()
    remember_layout(actual_gs, start)


def _fit_margins(
    fig: Figure,
    actual_gs: GridSpec,
    *,
    margins: _Sides,
    scope: Sequence[Axes],
    last_edges: _GridEdges | None,
    adopt_orphan_tick_font: bool,
    format_ticks: bool,
    verbose: bool,
    holder: SubFigure | None = None,
    gutter_pt: float | None = None,
) -> tuple[_LayoutStep | None, _GridEdges | None]:
    """Iterate layout steps until the GridSpec edges settle.

    ``scope`` is the Axes the call lays out (:func:`simple_layout`). Returns
    the last step (``None`` when the figure has no measurable Axes) and the
    edges written into ``actual_gs``, fractions of ``holder``'s box when the
    grid is a SubFigure's.
    """
    last = last_edges
    answers: list[_GridEdges] = []  # the solver's edges, in order
    step: _LayoutStep | None = None

    def solve(last_edges: _GridEdges | None) -> _LayoutStep | None:
        return _solve_layout_step(
            fig,
            margins=margins,
            scope=scope,
            grid=actual_gs,
            gutter_pt=gutter_pt,
            last_edges=last_edges,
            adopt_orphan_tick_font=adopt_orphan_tick_font,
            holder=holder,
        )

    for _ in range(2):
        for it in range(_MAX_ITER):
            step = solve(last)
            if step is None:
                break  # no measurable Axes: nothing to place
            new_edges = step.edges
            answers.append(new_edges)
            if step.delta_px >= _CONVERGE_TOL_PX and _two_state_cycle(answers):
                # The edges alternate between two fits (A, B, A, B): a tick
                # locator picks wider labels at one width than at the
                # other, which then fit (AutoLocator's 0.25 and 0.2 steps).
                # Try the inner of the two: kept when a fresh measure there
                # finds its content fits, else the fit goes on from there.
                inner = _inner_edges(answers[-1], answers[-2])
                _apply_edges(fig, actual_gs, inner)
                trial = solve(inner)
                if trial is not None and _holds(trial.edges, inner):
                    new_edges, step = inner, _LayoutStep(inner, 0.0)
                elif trial is not None:
                    new_edges, step = trial.edges, trial
                    answers.append(trial.edges)

            if verbose:
                print(
                    f"[simple_layout] iter {it + 1}: "
                    f"L={new_edges.left:.3f} R={new_edges.right:.3f} "
                    f"B={new_edges.bottom:.3f} T={new_edges.top:.3f}  "
                    f"Δ={step.delta_px:.2f}px"
                )

            _apply_edges(fig, actual_gs, new_edges)
            last = new_edges

            if step.delta_px < _CONVERGE_TOL_PX:
                break
        # Date ticks depend on the axis length only through their labels:
        # thin them at the fitted width, then fit once more if they moved.
        if step is None or not format_ticks:
            break
        from ..formatting import thin_crowded_date_ticks

        if not thin_crowded_date_ticks(fig):
            break
    return step, last


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


def _settle_panel_labels(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_axes``'s automatic labels from the panels as drawn now."""
    from ..annotation import settle_panel_labels

    return settle_panel_labels(fig, renderer)


def _place_grid(fig: Figure, gs: GridSpec) -> None:
    """Move the Axes of ``gs`` to where its spacing says now."""
    put_back_edges(fig, gs, grid_edges(gs))


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
    scope: Sequence[Axes],
    last_edges: _GridEdges | None,
    adopt_orphan_tick_font: bool,
    holder: SubFigure | None = None,
    grid: GridSpec | None = None,
    gutter_pt: float | None = None,
) -> _LayoutStep | None:
    """Measure the figure once and solve one iteration of ``simple_layout``.

    The grid is solved in the canvas, or in the box of the SubFigure
    ``holder`` that holds it: an Axes' position is a fraction of that box.
    ``scope`` is the Axes the call lays out (every Axes, or only the
    requested GridSpec's; :func:`simple_layout`). Returns the step, or
    ``None`` if the figure has no measurable axes (in which case the caller
    should bail out).

    Each step:

    1. Draws the canvas so artist bboxes are populated.
    2. Optionally adopts the axis-label font on orphan-label axes
       (so the measurement reflects the post-restyle ticks).
    3. Settles ``dm.label_bars`` labels at the current Axes size
       (crowding, headroom on autoscaled value axes;
       :func:`_settle_bar_labels`), redrawing when a limit moved. Each
       step starts again from matplotlib's autoscaled limits, so the
       headroom follows the final size without compounding.
    4. Places ``dm.place_legend``'s legends on ``scope`` again at the size
       they have now, re-anchors outside legends (past the bar values
       beyond that limit they would cover too) and lifts titles over
       legends above their axes (:func:`_settle_outside_legends`),
       redrawing after a move.
    5. Places ``dm.label_axes``'s automatic labels from the panels as
       drawn now (:func:`_settle_panel_labels`), then, with a ``gutter``,
       sets the spacing of ``grid`` so the content of facing panels is
       that far apart (:func:`~._gutter.fit_gutter`), redrawing after a
       move.
    6. Hides the bar labels a legend or other text covers where those are
       drawn now (:func:`_clear_bar_labels`).
    7. Measures the content overhang of every Axes in ``scope`` and the
       room figure-level artists reserve.
    8. Hands those measurements to the pure :func:`_solve_edges`.

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
        if not _settle_outside_legends(fig, renderer, scope):
            break
        fig.canvas.draw()
        renderer = get_renderer(fig)
    if _settle_panel_labels(fig, renderer):
        fig.canvas.draw()
        renderer = get_renderer(fig)
    spaced = 0.0
    if gutter_pt is not None and grid is not None:
        spaced = fit_gutter(fig, grid, scope, gutter_pt, renderer)
        if spaced > 0.0:
            _place_grid(fig, grid)
            fig.canvas.draw()
            renderer = get_renderer(fig)
            if _settle_panel_labels(fig, renderer):
                fig.canvas.draw()
                renderer = get_renderer(fig)
    _clear_bar_labels(fig, renderer)
    fbox = fig.bbox if holder is None else holder.bbox
    fw_px, fh_px = fbox.width, fbox.height
    # The canvas starts at 0; a SubFigure's box where it sits on it.
    ox, oy = (0.0, 0.0) if holder is None else (fbox.x0, fbox.y0)

    oh_l: list[float] = []
    oh_r: list[float] = []
    oh_b: list[float] = []
    oh_t: list[float] = []
    for ax in scope:
        ext = _axes_content_extent_px(ax, renderer, fig)
        if ext is None:
            continue
        x0, x1, y0, y1 = ext
        # On the canvas, an Axes a SubFigure holds is placed as a fraction of
        # the root figure, as the content is measured; in a SubFigure's box
        # every Axes is that SubFigure's own (the scope).
        pos = root_position(ax) if holder is None else ax.get_position()
        oh_l.append(pos.x0 - (x0 - ox) / fw_px)
        oh_r.append((x1 - ox) / fw_px - pos.x1)
        oh_b.append(pos.y0 - (y0 - oy) / fh_px)
        oh_t.append((y1 - oy) / fh_px - pos.y1)

    if not oh_l:  # no measurable axes
        return None

    # Reserve room for figure-level artists (suptitle / fig.legend /
    # fig.text) so the gridspec doesn't push axes content on top of them.
    reserved = _figure_artist_reservations(fig, renderer, fw_px, fh_px, holder)
    overhang = _Sides(
        left=max(oh_l), right=max(oh_r), bottom=max(oh_b), top=max(oh_t)
    )
    step = _solve_edges(overhang, reserved, margins, last_edges, fw_px, fh_px)
    if spaced > step.delta_px:
        # The panels moved apart or together: not settled yet.
        return _LayoutStep(step.edges, spaced)
    return step
